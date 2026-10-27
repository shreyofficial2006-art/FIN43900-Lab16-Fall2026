"""Lab 16: a reproducible point-in-time provenance gate; standard library only."""

# Editable inputs: original row numbers stay attached throughout the filter.
DECISION_DATE = "2026-03-31"
TABLE = [
    # row, ticker, month measured, published on, index
    (1, "AAA", "2026-01", "2026-02-10", "101.0"),
    (2, "AAA", "2026-02", "2026-03-10", "104.0"),
    (3, "AAA", "2026-03", "2026-04-10", "109.0"),
    (4, "AAA", "2026-02", "2026-03-25", "103.0"),
    (5, "BBB", "2026-01", "2026-02-10", "98.0"),
    (6, "BBB", "2026-02", "2026-03-10", "97.0"),
    (7, "BBB", "2026-02", "2026-03-10", "97.0"),
    (8, "BBB", "2026-03", "2026-04-10", "92.0"),
    (9, "CCC", "2026-01", "2026-02-10", "110.0"),
    (10, "CCC", "2026-02", "2026-04-05", "112.0"),
    (11, "", "2026-02", "2026-03-10", "99.0"),
    (12, "CCC", "2026-02", "2026-03-10", "111.0"),
]

import argparse
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Row:
    number: int
    ticker: str
    month: date
    published: date
    value: Decimal


def parse_rows(table):
    """Parse inputs, preserve source IDs, and reject ambiguous source records."""
    rows = []
    identifiers = set()
    for number, ticker, month, published, value in table:
        if not isinstance(number, int) or number in identifiers:
            raise ValueError("Each source row must have a unique integer row number.")
        identifiers.add(number)
        measured = date.fromisoformat(month + "-01")
        if measured.strftime("%Y-%m") != month:
            raise ValueError("Month measured must use YYYY-MM.")
        index = Decimal(str(value))
        if not index.is_finite():
            raise ValueError("Index values must be finite.")
        rows.append(Row(number, ticker, measured, date.fromisoformat(published), index))
    return sorted(rows, key=lambda row: row.number)


def latest_by_month(rows):
    """Rule 4: choose the latest publication among the rows passed to this function."""
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


def apply_gate(rows, decision_date):
    """Apply quarantine, duplicates, cutoff, then revisions, recording each removal."""
    funnel = []

    # Rule 1: quarantine rows whose ticker is empty or whitespace.
    quarantined = [row.number for row in rows if not row.ticker.strip()]
    eligible = [row for row in rows if row.ticker.strip()]
    funnel.append(("Quarantined: no ticker", quarantined, len(eligible)))

    # Rule 2: row number identifies the source record, not the observation's content.
    seen = set()
    unique = []
    duplicates = []
    for row in eligible:
        content = (row.ticker, row.month, row.published, row.value)
        if content in seen:
            duplicates.append(row.number)
        else:
            seen.add(content)
            unique.append(row)
    funnel.append(("Exact duplicate", duplicates, len(unique)))

    # Rule 3: a same-day publication is available under the lab's day-level rule.
    late = [row.number for row in unique if row.published > decision_date]
    knowable = [row for row in unique if row.published <= decision_date]
    funnel.append(("Published after decision date", late, len(knowable)))

    # Rule 4 is applied only to knowable rows; a later revision cannot erase them.
    panel, replaced = latest_by_month(knowable)
    funnel.append(("Older vintage replaced by a revision", replaced, len(panel)))

    # Naive comparison: apply the same identity rules, but skip the cutoff.
    naive_panel, _ = latest_by_month(unique)
    return funnel, panel, naive_panel


def signal_for(panel, ticker):
    """Use the latest measured month and its immediately preceding calendar month."""
    observations = sorted(
        (row for row in panel if row.ticker == ticker), key=lambda row: row.month
    )
    if len(observations) < 2:
        return None, "not enough knowable months"
    previous, latest = observations[-2:]
    month_distance = (latest.month.year - previous.month.year) * 12
    month_distance += latest.month.month - previous.month.month
    if month_distance != 1:
        return None, "previous calendar month unavailable"
    if previous.value == 0:
        return None, "previous month's index is zero"
    percent = (latest.value / previous.value - Decimal("1")) * Decimal("100")
    return percent, latest.month.strftime("%B %Y")


def describe_signal(panel, ticker):
    percent, month_or_reason = signal_for(panel, ticker)
    if percent is None:
        return month_or_reason
    return f"{percent:+.2f}% ({month_or_reason})"


def print_report(rows, decision_date):
    funnel, panel, naive_panel = apply_gate(rows, decision_date)
    print("LAB 16 - PROVENANCE GATE")
    print(f"Decision date: {decision_date.isoformat()}")
    print("Availability rule: published on or before the decision date")
    print(f"Input rows: {len(rows)}")
    print("\nROW FUNNEL")
    for step, (label, removed, remaining) in enumerate(funnel, start=1):
        ids = ", ".join(map(str, removed)) or "none"
        print(f"{step}. {label}: removed {len(removed)}; rows [{ids}]; remaining {remaining}")
    print("As-of panel row numbers: " + (", ".join(str(row.number) for row in panel) or "none"))
    print("\nAS-OF PANEL")
    print("Row | Ticker | Month measured | Published on | Index")
    for row in panel:
        print(f"{row.number:>3} | {row.ticker:<6} | {row.month:%Y-%m}        | {row.published}   | {row.value}")
    print("\nSIGNALS: (latest month / previous calendar month - 1) * 100")
    print("Ticker | As-of signal | Naive signal | Naive minus as-of (percentage points)")
    tickers = sorted({row.ticker for row in rows if row.ticker.strip()})
    for ticker in tickers:
        actual, _ = signal_for(panel, ticker)
        naive, _ = signal_for(naive_panel, ticker)
        gap = f"{naive - actual:+.2f}" if actual is not None and naive is not None else "n/a"
        print(f"{ticker} | {describe_signal(panel, ticker)} | {describe_signal(naive_panel, ticker)} | {gap}")
    print("\nNAIVE PANEL AUDIT")
    print("Latest publication for each ticker/month, with the publication cutoff ignored:")
    for row in naive_panel:
        status = "published after decision date" if row.published > decision_date else "published by decision date"
        print(f"row {row.number}: {row.ticker} {row.month:%Y-%m}, {row.value}, published {row.published} [{status}]")
    print("\nThe naive column is a leakage comparison; index changes are not investment returns.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=DECISION_DATE, help="decision date in YYYY-MM-DD")
    arguments = parser.parse_args()
    try:
        decision_date = date.fromisoformat(arguments.date)
        rows = parse_rows(TABLE)
        print_report(rows, decision_date)
    except (ValueError, ArithmeticError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
