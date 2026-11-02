# AskL-Rose evaluation: failure analysis

Runs of 2026-11-01, rescored on 2026-11-02 with the fixed grader. The full analysis, with every failure and filters, is in [`index.html`](index.html).

## Scores

qwen2.5-coder:7b through Ollama, temperature 0, self-repair on, 50 questions.

| Run | Passed | Failed |
|---|---|---|
| With the semantic layer | **31 (62%)** | 19 |
| Without it | 21 (42%) | 29 |

| Tag | Questions | With | Without |
|---|---|---|---|
| join | 29 | 19 | 9 |
| time | 18 | 10 | 5 |
| other-area | 18 | 9 | 5 |
| semantic | 16 | 10 | 5 |
| easy | 13 | 6 | 6 |
| not-data | 5 | 5 | 5 |

## Grader fixes before concluding

Fixed with general rules decided from the questions' wording, then both runs were rescored from their saved SQL (`python -m eval.run --rescore FILE`, no new model calls).

| Fix | What changed | Effect |
|---|---|---|
| Order | `ordered: true` only when the question asks for a sorted or ranked answer (now none). A wrong order is reported as "rows in a different order". | q01, q38 pass without the layer |
| Tolerance | Numbers may differ by 0.1% (at least 0.01): dividing `money` values loses precision. | q36 passes in both runs |
| q16 reworded | "Which resellers have the most employees?", since 6 tie. Asked again in both settings. | Still fails: the model keeps `TOP 1` |

With: 30 → 31. Without: 18 → 21. Gap: +12 → +10.

## The 19 failures with the semantic layer, by cause

All 19 are the model's fault.

| Cause | Count | Questions |
|---|---|---|
| gate: a data question refused as "not a data question" | 6 | q06 q09 q11 q14 q44 q50 |
| wrong logic: the SQL runs but answers a different question | 6 | q15 q16 q20 q23 q27 q31 |
| invented column | 4 | q03 q04 q41 q45 |
| T-SQL syntax: `FETCH FIRST` without `OFFSET` | 2 | q32 q37 |
| SCD: history rows of a Slowly Changing Dimension not filtered | 1 | q08 |

## With vs without

| | Passes without (21) | Fails without (29) |
|---|---|---|
| **Passes with (31)** | 18 pass both times | 13 helped by the layer |
| **Fails with (19)** | 3 hurt by the layer (q09 q14 q37) | 16 fail both times |

Net gain: **+10**. In 10 of the 13 helped questions the model used a definition from the layer (gross profit, number of orders, fiscal year, product name, …); 3 flipped for no clear reason. Of the 3 hurt, 2 are the gate refusing simple questions (q09, q14) and 1 is `FETCH FIRST` luck (q37).
