# Epoch 254 API Issue Analysis

## Epoch 254 Timeline

| Event | Block | Time (UTC) |
|-------|-------|------------|
| Epoch 254 start (PoC start) | 3,920,669 | 2026-05-05 20:06:15 |
| Epoch effective start (validators set) | 3,921,069 | 2026-05-05 20:41:04 |
| **CPoC 1 concluded** | 3,928,860 | 2026-05-06 07:54:58 |
| **CPoC 2 concluded** | 3,931,470 | 2026-05-06 11:41:04 |
| **CPoC 3 concluded** | 3,934,350 | 2026-05-06 15:49:58 |
| Epoch 254 end | 3,936,059 | 2026-05-06 18:17:29 |

## Root Cause

Commit `f85f991b` — `fix(api): avoid blocking startup on devshard migration` — merged 2026-05-06T19:00:03Z, released as `v0.2.12-api-post3`.

Prior versions had a blocking devshard migration on startup: after `docker restart api`, the servers on ports 9100, 9200, and 9400 did not become available until the migration completed, which could take up to ~20 minutes. Participants who restarted their API container during epoch 254 to apply the `v0.2.12-api-post2` fix came back online too late to participate in subsequent CPoC rounds.

The `v0.2.12-api-post2` release was tagged 2026-05-06T08:38:35Z — between CPoC 1 (07:54 UTC) and CPoC 2 (11:41 UTC). Participants who applied it immediately after CPoC 1 would have had their API offline during CPoC 2 and potentially CPoC 3.

## CPoC Results Summary

### CPoC 1 — Block 3,928,860 (07:54 UTC)
4 participants dropped. These are legitimate failures unrelated to the API bug.

| Address | Weight |
|---------|--------|
| gonka1wkgawwdzj623ss8eywayzdj6qcgr2llygactje | 1,262 |
| gonka12tfc6ccmadjqv6yaa3axxsuhy6zv6tupu78p8u | 683 |
| gonka1d7ghexkrnm00fh695zcd00xgfgwxe2vvamcsdt | 792 |
| gonka1tl5m3vuqsx333v7095ymwjdc4vdk2wd9r5hqws | 1,245 |

### CPoC 2 — Block 3,931,470 (11:41 UTC)
3 participants dropped + 6 participants had significant confirmation weight loss.
The `v0.2.12-api-post2` binary was released at 08:38 UTC — 3h before this CPoC.
Participants applying the update during this window would have been offline for CPoC 2.

**Dropped:**
| Address | Weight |
|---------|--------|
| gonka125n6kr5gvdup0lndfkps7t6rd6592panhrg3np | 1,288 |
| gonka1fvly5jrewyjmjfgwah3khy9rttq4cqajcesv9p | 1,285 |
| gonka1pvkv59e72vju2h7s9j3ex62c5xneqey350vpwn | 6,921 |

**Severe CW reduction (>25% loss):**
| Address | Weight | CW Before | CW After | Loss |
|---------|--------|-----------|----------|------|
| gonka1q5xt54wncgzk7dxv9x64uln68455g83wu9tugg | 185,380 | 179,972 | 2,899 | 98.4% |
| gonka1wthc28t25pg63hzvl07rl8e8r6km6hesl6jhsz | 3,986 | 4,428 | 1,498 | 66.2% |
| gonka1vjz8csqsr0ph0lv0yylc4auypnzrld7y6l2feu | 840 | 884 | 334 | 62.2% |
| gonka14tqh62mangwzrma2lgg2dm375rcjzn2ydy8ttm | 5,802 | 5,973 | 4,144 | 30.6% |
| gonka1tmk2tzdneht6smu34pkmqdvu7p34qavvmwtwq2 | 1,198 | 1,261 | 920 | 27.0% |

### CPoC 3 — Block 3,934,350 (15:49 UTC)
8 participants dropped. The `v0.2.12-api-post3` fix was released 2026-05-07T03:30 UTC — after the epoch ended. Participants who applied `v0.2.12-api-post2` between CPoC 1 and CPoC 2 would still be affected here if migration took long enough.

**Dropped:**
| Address | Weight |
|---------|--------|
| gonka1h2m79scgaq6ultrwge03wjk0ys4whgcejphmql | 1,705 |
| gonka1y4kyhqy022gt4kklxxflgqkutnx96ssww66zg6 | 787 |
| gonka18xeqnspxpg2vncufnjne485rkaagwvz7whyn0d | 1,253 |
| gonka19cjm4c5mt3j3qdr8vhytmm4hef3pnkvkm0x7m2 | 1,245 |
| gonka163ug8zucqeag9v5ey4au34jqt7vejkmxsg74eu | 1,236 |
| gonka1mdy7nlecw4xaqdxmeh3qlqzakg9ftge9szfqgg | 1,124 |
| gonka1xwkesaxvdadh9wt9yyladu0r260s7whklcktds | 1,245 |
| gonka1f0u3y2wneer8zhz3ypw4x54h38cpa0qsy8ts3e | 1,262 |

## Affected Participants — Compensation Scope

Eligibility criteria:
- CPoC 1: **pass** — node was active before the bug window
- Final CPoC: **fail** (dropped or confirmation ratio < 45.5%) — node was severely impacted by epoch end
- Rewards received **= 0**

CPoC 1 dropouts are excluded (failed before the bug window). Participants who received rewards are excluded (partially compensated by the protocol).

This yields **14 affected addresses** with a total compensation of **58,375.96 GONKA** — see `compensation.csv` for per-address amounts.

Compensation formula: `weight / total_epoch_weight * epoch_theoretical_reward`  
Epoch 254 theoretical reward pool: **286,425.17 GONKA** (`323,000 * e^(-0.000475 * 253)`)  
Total epoch weight: **1,028,204**

| Address | Weight | CPoC 1 | Final CPoC | Compensation (GONKA) |
|---------|--------|--------|------------|---------------------|
| gonka1q5xt54wncgzk7dxv9x64uln68455g83wu9tugg | 185,380 | pass | fail | 51,641.02 |
| gonka1pvkv59e72vju2h7s9j3ex62c5xneqey350vpwn | 6,921 | pass | fail | 1,927.97 |
| gonka1wthc28t25pg63hzvl07rl8e8r6km6hesl6jhsz | 3,986 | pass | fail | 1,110.37 |
| gonka1h2m79scgaq6ultrwge03wjk0ys4whgcejphmql | 1,705 | pass | fail | 474.96 |
| gonka125n6kr5gvdup0lndfkps7t6rd6592panhrg3np | 1,288 | pass | fail | 358.80 |
| gonka1fvly5jrewyjmjfgwah3khy9rttq4cqajcesv9p | 1,285 | pass | fail | 357.96 |
| gonka1f0u3y2wneer8zhz3ypw4x54h38cpa0qsy8ts3e | 1,262 | pass | fail | 351.55 |
| gonka18xeqnspxpg2vncufnjne485rkaagwvz7whyn0d | 1,253 | pass | fail | 349.05 |
| gonka19cjm4c5mt3j3qdr8vhytmm4hef3pnkvkm0x7m2 | 1,245 | pass | fail | 346.82 |
| gonka1xwkesaxvdadh9wt9yyladu0r260s7whklcktds | 1,245 | pass | fail | 346.82 |
| gonka163ug8zucqeag9v5ey4au34jqt7vejkmxsg74eu | 1,236 | pass | fail | 344.31 |
| gonka1mdy7nlecw4xaqdxmeh3qlqzakg9ftge9szfqgg | 1,124 | pass | fail | 313.11 |
| gonka1vjz8csqsr0ph0lv0yylc4auypnzrld7y6l2feu | 840 | pass | fail | 233.99 |
| gonka1y4kyhqy022gt4kklxxflgqkutnx96ssww66zg6 | 787 | pass | fail | 219.23 |

## Fix Commits

| Version | Timestamp | Fix |
|---------|-----------|-----|
| v0.2.12-api-post2 | 2026-05-06T08:38:35Z | Kimi-K2.6 response parsing fix |
| v0.2.12-api-post3 | 2026-05-06T19:00:03Z | Parallel devshard loading — removes blocking startup (commit `f85f991b17`) |

The root blocker (`f85f991b` — avoid blocking startup on devshard migration) landed in `v0.2.12-api-post3`, released after epoch 254 ended.
