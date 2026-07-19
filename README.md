# P-IC3 ICECCS 2026 Artifact

This lightweight artifact contains the executable and experiment outputs for
the five-way comparison:

- `base`: one native IC3QE worker
- `asc_l1l2`: ascending literal-deletion order
- `desc_l2l1`: descending literal-deletion order
- `pic3`: the three heterogeneous IC3 workers
- `base_x3`: three native IC3QE workers

## Contents

- `bin/kind2`: executable used by the completed `base_x3` run
- `scripts/exp_resume.py`: experiment runner and report generator
- `scripts/analyze_minimal_results.py`: additional result analysis
- `scripts/reconstruct_portfolios.py`: offline portfolio reconstruction
- `configs/compare_single_p_907_resume.json`: experiment configuration
- `datasets/`: benchmark path lists
- `results/raw/`: per-variant raw CSV files
- `results/compare/`: aligned, pairwise, and summary CSV files
- `results/report.md`: generated experiment report
- `results/manifest.json`: run metadata

The full per-instance logs are not included in this lightweight package.

## Binary

The included executable targets x86-64 Linux and dynamically links to the
system libraries used by Kind2, including ZeroMQ.

Check the available modules with:

```bash
./bin/kind2 --help
```

The custom modules are:

```text
IC3QEL1L2
IC3QEL2L1
IC3QEBASE1
IC3QEBASE2
IC3QEBASE3
```

## Quick smoke test

Run all five variants on the included small Lustre example:

```bash
python3 scripts/quick_start.py
```

The command prints a compact pass/fail table and writes full solver output to
`quick_results/`. To run one variant or use another Lustre input:

```bash
python3 scripts/quick_start.py --variant pic3
python3 scripts/quick_start.py path/to/example.lus --timeout 60
```

Kind2 uses local ZeroMQ inter-process communication. Run the smoke test outside
containers or sandboxes that prohibit local IPC/network socket operations.

## Rebuilding the report

From the artifact directory:

```bash
python3 scripts/exp_resume.py compare results
python3 scripts/exp_resume.py report results
```

## Rerunning

Update the absolute binary and dataset paths in the JSON configuration for the
target machine, then run:

```bash
python3 scripts/exp_resume.py run \
  configs/compare_single_p_907_resume.json \
  --run-id compare_single_p_907_with_base_x3 \
  --report-every 100
```

All experiment scripts use only the Python standard library.
