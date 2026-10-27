# Lab 16 - Provenance Gate

**Decision date:** March 31, 2026  
**Data:** the assigned fictional card-spend index for AAA, BBB, and CCC  
**Conclusion:** use the as-of signals of **AAA +1.98%, BBB -1.02%, and CCC +0.91%**, all measuring February 2026. The naive signals incorporate information published after the decision date and cannot describe what was available on March 31.

## Define: the decision and information set

The question is which observations a decision-maker could have used on the trading decision date. My information set includes only records published on or before March 31, 2026, with the latest available vintage retained for each ticker and measured month.

The **month measured** identifies the activity described by the observation. The **publication date** identifies when that observation became available. AAA's March index of 109.0 measures March activity, but its April 10 publication makes it unavailable for a March 31 decision. A month having ended does not make its measurement knowable.

## Represent: data and rules

The complete, unchanged 12-row training table is embedded at the top of [asof.py](asof.py). Original row numbers remain attached to every record.

I apply the following rules in order:

1. Quarantine any row without a ticker, because it cannot be assigned to a security.
2. Remove exact duplicates, comparing ticker, measured month, publication date, and index. The source row number is an identifier, so it is excluded from the duplicate key.
3. Remove publications later than the decision date. Publications on the decision date are included under the lab's convention.
4. Within each ticker and measured month, keep the latest publication among the rows that survived the cutoff.

The naive comparison uses the same ticker and duplicate rules, then keeps each month's latest publication without imposing the decision-date cutoff. This isolates the effect of unavailable publications rather than mixing it with missing identifiers or duplicated records.

## Implement: reproducible calculation

```text
python asof.py
```

The script computes every panel and signal from the editable table. It prints each rule's removal count, removed row numbers, remaining count, the surviving panel, both signals, their difference, and an audit of the naive panel's publications. There are no embedded expected answers in the production calculation.

For each ticker, the signal is:

```text
100 * (index in latest available month / index in previous calendar month - 1)
```

The code uses `Decimal` arithmetic and rounds only the displayed result to two decimals. If the previous calendar month is missing, fewer than two months are knowable, or the denominator is zero, it reports the reason instead of inventing a percentage.

## Validate: March 31 row funnel

| Stage | Removed count | Removed source rows | Rows remaining |
|---|---:|---|---:|
| Input | 0 | None | 12 |
| 1. Missing ticker quarantined | 1 | 11 | 11 |
| 2. Exact duplicate removed | 1 | 7 | 10 |
| 3. Publication after March 31 removed | 3 | 3, 8, 10 | 7 |
| 4. Earlier available vintage replaced | 1 | 2 | 6 |

The accounting reconciles: **12 - 1 - 1 - 3 - 1 = 6**. The as-of source rows are **1, 4, 5, 6, 9, 12**.

| Row | Ticker | Month measured | Published on | Index |
|---:|---|---|---|---:|
| 1 | AAA | 2026-01 | 2026-02-10 | 101.0 |
| 4 | AAA | 2026-02 | 2026-03-25 | 103.0 |
| 5 | BBB | 2026-01 | 2026-02-10 | 98.0 |
| 6 | BBB | 2026-02 | 2026-03-10 | 97.0 |
| 9 | CCC | 2026-01 | 2026-02-10 | 110.0 |
| 12 | CCC | 2026-02 | 2026-03-10 | 111.0 |

Row 4 replaces row 2 because both describe AAA's February activity and the March 25 revision was already public by March 31. Row 12 remains for CCC because row 10's revision was not published until April 5. These are different outcomes of the same availability rule.

### Signals and independent arithmetic

| Ticker | As-of calculation | As-of signal | Naive calculation | Naive signal | Naive minus as-of |
|---|---|---|---|---|---:|
| AAA | 100 x (103 / 101 - 1) | +1.98%, February | 100 x (109 / 103 - 1) | +5.83%, March | +3.85 pp |
| BBB | 100 x (97 / 98 - 1) | -1.02%, February | 100 x (92 / 97 - 1) | -5.15%, March | -4.13 pp |
| CCC | 100 x (111 / 110 - 1) | +0.91%, February | 100 x (112 / 110 - 1) | +1.82%, February | +0.91 pp |

Every month above is in 2026. Gaps are calculated from the unrounded signals and then rounded; `pp` means percentage points. The AAA and BBB comparisons use different latest months, while CCC isolates a revision to the same month.

The unavailable observations are row 3, AAA March, published April 10; row 8, BBB March, published April 10; and row 10, CCC February revised, published April 5. They are exactly the three records removed by the publication cutoff.

Keeping AAA row 2 by mistake would calculate `100 x (104 / 101 - 1) = +2.97%`. That differs from the correct +1.98% and reveals a failure to apply the already-known revision.

The complete executed report is in [output-2026-03-31.txt](output-2026-03-31.txt).

## Explain the revision code

Rule 4 is implemented by `latest_by_month`:

```python
latest = {}
for row in sorted(rows, key=lambda item: (item.published, item.number)):
    key = (row.ticker, row.month)
    previous = latest.get(key)
    if previous is not None and previous.published == row.published:
        if previous.value != row.value:
            raise ValueError("Conflicting values share a ticker, month, and publication date.")
    latest[key] = row
panel = sorted(latest.values(), key=lambda row: row.number)
kept_ids = {row.number for row in panel}
replaced = sorted(row.number for row in rows if row.number not in kept_ids)
return panel, replaced
```

1. `latest = {}` creates a dictionary holding one chosen record for each ticker-month pair.
2. The `for` line processes publications from earliest to latest. The row-number tie-break makes ordering reproducible.
3. `key = (row.ticker, row.month)` groups publications describing the same security and activity month. Publication date is deliberately excluded from this key so that revisions compete for the same entry.
4. `previous = latest.get(key)` retrieves any record already stored for that pair.
5. The next three lines reject different values with an identical ticker, month, and publication date. The source would need to resolve that ambiguity; an arbitrary tie-break cannot establish which value was correct.
6. `latest[key] = row` inserts the first record or overwrites it with a later publication. Thus row 4 replaces row 2.
7. The `panel` line collects the chosen records and sorts them by original row number for the audit display.
8. `kept_ids` identifies the surviving records; `replaced` records the source numbers excluded by the revision rule. The function returns both the panel and its removal evidence.

For the as-of calculation, `apply_gate` passes only `knowable` rows to this function. Consequently, row 10 never competes with row 12 at the March 31 cutoff. Selecting the latest full-history revision before applying the cutoff would delete row 12 and then discard row 10, incorrectly losing CCC's knowable February observation.

### Code quiz

**Question:** Why does `latest[key] = row` retain the correct revision rather than whichever row happens to appear last in the input table?

**Answer:** The loop explicitly sorts by publication date before assigning to the dictionary. For AAA February, March 10 is processed first and March 25 second, so row 4 overwrites row 2 even if the raw table is rearranged.

**Explanation:** The dictionary provides one slot per ticker-month; chronological assignment determines its final value. The cutoff must already have been applied so that a future revision cannot occupy that slot.

### Partner discussion questions and answers

**Question:** Why is row 7 a duplicate of row 6 even though its row number differs?

**Answer:** All four observation fields match. A new identifier does not create new economic information, so row 6 is retained and row 7 is logged as a duplicate.

**Question:** Why can CCC use 111.0 but not 112.0 when both refer to February?

**Answer:** The value 111.0 was published March 10 and was available at the cutoff. The value 112.0 was published April 5, so using it on March 31 would import a future revision.

**Question:** What happens if a revision is published exactly on the decision date?

**Answer:** The inclusive `row.published <= decision_date` condition admits it, and rule 4 can replace the earlier vintage. This follows the assignment's date-level rule; intraday trading would require a release timestamp and a later executable trade time.

## Evolve: later-date check

The changed input is **March 31, 2026 -> April 15, 2026**. The table, rule order, and signal formula stay fixed.

```text
python asof.py --date 2026-04-15
```

The equivalent edit is to set `DECISION_DATE = "2026-04-15"` at the top of the file and run `python asof.py`. The validation record verifies that this edit produces the same report as the command-line override and that the saved default remains March 31.

| Stage | Removed count | Removed source rows | Rows remaining |
|---|---:|---|---:|
| Input | 0 | None | 12 |
| Missing ticker quarantined | 1 | 11 | 11 |
| Exact duplicate removed | 1 | 7 | 10 |
| Publication after April 15 removed | 0 | None | 10 |
| Earlier vintage replaced | 2 | 2, 12 | 8 |

The later panel contains **1, 3, 4, 5, 6, 8, 9, 10**. Row 10 can now replace row 12, and March observations for AAA and BBB are available.

| Ticker | April 15 as-of signal | Naive signal | Difference |
|---|---|---|---:|
| AAA | +5.83%, March 2026 | +5.83%, March 2026 | 0.00 pp |
| BBB | -5.15%, March 2026 | -5.15%, March 2026 | 0.00 pp |
| CCC | +1.82%, February 2026 | +1.82%, February 2026 | 0.00 pp |

The equality occurs because the last publication in this table is April 10, before the later cutoff. Both columns therefore use the same vintage for every ticker-month. This validates the requested changed-date behavior. The saved submission default is **March 31, 2026**.

See [output-2026-04-15.txt](output-2026-04-15.txt) and [validation.txt](validation.txt). All 16 automated tests pass, covering the known answers, revision boundaries, ordered removal rules, changed input values, and invalid or insufficient inputs.

## Learn: point-in-time reasoning

**1. What is look-ahead bias?**

Look-ahead bias occurs when a historical decision uses information that became available only afterward. A backtest then evaluates an information advantage that the real decision-maker did not have.

**2. How do event time, publication time, and revisions create it?**

Event time tells me what period the number describes. Publication time tells me when that version became usable. A revision creates another version with another availability date. Filtering only by measured month, or replacing every historical observation with its final revision, mixes these clocks and can insert future knowledge into earlier decisions.

**3. Why does AAA's naive +5.83% look stronger than what was knowable?**

The +5.83% calculation compares March's 109.0 with February's revised 103.0. March's 109.0 did not become public until April 10. On March 31 the latest usable comparison was February 103.0 against January 101.0, or +1.98%. The apparent extra **3.85 percentage points** comes from unavailable March information, not from a forecast demonstrated by this exercise.

**4. Why does the as-of filter work better than a fixed lag on today's file?**

A fixed lag does not reconstruct old versions. Even if I exclude the latest month, today's file can still place CCC's April 5 revision of February into a March 31 decision. The as-of filter checks each publication and selects the version actually available, handling both delayed first releases and subsequent revisions.

**5. What does the ALFRED prework contribute?**

ALFRED preserves historical versions of economic data so analysis can reconstruct what a source reported at earlier dates. Its help page distinguishes release dates from observation periods and explains that release-date evidence can come from the original source, a provider, or the date of first FRED availability when other evidence is unavailable. For a real series, I would record that provenance instead of assuming the observation date is the release date.

## Reflect

**Which rule removed the row that mattered most?**

For the strongest false positive in this table, rule 3's removal of AAA row 3 matters most: it prevents an April 10 publication from creating a +5.83% March signal at a March 31 decision. Rule 4 is also consequential because the already-public downward revision in row 4 changes AAA's legitimate February signal from +2.97% to +1.98%. The former blocks future knowledge; the latter uses the best knowledge actually available.

**What would a backtest built on the naive column claim?**

It would behave as though March 31 already provided strong AAA growth of +5.83%, a sharper BBB decline of -5.15%, and CCC growth of +1.82%. A rule favoring stronger spending might therefore favor AAA or avoid BBB using releases from April, while CCC benefits from a later revision. That historical decision would be infeasible. The exercise demonstrates contaminated signals; without asset returns, a trading rule, execution assumptions, and costs, it does not establish how much portfolio performance would be overstated.

## Sources

- [Lab 16 - Provenance Gate](https://github.com/CinderZhang/FIN43900-Fall2026/blob/main/lessons/week-10/lab-16-provenance-gate.md)
- [Week 10 Student Handout](https://github.com/CinderZhang/FIN43900-Fall2026/blob/main/lessons/week-10/student-handout.md)
- [ALFRED Help](https://alfred.stlouisfed.org/help)

The training data and reference outputs come from the assigned lab. The attached text reports are generated by the submitted program; the attached validation record is generated by its tests.
