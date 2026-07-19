#!/usr/bin/env python3
"""Run a small smoke test for every P-IC3 artifact variant."""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


ARTIFACT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ARTIFACT_DIR / "configs" / "compare_single_p_907_resume.json"
DEFAULT_INPUT = ARTIFACT_DIR / "test" / "reset_counters.lus"
DEFAULT_OUTPUT = ARTIFACT_DIR / "quick_results"

RESULT_RE = re.compile(r"<(?P<tag>Success|Failure)> Property .*? is (?P<result>valid|invalid)")
SUMMARY_RE = re.compile(r"^\s*[^\n:]+:\s*(valid|invalid)\b", re.MULTILINE)
WINNER_RE = re.compile(r"is (?:valid|invalid) by (.*?) after [\d.]+s")


def load_variants(config_path):
    with config_path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    return {item["name"]: list(item.get("args", [])) for item in config["variants"]}


def kill_process_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def classify(log_text, returncode, hard_timed_out):
    match = RESULT_RE.search(log_text)
    if match:
        result = match.group("result")
    else:
        summary = SUMMARY_RE.search(log_text)
        result = summary.group(1) if summary else "unknown"

    winner = WINNER_RE.search(log_text)
    winner_name = winner.group(1) if winner else "-"
    environment_error = "Operation not permitted (src/ip_resolver.cpp" in log_text
    passed = returncode == 0 and result in {"valid", "invalid"} and not hard_timed_out
    return passed, result, winner_name, environment_error


def run_variant(binary, input_path, output_dir, name, variant_args, timeout_seconds, verbose):
    log_path = output_dir / (name + ".log")
    command = [
        str(binary),
        "--color", "false",
        "--timeout", str(timeout_seconds),
    ]
    if verbose:
        command.append("-vv")
    command.extend(variant_args)
    command.append(str(input_path))

    started = time.monotonic()
    hard_timed_out = False
    with log_path.open("w", encoding="utf-8") as log_handle:
        log_handle.write("COMMAND: " + " ".join(command) + "\n\n")
        log_handle.flush()
        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
        try:
            returncode = process.wait(timeout=timeout_seconds + 5)
        except subprocess.TimeoutExpired:
            hard_timed_out = True
            kill_process_group(process)
            returncode = 124
            log_handle.write("\nHARD TIMEOUT: process group terminated by quick_start.py\n")

    elapsed = time.monotonic() - started
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    passed, result, winner, environment_error = classify(
        log_text, returncode, hard_timed_out
    )
    return {
        "name": name,
        "passed": passed,
        "result": result,
        "winner": winner,
        "returncode": returncode,
        "elapsed": elapsed,
        "log": log_path,
        "environment_error": environment_error,
    }


def main():
    variants = load_variants(DEFAULT_CONFIG)
    parser = argparse.ArgumentParser(
        description="Smoke-test the five artifact variants on a small Lustre model."
    )
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--variant",
        action="append",
        choices=list(variants),
        help="run only this variant; repeat to select several (default: all)",
    )
    parser.add_argument("--timeout", type=int, default=20, help="seconds per variant")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verbose", action="store_true", help="pass -vv to Kind2")
    args = parser.parse_args()

    binary = ARTIFACT_DIR / "bin" / "kind2"
    input_path = args.input.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error("executable not found or not executable: %s" % binary)
    if not input_path.is_file():
        parser.error("input file not found: %s" % input_path)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = args.variant or list(variants)

    print("Input : %s" % input_path)
    print("Logs  : %s" % output_dir)
    print("%-12s %-6s %-8s %-5s %-8s %s" %
          ("variant", "status", "property", "exit", "seconds", "winner"))
    print("-" * 88)

    results = []
    for name in selected:
        result = run_variant(
            binary, input_path, output_dir, name, variants[name], args.timeout, args.verbose
        )
        results.append(result)
        print("%-12s %-6s %-8s %-5d %-8.2f %s" % (
            name,
            "PASS" if result["passed"] else "FAIL",
            result["result"],
            result["returncode"],
            result["elapsed"],
            result["winner"],
        ))
        if result["environment_error"]:
            print("  hint: local ZeroMQ IPC was denied; run outside a restricted sandbox")
        if not result["passed"]:
            print("  log: %s" % result["log"])

    failed = [item["name"] for item in results if not item["passed"]]
    if failed:
        print("\nSmoke test failed: %s" % ", ".join(failed))
        return 1
    print("\nAll selected variants passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
