# Lab 16 - Provenance Gate

This submission reconstructs the fictional card-spend information available on **March 31, 2026**. It preserves source row numbers, records each filtering decision, and compares the knowable signal with a naive signal that uses later publications.

## Files

| File | Contents |
|---|---|
| [asof.py](asof.py) | One executable Python file, including all 12 input rows and the editable decision date |
| [CHECKOUT.md](CHECKOUT.md) | Completed analysis, calculations, revision-code explanation, discussion answers, and reflections |
| [output-2026-03-31.txt](output-2026-03-31.txt) | Executed baseline report: funnel, panel, signals, and naive-row audit |
| [output-2026-04-15.txt](output-2026-04-15.txt) | Executed later-date report demonstrating equality with the naive signals |
| [test_asof.py](test_asof.py) | Independent known-answer checks and publication/revision boundary tests |
| [validation.txt](validation.txt) | Executed test results and verification of the edit-date-and-restore procedure |

## Run

Use Python 3.9 or newer. All imports are from the Python standard library; no packages, accounts, API keys, or downloads are needed.

From this folder:

```text
python asof.py
python asof.py --date 2026-04-15
python -m unittest -v
```

If the Python launcher on your computer is `py`, substitute `py` for `python`.

The original table and `DECISION_DATE = "2026-03-31"` are at the top of `asof.py`. Editing that date to `2026-04-15` and running the first command produces the later-date check. Restore it to `2026-03-31` afterward. The optional `--date` argument produces the same result without changing the saved default.

## Results

| Ticker | March 31 as-of | Naive | April 15 as-of |
|---|---|---|---|
| AAA | +1.98%, February | +5.83%, March | +5.83%, March |
| BBB | -1.02%, February | -5.15%, March | -5.15%, March |
| CCC | +0.91%, February | +1.82%, February | +1.82%, February |

All months are in 2026. At March 31, the surviving rows are **1, 4, 5, 6, 9, 12**. At April 15, the as-of panel equals the naive panel and every signal gap is zero.

## GitHub checkout

Upload this folder's files together to your own course repository, for example under `lab16/`. In **Brightspace -> Quizzes -> Lab 16**, submit the GitHub links to `CHECKOUT.md`, `asof.py`, and the two output files. Keeping all files together preserves the relative links in this README. Ensure the instructor can access the repository.

## Sources and scope

- [Lab 16 instructions](https://github.com/CinderZhang/FIN43900-Fall2026/blob/main/lessons/week-10/lab-16-provenance-gate.md): training data, required rule order, known answers, and checkout.
- [Session 16 slides](https://github.com/CinderZhang/FIN43900-Fall2026/blob/main/lessons/week-10/slides-session-16.md): Brightspace quiz location and later-date exercise.
- [Week 10 handout](https://github.com/CinderZhang/FIN43900-Fall2026/blob/main/lessons/week-10/student-handout.md): point-in-time interpretation.
- [ALFRED Help](https://alfred.stlouisfed.org/help): vintage data and release-date definitions.

Course repository revision reviewed: `524f3a385ac7d5b213bcc5eed69160924f200585`.

The index and tickers are the course's fictional training data. The date cutoff follows its inclusive day-level convention. A production trading system would also need release times, time zones, and the first executable trade after publication. These index changes do not establish realized portfolio returns or predictive performance.
