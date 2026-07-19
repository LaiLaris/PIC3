#!/usr/bin/env python3
"""Summarize singleton IC3 runs and an optional actual three-lane P-IC3 run."""

import argparse
import csv
import math
import statistics
from pathlib import Path


SINGLETONS = ["base", "fwd_l1l2", "bwd_l2l1"]
PORTFOLIOS = [
    ("base+fwd_l1l2", ["base", "fwd_l1l2"]),
    ("base+bwd_l2l1", ["base", "bwd_l2l1"]),
    ("fwd_l1l2+bwd_l2l1", ["fwd_l1l2", "bwd_l2l1"]),
    ("base+fwd_l1l2+bwd_l2l1", SINGLETONS),
]
SOLVED = {"Safe", "Unsafe"}


def number(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    by_file = {}
    for row in rows:
        filename = row.get("filename", "")
        if not filename:
            raise ValueError("missing filename in %s" % path)
        if filename in by_file:
            raise ValueError("duplicate filename %s in %s" % (filename, path))
        by_file[filename] = row
    return by_file


def load_singletons(run_dir):
    return {name: load_csv(run_dir / "raw" / (name + ".csv")) for name in SINGLETONS}


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def fmt(value):
    return "" if value is None else "%.6f" % value


def row_time(row):
    return number(row.get("execution_time(s)"))


def classified_result(row):
    """Normalize legacy CSVs that recorded timeouts and failures as Unknown/Error."""
    result = row.get("property_result", "")
    if result in SOLVED:
        return result
    if row.get("timed_out", "").lower() == "true":
        return "Timeout"
    if result in {"Error", "MissingInput"}:
        return result
    if row.get("exit_code", "") not in {"", "0", "40"}:
        return "Error"
    return "Unknown"


def summarize(name, rows, mode):
    values = list(rows.values())
    memory = [x for x in (number(row.get("max_memory(MB)")) for row in values) if x is not None]
    wall = [x for x in (row_time(row) for row in values) if x is not None]
    cpu = [x for x in (number(row.get("cpu_time(s)")) for row in values) if x is not None]
    kind2 = [x for x in (number(row.get("total_time")) for row in values) if x is not None]
    counts = {result: sum(classified_result(row) == result for row in values)
              for result in ("Safe", "Unsafe", "Timeout", "Error", "MissingInput", "Unknown")}
    return {
        "mode": mode,
        "variant": name,
        "samples": len(values),
        "solved": counts["Safe"] + counts["Unsafe"],
        "safe": counts["Safe"],
        "unsafe": counts["Unsafe"],
        "timeout": counts["Timeout"],
        "error": counts["Error"],
        "missing_input": counts["MissingInput"],
        "unknown": counts["Unknown"],
        "wall_total_s": fmt(sum(wall)),
        "cpu_total_s": fmt(sum(cpu)),
        "kind2_total_s": fmt(sum(kind2)),
        "peak_aggregate_rss_mean_mb": fmt(statistics.mean(memory) if memory else None),
        "peak_aggregate_rss_median_mb": fmt(statistics.median(memory) if memory else None),
        "peak_aggregate_rss_p95_mb": fmt(percentile(memory, 0.95)),
        "peak_aggregate_rss_max_mb": fmt(max(memory) if memory else None),
    }


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def reconstruct(singletons, filenames):
    detail = []
    summary = []
    for portfolio, members in PORTFOLIOS:
        wins = {member: 0 for member in members}
        solved_count = 0
        wall_total = 0.0
        for filename in filenames:
            candidates = []
            fallback = []
            for member in members:
                row = singletons[member][filename]
                elapsed = row_time(row)
                if elapsed is not None:
                    fallback.append(elapsed)
                result = classified_result(row)
                if result in SOLVED and elapsed is not None:
                    candidates.append((elapsed, member, result))
            if candidates:
                elapsed, winner, result = min(candidates, key=lambda item: (item[0], item[1]))
                solved_count += 1
                wins[winner] += 1
            else:
                elapsed = max(fallback) if fallback else None
                member_results = [classified_result(singletons[member][filename]) for member in members]
                if "Timeout" in member_results:
                    result = "Timeout"
                elif "Error" in member_results:
                    result = "Error"
                elif member_results and all(value == "MissingInput" for value in member_results):
                    result = "MissingInput"
                else:
                    result = "Unknown"
                winner = ""
            if elapsed is not None:
                wall_total += elapsed
            detail.append({
                "portfolio": portfolio,
                "filename": filename,
                "winner": winner,
                "result": result,
                "simulated_wall_s": fmt(elapsed),
                "note": "reconstructed_min_of_complete_singleton_runs",
            })
        item = {"portfolio": portfolio, "samples": len(filenames),
                "solved": solved_count, "simulated_wall_total_s": fmt(wall_total)}
        for singleton in SINGLETONS:
            item["wins_" + singleton] = wins.get(singleton, 0)
        summary.append(item)
    return detail, summary


def singleton_complementarity(singletons, filenames):
    solved_sets = {
        name: {filename for filename in filenames if classified_result(singletons[name][filename]) in SOLVED}
        for name in SINGLETONS
    }
    rows = []
    for name in SINGLETONS:
        other_union = set().union(*(solved_sets[other] for other in SINGLETONS if other != name))
        rows.append({
            "variant": name,
            "solved": len(solved_sets[name]),
            "exclusive_solves": len(solved_sets[name] - other_union),
            "additional_solves_over_other_union": len(solved_sets[name] - other_union),
        })
    return rows, set().union(*solved_sets.values())


def actual_first_finish(actual):
    counts = {name: 0 for name in ("IC3QE", "IC3QEL1L2", "IC3QEL2L1")}
    solved_count = 0
    for row in actual.values():
        if classified_result(row) not in SOLVED:
            continue
        solved_count += 1
        winner = row.get("winner", "")
        counts[winner] = counts.get(winner, 0) + 1
    return [{
        "winner": winner,
        "first_finishes": count,
        "share_of_solved": fmt(count / solved_count if solved_count else None),
    } for winner, count in counts.items()]


def resolve_actual_csv(run_dir, variant_name=None):
    raw_dir = run_dir / "raw"
    if variant_name:
        path = raw_dir / (variant_name + ".csv")
        if not path.exists():
            raise ValueError("actual variant CSV not found: %s" % path)
        return path
    candidates = sorted(raw_dir.glob("*.csv"))
    if len(candidates) != 1:
        raise ValueError("expected exactly one actual-run CSV in %s; use --actual-variant" % raw_dir)
    return candidates[0]


def actual_vs_reconstructed(summary, portfolio_summary, actual, singleton_union, actual_name):
    actual_solved_set = {
        filename for filename, row in actual.items() if classified_result(row) in SOLVED
    }
    actual_wall = sum(row_time(row) or 0.0 for row in actual.values())
    singleton_rows = [row for row in summary if row["mode"] == "singleton"]
    best_solved = max(int(row["solved"]) for row in singleton_rows)
    fastest_singleton_wall = min(float(row["wall_total_s"]) for row in singleton_rows)
    reconstructed_three = next(
        row for row in portfolio_summary if row["portfolio"] == "base+fwd_l1l2+bwd_l2l1"
    )
    reconstructed_wall = float(reconstructed_three["simulated_wall_total_s"])
    return [{
        "actual_variant": actual_name,
        "actual_solved": len(actual_solved_set),
        "best_singleton_solved": best_solved,
        "actual_gain_over_best_singleton": len(actual_solved_set) - best_solved,
        "singleton_union_solved": len(singleton_union),
        "common_solved": len(actual_solved_set & singleton_union),
        "actual_only_solved": len(actual_solved_set - singleton_union),
        "singleton_union_only_solved": len(singleton_union - actual_solved_set),
        "actual_wall_total_s": fmt(actual_wall),
        "fastest_singleton_wall_total_s": fmt(fastest_singleton_wall),
        "actual_speedup_vs_fastest_singleton": fmt(fastest_singleton_wall / actual_wall if actual_wall else None),
        "reconstructed_three_way_wall_total_s": fmt(reconstructed_wall),
        "actual_over_reconstructed_wall": fmt(actual_wall / reconstructed_wall if reconstructed_wall else None),
    }]


def paired_timing(singletons, actual=None, actual_name=None):
    variants = dict(singletons)
    comparisons = [
        ("base", "fwd_l1l2"),
        ("base", "bwd_l2l1"),
        ("fwd_l1l2", "bwd_l2l1"),
    ]
    if actual is not None:
        variants[actual_name] = actual
        comparisons += [(name, actual_name) for name in SINGLETONS]

    detail = []
    summary = []
    for reference, contender in comparisons:
        common = sorted(set(variants[reference]) & set(variants[contender]))
        pairs = []
        for filename in common:
            reference_row = variants[reference][filename]
            contender_row = variants[contender][filename]
            reference_result = classified_result(reference_row)
            contender_result = classified_result(contender_row)
            reference_time = row_time(reference_row)
            contender_time = row_time(contender_row)
            if (reference_result not in SOLVED or reference_result != contender_result
                    or reference_time is None or contender_time is None):
                continue
            ratio = reference_time / contender_time if reference_time > 0 and contender_time > 0 else None
            pairs.append((reference_result, reference_time, contender_time, ratio))
            detail.append({
                "reference": reference,
                "contender": contender,
                "filename": filename,
                "result": reference_result,
                "reference_wall_s": fmt(reference_time),
                "contender_wall_s": fmt(contender_time),
                "speedup_reference_over_contender": fmt(ratio),
            })

        for group in ("All", "Safe", "Unsafe"):
            selected = pairs if group == "All" else [item for item in pairs if item[0] == group]
            ratios = [item[3] for item in selected if item[3] is not None and item[3] > 0]
            reference_total = sum(item[1] for item in selected)
            contender_total = sum(item[2] for item in selected)
            contender_materially_faster = sum(
                item[2] < item[1] * 0.95 and item[1] - item[2] > 0.1 for item in selected
            )
            reference_materially_faster = sum(
                item[2] > item[1] * 1.05 and item[2] - item[1] > 0.1 for item in selected
            )
            summary.append({
                "reference": reference,
                "contender": contender,
                "result_group": group,
                "common_solved": len(selected),
                "contender_faster": sum(item[2] < item[1] for item in selected),
                "reference_faster": sum(item[2] > item[1] for item in selected),
                "exact_ties": sum(item[2] == item[1] for item in selected),
                "contender_materially_faster": contender_materially_faster,
                "reference_materially_faster": reference_materially_faster,
                "within_5pct_or_0_1s": len(selected) - contender_materially_faster - reference_materially_faster,
                "geomean_speedup_reference_over_contender": fmt(
                    math.exp(sum(math.log(value) for value in ratios) / len(ratios)) if ratios else None
                ),
                "median_speedup_reference_over_contender": fmt(statistics.median(ratios) if ratios else None),
                "reference_paired_wall_total_s": fmt(reference_total),
                "contender_paired_wall_total_s": fmt(contender_total),
                "paired_total_speedup_reference_over_contender": fmt(
                    reference_total / contender_total if contender_total else None
                ),
            })
    return detail, summary


def compare_memory(singletons, actual, filenames):
    rows = []
    for filename in filenames:
        values = {name: number(singletons[name][filename].get("max_memory(MB)"))
                  for name in SINGLETONS}
        actual_mb = number(actual[filename].get("max_memory(MB)"))
        available = [value for value in values.values() if value is not None]
        singleton_sum = sum(available) if len(available) == len(SINGLETONS) else None
        rows.append({
            "filename": filename,
            "base_peak_aggregate_rss_mb": fmt(values["base"]),
            "fwd_peak_aggregate_rss_mb": fmt(values["fwd_l1l2"]),
            "bwd_peak_aggregate_rss_mb": fmt(values["bwd_l2l1"]),
            "singleton_peak_rss_sum_mb": fmt(singleton_sum),
            "pic3_actual_peak_aggregate_rss_mb": fmt(actual_mb),
            "actual_over_singleton_sum": fmt(actual_mb / singleton_sum)
                if actual_mb is not None and singleton_sum else "",
        })
    return rows


def markdown_table(fields, rows):
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("singleton_run", type=Path)
    parser.add_argument("--actual-run", type=Path)
    parser.add_argument("--actual-variant")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    singleton_run = args.singleton_run.resolve()
    out_dir = (args.out_dir or singleton_run / "analysis").resolve()
    singletons = load_singletons(singleton_run)
    singleton_sets = [set(singletons[name]) for name in SINGLETONS]
    filenames = sorted(set.intersection(*singleton_sets))
    if not filenames:
        raise ValueError("the singleton CSVs have no common benchmarks")

    summary = [summarize(name, singletons[name], "singleton") for name in SINGLETONS]
    actual = None
    if args.actual_run:
        actual_path = resolve_actual_csv(args.actual_run.resolve(), args.actual_variant)
        actual = load_csv(actual_path)
        summary.append(summarize(actual_path.stem, actual, "actual_three_lane"))

    summary_fields = list(summary[0])
    write_csv(out_dir / "strategy_summary.csv", summary, summary_fields)
    detail, portfolio_summary = reconstruct(singletons, filenames)
    write_csv(out_dir / "reconstructed_portfolios.csv", detail, list(detail[0]))
    write_csv(out_dir / "reconstructed_portfolios_summary.csv", portfolio_summary, list(portfolio_summary[0]))

    complementarity, singleton_union = singleton_complementarity(singletons, filenames)
    write_csv(out_dir / "singleton_complementarity.csv", complementarity, list(complementarity[0]))

    first_finish = []
    actual_comparison = []
    if actual is not None:
        first_finish = actual_first_finish(actual)
        write_csv(out_dir / "actual_first_finish.csv", first_finish, list(first_finish[0]))
        actual_comparison = actual_vs_reconstructed(
            summary, portfolio_summary, actual, singleton_union, actual_path.stem
        )
        write_csv(out_dir / "actual_vs_reconstructed.csv", actual_comparison, list(actual_comparison[0]))

    paired_detail, paired_summary = paired_timing(
        singletons, actual, actual_path.stem if actual is not None else None
    )
    write_csv(out_dir / "paired_common_solved.csv", paired_detail, list(paired_detail[0]))
    write_csv(out_dir / "paired_common_solved_summary.csv", paired_summary, list(paired_summary[0]))

    memory_rows = []
    if actual is not None:
        common = sorted(set(filenames) & set(actual))
        memory_rows = compare_memory(singletons, actual, common)
        write_csv(out_dir / "memory_comparison.csv", memory_rows, list(memory_rows[0]))

    report = [
        "# Minimal P-IC3 Experiment Analysis", "",
        "- Singleton run: `%s`" % singleton_run,
        "- Actual three-lane run: `%s`" % (args.actual_run.resolve() if args.actual_run else "not supplied"),
        "- Complete common singleton samples: `%d`" % len(filenames), "",
        "Memory values are peak aggregate RSS (supervisor plus visible descendants). RSS may double-count shared pages.", "",
        "All aggregate times use measured `execution_time(s)`. Legacy rows are normalized so `timed_out=true` is reported as Timeout.", "",
        "The `cpu_total_s` column is the runner's child-process accounting, not a sum of complete per-lane runtimes; do not present it as precise three-lane CPU cost.", "",
        "## Strategy Summary", "",
        markdown_table(summary_fields, summary), "",
        "## Singleton Complementarity", "",
        "Exclusive solves are benchmarks solved by that singleton and by neither other singleton.", "",
        markdown_table(list(complementarity[0]), complementarity), "",
        "- Union solved by the three complete singleton runs: `%d`" % len(singleton_union), "",
        "## Paired Timing on Common Solved Benchmarks", "",
        "Each row includes only benchmarks for which both methods returned the same Safe/Unsafe result. A speedup above 1 means the contender is faster. A material win must exceed both 5% and 0.1 s, matching the runner's timing granularity.", "",
        markdown_table(list(paired_summary[0]), [row for row in paired_summary if row["result_group"] == "All"]), "",
        "## Reconstructed Portfolios", "",
        "These are simulated portfolios computed from complete singleton runs; they are not measured parallel executions.", "",
        markdown_table(list(portfolio_summary[0]), portfolio_summary), "",
    ]
    if first_finish:
        report += ["## Actual Three-Lane First-Finish Distribution", "",
                   markdown_table(list(first_finish[0]), first_finish), ""]
    if actual_comparison:
        report += ["## Actual vs Reconstructed Three-Way", "",
                   "The reconstructed value is an ideal min-of-complete-singletons oracle, not a measured parallel execution.", "",
                   markdown_table(list(actual_comparison[0]), actual_comparison), ""]
    if memory_rows:
        report += ["## Actual Three-Lane Memory", "",
                   "Per-benchmark values are in `memory_comparison.csv`. The singleton sum is a reference, not a simultaneously measured portfolio.", ""]
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print("Analyzed %d complete singleton benchmarks" % len(filenames))
    print("Wrote %s" % out_dir)


if __name__ == "__main__":
    main()
