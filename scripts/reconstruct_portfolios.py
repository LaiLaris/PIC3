#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path

VARIANTS = ["base", "fwd_l1l2", "bwd_l2l1"]
PORTFOLIOS = [
    ("base+fwd_l1l2", ["base", "fwd_l1l2"]),
    ("base+bwd_l2l1", ["base", "bwd_l2l1"]),
    ("fwd_l1l2+bwd_l2l1", ["fwd_l1l2", "bwd_l2l1"]),
    ("base+fwd_l1l2+bwd_l2l1", ["base", "fwd_l1l2", "bwd_l2l1"]),
]
SOLVED = {"Safe", "Unsafe"}

def fnum(x):
    try:
        if x in (None, ""):
            return None
        return float(x)
    except Exception:
        return None

def load_variant(run_dir, variant):
    path = Path(run_dir) / "raw" / f"{variant}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["filename"]: row for row in csv.DictReader(handle)}

def time_of(row):
    return fnum(row.get("total_time")) or fnum(row.get("execution_time(s)"))

def main():
    ap = argparse.ArgumentParser(description="Reconstruct ideal P-IC3 portfolios from singleton runs")
    ap.add_argument("run_dir", help="Run directory containing raw/base.csv, raw/fwd_l1l2.csv, raw/bwd_l2l1.csv")
    ap.add_argument("--out", default="", help="Output CSV path")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    rows = {v: load_variant(run_dir, v) for v in VARIANTS}
    filenames = sorted(set.intersection(*(set(rows[v]) for v in VARIANTS)))
    out = Path(args.out) if args.out else run_dir / "reconstructed_portfolios.csv"
    fieldnames = [
        "portfolio", "filename", "winner", "result", "time_s",
        "complete_all_variants", "note",
    ]
    summary = {}
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for pname, members in PORTFOLIOS:
            solved_count = 0
            total_time = 0.0
            winner_counts = {m: 0 for m in members}
            for filename in filenames:
                candidates = []
                for member in members:
                    row = rows[member][filename]
                    result = row.get("property_result", "")
                    t = time_of(row)
                    if result in SOLVED and t is not None:
                        candidates.append((t, member, result))
                if candidates:
                    t, winner, result = min(candidates, key=lambda item: (item[0], item[1]))
                    solved_count += 1
                    total_time += t
                    winner_counts[winner] += 1
                    writer.writerow({
                        "portfolio": pname,
                        "filename": filename,
                        "winner": winner,
                        "result": result,
                        "time_s": f"{t:.6f}",
                        "complete_all_variants": "true",
                        "note": "reconstructed_min_of_complete_singleton_runs",
                    })
                else:
                    writer.writerow({
                        "portfolio": pname,
                        "filename": filename,
                        "winner": "",
                        "result": "Unknown",
                        "time_s": "",
                        "complete_all_variants": "true",
                        "note": "no_member_solved_with_time",
                    })
            summary[pname] = (solved_count, total_time, winner_counts)
    summary_path = out.with_name(out.stem + "_summary.csv")
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["portfolio", "solved_count", "total_time_s"] + [f"wins_{v}" for v in VARIANTS]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for pname, (solved_count, total_time, winner_counts) in summary.items():
            row = {"portfolio": pname, "solved_count": solved_count, "total_time_s": f"{total_time:.6f}"}
            for v in VARIANTS:
                row[f"wins_{v}"] = winner_counts.get(v, 0)
            writer.writerow(row)
    print(f"wrote {out}")
    print(f"wrote {summary_path}")

if __name__ == "__main__":
    main()
