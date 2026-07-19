# OrderIC3 Experiment Report

- Run ID: `compare_single_p_907_with_base_x3`
- Config Label: `compare_single_p_907_resume`
- Config Path: `/home/lyh/kind2-exp/PIC3_ICECCS2026/configs/compare_single_p_907_resume.json`
- Created At: `2026-07-18T23:49:37`
- Binary: `/home/lyh/kind2-exp/PIC3_ICECCS2026/runs/compare_single_p_907_with_base_x3/bin/kind2`
- Binary Source: `/home/lyh/kind2-3.0.0-PIC3/bin/kind2`
- Binary Snapshot Created At: `2026-07-18T23:49:37`
- Commit: `e649cde`
- Dataset List: `/home/lyh/kind2-exp/kind2-benchmark/lus_path_907`
- Dataset Root: `/home/lyh/kind2-exp/kind2-benchmark`
- Samples: `907`
- Skip List: `/home/lyh/kind2-exp/PIC3_ICECCS2026/datasets/all_strategies_repeated_timeouts_82.txt`
- Skipped Dataset Entries: `82`
- Status: `finished`
- Finished At: `2026-07-19T02:31:46`
- Last Partial Report At: `2026-07-19T02:15:44`
- Current Progress: `base_x3 907/907`
- Last Completed Benchmark: `FMCAD08/Real_Int32/large/cruise_controller_01.lus`
- Batch Wall Time: `9729.00 s (2h 42m 09.00s)`
- Last Session Wall Time: `9729.00 s (2h 42m 09.00s)`
- Strategy Execution Time Sum: `44185.61 s (12h 16m 25.61s)`
- Strategy CPU Time Sum: `33959.16 s (9h 25m 59.16s)`
- Strategy Kind2 Total Time Sum: `21584.81 s (5h 59m 44.81s)`
- Baseline: `base`
- Metrics: `frame_sizes, total_time, k, solver`
- Reused Variants: `asc_l1l2 <- /home/lyh/kind2-exp/PIC3_ICECCS2026/runs/20260717_110114_compare_single_p, base <- /home/lyh/kind2-exp/PIC3_ICECCS2026/runs/20260717_110114_compare_single_p, desc_l2l1 <- /home/lyh/kind2-exp/PIC3_ICECCS2026/runs/20260717_110114_compare_single_p, pic3 <- /home/lyh/kind2-exp/PIC3_ICECCS2026/runs/20260717_110114_compare_single_p`

## Variant Summary

| variant | safe | unsafe | unknown | timed_out | execution_total_time_s | cpu_total_time_s | kind2_total_time_s | common_solved_count_vs_base | common_solved_total_time_s_vs_base | common_base_total_time_s_vs_base | common_total_time_ratio_vs_base | median_total_time_s | geomean_total_time_s | wins_vs_base | losses_vs_base | newly_solved_vs_base | regressed_vs_base | geomean_speedup_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | 460 | 338 | 0 | 107 | 11142.2900 | 4485.6400 | 5255.8450 | 798 | 3205.9580 | 3205.9580 |  | 0.0670 | 0.1299 |  |  |  |  |  |
| asc_l1l2 | 460 | 344 | 0 | 100 | 8906.5100 | 4352.8800 | 4473.1870 | 788 | 1906.6250 | 2668.5730 | 0.7145 | 0.0660 | 0.1363 | 278 | 392 | 16 | 10 | 0.9984 |
| desc_l2l1 | 461 | 343 | 0 | 101 | 9668.8900 | 4660.0600 | 5076.0520 | 788 | 2392.8500 | 2982.1160 | 0.8024 | 0.0680 | 0.1342 | 297 | 337 | 16 | 10 | 1.0190 |
| pic3 | 465 | 353 | 0 | 87 | 4775.0000 | 8306.8200 | 3052.1040 | 798 | 1343.8700 | 3205.9580 | 0.4192 | 0.0670 | 0.1271 | 325 | 302 | 20 | 0 | 1.1398 |
| base_x3 | 460 | 344 | 0 | 101 | 9692.9200 | 12153.7600 | 3727.6260 | 796 | 1905.2010 | 2868.8710 | 0.6641 | 0.0710 | 0.1329 | 138 | 538 | 8 | 2 | 1.0020 |

## Safe/Unsafe Summary vs Base

| baseline_result_group | variant | variant_group_samples | variant_kind2_total_time_s | baseline_group_samples | common_solved_count_vs_base | common_variant_total_time_s_vs_base | common_base_total_time_s_vs_base | common_total_time_ratio_vs_base | variant_median_total_time_s | variant_geomean_total_time_s | wins_vs_base | losses_vs_base | regressed_vs_base | geomean_speedup_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Safe | base | 460 | 1293.3060 | 460 | 460 | 1293.3060 | 1293.3060 | 1.0000 | 0.0865 | 0.1740 |  |  |  |  |
| Safe | asc_l1l2 | 460 | 1090.3660 | 460 | 456 | 985.4860 | 1172.4330 | 0.8405 | 0.0860 | 0.1762 | 189 | 223 | 4 | 0.9867 |
| Safe | desc_l2l1 | 461 | 1470.4530 | 460 | 457 | 1282.2340 | 1235.3280 | 1.0380 | 0.0880 | 0.1758 | 184 | 215 | 3 | 1.0063 |
| Safe | pic3 | 465 | 721.6240 | 460 | 460 | 621.9900 | 1293.3060 | 0.4809 | 0.0870 | 0.1668 | 187 | 202 | 0 | 1.0936 |
| Safe | base_x3 | 460 | 1168.8910 | 460 | 460 | 1168.8910 | 1293.3060 | 0.9038 | 0.0925 | 0.1814 | 55 | 368 | 0 | 0.9592 |
| Unsafe | base | 338 | 1912.6520 | 338 | 338 | 1912.6520 | 1912.6520 | 1.0000 | 0.0335 | 0.0872 |  |  |  |  |
| Unsafe | asc_l1l2 | 344 | 1836.9320 | 338 | 332 | 921.1390 | 1496.1400 | 0.6157 | 0.0340 | 0.0967 | 89 | 169 | 6 | 1.0146 |
| Unsafe | desc_l2l1 | 343 | 2075.1260 | 338 | 331 | 1110.6160 | 1746.7880 | 0.6358 | 0.0320 | 0.0933 | 113 | 122 | 7 | 1.0368 |
| Unsafe | pic3 | 353 | 1488.7480 | 338 | 338 | 721.8800 | 1912.6520 | 0.3774 | 0.0390 | 0.0888 | 138 | 100 | 0 | 1.2059 |
| Unsafe | base_x3 | 344 | 1195.2650 | 338 | 336 | 736.3100 | 1575.5650 | 0.4673 | 0.0335 | 0.0877 | 83 | 170 | 2 | 1.0637 |

### Result Changes vs Base

#### asc_l1l2

| base result | variant result | count |
| --- | --- | --- |
| Error | Error | 2 |
| Safe | Safe | 456 |
| Safe | Timeout | 4 |
| Timeout | Safe | 4 |
| Timeout | Timeout | 91 |
| Timeout | Unsafe | 12 |
| Unsafe | Error | 1 |
| Unsafe | Timeout | 5 |
| Unsafe | Unsafe | 332 |

#### desc_l2l1

| base result | variant result | count |
| --- | --- | --- |
| Error | Error | 2 |
| Safe | Safe | 457 |
| Safe | Timeout | 3 |
| Timeout | Safe | 4 |
| Timeout | Timeout | 91 |
| Timeout | Unsafe | 12 |
| Unsafe | Timeout | 7 |
| Unsafe | Unsafe | 331 |

#### pic3

| base result | variant result | count |
| --- | --- | --- |
| Error | Error | 2 |
| Safe | Safe | 460 |
| Timeout | Safe | 5 |
| Timeout | Timeout | 87 |
| Timeout | Unsafe | 15 |
| Unsafe | Unsafe | 338 |

#### base_x3

| base result | variant result | count |
| --- | --- | --- |
| Error | Error | 2 |
| Safe | Safe | 460 |
| Timeout | Timeout | 99 |
| Timeout | Unsafe | 8 |
| Unsafe | Timeout | 2 |
| Unsafe | Unsafe | 336 |

## Unknown Cases

### base

None

### asc_l1l2

None

### desc_l2l1

None

### pic3

None

### base_x3

None

## Large Time Deltas vs Base

Threshold: `10.0s` absolute delta on the common solved set.

### base

Baseline

### asc_l1l2

Faster by at least 10s:
- `FMCAD08/Int/memory1/DRAGON_8.lus` | result=Safe | delta=-288.6880s | base=289.5260s | variant=0.8380s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e7_1440.lus` | result=Unsafe | delta=-233.4220s | base=253.9340s | variant=20.5120s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e4_232.lus` | result=Unsafe | delta=-122.6890s | base=143.9710s | variant=21.2820s
- `FMCAD08/Int/large/microwave39.lus` | result=Unsafe | delta=-70.6910s | base=78.7980s | variant=8.1070s
- `FMCAD08/Int/simulation/car_6.lus` | result=Safe | delta=-57.2830s | base=104.7240s | variant=47.4410s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e1_1044.lus` | result=Unsafe | delta=-40.1970s | base=195.5270s | variant=155.3300s
- `FMCAD08/Int/simulation/metros_4_e2_968_e7_860.lus` | result=Unsafe | delta=-32.5950s | base=65.1460s | variant=32.5510s
- `FMCAD08/Real_Int32/large/ccp21.lus` | result=Unsafe | delta=-29.5360s | base=103.6980s | variant=74.1620s
- `FMCAD08/Int/simulation/metros_2_e3_112.lus` | result=Unsafe | delta=-28.9330s | base=66.9920s | variant=38.0590s
- `FMCAD08/Real_Int/large/ccp21.lus` | result=Unsafe | delta=-24.4410s | base=59.4690s | variant=35.0280s
- `FMCAD08/Int/simulation/metros_2_e2_968.lus` | result=Unsafe | delta=-24.0340s | base=45.4660s | variant=21.4320s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e1_556.lus` | result=Unsafe | delta=-23.4090s | base=40.3870s | variant=16.9780s
- `FMCAD08/Real_Int32/large/cruise_controller_15.lus` | result=Unsafe | delta=-21.7790s | base=35.5500s | variant=13.7710s
- `FMCAD08/Real_Int/large/ccp14.lus` | result=Unsafe | delta=-21.5700s | base=62.1990s | variant=40.6290s
- `FMCAD08/Int/memory1/DRAGON_13.lus` | result=Safe | delta=-20.7010s | base=28.2770s | variant=7.5760s
- `FMCAD08/Int/large/microwave35.lus` | result=Unsafe | delta=-19.6670s | base=29.0690s | variant=9.4020s
- `FMCAD08/Int/simulation/car_5.lus` | result=Safe | delta=-19.0870s | base=66.3600s | variant=47.2730s
- `FMCAD08/Int/large/microwave29.lus` | result=Safe | delta=-15.6380s | base=20.9110s | variant=5.2730s
- `FMCAD08/Int/simulation/metros_4_e2_968_e6_236.lus` | result=Unsafe | delta=-15.4950s | base=27.3380s | variant=11.8430s
- `FMCAD08/Int/simulation/car_5_e7_244_e1_823.lus` | result=Safe | delta=-10.6580s | base=51.1390s | variant=40.4810s

Slower by at least 10s:
- `FMCAD08/Int/simulation/car_5_e7_244.lus` | result=Safe | delta=+63.6450s | base=58.8630s | variant=122.5080s
- `FMCAD08/Int/large/microwave36.lus` | result=Unsafe | delta=+55.2410s | base=4.5360s | variant=59.7770s
- `FMCAD08/Int/simulation/metros_2.lus` | result=Safe | delta=+51.2290s | base=95.7070s | variant=146.9360s
- `FMCAD08/Int/simulation/metros_2_e1_190.lus` | result=Safe | delta=+46.4710s | base=69.0650s | variant=115.5360s
- `FMCAD08/Int/memory1/FIREFLY_luke_3.lus` | result=Safe | delta=+45.3470s | base=1.9120s | variant=47.2590s
- `FMCAD08/Int/large/microwave32.lus` | result=Unsafe | delta=+21.5630s | base=6.1420s | variant=27.7050s
- `FMCAD08/Int/large/microwave24.lus` | result=Safe | delta=+15.6470s | base=5.3250s | variant=20.9720s
- `FMCAD08/Int/simulation/metros_2_e2_704_e7_810.lus` | result=Unsafe | delta=+15.3490s | base=2.7420s | variant=18.0910s
- `FMCAD08/Real_Int/large/cruise_controller_17.lus` | result=Unsafe | delta=+11.9780s | base=22.6090s | variant=34.5870s

### desc_l2l1

Faster by at least 10s:
- `FMCAD08/Int/memory1/DRAGON_8.lus` | result=Safe | delta=-288.5620s | base=289.5260s | variant=0.9640s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e7_1440.lus` | result=Unsafe | delta=-247.2070s | base=253.9340s | variant=6.7270s
- `FMCAD08/Int/simulation/metros_3_e3_1275_e5_846.lus` | result=Unsafe | delta=-194.4130s | base=279.5460s | variant=85.1330s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e4_232.lus` | result=Unsafe | delta=-121.9550s | base=143.9710s | variant=22.0160s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e1_1044.lus` | result=Unsafe | delta=-102.0270s | base=195.5270s | variant=93.5000s
- `FMCAD08/Int/large/microwave39.lus` | result=Unsafe | delta=-73.3150s | base=78.7980s | variant=5.4830s
- `FMCAD08/Int/simulation/car_5_e7_244_e1_823.lus` | result=Safe | delta=-44.0420s | base=51.1390s | variant=7.0970s
- `FMCAD08/Int/simulation/metros_2_e2_968.lus` | result=Unsafe | delta=-32.2020s | base=45.4660s | variant=13.2640s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e1_556.lus` | result=Unsafe | delta=-28.2360s | base=40.3870s | variant=12.1510s
- `FMCAD08/Real_Int32/large/ccp21.lus` | result=Unsafe | delta=-20.4090s | base=103.6980s | variant=83.2890s
- `FMCAD08/Real_Int32/large/cruise_controller_15.lus` | result=Unsafe | delta=-19.0220s | base=35.5500s | variant=16.5280s
- `FMCAD08/Int/memory1/DRAGON_13.lus` | result=Safe | delta=-18.6780s | base=28.2770s | variant=9.5990s
- `FMCAD08/Real_Int32/large/cruise_controller_17.lus` | result=Unsafe | delta=-13.0970s | base=34.5620s | variant=21.4650s
- `FMCAD08/Real_Int/large/ccp14.lus` | result=Unsafe | delta=-12.4940s | base=62.1990s | variant=49.7050s
- `FMCAD08/Real_Int/large/ccp12.lus` | result=Unsafe | delta=-10.3540s | base=72.2400s | variant=61.8860s

Slower by at least 10s:
- `FMCAD08/Int/memory1/FIREFLY_u1_e2_3403_e2_957.lus` | result=Safe | delta=+221.0200s | base=5.1170s | variant=226.1370s
- `FMCAD08/Int/large/microwave35.lus` | result=Unsafe | delta=+119.9510s | base=29.0690s | variant=149.0200s
- `FMCAD08/Int/simulation/car_5_e7_244.lus` | result=Safe | delta=+72.2300s | base=58.8630s | variant=131.0930s
- `FMCAD08/Int/simulation/car_6.lus` | result=Safe | delta=+68.0860s | base=104.7240s | variant=172.8100s
- `FMCAD08/Int/simulation/metros_2.lus` | result=Safe | delta=+57.5000s | base=95.7070s | variant=153.2070s
- `FMCAD08/Real_Int32/large/ccp14.lus` | result=Unsafe | delta=+43.4310s | base=57.5410s | variant=100.9720s
- `FMCAD08/Int/simulation/metros_2_e3_112.lus` | result=Unsafe | delta=+27.1940s | base=66.9920s | variant=94.1860s
- `FMCAD08/Int/simulation/metros_2_e1_190.lus` | result=Safe | delta=+21.6970s | base=69.0650s | variant=90.7620s
- `FMCAD08/Real_Int/large/ccp10.lus` | result=Unsafe | delta=+20.1410s | base=9.1980s | variant=29.3390s
- `FMCAD08/Int/simulation/metros_2_e2_704_e7_810.lus` | result=Unsafe | delta=+13.5380s | base=2.7420s | variant=16.2800s
- `FMCAD08/Int/large/microwave36.lus` | result=Unsafe | delta=+11.3810s | base=4.5360s | variant=15.9170s

### pic3

Faster by at least 10s:
- `FMCAD08/Int/memory1/DRAGON_8.lus` | result=Safe | delta=-288.5340s | base=289.5260s | variant=0.9920s
- `FMCAD08/Int/simulation/metros_3_e3_1275_e5_846.lus` | result=Unsafe | delta=-278.5760s | base=279.5460s | variant=0.9700s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e7_1440.lus` | result=Unsafe | delta=-249.3790s | base=253.9340s | variant=4.5550s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e1_1044.lus` | result=Unsafe | delta=-172.1670s | base=195.5270s | variant=23.3600s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e4_232.lus` | result=Unsafe | delta=-143.5100s | base=143.9710s | variant=0.4610s
- `FMCAD08/Int/simulation/car_6.lus` | result=Safe | delta=-86.0170s | base=104.7240s | variant=18.7070s
- `FMCAD08/Int/large/microwave39.lus` | result=Unsafe | delta=-74.1260s | base=78.7980s | variant=4.6720s
- `FMCAD08/Int/simulation/metros_2_e3_112.lus` | result=Unsafe | delta=-52.7990s | base=66.9920s | variant=14.1930s
- `FMCAD08/Int/protocol/rtp_vt.lus` | result=Safe | delta=-50.0280s | base=77.3160s | variant=27.2880s
- `FMCAD08/Int/simulation/car_5.lus` | result=Safe | delta=-47.0930s | base=66.3600s | variant=19.2670s
- `FMCAD08/Int/simulation/car_5_e7_244_e1_823.lus` | result=Safe | delta=-44.9490s | base=51.1390s | variant=6.1900s
- `FMCAD08/Int/simulation/metros_2_e2_968.lus` | result=Unsafe | delta=-44.9410s | base=45.4660s | variant=0.5250s
- `FMCAD08/Int/simulation/metros_2_e1_190.lus` | result=Safe | delta=-41.4440s | base=69.0650s | variant=27.6210s
- `FMCAD08/Real_Int32/large/cruise_controller_15.lus` | result=Unsafe | delta=-32.4530s | base=35.5500s | variant=3.0970s
- `FMCAD08/Int/simulation/metros_4_e2_968_e6_236.lus` | result=Unsafe | delta=-27.2960s | base=27.3380s | variant=0.0420s
- `FMCAD08/Real_Int32/large/cruise_controller_17.lus` | result=Unsafe | delta=-24.6560s | base=34.5620s | variant=9.9060s
- `FMCAD08/Real_Int32/large/ccp21.lus` | result=Unsafe | delta=-24.3440s | base=103.6980s | variant=79.3540s
- `FMCAD08/Int/large/microwave35.lus` | result=Unsafe | delta=-24.1630s | base=29.0690s | variant=4.9060s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e1_556.lus` | result=Unsafe | delta=-20.6270s | base=40.3870s | variant=19.7600s
- `FMCAD08/Real_Int/large/ccp21.lus` | result=Unsafe | delta=-20.2440s | base=59.4690s | variant=39.2250s
- `FMCAD08/Real_Int32/large/cruise_controller_22.lus` | result=Unsafe | delta=-18.2220s | base=40.8680s | variant=22.6460s
- `FMCAD08/Real_Int32/large/cruise_controller_10.lus` | result=Safe | delta=-18.0160s | base=19.9230s | variant=1.9070s
- `FMCAD08/Int/memory1/DRAGON_13.lus` | result=Safe | delta=-17.9740s | base=28.2770s | variant=10.3030s
- `FMCAD08/Real_Int32/large/cruise_controller_20.lus` | result=Unsafe | delta=-14.1590s | base=32.7130s | variant=18.5540s
- `FMCAD08/Int/large/microwave29.lus` | result=Safe | delta=-13.9310s | base=20.9110s | variant=6.9800s
- `FMCAD08/Real_Int/large/cruise_controller_17.lus` | result=Unsafe | delta=-12.3780s | base=22.6090s | variant=10.2310s

Slower by at least 10s:
- `FMCAD08/Real_Int32/large/ccp14.lus` | result=Unsafe | delta=+45.2400s | base=57.5410s | variant=102.7810s
- `FMCAD08/Int/simulation/metros_2.lus` | result=Safe | delta=+21.7970s | base=95.7070s | variant=117.5040s
- `FMCAD08/Int/simulation/metros_4_e2_968_e7_860.lus` | result=Unsafe | delta=+20.4690s | base=65.1460s | variant=85.6150s

### base_x3

Faster by at least 10s:
- `FMCAD08/Int/memory1/DRAGON_8.lus` | result=Safe | delta=-284.3270s | base=289.5260s | variant=5.1990s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e7_1440.lus` | result=Unsafe | delta=-247.9200s | base=253.9340s | variant=6.0140s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e1_1044.lus` | result=Unsafe | delta=-167.6910s | base=195.5270s | variant=27.8360s
- `FMCAD08/Int/simulation/metros_4_e3_1091_e4_232.lus` | result=Unsafe | delta=-143.4880s | base=143.9710s | variant=0.4830s
- `FMCAD08/Real_Int32/large/ccp21.lus` | result=Unsafe | delta=-68.4640s | base=103.6980s | variant=35.2340s
- `FMCAD08/Int/simulation/metros_4_e2_968_e7_860.lus` | result=Unsafe | delta=-60.6710s | base=65.1460s | variant=4.4750s
- `FMCAD08/Real_Int/large/ccp21.lus` | result=Unsafe | delta=-45.5660s | base=59.4690s | variant=13.9030s
- `FMCAD08/Real_Int/large/ccp12.lus` | result=Unsafe | delta=-35.3680s | base=72.2400s | variant=36.8720s
- `FMCAD08/Real_Int32/large/cruise_controller_20.lus` | result=Unsafe | delta=-31.6370s | base=32.7130s | variant=1.0760s
- `FMCAD08/Real_Int32/large/cruise_controller_17.lus` | result=Unsafe | delta=-23.6720s | base=34.5620s | variant=10.8900s
- `FMCAD08/Int/simulation/metros_2_e1_1116_e1_556.lus` | result=Unsafe | delta=-22.6360s | base=40.3870s | variant=17.7510s
- `FMCAD08/Int/simulation/metros_2_e3_112.lus` | result=Unsafe | delta=-19.5610s | base=66.9920s | variant=47.4310s
- `FMCAD08/Int/simulation/metros_4_e2_968_e6_236.lus` | result=Unsafe | delta=-11.3230s | base=27.3380s | variant=16.0150s

Slower by at least 10s:
- `FMCAD08/Int/simulation/metros_2.lus` | result=Safe | delta=+46.4430s | base=95.7070s | variant=142.1500s
- `FMCAD08/Int/simulation/car_5.lus` | result=Safe | delta=+21.0850s | base=66.3600s | variant=87.4450s
- `FMCAD08/Int/large/microwave39.lus` | result=Unsafe | delta=+16.5470s | base=78.7980s | variant=95.3450s
- `FMCAD08/Int/protocol/rtp_vt.lus` | result=Safe | delta=+14.8810s | base=77.3160s | variant=92.1970s
- `FMCAD08/Int/simulation/car_5_e7_244_e1_823.lus` | result=Safe | delta=+14.7660s | base=51.1390s | variant=65.9050s
- `FMCAD08/Int/simulation/car_5_e7_244.lus` | result=Safe | delta=+12.7940s | base=58.8630s | variant=71.6570s

## Artifacts

- Config snapshot: `config_snapshot.json` or `config_snapshot.jsonc`
- Raw per-variant CSVs: `raw/`
- Aligned comparison table: `compare/aligned.csv`
- Pairwise baseline comparison: `compare/pairwise_vs_base.csv`
- Summary table: `compare/summary.csv`
- Logs by variant: `logs/`
- Binary snapshot: `bin/`

## Variant Commands

- `base`: `/home/lyh/kind2-exp/PIC3_ICECCS2026/runs/compare_single_p_907_with_base_x3/bin/kind2 -vv --color false --timeout 300 --enable IC3QE <lus-file>`
- `asc_l1l2`: `/home/lyh/kind2-exp/PIC3_ICECCS2026/runs/compare_single_p_907_with_base_x3/bin/kind2 -vv --color false --timeout 300 --enable IC3QEL1L2 <lus-file>`
- `desc_l2l1`: `/home/lyh/kind2-exp/PIC3_ICECCS2026/runs/compare_single_p_907_with_base_x3/bin/kind2 -vv --color false --timeout 300 --enable IC3QEL2L1 <lus-file>`
- `pic3`: `/home/lyh/kind2-exp/PIC3_ICECCS2026/runs/compare_single_p_907_with_base_x3/bin/kind2 -vv --color false --timeout 300 --enable IC3QE --enable IC3QEL1L2 --enable IC3QEL2L1 <lus-file>`
- `base_x3`: `/home/lyh/kind2-exp/PIC3_ICECCS2026/runs/compare_single_p_907_with_base_x3/bin/kind2 -vv --color false --timeout 300 --enable IC3QEBASE1 --enable IC3QEBASE2 --enable IC3QEBASE3 <lus-file>`
