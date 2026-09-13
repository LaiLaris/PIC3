#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SOLVED = {"Safe", "Unsafe"}
METRIC_COLUMN = "execution_time(s)"
METRIC_LABEL = "Execution time (s)"


def load_variant(run_dir: Path, variant: str) -> pd.DataFrame:
    csv_path = run_dir / "raw" / f"{variant}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"missing {csv_path}")
    columns = ["filename", "property_result", METRIC_COLUMN]
    frame = pd.read_csv(csv_path, usecols=columns)
    frame.rename(columns={METRIC_COLUMN: "plot_time"}, inplace=True)
    frame["plot_time"] = pd.to_numeric(frame["plot_time"], errors="coerce")
    return frame


def load_raw(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        load_variant(run_dir, "base"),
        load_variant(run_dir, "pic3"),
    )


def solved_times(frame: pd.DataFrame, timeout: float) -> np.ndarray:
    values = frame.loc[
        frame["property_result"].isin(SOLVED), "plot_time"
    ].dropna()
    return np.sort(values[(values > 0) & (values < timeout)].to_numpy())


def common_solved(base: pd.DataFrame, pic3: pd.DataFrame) -> pd.DataFrame:
    common = base.merge(pic3, on="filename", suffixes=("_base", "_pic3"))
    common = common[
        common["property_result_base"].isin(SOLVED)
        & common["property_result_pic3"].isin(SOLVED)
    ].dropna(subset=["plot_time_base", "plot_time_pic3"])
    return common[
        (common["plot_time_base"] > 0) & (common["plot_time_pic3"] > 0)
    ].copy()


def plot_combined(
    base: pd.DataFrame,
    pic3: pd.DataFrame,
    output_base: Path,
    timeout: float,
    standalone: dict[str, pd.DataFrame],
) -> None:
    base_times = solved_times(base, timeout)
    pic3_times = solved_times(pic3, timeout)
    common = common_solved(base, pic3)
    standalone_times = {
        label: solved_times(frame, timeout)
        for label, frame in standalone.items()
    }
    lane_frames = {"Base": base, **standalone}
    lane_series = []
    for label, frame in lane_frames.items():
        indexed = frame.set_index("filename")
        lane_series.append(
            indexed["plot_time"]
            .where(indexed["property_result"].isin(SOLVED))
            .rename(label)
        )
    vbs = pd.concat(lane_series, axis=1).min(axis=1, skipna=True).dropna()
    vbs_times = np.sort(vbs[(vbs > 0) & (vbs < timeout)].to_numpy())

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )

    fig, (ax_cactus, ax_scatter) = plt.subplots(1, 2, figsize=(9.6, 4.5))

    cactus_low = 10 ** np.floor(
        np.log10(min(base_times.min(), pic3_times.min()))
    )
    time_grid = np.geomspace(cactus_low, timeout, 900)
    base_counts = np.searchsorted(base_times, time_grid, side="right")
    pic3_counts = np.searchsorted(pic3_times, time_grid, side="right")
    solved_gap = pic3_counts - base_counts
    vbs_counts = np.searchsorted(vbs_times, time_grid, side="right")

    ax_cactus.plot(
        time_grid,
        base_counts,
        color="#2563eb",
        linestyle="--",
        linewidth=1.8,
        label="Kind2-IC3",
    )
    standalone_styles = {
        "Asc-only": ("#16a34a", "-."),
        "Desc-only": ("#9333ea", ":"),
    }
    for label, times in standalone_times.items():
        color, linestyle = standalone_styles[label]
        ax_cactus.plot(
            time_grid,
            np.searchsorted(times, time_grid, side="right"),
            color=color,
            linestyle=linestyle,
            linewidth=1.45,
            label=label,
        )
    ax_cactus.plot(
        time_grid,
        pic3_counts,
        color="#dc2626",
        linestyle="-",
        linewidth=2.0,
        label="P-IC3",
    )
    ax_cactus.plot(
        time_grid,
        vbs_counts,
        color="#111827",
        linestyle="-",
        linewidth=1.7,
        label="VBS (3 standalone)",
    )
    ax_cactus.fill_between(
        time_grid,
        pic3_counts,
        vbs_counts,
        color="#6b7280",
        alpha=0.13,
        linewidth=0,
    )
    ax_cactus.set_xscale("log")
    ax_cactus.set_xlim(0.8, timeout)
    solved_max = max(
        [len(base_times), len(pic3_times)]
        + [len(times) for times in standalone_times.values()]
        + [len(vbs_times)]
    )
    ax_cactus.set_ylim(675, solved_max * 1.01)
    ax_cactus.set_xlabel(METRIC_LABEL)
    ax_cactus.set_ylabel("Cases solved")
    ax_cactus.set_title("(a) Cumulative solved cases (zoomed)")
    ax_cactus.grid(True, linestyle=":", linewidth=0.65, alpha=0.55)
    ax_cactus.legend(loc="upper left", frameon=True, fontsize=7.5)

    gap_ax = ax_cactus.inset_axes([0.53, 0.10, 0.42, 0.27])
    gap_ax.plot(
        time_grid,
        solved_gap,
        color="#b91c1c",
        linewidth=1.1,
        label="P-IC3 $-$ Base",
    )
    gap_ax.fill_between(time_grid, 0, solved_gap, color="#ef4444", alpha=0.18)
    gap_ax.axhline(0, color="#374151", linestyle=":", linewidth=0.7)
    gap_ax.set_xscale("log")
    gap_ax.set_xlim(0.8, timeout)
    gap_ax.set_ylim(0, 30)
    gap_ax.set_title(r"Gap: P-IC3 $-$ Kind2-IC3", fontsize=7, pad=2)
    gap_ax.set_xlabel(METRIC_LABEL, fontsize=6, labelpad=1)
    gap_ax.set_ylabel(r"$\Delta$ solved", fontsize=6, labelpad=1)
    gap_ax.tick_params(axis="both", labelsize=6, pad=1)
    gap_ax.grid(True, linestyle=":", linewidth=0.45, alpha=0.45)

    ax_cactus.set_box_aspect(1)

    x = common["plot_time_base"]
    y = common["plot_time_pic3"]
    low = 10 ** np.floor(np.log10(min(x.min(), y.min())))
    high = 10 ** np.ceil(np.log10(max(x.max(), y.max())))
    ax_scatter.scatter(
        x,
        y,
        s=13,
        color="#dc2626",
        alpha=0.62,
        edgecolors="none",
        label=f"Common solved ({len(common)})",
    )
    ax_scatter.plot(
        [low, high],
        [low, high],
        color="#111827",
        linestyle="--",
        linewidth=1.1,
        label="Equal time",
    )
    ax_scatter.set_xscale("log")
    ax_scatter.set_yscale("log")
    ax_scatter.set_xlim(low, high)
    ax_scatter.set_ylim(low, high)
    ax_scatter.set_xlabel(f"Kind2-IC3 {METRIC_LABEL.lower()}")
    ax_scatter.set_ylabel(f"P-IC3 {METRIC_LABEL.lower()}")
    ax_scatter.set_title("(b) Runtime comparison")
    ax_scatter.grid(True, which="both", linestyle=":", linewidth=0.55, alpha=0.45)
    ax_scatter.legend(loc="upper left", frameon=True)
    ax_scatter.set_box_aspect(1)

    output_base.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.14, top=0.93, wspace=0.30)
    for suffix in (".png", ".pdf"):
        fig.savefig(output_base.with_suffix(suffix), dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"base_solved={len(base_times)}")
    print(f"pic3_solved={len(pic3_times)}")
    print(f"common_solved={len(common)}")
    print(f"wrote {output_base.with_suffix('.png')}")
    print(f"wrote {output_base.with_suffix('.pdf')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a side-by-side square cactus plot and runtime scatter plot."
    )
    parser.add_argument(
        "--run-dir", type=Path,
        default=Path("/home/lyh/kind2-exp/PIC3_ICECCS2026/results"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parents[1] / "fig"
        / "base_vs_pic3_execution_time_with_standalone_vbs",
    )
    parser.add_argument("--timeout", type=float, default=300.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    standalone = {
        "Asc-only": load_variant(args.run_dir, "asc_l1l2"),
        "Desc-only": load_variant(args.run_dir, "desc_l2l1"),
    }
    plot_combined(
        *load_raw(args.run_dir),
        args.output,
        args.timeout,
        standalone,
    )



if __name__ == "__main__":
    main()
