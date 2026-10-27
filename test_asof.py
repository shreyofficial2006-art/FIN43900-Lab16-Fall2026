"""Independent expected answers and boundary tests for Lab 16. Run: python -m unittest -v"""

import unittest
from datetime import date
from decimal import Decimal

from asof import TABLE, apply_gate, latest_by_month, parse_rows, signal_for


class ProvenanceGateTests(unittest.TestCase):
    def setUp(self):
        self.rows = parse_rows(TABLE)
        self.funnel, self.panel, self.naive = apply_gate(self.rows, date(2026, 3, 31))

    def test_known_row_funnel(self):
        self.assertEqual([step[1] for step in self.funnel], [[11], [7], [3, 8, 10], [2]])
        self.assertEqual([step[2] for step in self.funnel], [11, 10, 7, 6])

    def test_known_asof_panel(self):
        self.assertEqual([row.number for row in self.panel], [1, 4, 5, 6, 9, 12])

    def test_all_known_signals_and_months(self):
        expected = {
            "AAA": ("+1.98", "February 2026", "+5.83", "March 2026"),
            "BBB": ("-1.02", "February 2026", "-5.15", "March 2026"),
            "CCC": ("+0.91", "February 2026", "+1.82", "February 2026"),
        }
        for ticker, (asof_pct, asof_month, naive_pct, naive_month) in expected.items():
            with self.subTest(ticker=ticker):
                actual, actual_month = signal_for(self.panel, ticker)
                naive, latest_month = signal_for(self.naive, ticker)
                self.assertEqual((f"{actual:+.2f}", actual_month), (asof_pct, asof_month))
                self.assertEqual((f"{naive:+.2f}", latest_month), (naive_pct, naive_month))

    def test_later_date_matches_naive(self):
        funnel, panel, naive = apply_gate(self.rows, date(2026, 4, 15))
        self.assertEqual([step[1] for step in funnel], [[11], [7], [], [2, 12]])
        self.assertEqual([row.number for row in panel], [1, 3, 4, 5, 6, 8, 9, 10])
        self.assertEqual(panel, naive)
        for ticker in ("AAA", "BBB", "CCC"):
            self.assertEqual(signal_for(panel, ticker), signal_for(naive, ticker))

    def test_rule_order_preserves_earlier_ccc_vintage(self):
        ccc_feb = next(row for row in self.panel if row.ticker == "CCC" and row.month.month == 2)
        self.assertEqual((ccc_feb.number, ccc_feb.value), (12, Decimal("111.0")))

    def test_publication_cutoff_includes_same_day(self):
        _, before, _ = apply_gate(self.rows, date(2026, 3, 24))
        _, on_date, _ = apply_gate(self.rows, date(2026, 3, 25))
        self.assertIn(2, [row.number for row in before])
        self.assertIn(4, [row.number for row in on_date])
        self.assertNotIn(2, [row.number for row in on_date])

    def test_late_revision_arrives_on_its_publication_date(self):
        _, before, _ = apply_gate(self.rows, date(2026, 4, 4))
        _, on_date, _ = apply_gate(self.rows, date(2026, 4, 5))
        self.assertIn(12, [row.number for row in before])
        self.assertIn(10, [row.number for row in on_date])
        self.assertNotIn(12, [row.number for row in on_date])

    def test_shuffled_input_preserves_source_row_results(self):
        self.assertEqual(apply_gate(parse_rows(list(reversed(TABLE))), date(2026, 3, 31)),
                         (self.funnel, self.panel, self.naive))

    def test_changed_input_changes_computed_signal(self):
        changed = [row[:-1] + ("102.0",) if row[0] == 4 else row for row in TABLE]
        _, panel, _ = apply_gate(parse_rows(changed), date(2026, 3, 31))
        percent, _ = signal_for(panel, "AAA")
        self.assertEqual(f"{percent:+.2f}", "+0.99")

    def test_insufficient_history(self):
        _, panel, _ = apply_gate(self.rows, date(2026, 2, 28))
        for ticker in ("AAA", "BBB", "CCC"):
            self.assertEqual(signal_for(panel, ticker), (None, "not enough knowable months"))

    def test_missing_calendar_month_is_not_monthly_growth(self):
        rows = parse_rows([(1, "X", "2026-01", "2026-02-01", "100"),
                           (2, "X", "2026-03", "2026-04-01", "110")])
        self.assertEqual(signal_for(rows, "X"), (None, "previous calendar month unavailable"))

    def test_zero_denominator_is_not_a_return(self):
        rows = parse_rows([(1, "X", "2026-01", "2026-02-01", "0"),
                           (2, "X", "2026-02", "2026-03-01", "100")])
        self.assertEqual(signal_for(rows, "X"), (None, "previous month's index is zero"))

    def test_quarantine_precedes_duplicate_detection(self):
        rows = parse_rows([(1, " ", "2026-01", "2026-02-01", "100"),
                           (2, " ", "2026-01", "2026-02-01", "100")])
        funnel, panel, naive = apply_gate(rows, date(2026, 3, 31))
        self.assertEqual(funnel[0][1], [1, 2])
        self.assertEqual(funnel[1][1], [])
        self.assertEqual((panel, naive), ([], []))

    def test_duplicate_detection_precedes_cutoff(self):
        rows = parse_rows([(1, "X", "2026-03", "2026-04-10", "100"),
                           (2, "X", "2026-03", "2026-04-10", "100")])
        funnel, _, _ = apply_gate(rows, date(2026, 3, 31))
        self.assertEqual(funnel[1][1], [2])
        self.assertEqual(funnel[2][1], [1])

    def test_ambiguous_same_date_revision_is_rejected(self):
        rows = parse_rows([(1, "X", "2026-01", "2026-02-01", "100"),
                           (2, "X", "2026-01", "2026-02-01", "101")])
        with self.assertRaisesRegex(ValueError, "Conflicting values"):
            latest_by_month(rows)

    def test_invalid_inputs_are_rejected(self):
        bad_tables = [
            [TABLE[0], TABLE[0]],
            [(1, "X", "2026-1", "2026-02-01", "100")],
            [(1, "X", "2026-01", "2026-02-30", "100")],
            [(1, "X", "2026-01", "2026-02-01", "NaN")],
        ]
        for table in bad_tables:
            with self.subTest(table=table), self.assertRaises(ValueError):
                parse_rows(table)


if __name__ == "__main__":
    unittest.main(verbosity=2)
