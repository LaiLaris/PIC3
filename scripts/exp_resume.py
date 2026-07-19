#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import re
import resource
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


CURRENT_RUN_DIR = None


class ExperimentInterrupted(Exception):
    def __init__(self, run_dir):
        super().__init__(str(run_dir))
        self.run_dir = Path(run_dir)


PROPERTY_PATTERNS = {
    "safe": re.compile(r"<Success> Property .* is valid .*"),
    "unsafe": re.compile(r"<Failure> Property .* is invalid .*"),
    "error": re.compile(r"^\s*<Error>\s+", re.MULTILINE),
    "timeout": re.compile(r"^\s*<Timeout>\s+", re.MULTILINE),
}

METRIC_PATTERNS = {
    "winner": re.compile(
        r"<(?:Success|Failure)> Property .*? is (?:valid|invalid) by "
        r"property directed reachability \((QE(?: sorting clause (?:l1l2|l2l1))?)\)"
    ),
    "frame_sizes": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Frame sizes\s+:\s+(\d+(?:\s+\d+)*)"),
    "total_time": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Total time\s+:\s+([\d.]+)"),
    "k": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?k\s+:\s+([\d.]+)"),
    "solver": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Solver\s+:\s+(\d+(?:\s+\d+)*)"),
    "tree_size": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Tree size\s+:\s+(\d+)"),
    "reuse_num_base": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Reuse_num_base\s+:\s+(\d+)"),
    "reuse_num_pre": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Reuse_num_predessors\s+:\s+(\d+)"),
    "reuse_num_gen": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Reuse_num_gen\s+:\s+(\d+)"),
    "tree_time": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Tree time\s+:\s+([\d.]+)"),
    "filter_reuse": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Filtered reuse\s+:\s+([\d.]+)"),
    "gene_time": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Generalization time\s+:\s+([\d.]+)"),
    "smt_value_time": re.compile(r"Final statistics:[\s\S]*?\[SMT\][\s\S]*?get-value time\s+:\s+([\d.]+)"),
    "keep_literals": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Keep literals\s+:\s+([\d.]+)"),
    "forward_copy_gen_time": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Forward copy generation time\s+:\s+([\d.]+)"),
    "fwd_all": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Fwd all\s+:\s+([\d.]+)"),
    "fwd_new_all": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Fwd' all\s+:\s+([\d.]+)"),
    "fwd_new_yes": re.compile(r"Final statistics:[\s\S]*?\[IC3\][\s\S]*?Fwd' yes\s+:\s+([\d.]+)"),
}

WINNER_NAMES = {
    "QE": "IC3QE",
    "QE sorting clause l1l2": "IC3QEL1L2",
    "QE sorting clause l2l1": "IC3QEL2L1",
}


def strip_json_comments(text):
    result = []
    i = 0
    in_string = False
    string_quote = ""
    escape = False
    length = len(text)
    while i < length:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < length else ""
        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == string_quote:
                in_string = False
            i += 1
            continue
        if ch in ('"', "'"):
            in_string = True
            string_quote = ch
            result.append(ch)
            i += 1
            continue
        if ch == '/' and nxt == '/':
            i += 2
            while i < length and text[i] not in ('\n', '\r'):
                i += 1
            continue
        if ch == '/' and nxt == '*':
            i += 2
            while i + 1 < length and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2 if i + 1 < length else 0
            continue
        result.append(ch)
        i += 1
    return ''.join(result)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read()
    return json.loads(strip_json_comments(content))


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def slugify(text):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return cleaned or "variant"


def truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def derive_variant_name(variant, index):
    explicit_name = variant.get("name")
    if explicit_name:
        return explicit_name

    args = list(variant.get("args", []))
    if not args:
        return "base"

    parts = []
    used_positions = set()
    i = 0
    while i < len(args):
        arg = str(args[i])
        nxt = str(args[i + 1]) if i + 1 < len(args) else None
        if arg == "--ic3qe_refer_skipping" and nxt is not None:
            used_positions.update([i, i + 1])
            if truthy(nxt):
                parts.append("refer_skipping")
            i += 2
            continue
        if arg == "--ic3qe_branching" and nxt is not None:
            used_positions.update([i, i + 1])
            if truthy(nxt):
                parts.append("branching")
            i += 2
            continue
        if arg == "--ic3qe_intersection" and nxt is not None:
            used_positions.update([i, i + 1])
            enabled = truthy(nxt)
            limit = None
            if i + 3 < len(args) and str(args[i + 2]) == "--ic3qe_intersection_limit":
                used_positions.update([i + 2, i + 3])
                limit = str(args[i + 3])
                i += 4
            else:
                i += 2
            if enabled:
                parts.append("intersection_n%s" % (limit or "1"))
            continue
        i += 1

    leftovers = [slugify(str(args[pos])) for pos in range(len(args)) if pos not in used_positions]
    leftovers = [item for item in leftovers if item]
    if leftovers:
        parts.extend(leftovers)

    if not parts:
        parts.append("variant_%d" % index)
    return "__".join(parts)


def resolve_variants(config):
    resolved = []
    for index, variant in enumerate(config.get("variants", []), start=1):
        item = dict(variant)
        item["name"] = derive_variant_name(item, index)
        resolved.append(item)
    return resolved


def get_reuse_variants(config):
    reuse = dict(config.get("reuse_variants", {}))
    normalized = {}
    for variant_name, run_dir in reuse.items():
        normalized[str(variant_name)] = str(Path(run_dir).resolve())
    return normalized


def resolve_reused_variant_csv(variant_name, run_dir):
    return Path(run_dir).resolve() / "raw" / (variant_name + ".csv")


def resolve_reused_variant_log_dir(variant_name, run_dir):
    return Path(run_dir).resolve() / "logs" / variant_name


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def copy_reused_variant_logs(variant_name, source_run_dir, target_log_root):
    source_dir = resolve_reused_variant_log_dir(variant_name, source_run_dir)
    target_dir = Path(target_log_root) / variant_name
    if not source_dir.exists():
        print("[%s] reused logs directory not found: %s" % (variant_name, source_dir))
        return
    ensure_dir(target_dir.parent)
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)


def git_output(repo_path, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path)] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def extract_metrics(log_content, metrics):
    data = {}
    if PROPERTY_PATTERNS["timeout"].search(log_content):
        data["property_result"] = "Timeout"
    elif PROPERTY_PATTERNS["safe"].search(log_content):
        data["property_result"] = "Safe"
    elif PROPERTY_PATTERNS["unsafe"].search(log_content):
        data["property_result"] = "Unsafe"
    elif PROPERTY_PATTERNS["error"].search(log_content):
        data["property_result"] = "Error"
    else:
        data["property_result"] = "Unknown"

    for metric in metrics:
        pattern = METRIC_PATTERNS.get(metric)
        match = pattern.search(log_content) if pattern else None
        data[metric] = match.group(1) if match else ""
        if metric == "winner" and data[metric]:
            data[metric] = WINNER_NAMES.get(data[metric], data[metric])
    return data


def sanitize_relpath(value):
    cleaned = value.replace("\\", "/").lstrip("/")
    return cleaned


def proc_status_value_kb(pid, field):
    status_path = Path("/proc") / str(pid) / "status"
    try:
        with open(status_path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if line.startswith(field + ":"):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        return int(parts[1])
    except Exception:
        return 0
    return 0


def proc_ppid(pid):
    status_path = Path("/proc") / str(pid) / "status"
    try:
        with open(status_path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if line.startswith("PPid:"):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        return int(parts[1])
    except Exception:
        return 0
    return 0


def rss_memory_mb(pid):
    """Return aggregate RSS for a process and all currently visible descendants."""
    proc_root = Path("/proc")
    parent_by_pid = {}
    try:
        entries = list(proc_root.iterdir())
    except Exception:
        entries = []

    for entry in entries:
        if entry.name.isdigit():
            child_pid = int(entry.name)
            parent_by_pid[child_pid] = proc_ppid(child_pid)

    family = {pid}
    changed = True
    while changed:
        changed = False
        for child_pid, parent_pid in parent_by_pid.items():
            if child_pid not in family and parent_pid in family:
                family.add(child_pid)
                changed = True

    total_rss_kb = sum(proc_status_value_kb(member_pid, "VmRSS") for member_pid in family)
    return float(total_rss_kb) / 1024.0


def terminate_process_group(pgid, grace_seconds=0.5):
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    except PermissionError:
        return False

    time.sleep(grace_seconds)
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return True

    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return True


def current_process_family():
    family = {os.getpid()}
    pid = os.getpid()
    while pid > 1:
        status_path = Path("/proc") / str(pid) / "status"
        ppid = 0
        try:
            with open(status_path, "r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    if line.startswith("PPid:"):
                        ppid = int(line.split()[1])
                        break
        except Exception:
            break
        if ppid <= 0 or ppid in family:
            break
        family.add(ppid)
        pid = ppid
    return family


def proc_cmdline(pid):
    try:
        data = (Path("/proc") / str(pid) / "cmdline").read_bytes()
    except Exception:
        return []
    return [part.decode("utf-8", errors="ignore") for part in data.split(b"\0") if part]


def proc_exe(pid):
    try:
        return str((Path("/proc") / str(pid) / "exe").resolve())
    except Exception:
        return ""


def process_matches_binary(pid, binary_path):
    binary_path = str(Path(binary_path).resolve())
    exe_path = proc_exe(pid)
    if exe_path == binary_path:
        return True
    cmdline = proc_cmdline(pid)
    return bool(cmdline) and cmdline[0] == binary_path


def find_kind2_processes(binary_path):
    protected = current_process_family()
    matches = []
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in protected:
            continue
        if process_matches_binary(pid, binary_path):
            matches.append(pid)
    return sorted(set(matches))


def cleanup_kind2_processes(binary_path, label="cleanup"):
    pids = find_kind2_processes(binary_path)
    if not pids:
        print("[%s] no residual kind2 processes found" % label)
        return []

    groups = []
    for pid in pids:
        try:
            pgid = os.getpgid(pid)
        except ProcessLookupError:
            continue
        except PermissionError:
            continue
        groups.append(pgid)

    killed = []
    for pgid in sorted(set(groups)):
        if terminate_process_group(pgid):
            killed.append(pgid)

    time.sleep(0.2)
    remaining = find_kind2_processes(binary_path)
    print("[%s] cleaned residual kind2 process groups: %s" % (label, ", ".join(str(item) for item in killed) if killed else "none"))
    if remaining:
        print("[%s] residual kind2 processes still visible: %s" % (label, ", ".join(str(item) for item in remaining)))
    return remaining


def run_command(command, cwd, timeout_seconds):
    output = {"stdout": [], "stderr": []}
    timed_out = False
    max_memory_mb = 0.0
    start = time.time()
    usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)

    def reader(pipe, key):
        try:
            for line in pipe:
                output[key].append(line)
        finally:
            pipe.close()

    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )

    stdout_thread = threading.Thread(target=reader, args=(process.stdout, "stdout"))
    stderr_thread = threading.Thread(target=reader, args=(process.stderr, "stderr"))
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()

    try:
        while True:
            if process.poll() is not None:
                break
            max_memory_mb = max(max_memory_mb, rss_memory_mb(process.pid))
            if time.time() - start > timeout_seconds:
                timed_out = True
                terminate_process_group(process.pid, grace_seconds=0.2)
                break
            time.sleep(0.1)
    finally:
        if process.poll() is None:
            terminate_process_group(process.pid, grace_seconds=0.2)
        else:
            terminate_process_group(process.pid, grace_seconds=0.1)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

    elapsed = time.time() - start
    exit_code = process.poll()
    if exit_code is None:
        exit_code = -9 if timed_out else -1
    usage_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_time_s = (
        usage_end.ru_utime
        - usage_start.ru_utime
        + usage_end.ru_stime
        - usage_start.ru_stime
    )
    text = "".join(output["stdout"]) + "".join(output["stderr"])
    return {
        "output": text,
        "max_memory_mb": round(max_memory_mb, 2),
        "execution_time_s": round(elapsed, 2),
        "cpu_time_s": round(cpu_time_s, 2),
        "exit_code": exit_code,
        "timed_out": timed_out,
    }


def read_dataset_lines(path):
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def resolve_skip_path_file(config, config_path=None, override=None):
    configured = override if override is not None else config.get("run", {}).get("skip_path_file")
    if not configured:
        return None
    path = Path(configured).expanduser()
    if path.is_absolute():
        return path.resolve()
    if override is not None or config_path is None:
        return path.resolve()
    return (Path(config_path).resolve().parent / path).resolve()


def load_skip_benchmarks(path):
    if path is None:
        return set()
    if not path.exists():
        raise SystemExit("Skip path file not found: %s" % path)
    if not path.is_file():
        raise SystemExit("Skip path is not a regular file: %s" % path)
    return {sanitize_relpath(item) for item in read_dataset_lines(path)}


def csv_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_rows_if_exists(path):
    path = Path(path)
    if not path.exists():
        return []
    return csv_rows(path)


def safe_float(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except Exception:
        return None


def row_total_time(row):
    total_time = safe_float(row.get("total_time"))
    if total_time is not None:
        return total_time
    return safe_float(row.get("execution_time(s)"))


def sum_column(rows, column):
    values = [safe_float(row.get(column)) for row in rows]
    values = [value for value in values if value is not None]
    return sum(values) if values else None


def seconds_text(value):
    if value is None:
        return ""
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = value - hours * 3600 - minutes * 60
    if hours:
        return "%.2f s (%dh %02dm %05.2fs)" % (value, hours, minutes, seconds)
    if minutes:
        return "%.2f s (%dm %05.2fs)" % (value, minutes, seconds)
    return "%.2f s" % value


def write_csv_row(writer, handle, row):
    writer.writerow(row)
    handle.flush()


def geomean(values):
    positives = [value for value in values if value and value > 0]
    if not positives:
        return ""
    return math.exp(sum(math.log(value) for value in positives) / len(positives))


def median(values):
    numbers = sorted(value for value in values if value is not None)
    if not numbers:
        return ""
    mid = len(numbers) // 2
    if len(numbers) % 2:
        return numbers[mid]
    return (numbers[mid - 1] + numbers[mid]) / 2.0


def format_float(value):
    return "%.4f" % value if value is not None else ""


def build_safe_unsafe_report_lines(variant_rows, variants, baseline):
    baseline_rows = {
        row.get("filename"): row
        for row in variant_rows.get(baseline, [])
        if row.get("filename")
    }
    if not baseline_rows:
        return []

    report_lines = []
    report_lines.append("## Safe/Unsafe Summary vs Base")
    report_lines.append("")
    header = [
        "baseline_result_group",
        "variant",
        "variant_group_samples",
        "variant_kind2_total_time_s",
        "baseline_group_samples",
        "common_solved_count_vs_base",
        "common_variant_total_time_s_vs_base",
        "common_base_total_time_s_vs_base",
        "common_total_time_ratio_vs_base",
        "variant_median_total_time_s",
        "variant_geomean_total_time_s",
        "wins_vs_base",
        "losses_vs_base",
        "regressed_vs_base",
        "geomean_speedup_vs_base",
    ]
    report_lines.append("| " + " | ".join(header) + " |")
    report_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for result_group in ("Safe", "Unsafe"):
        baseline_group_rows = [
            row for row in baseline_rows.values()
            if row.get("property_result") == result_group
        ]
        baseline_group_times = [row_total_time(row) for row in baseline_group_rows]
        baseline_group_total_time = sum(value for value in baseline_group_times if value is not None)
        baseline_group_median = median(baseline_group_times)
        baseline_group_geomean = geomean(baseline_group_times)

        for variant in variants:
            variant_name = variant["name"]
            rows = variant_rows.get(variant_name, [])
            rows_by_filename = {
                row.get("filename"): row
                for row in rows
                if row.get("filename")
            }
            variant_group_rows = [
                row for row in rows
                if row.get("property_result") == result_group
            ]
            variant_group_times = [row_total_time(row) for row in variant_group_rows]
            variant_group_total_time = sum(value for value in variant_group_times if value is not None)
            variant_group_median = median(variant_group_times)
            variant_group_geomean = geomean(variant_group_times)

            common_pairs = []
            for filename, base_row in baseline_rows.items():
                variant_row = rows_by_filename.get(filename, {})
                if base_row.get("property_result") != result_group:
                    continue
                if variant_row.get("property_result") != result_group:
                    continue
                base_time = row_total_time(base_row)
                variant_time = row_total_time(variant_row)
                if base_time is not None and variant_time is not None:
                    common_pairs.append((base_time, variant_time))

            common_base_total_time = sum(base_time for base_time, _ in common_pairs)
            common_variant_total_time = sum(variant_time for _, variant_time in common_pairs)
            common_total_time_ratio = None
            if common_base_total_time:
                common_total_time_ratio = common_variant_total_time / common_base_total_time

            wins = ""
            losses = ""
            regressed = ""
            speedup_geomean = ""
            if variant_name != baseline:
                wins_count = 0
                losses_count = 0
                speedups = []
                for base_time, variant_time in common_pairs:
                    if base_time and variant_time:
                        speedups.append(base_time / variant_time)
                    if abs(variant_time - base_time) <= 1e-9:
                        continue
                    if variant_time < base_time:
                        wins_count += 1
                    else:
                        losses_count += 1
                wins = str(wins_count)
                losses = str(losses_count)
                regressed = str(len(baseline_group_rows) - len(common_pairs))
                speedup_geomean_value = geomean(speedups)
                speedup_geomean = format_float(speedup_geomean_value) if speedup_geomean_value != "" else ""

            row = [
                result_group,
                variant_name,
                str(len(variant_group_rows)),
                format_float(variant_group_total_time),
                str(len(baseline_group_rows)),
                str(len(common_pairs)),
                format_float(common_variant_total_time),
                format_float(common_base_total_time),
                format_float(common_total_time_ratio),
                format_float(variant_group_median) if variant_group_median != "" else "",
                format_float(variant_group_geomean) if variant_group_geomean != "" else "",
                wins,
                losses,
                regressed,
                speedup_geomean,
            ]
            report_lines.append("| " + " | ".join(row) + " |")

    non_baseline_variants = [variant["name"] for variant in variants if variant["name"] != baseline]
    if non_baseline_variants:
        report_lines.append("")
        report_lines.append("### Result Changes vs Base")
        report_lines.append("")
        for index, variant_name in enumerate(non_baseline_variants):
            if len(non_baseline_variants) > 1:
                report_lines.append("#### %s" % variant_name)
                report_lines.append("")
            rows_by_filename = {
                row.get("filename"): row
                for row in variant_rows.get(variant_name, [])
                if row.get("filename")
            }
            changes = {}
            for filename, base_row in baseline_rows.items():
                variant_row = rows_by_filename.get(filename, {})
                base_result = base_row.get("property_result", "")
                variant_result = variant_row.get("property_result", "")
                changes[(base_result, variant_result)] = changes.get((base_result, variant_result), 0) + 1

            report_lines.append("| base result | variant result | count |")
            report_lines.append("| --- | --- | --- |")
            for base_result, variant_result in sorted(changes):
                report_lines.append("| %s | %s | %s |" % (
                    base_result or "",
                    variant_result or "",
                    changes[(base_result, variant_result)],
                ))
            if index != len(non_baseline_variants) - 1:
                report_lines.append("")

    return report_lines


def discover_binary_info(config):
    binary_path = Path(config["binary"]["path"]).resolve()
    repo_path = Path(config["binary"].get("repo", binary_path.parent)).resolve()
    return {
        "path": str(binary_path),
        "repo": str(repo_path),
        "exists": binary_path.exists(),
        "git_commit": git_output(repo_path, "rev-parse", "HEAD"),
        "git_short_commit": git_output(repo_path, "rev-parse", "--short", "HEAD"),
        "git_branch": git_output(repo_path, "rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(git_output(repo_path, "status", "--short")),
    }


def apply_binary_override(config, binary_path):
    if not binary_path:
        return config

    resolved_path = Path(binary_path).expanduser().resolve()
    if resolved_path.exists() and resolved_path.is_file() and not os.access(str(resolved_path), os.X_OK):
        resolved_path.chmod(resolved_path.stat().st_mode | 0o111)
    config.setdefault("binary", {})
    config["binary"]["path"] = str(resolved_path)
    return config


def snapshot_binary(binary_info, run_dir):
    source_path = Path(binary_info["path"]).resolve()
    snapshot_dir = Path(run_dir) / "bin"
    ensure_dir(snapshot_dir)
    snapshot_path = snapshot_dir / source_path.name
    if snapshot_path.exists():
        try:
            snapshot_path.chmod(snapshot_path.stat().st_mode | 0o600)
        except Exception:
            pass
        snapshot_path.unlink()
    shutil.copy2(source_path, snapshot_path)
    snapshot_path.chmod(snapshot_path.stat().st_mode | 0o111)

    snapshot_info = dict(binary_info)
    snapshot_info["source_path"] = str(source_path)
    snapshot_info["path"] = str(snapshot_path.resolve())
    snapshot_info["snapshot"] = True
    snapshot_info["snapshot_created_at"] = datetime.now().isoformat(timespec="seconds")
    return snapshot_info


def resolve_run_binary_info(binary_info, run_dir, reuse_existing=False):
    manifest_path = Path(run_dir) / "manifest.json"
    if reuse_existing and manifest_path.exists():
        try:
            previous_binary = load_json(manifest_path).get("binary", {})
            previous_path = previous_binary.get("path")
            if previous_path and Path(previous_path).exists():
                return previous_binary
        except Exception:
            pass
    return snapshot_binary(binary_info, run_dir)


def validate_config(config, config_path=None):
    errors = []
    warnings = []

    binary_info = discover_binary_info(config)
    binary_path = Path(binary_info["path"])
    dataset_file = Path(config["dataset"]["path_file"]).resolve()
    dataset_root = Path(config["dataset"]["root"]).resolve()
    metrics = list(config.get("run", {}).get("metrics", []))
    variants = resolve_variants(config)
    baseline = config.get("baseline")
    config_stem = Path(config_path).resolve().stem if config_path else None
    skip_path_file = resolve_skip_path_file(config, config_path=config_path)
    skip_entries = []

    if not binary_info["exists"]:
        errors.append("binary not found: %s" % binary_path)
    elif not binary_path.is_file():
        errors.append("binary path is not a file: %s" % binary_path)
    elif not os.access(str(binary_path), os.X_OK):
        errors.append("binary is not executable: %s" % binary_path)

    if not dataset_file.exists():
        errors.append("dataset path file not found: %s" % dataset_file)
        dataset_entries = []
    elif not dataset_file.is_file():
        errors.append("dataset path file is not a regular file: %s" % dataset_file)
        dataset_entries = []
    else:
        dataset_entries = read_dataset_lines(dataset_file)
        if not dataset_entries:
            errors.append("dataset path file is empty: %s" % dataset_file)

    if skip_path_file is not None:
        if not skip_path_file.exists():
            errors.append("skip path file not found: %s" % skip_path_file)
        elif not skip_path_file.is_file():
            errors.append("skip path is not a regular file: %s" % skip_path_file)
        else:
            skip_entries = read_dataset_lines(skip_path_file)

    if not dataset_root.exists():
        errors.append("dataset root not found: %s" % dataset_root)
    elif not dataset_root.is_dir():
        errors.append("dataset root is not a directory: %s" % dataset_root)

    missing_inputs = []
    duplicate_inputs = []
    seen = set()
    for rel_path in dataset_entries:
        if rel_path in seen:
            duplicate_inputs.append(rel_path)
        else:
            seen.add(rel_path)
        candidate = (dataset_root / sanitize_relpath(rel_path)).resolve()
        if not candidate.exists():
            missing_inputs.append(rel_path)

    if missing_inputs:
        errors.append("missing benchmark files: %d" % len(missing_inputs))
    if duplicate_inputs:
        warnings.append("duplicate benchmark entries: %d" % len(duplicate_inputs))

    unknown_metrics = [metric for metric in metrics if metric not in METRIC_PATTERNS]
    if unknown_metrics:
        errors.append("unknown metrics in config: %s" % ", ".join(unknown_metrics))

    if not variants:
        errors.append("no variants configured")

    variant_names = []
    for variant in variants:
        name = variant.get("name", "")
        if not name:
            errors.append("variant with empty name detected")
            continue
        variant_names.append(name)
        if not isinstance(variant.get("args", []), list):
            errors.append("variant args must be a list: %s" % name)

    if len(set(variant_names)) != len(variant_names):
        errors.append("variant names must be unique")

    if baseline and baseline not in variant_names:
        errors.append("baseline '%s' not found in variants" % baseline)

    config_name = config.get("name", "")
    if config_stem and config_name and config_name != config_stem:
        warnings.append("config name differs from filename stem: name=%s, file=%s" % (config_name, config_stem))
    if not config_name:
        warnings.append("config name is omitted; filename stem will be used for the run id")

    timeout_seconds = config.get("run", {}).get("timeout_seconds", 0)
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        errors.append("timeout_seconds must be a positive integer")

    reuse_variants = get_reuse_variants(config)
    for variant_name, run_dir in reuse_variants.items():
        if variant_name not in variant_names:
            errors.append("reuse_variants references unknown variant: %s" % variant_name)
            continue
        csv_path = resolve_reused_variant_csv(variant_name, run_dir)
        if not csv_path.exists():
            errors.append("reused variant csv not found: %s" % csv_path)
        log_dir = resolve_reused_variant_log_dir(variant_name, run_dir)
        if not log_dir.exists():
            warnings.append("reused variant logs directory not found: %s" % log_dir)

    print("Validation summary")
    print("- Binary: %s" % binary_path)
    print("- Binary exists: %s" % ("yes" if binary_info["exists"] else "no"))
    print("- Dataset path file: %s" % dataset_file)
    print("- Dataset root: %s" % dataset_root)
    print("- Dataset entries: %d" % len(dataset_entries))
    print("- Skip path file: %s" % (skip_path_file or "<none>"))
    print("- Skip entries: %d" % len(skip_entries))
    print("- Variants: %d" % len(variants))
    print("- Baseline: %s" % (baseline or "<first variant>"))
    print("- Git commit: %s" % (binary_info["git_short_commit"] or "unknown"))

    if missing_inputs:
        preview = missing_inputs[:10]
        print("- Missing benchmark examples (%d shown of %d):" % (len(preview), len(missing_inputs)))
        for item in preview:
            print("  %s" % item)

    if duplicate_inputs:
        preview = duplicate_inputs[:10]
        print("- Duplicate benchmark examples (%d shown of %d):" % (len(preview), len(duplicate_inputs)))
        for item in preview:
            print("  %s" % item)

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print("- %s" % warning)

    if errors:
        print("Errors:")
        for error in errors:
            print("- %s" % error)
        return 1

    print("Validation passed")
    return 0


def build_run_id(name, config_path=None):
    config_stem = Path(config_path).resolve().stem if config_path else ""
    run_name = config_stem or name or "run"
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + run_name


def resolve_run_dir(run_root, run_dir_or_id):
    candidate = Path(run_dir_or_id).expanduser()
    if candidate.is_absolute() or len(candidate.parts) > 1:
        return candidate.resolve()
    return (Path(run_root) / candidate).resolve()


def update_manifest_run_status(run_dir, run_start, status, timestamp_key, **fields):
    manifest_path = Path(run_dir) / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = load_json(manifest_path)
    session_elapsed = round(time.time() - run_start, 2)
    manifest["status"] = status
    manifest[timestamp_key] = datetime.now().isoformat(timespec="seconds")
    manifest["last_session_wall_time_s"] = session_elapsed
    manifest["elapsed_wall_time_s"] = round(float(manifest.get("previous_elapsed_wall_time_s", 0.0)) + session_elapsed, 2)
    manifest.update(fields)
    manifest.pop("previous_elapsed_wall_time_s", None)
    write_json(manifest_path, manifest)


def update_manifest_progress(run_dir, run_start, **fields):
    manifest_path = Path(run_dir) / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = load_json(manifest_path)
    session_elapsed = round(time.time() - run_start, 2)
    previous_elapsed = safe_float(manifest.get("previous_elapsed_wall_time_s")) or 0.0
    manifest["status"] = "running"
    manifest["last_session_wall_time_s"] = session_elapsed
    manifest["elapsed_wall_time_s"] = round(previous_elapsed + session_elapsed, 2)
    manifest.update(fields)
    write_json(manifest_path, manifest)


def refresh_partial_report(run_dir, run_start, **progress_fields):
    update_manifest_progress(
        run_dir,
        run_start,
        last_partial_report_at=datetime.now().isoformat(timespec="seconds"),
        **progress_fields,
    )
    build_comparison(run_dir)
    build_report(run_dir)


def variant_command(config, variant, absolute_lus_path):
    common_args = list(config["run"].get("common_args", []))
    variant_args = list(variant.get("args", []))
    return [config["binary"]["path"]] + common_args + variant_args + [str(absolute_lus_path)]


def should_cleanup_kind2_between_variants(config):
    run_config = config.get("run", {})
    return truthy(run_config.get("cleanup_kind2_between_variants", True))


def select_variant(config, variant_name=None):
    variants = resolve_variants(config)
    if not variants:
        raise SystemExit("No variants configured")
    if variant_name:
        for variant in variants:
            if variant["name"] == variant_name:
                return variant
        available = ", ".join(variant["name"] for variant in variants)
        raise SystemExit("Unknown variant '%s'. Available variants: %s" % (variant_name, available))

    baseline = config.get("baseline")
    if baseline:
        for variant in variants:
            if variant["name"] == baseline:
                return variant
    return variants[0]


def select_variants(config, variant_name=None):
    variants = resolve_variants(config)
    if not variants:
        raise SystemExit("No variants configured")
    if variant_name:
        return [select_variant(config, variant_name=variant_name)]
    return variants


def resolve_benchmark_path(dataset_root, benchmark):
    benchmark_path = Path(benchmark)
    if benchmark_path.is_absolute():
        resolved = benchmark_path.resolve()
        try:
            rel_path = str(resolved.relative_to(dataset_root)).replace(os.sep, "/")
        except ValueError:
            rel_path = benchmark
        return rel_path, resolved

    rel_clean = sanitize_relpath(benchmark)
    return rel_clean, (dataset_root / rel_clean).resolve()


def run_sample(config, config_path, benchmark, variant_name=None):
    binary_info = discover_binary_info(config)
    if not binary_info["exists"]:
        raise SystemExit("Binary not found: %s" % binary_info["path"])

    sample_root = Path(__file__).resolve().parents[1] / "runs" / "_sample"
    run_config = json.loads(json.dumps(config))
    run_binary_info = snapshot_binary(binary_info, sample_root)
    run_config["binary"]["path"] = run_binary_info["path"]
    dataset_root = Path(config["dataset"]["root"]).resolve()
    timeout_seconds = int(config["run"].get("timeout_seconds", 300))
    metrics = list(config["run"].get("metrics", []))
    variants = select_variants(run_config, variant_name=variant_name)
    rel_path, input_path = resolve_benchmark_path(dataset_root, benchmark)

    if not input_path.exists():
        raise SystemExit("Benchmark not found: %s" % input_path)
    if not input_path.is_file():
        raise SystemExit("Benchmark path is not a file: %s" % input_path)

    print("Sample run")
    print("- Config: %s" % Path(config_path).resolve())
    print("- Binary snapshot: %s" % run_binary_info["path"])
    print("- Binary source: %s" % run_binary_info["source_path"])
    if variant_name:
        print("- Variant: %s" % variants[0]["name"])
    else:
        print("- Variants: %d" % len(variants))
    print("- Benchmark: %s" % rel_path)
    print("- Input path: %s" % input_path)
    print("- Working directory: %s" % dataset_root)
    print("")

    cleanup_between_variants = should_cleanup_kind2_between_variants(run_config)
    for index, variant in enumerate(variants, start=1):
        command = variant_command(run_config, variant, input_path)
        sample_log_dir = sample_root / variant["name"] / os.path.dirname(sanitize_relpath(rel_path))
        ensure_dir(sample_log_dir)
        log_path = sample_log_dir / (Path(rel_path).stem + ".log")

        print("[%d/%d] Variant: %s" % (index, len(variants), variant["name"]))
        print("- Log path: %s" % log_path)
        print("- Command: %s" % " ".join(shlex.quote(part) for part in command))

        if cleanup_between_variants:
            cleanup_kind2_processes(run_config["binary"]["path"], label="%s pre-run" % variant["name"])
        try:
            result = run_command(command, cwd=dataset_root, timeout_seconds=timeout_seconds)
            with open(log_path, "w", encoding="utf-8", errors="ignore") as log_handle:
                log_handle.write(result["output"])
            parsed = extract_metrics(result["output"], metrics)

            print("- Property result: %s" % parsed["property_result"])
            for metric in metrics:
                print("- %s: %s" % (metric, parsed.get(metric, "")))
            print("- Max memory (MB): %.2f" % result["max_memory_mb"])
            print("- Execution time (s): %.2f" % result["execution_time_s"])
            print("- CPU time (s): %.2f" % result["cpu_time_s"])
            print("- Exit code: %s" % result["exit_code"])
            print("- Timed out: %s" % ("true" if result["timed_out"] else "false"))
            print("")
        finally:
            if cleanup_between_variants:
                cleanup_kind2_processes(run_config["binary"]["path"], label="%s post-run" % variant["name"])
    return 0


def run_matrix(
    config,
    config_path,
    run_id=None,
    skip_existing=False,
    resume_run=None,
    report_every=0,
    skip_path_file=None,
):
    global CURRENT_RUN_DIR
    binary_info = discover_binary_info(config)
    if not binary_info["exists"]:
        raise SystemExit("Binary not found: %s" % binary_info["path"])

    dataset_file = Path(config["dataset"]["path_file"]).resolve()
    dataset_root = Path(config["dataset"]["root"]).resolve()
    metrics = list(config["run"]["metrics"])
    timeout_seconds = int(config["run"].get("timeout_seconds", 300))
    run_root = Path(__file__).resolve().parents[1] / "runs"
    resuming = resume_run is not None
    previous_manifest = None
    if resuming:
        run_dir = resolve_run_dir(run_root, resume_run)
        if not (run_dir / "manifest.json").exists():
            raise SystemExit("Cannot resume; manifest not found: %s" % (run_dir / "manifest.json"))
        previous_manifest = load_json(run_dir / "manifest.json")
        run_id = previous_manifest.get("run_id", run_dir.name)
        skip_existing = True
    else:
        run_id = run_id or build_run_id(config.get("name", ""), config_path=config_path)
        run_dir = run_root / run_id
        if run_dir.exists():
            raise SystemExit(
                "Run directory already exists: %s\n"
                "Use --resume %s to continue it, or choose a different --run-id."
                % (run_dir, run_id)
            )
    raw_dir = run_dir / "raw"
    CURRENT_RUN_DIR = run_dir.resolve()
    log_dir = run_dir / "logs"
    compare_dir = run_dir / "compare"
    ensure_dir(raw_dir)
    ensure_dir(log_dir)
    ensure_dir(compare_dir)
    run_config = json.loads(json.dumps(config))
    run_binary_info = resolve_run_binary_info(binary_info, run_dir, reuse_existing=resuming or skip_existing)
    run_config["binary"]["path"] = run_binary_info["path"]
    cleanup_between_variants = should_cleanup_kind2_between_variants(run_config)
    if resuming and cleanup_between_variants:
        cleanup_kind2_processes(run_config["binary"]["path"], label="resume pre-run")

    dataset_entries = read_dataset_lines(dataset_file)
    resolved_skip_path_file = resolve_skip_path_file(
        run_config,
        config_path=config_path,
        override=skip_path_file,
    )
    if resolved_skip_path_file is None and previous_manifest:
        previous_skip = previous_manifest.get("skip_benchmarks", {}).get("path_file")
        if previous_skip:
            resolved_skip_path_file = Path(previous_skip).resolve()
    skip_benchmarks = load_skip_benchmarks(resolved_skip_path_file)
    matched_skip_benchmarks = {
        rel_path for rel_path in dataset_entries if sanitize_relpath(rel_path) in skip_benchmarks
    }
    if resolved_skip_path_file is not None:
        print(
            "Skip benchmarks: %d/%d dataset entries matched from %s"
            % (len(matched_skip_benchmarks), len(dataset_entries), resolved_skip_path_file)
        )
    run_start = time.time()
    now = datetime.now().isoformat(timespec="seconds")
    resolved_config_path = Path(config_path).resolve()
    config_label = resolved_config_path.stem
    reuse_variants = get_reuse_variants(config)
    manifest = {
        "run_id": run_id,
        "created_at": now,
        "started_at": now,
        "config_label": config_label,
        "config_path": str(resolved_config_path),
        "binary": run_binary_info,
        "dataset": {
            "path_file": str(dataset_file),
            "root": str(dataset_root),
            "size": len(dataset_entries),
        },
        "skip_benchmarks": {
            "path_file": str(resolved_skip_path_file) if resolved_skip_path_file else "",
            "configured_count": len(skip_benchmarks),
            "matched_count": len(matched_skip_benchmarks),
        },
        "baseline": config.get("baseline"),
        "run": run_config["run"],
        "cleanup_kind2_between_variants": cleanup_between_variants,
        "variants": resolve_variants(run_config),
        "reuse_variants": reuse_variants,
        "status": "running",
    }
    if resuming:
        manifest["created_at"] = previous_manifest.get("created_at", now)
        manifest["started_at"] = previous_manifest.get("started_at", now)
        manifest["resumed_at"] = now
        manifest["resume_count"] = int(previous_manifest.get("resume_count", 0)) + 1
        manifest["previous_elapsed_wall_time_s"] = safe_float(previous_manifest.get("elapsed_wall_time_s")) or 0.0
        if previous_manifest.get("last_session_wall_time_s") is not None:
            manifest["last_session_wall_time_s"] = previous_manifest.get("last_session_wall_time_s")
    for key in ("interrupted_at", "finished_at"):
        manifest.pop(key, None)
    write_json(run_dir / "manifest.json", manifest)
    if not resuming:
        snapshot_suffix = resolved_config_path.suffix or ".json"
        with open(run_dir / ("config_snapshot" + snapshot_suffix), "w", encoding="utf-8") as handle:
            handle.write(read_text(resolved_config_path))

    header = ["filename", "property_result"] + metrics + [
        "max_memory(MB)",
        "execution_time(s)",
        "cpu_time(s)",
        "exit_code",
        "timed_out",
        "variant",
    ]

    completed_since_report = 0
    for variant in resolve_variants(run_config):
        variant_name = variant["name"]
        variant_csv = raw_dir / (variant_name + ".csv")
        reuse_run_dir = reuse_variants.get(variant_name)
        if reuse_run_dir:
            source_csv = resolve_reused_variant_csv(variant_name, reuse_run_dir)
            print("[%s] reusing existing csv: %s" % (variant_name, source_csv))
            with open(source_csv, "r", encoding="utf-8", newline="") as src_handle:
                rows = list(csv.DictReader(src_handle))
            with open(variant_csv, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                handle.flush()
                for row in rows:
                    normalized = {field: row.get(field, "") for field in header}
                    normalized["variant"] = variant_name
                    write_csv_row(writer, handle, normalized)
            copy_reused_variant_logs(variant_name, reuse_run_dir, log_dir)
            continue
        existing = {}
        if skip_existing and variant_csv.exists():
            for row in csv_rows(variant_csv):
                filename = row.get("filename")
                if filename:
                    existing[filename] = row
            if existing:
                print("[%s] resume/skip existing rows: %d/%d" % (variant_name, len(existing), len(dataset_entries)))
        if cleanup_between_variants:
            cleanup_kind2_processes(run_config["binary"]["path"], label="%s pre-run" % variant_name)
        try:
            with open(variant_csv, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                handle.flush()
                for index, rel_path in enumerate(dataset_entries, start=1):
                    if rel_path in existing:
                        normalized = {field: existing[rel_path].get(field, "") for field in header}
                        normalized["variant"] = variant_name
                        write_csv_row(writer, handle, normalized)
                        continue

                    rel_clean = sanitize_relpath(rel_path)
                    if rel_clean in skip_benchmarks:
                        print("[%s][%d/%d] skipped: %s" % (variant_name, index, len(dataset_entries), rel_path))
                        row = dict.fromkeys(header, "")
                        row["filename"] = rel_path
                        row["property_result"] = "Timeout"
                        row["timed_out"] = "true"
                        row["variant"] = variant_name
                        write_csv_row(writer, handle, row)
                        continue
                    input_path = (dataset_root / rel_clean).resolve()
                    if not input_path.exists():
                        row = dict.fromkeys(header, "")
                        row["filename"] = rel_path
                        row["property_result"] = "MissingInput"
                        row["variant"] = variant_name
                        write_csv_row(writer, handle, row)
                        completed_since_report += 1
                        if report_every and completed_since_report >= report_every:
                            refresh_partial_report(
                                run_dir,
                                run_start,
                                current_variant=variant_name,
                                current_index=index,
                                current_total=len(dataset_entries),
                                last_completed_benchmark=rel_path,
                            )
                            print("[%s] partial report updated after %d new cases: %s" % (variant_name, completed_since_report, run_dir / "report.md"))
                            completed_since_report = 0
                        continue

                    variant_log_dir = log_dir / variant_name / os.path.dirname(rel_clean)
                    ensure_dir(variant_log_dir)
                    log_path = variant_log_dir / (Path(rel_clean).stem + ".log")
                    command = variant_command(run_config, variant, input_path)
                    print("[%s][%d/%d] %s" % (variant_name, index, len(dataset_entries), rel_path))
                    try:
                        result = run_command(command, cwd=dataset_root, timeout_seconds=timeout_seconds)
                    finally:
                        if cleanup_between_variants:
                            cleanup_kind2_processes(
                                run_config["binary"]["path"],
                                label="%s benchmark post-run: %s" % (variant_name, rel_path),
                            )
                    with open(log_path, "w", encoding="utf-8", errors="ignore") as log_handle:
                        log_handle.write(result["output"])

                    parsed = extract_metrics(result["output"], metrics)
                    row = {
                        "filename": rel_path,
                        "property_result": "Timeout" if result["timed_out"] else parsed["property_result"],
                        "max_memory(MB)": "%.2f" % result["max_memory_mb"],
                        "execution_time(s)": "%.2f" % result["execution_time_s"],
                        "cpu_time(s)": "%.2f" % result["cpu_time_s"],
                        "exit_code": str(result["exit_code"]),
                        "timed_out": "true" if result["timed_out"] else "false",
                        "variant": variant_name,
                    }
                    for metric in metrics:
                        row[metric] = parsed.get(metric, "")
                    write_csv_row(writer, handle, row)
                    completed_since_report += 1
                    if report_every and completed_since_report >= report_every:
                        refresh_partial_report(
                            run_dir,
                            run_start,
                            current_variant=variant_name,
                            current_index=index,
                            current_total=len(dataset_entries),
                            last_completed_benchmark=rel_path,
                        )
                        print("[%s] partial report updated after %d new cases: %s" % (variant_name, completed_since_report, run_dir / "report.md"))
                        completed_since_report = 0
        finally:
            if cleanup_between_variants:
                cleanup_kind2_processes(run_config["binary"]["path"], label="%s post-run" % variant_name)

    final_progress = {}
    variants = resolve_variants(run_config)
    if variants:
        final_progress["current_variant"] = variants[-1]["name"]
    final_progress["current_index"] = len(dataset_entries)
    final_progress["current_total"] = len(dataset_entries)
    if dataset_entries:
        final_progress["last_completed_benchmark"] = dataset_entries[-1]
    update_manifest_run_status(run_dir, run_start, "finished", "finished_at", **final_progress)

    build_comparison(run_dir)
    build_report(run_dir)
    return run_dir


def build_comparison(run_dir):
    run_dir = Path(run_dir).resolve()
    manifest = load_json(run_dir / "manifest.json")
    raw_dir = run_dir / "raw"
    compare_dir = run_dir / "compare"
    ensure_dir(compare_dir)
    metrics = list(manifest["run"]["metrics"])
    variants = [variant["name"] for variant in manifest["variants"]]
    baseline = manifest.get("baseline") or variants[0]
    config_label = Path(manifest.get("config_path", "")).stem or manifest["run_id"]

    variant_rows = {}
    all_filenames = []
    seen = set()
    for variant in variants:
        rows = csv_rows_if_exists(raw_dir / (variant + ".csv"))
        keyed = {row["filename"]: row for row in rows}
        variant_rows[variant] = keyed
        for row in rows:
            filename = row["filename"]
            if filename not in seen:
                seen.add(filename)
                all_filenames.append(filename)

    aligned_header = ["run_id", "config_label", "baseline_variant", "filename"]
    per_variant_fields = ["property_result"] + metrics + ["max_memory(MB)", "execution_time(s)", "cpu_time(s)", "exit_code", "timed_out"]
    for variant in variants:
        for field in per_variant_fields:
            aligned_header.append("%s__%s" % (variant, field))

    with open(compare_dir / "aligned.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=aligned_header)
        writer.writeheader()
        for filename in all_filenames:
            row = {
                "run_id": manifest["run_id"],
                "config_label": config_label,
                "baseline_variant": baseline,
                "filename": filename,
            }
            for variant in variants:
                data = variant_rows[variant].get(filename, {})
                for field in per_variant_fields:
                    row["%s__%s" % (variant, field)] = data.get(field, "")
            writer.writerow(row)

    summary_rows = []
    baseline_rows = variant_rows.get(baseline, {})
    pairwise_header = [
        "run_id",
        "config_label",
        "baseline_variant",
        "variant",
        "filename",
        "base_property_result",
        "variant_property_result",
        "base_total_time_s",
        "variant_total_time_s",
        "time_ratio_variant_over_base",
        "delta_total_time_s",
        "comparison",
    ]
    with open(compare_dir / "pairwise_vs_base.csv", "w", encoding="utf-8", newline="") as handle:
        pairwise_writer = csv.DictWriter(handle, fieldnames=pairwise_header)
        pairwise_writer.writeheader()

        for variant in variants:
            rows = list(variant_rows[variant].values())
            times = [row_total_time(row) for row in rows]
            solved_rows = [row for row in rows if row["property_result"] in ("Safe", "Unsafe")]
            solved_times = [row_total_time(row) for row in solved_rows]
            execution_total_time = sum_column(rows, "execution_time(s)")
            cpu_total_time = sum_column(rows, "cpu_time(s)")
            kind2_total_time = sum_column(rows, "total_time")

            common_solved_count = 0
            common_solved_total_time = None
            common_base_total_time = None
            if variant == baseline:
                common_solved_values = [value for value in solved_times if value is not None]
                common_solved_count = len(common_solved_values)
                if common_solved_values:
                    common_solved_total_time = sum(common_solved_values)
            else:
                common_variant_values = []
                common_base_values = []
                for filename in all_filenames:
                    base_row = baseline_rows.get(filename, {})
                    var_row = variant_rows[variant].get(filename, {})
                    if base_row.get("property_result") in ("Safe", "Unsafe") and var_row.get("property_result") in ("Safe", "Unsafe"):
                        base_time = row_total_time(base_row)
                        var_time = row_total_time(var_row)
                        if base_time is not None and var_time is not None:
                            common_base_values.append(base_time)
                            common_variant_values.append(var_time)
                common_solved_count = len(common_variant_values)
                if common_variant_values:
                    common_solved_total_time = sum(common_variant_values)
                    common_base_total_time = sum(common_base_values)

            common_total_time_ratio = None
            if common_solved_total_time is not None and common_base_total_time not in (None, 0):
                common_total_time_ratio = common_solved_total_time / common_base_total_time

            summary = {
                "run_id": manifest["run_id"],
                "config_label": config_label,
                "baseline_variant": baseline,
                "variant": variant,
                "samples": str(len(rows)),
                "safe": str(sum(1 for row in rows if row["property_result"] == "Safe")),
                "unsafe": str(sum(1 for row in rows if row["property_result"] == "Unsafe")),
                "unknown": str(sum(1 for row in rows if row["property_result"] == "Unknown")),
                "timed_out": str(sum(1 for row in rows if row["timed_out"] == "true")),
                "missing_input": str(sum(1 for row in rows if row["property_result"] == "MissingInput")),
                "execution_total_time_s": "%.4f" % execution_total_time if execution_total_time is not None else "",
                "cpu_total_time_s": "%.4f" % cpu_total_time if cpu_total_time is not None else "",
                "kind2_total_time_s": "%.4f" % kind2_total_time if kind2_total_time is not None else "",
                "common_solved_count_vs_%s" % baseline: str(common_solved_count) if common_solved_count else "0",
                "common_solved_total_time_s_vs_%s" % baseline: "%.4f" % common_solved_total_time if common_solved_total_time is not None else "",
                "common_base_total_time_s_vs_%s" % baseline: "%.4f" % common_base_total_time if common_base_total_time is not None else ("%.4f" % common_solved_total_time if variant == baseline and common_solved_total_time is not None else ""),
                "common_total_time_ratio_vs_%s" % baseline: "%.4f" % common_total_time_ratio if common_total_time_ratio is not None else "",
                "median_total_time_s": "%.4f" % median([value for value in times if value is not None]) if any(value is not None for value in times) else "",
                "geomean_total_time_s": "%.4f" % geomean([value for value in solved_times if value is not None]) if solved_times else "",
                "wins_vs_%s" % baseline: "",
                "ties_vs_%s" % baseline: "",
                "losses_vs_%s" % baseline: "",
                "geomean_speedup_vs_%s" % baseline: "",
                "newly_solved_vs_%s" % baseline: "",
                "regressed_vs_%s" % baseline: "",
            }

            wins = 0
            ties = 0
            losses = 0
            speedups = []
            newly_solved = 0
            regressed = 0

            for filename in all_filenames:
                base_row = baseline_rows.get(filename, {})
                var_row = variant_rows[variant].get(filename, {})
                base_result = base_row.get("property_result", "")
                var_result = var_row.get("property_result", "")
                base_time = row_total_time(base_row)
                var_time = row_total_time(var_row)

                comparison = ""
                ratio = ""
                delta = ""

                if variant == baseline:
                    comparison = "baseline"
                elif base_result in ("Safe", "Unsafe") and var_result in ("Safe", "Unsafe") and base_time and var_time:
                    ratio_value = var_time / base_time if base_time else None
                    delta_value = var_time - base_time
                    ratio = "%.6f" % ratio_value
                    delta = "%.6f" % delta_value
                    speedups.append(base_time / var_time)
                    if abs(var_time - base_time) <= 1e-9:
                        ties += 1
                        comparison = "tie"
                    elif var_time < base_time:
                        wins += 1
                        comparison = "win"
                    else:
                        losses += 1
                        comparison = "loss"
                elif base_result not in ("Safe", "Unsafe") and var_result in ("Safe", "Unsafe"):
                    newly_solved += 1
                    comparison = "newly_solved"
                elif base_result in ("Safe", "Unsafe") and var_result not in ("Safe", "Unsafe"):
                    regressed += 1
                    comparison = "regressed"
                else:
                    comparison = "unsolved_both"

                pairwise_writer.writerow(
                    {
                        "run_id": manifest["run_id"],
                        "config_label": config_label,
                        "baseline_variant": baseline,
                        "variant": variant,
                        "filename": filename,
                        "base_property_result": base_result,
                        "variant_property_result": var_result,
                        "base_total_time_s": "" if base_time is None else "%.6f" % base_time,
                        "variant_total_time_s": "" if var_time is None else "%.6f" % var_time,
                        "time_ratio_variant_over_base": ratio,
                        "delta_total_time_s": delta,
                        "comparison": comparison,
                    }
                )

            if variant != baseline:
                summary["wins_vs_%s" % baseline] = str(wins)
                summary["ties_vs_%s" % baseline] = str(ties)
                summary["losses_vs_%s" % baseline] = str(losses)
                summary["newly_solved_vs_%s" % baseline] = str(newly_solved)
                summary["regressed_vs_%s" % baseline] = str(regressed)
                summary["geomean_speedup_vs_%s" % baseline] = "%.4f" % geomean(speedups) if speedups else ""

            summary_rows.append(summary)

    summary_header = list(summary_rows[0].keys()) if summary_rows else ["variant"]
    with open(compare_dir / "summary.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_header)
        writer.writeheader()
        writer.writerows(summary_rows)


def build_report(run_dir):
    run_dir = Path(run_dir).resolve()
    manifest = load_json(run_dir / "manifest.json")
    summary_rows = csv_rows_if_exists(run_dir / "compare" / "summary.csv")
    pairwise_rows = csv_rows_if_exists(run_dir / "compare" / "pairwise_vs_base.csv")
    baseline = manifest.get("baseline") or manifest["variants"][0]["name"]
    metrics = manifest["run"]["metrics"]
    variant_rows = {
        variant["name"]: csv_rows_if_exists(run_dir / "raw" / (variant["name"] + ".csv"))
        for variant in manifest["variants"]
    }
    report_lines = []
    report_lines.append("# OrderIC3 Experiment Report")
    report_lines.append("")
    report_lines.append("- Run ID: `%s`" % manifest["run_id"])
    report_lines.append("- Config Label: `%s`" % manifest.get("config_label", Path(manifest.get("config_path", "")).stem))
    report_lines.append("- Config Path: `%s`" % manifest.get("config_path", ""))
    report_lines.append("- Created At: `%s`" % manifest["created_at"])
    report_lines.append("- Binary: `%s`" % manifest["binary"]["path"])
    if manifest["binary"].get("source_path"):
        report_lines.append("- Binary Source: `%s`" % manifest["binary"]["source_path"])
    if manifest["binary"].get("snapshot_created_at"):
        report_lines.append("- Binary Snapshot Created At: `%s`" % manifest["binary"]["snapshot_created_at"])
    report_lines.append("- Commit: `%s`" % (manifest["binary"]["git_short_commit"] or "unknown"))
    report_lines.append("- Dataset List: `%s`" % manifest["dataset"]["path_file"])
    report_lines.append("- Dataset Root: `%s`" % manifest["dataset"]["root"])
    report_lines.append("- Samples: `%s`" % manifest["dataset"]["size"])
    skip_info = manifest.get("skip_benchmarks", {})
    if skip_info.get("path_file"):
        report_lines.append("- Skip List: `%s`" % skip_info["path_file"])
        report_lines.append("- Skipped Dataset Entries: `%s`" % skip_info.get("matched_count", 0))
    if manifest.get("status"):
        report_lines.append("- Status: `%s`" % manifest["status"])
    if manifest.get("resumed_at"):
        report_lines.append("- Last Resumed At: `%s`" % manifest["resumed_at"])
    if manifest.get("resume_count") is not None:
        report_lines.append("- Resume Count: `%s`" % manifest["resume_count"])
    if manifest.get("interrupted_at"):
        report_lines.append("- Interrupted At: `%s`" % manifest["interrupted_at"])
    if manifest.get("finished_at"):
        report_lines.append("- Finished At: `%s`" % manifest["finished_at"])
    if manifest.get("last_partial_report_at"):
        report_lines.append("- Last Partial Report At: `%s`" % manifest["last_partial_report_at"])
    if manifest.get("current_variant"):
        progress = manifest.get("current_variant", "")
        if manifest.get("current_index") is not None and manifest.get("current_total") is not None:
            progress += " %s/%s" % (manifest.get("current_index"), manifest.get("current_total"))
        report_lines.append("- Current Progress: `%s`" % progress)
    if manifest.get("last_completed_benchmark"):
        report_lines.append("- Last Completed Benchmark: `%s`" % manifest["last_completed_benchmark"])
    if manifest.get("elapsed_wall_time_s") is not None:
        report_lines.append("- Batch Wall Time: `%s`" % seconds_text(float(manifest["elapsed_wall_time_s"])))
    if manifest.get("wall_time_source"):
        report_lines.append("- Batch Wall Time Source: `%s`" % manifest["wall_time_source"])
    if manifest.get("last_session_wall_time_s") is not None:
        report_lines.append("- Last Session Wall Time: `%s`" % seconds_text(float(manifest["last_session_wall_time_s"])))
    execution_totals = [safe_float(row.get("execution_total_time_s")) for row in summary_rows]
    execution_totals = [value for value in execution_totals if value is not None]
    cpu_totals = [safe_float(row.get("cpu_total_time_s")) for row in summary_rows]
    cpu_totals = [value for value in cpu_totals if value is not None]
    kind2_totals = [safe_float(row.get("kind2_total_time_s")) for row in summary_rows]
    kind2_totals = [value for value in kind2_totals if value is not None]
    if execution_totals:
        report_lines.append("- Strategy Execution Time Sum: `%s`" % seconds_text(sum(execution_totals)))
    if cpu_totals:
        report_lines.append("- Strategy CPU Time Sum: `%s`" % seconds_text(sum(cpu_totals)))
    if kind2_totals:
        report_lines.append("- Strategy Kind2 Total Time Sum: `%s`" % seconds_text(sum(kind2_totals)))
    report_lines.append("- Baseline: `%s`" % baseline)
    report_lines.append("- Metrics: `%s`" % ", ".join(metrics))
    if manifest.get("reuse_variants"):
        report_lines.append("- Reused Variants: `%s`" % ", ".join("%s <- %s" % (k, v) for k, v in sorted(manifest["reuse_variants"].items())))
    report_lines.append("")
    report_lines.append("## Variant Summary")
    report_lines.append("")

    summary_header = [
        "variant",
        "safe",
        "unsafe",
        "unknown",
        "timed_out",
        "execution_total_time_s",
        "cpu_total_time_s",
        "kind2_total_time_s",
        "common_solved_count_vs_%s" % baseline,
        "common_solved_total_time_s_vs_%s" % baseline,
        "common_base_total_time_s_vs_%s" % baseline,
        "common_total_time_ratio_vs_%s" % baseline,
        "median_total_time_s",
        "geomean_total_time_s",
        "wins_vs_%s" % baseline,
        "losses_vs_%s" % baseline,
        "newly_solved_vs_%s" % baseline,
        "regressed_vs_%s" % baseline,
        "geomean_speedup_vs_%s" % baseline,
    ]
    report_lines.append("| " + " | ".join(summary_header) + " |")
    report_lines.append("| " + " | ".join(["---"] * len(summary_header)) + " |")
    for row in summary_rows:
        report_lines.append("| " + " | ".join(row.get(column, "") for column in summary_header) + " |")

    safe_unsafe_lines = build_safe_unsafe_report_lines(variant_rows, manifest["variants"], baseline)
    if safe_unsafe_lines:
        report_lines.append("")
        report_lines.extend(safe_unsafe_lines)

    report_lines.append("")
    report_lines.append("## Unknown Cases")
    report_lines.append("")
    for variant in manifest["variants"]:
        unknown_rows = [row for row in variant_rows[variant["name"]] if row.get("property_result") == "Unknown"]
        report_lines.append("### %s" % variant["name"])
        report_lines.append("")
        if not unknown_rows:
            report_lines.append("None")
            report_lines.append("")
            continue
        for row in unknown_rows:
            report_lines.append("- `%s` | timed_out=%s | time=%s | exit_code=%s" % (
                row.get("filename", ""),
                row.get("timed_out", ""),
                row.get("total_time", row.get("execution_time(s)", "")),
                row.get("exit_code", ""),
            ))
        report_lines.append("")

    report_lines.append("## Large Time Deltas vs Base")
    report_lines.append("")
    report_lines.append("Threshold: `10.0s` absolute delta on the common solved set.")
    report_lines.append("")
    threshold_s = 10.0
    for variant in manifest["variants"]:
        variant_name = variant["name"]
        report_lines.append("### %s" % variant_name)
        report_lines.append("")
        if variant_name == baseline:
            report_lines.append("Baseline")
            report_lines.append("")
            continue
        faster_rows = []
        slower_rows = []
        for row in pairwise_rows:
            if row.get("variant") != variant_name:
                continue
            if row.get("comparison") not in ("win", "loss"):
                continue
            try:
                delta = float(row.get("delta_total_time_s", ""))
                base_time = float(row.get("base_total_time_s", ""))
                variant_time = float(row.get("variant_total_time_s", ""))
            except ValueError:
                continue
            if abs(delta) < threshold_s:
                continue
            entry = {
                "filename": row.get("filename", ""),
                "base_result": row.get("base_property_result", ""),
                "variant_result": row.get("variant_property_result", ""),
                "delta": delta,
                "base_time": base_time,
                "variant_time": variant_time,
            }
            if delta <= -threshold_s:
                faster_rows.append(entry)
            elif delta >= threshold_s:
                slower_rows.append(entry)
        faster_rows.sort(key=lambda item: item["delta"])
        slower_rows.sort(key=lambda item: item["delta"], reverse=True)
        report_lines.append("Faster by at least 10s:")
        if not faster_rows:
            report_lines.append("- None")
        else:
            for item in faster_rows:
                if item["base_result"] == item["variant_result"]:
                    result_text = "result=%s" % item["base_result"]
                else:
                    result_text = "base_result=%s | variant_result=%s" % (item["base_result"], item["variant_result"])
                report_lines.append("- `%s` | %s | delta=%+.4fs | base=%0.4fs | variant=%0.4fs" % (
                    item["filename"],
                    result_text,
                    item["delta"],
                    item["base_time"],
                    item["variant_time"],
                ))
        report_lines.append("")
        report_lines.append("Slower by at least 10s:")
        if not slower_rows:
            report_lines.append("- None")
        else:
            for item in slower_rows:
                if item["base_result"] == item["variant_result"]:
                    result_text = "result=%s" % item["base_result"]
                else:
                    result_text = "base_result=%s | variant_result=%s" % (item["base_result"], item["variant_result"])
                report_lines.append("- `%s` | %s | delta=%+.4fs | base=%0.4fs | variant=%0.4fs" % (
                    item["filename"],
                    result_text,
                    item["delta"],
                    item["base_time"],
                    item["variant_time"],
                ))
        report_lines.append("")

    report_lines.append("## Artifacts")
    report_lines.append("")
    report_lines.append("- Config snapshot: `config_snapshot.json` or `config_snapshot.jsonc`")
    report_lines.append("- Raw per-variant CSVs: `raw/`")
    report_lines.append("- Aligned comparison table: `compare/aligned.csv`")
    report_lines.append("- Pairwise baseline comparison: `compare/pairwise_vs_base.csv`")
    report_lines.append("- Summary table: `compare/summary.csv`")
    report_lines.append("- Logs by variant: `logs/`")
    report_lines.append("- Binary snapshot: `bin/`")
    report_lines.append("")
    report_lines.append("## Variant Commands")
    report_lines.append("")
    for variant in manifest["variants"]:
        args = list(manifest["run"].get("common_args", [])) + list(variant.get("args", []))
        report_lines.append("- `%s`: `%s %s <lus-file>`" % (
            variant["name"],
            manifest["binary"]["path"],
            " ".join(shlex.quote(arg) for arg in args),
        ))

    with open(run_dir / "report.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(report_lines))
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Standalone OrderIC3 experiment automation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate binary and dataset paths before a full run")
    validate_parser.add_argument("config", help="Path to the experiment JSON config")
    validate_parser.add_argument("--binary", help="Override binary.path from the config")

    sample_parser = subparsers.add_parser("sample", help="Run one benchmark from a config before a full matrix run")
    sample_parser.add_argument("config", help="Path to the experiment JSON config")
    sample_parser.add_argument("benchmark", help="Benchmark path relative to dataset.root or an absolute .lus path")
    sample_parser.add_argument("--variant", help="Variant name to run; defaults to baseline or the first variant")
    sample_parser.add_argument("--binary", help="Override binary.path from the config")

    run_parser = subparsers.add_parser("run", help="Run a configured experiment matrix and build reports")
    run_parser.add_argument("config", help="Path to the experiment JSON config")
    run_parser.add_argument(
        "--run-id",
        help="Name for a new directory under runs/; fails if it already exists",
    )
    run_parser.add_argument("--skip-existing", action="store_true", help="Reuse rows already present in raw CSVs")
    run_parser.add_argument(
        "--resume",
        help="Resume an existing run directory or run id; implies --skip-existing",
    )
    run_parser.add_argument(
        "--skip-path-file",
        help="Path file listing benchmarks that must not be executed; overrides run.skip_path_file",
    )
    run_parser.add_argument("--report-every", type=int, default=0, help="Refresh compare/ and report.md after this many newly completed benchmarks; 0 disables periodic reports")
    run_parser.add_argument("--binary", help="Override binary.path from the config")

    compare_parser = subparsers.add_parser("compare", help="Rebuild aligned and summary CSVs for an existing run")
    compare_parser.add_argument("run_dir", help="Path to an existing run directory")

    report_parser = subparsers.add_parser("report", help="Rebuild the Markdown report for an existing run")
    report_parser.add_argument("run_dir", help="Path to an existing run directory")

    args = parser.parse_args()

    if args.command == "validate":
        config = load_json(args.config)
        apply_binary_override(config, args.binary)
        return validate_config(config, config_path=args.config)
    if args.command == "sample":
        config = load_json(args.config)
        apply_binary_override(config, args.binary)
        return run_sample(config, args.config, args.benchmark, variant_name=args.variant)
    if args.command == "run":
        config = load_json(args.config)
        apply_binary_override(config, args.binary)
        if args.report_every < 0:
            raise SystemExit("--report-every must be >= 0")
        try:
            run_dir = run_matrix(
                config,
                args.config,
                run_id=args.run_id,
                skip_existing=args.skip_existing,
                resume_run=args.resume,
                report_every=args.report_every,
                skip_path_file=args.skip_path_file,
            )
            print("Run completed: %s" % run_dir)
            return 0
        except KeyboardInterrupt:
            run_root = Path(__file__).resolve().parents[1] / "runs"
            if CURRENT_RUN_DIR:
                run_dir = CURRENT_RUN_DIR
            elif args.resume:
                run_dir = resolve_run_dir(run_root, args.resume)
            elif args.run_id:
                run_dir = resolve_run_dir(run_root, args.run_id)
            else:
                run_dir = None
            if run_dir and (run_dir / "manifest.json").exists():
                print("\nInterrupted. Partial run preserved: %s" % run_dir)
                try:
                    cleanup_kind2_processes(config["binary"]["path"], label="interrupt cleanup")
                    manifest = load_json(run_dir / "manifest.json")
                    previous_elapsed = safe_float(manifest.get("previous_elapsed_wall_time_s")) or 0.0
                    session_elapsed = 0.0
                    if manifest.get("resumed_at"):
                        try:
                            session_start = datetime.fromisoformat(manifest["resumed_at"])
                            session_elapsed = max(0.0, (datetime.now() - session_start).total_seconds())
                        except Exception:
                            session_elapsed = 0.0
                    manifest["status"] = "interrupted"
                    manifest["interrupted_at"] = datetime.now().isoformat(timespec="seconds")
                    manifest["last_session_wall_time_s"] = round(session_elapsed, 2)
                    manifest["elapsed_wall_time_s"] = round(previous_elapsed + session_elapsed, 2)
                    manifest.pop("previous_elapsed_wall_time_s", None)
                    write_json(run_dir / "manifest.json", manifest)
                    build_comparison(run_dir)
                    build_report(run_dir)
                    print("Partial report rebuilt: %s" % (run_dir / "report.md"))
                except Exception as exc:
                    print("Partial report rebuild failed: %s" % exc)
            raise SystemExit(130)
    if args.command == "compare":
        build_comparison(args.run_dir)
        print("Comparison rebuilt: %s" % args.run_dir)
        return 0
    if args.command == "report":
        build_report(args.run_dir)
        print("Report rebuilt: %s" % args.run_dir)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
