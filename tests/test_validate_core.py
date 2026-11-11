from core import Table, Violation, finalize, flag, quarantine_rate_violation, suppress


def test_flag_makes_one_violation_per_true_row_with_id_and_excel_row():
    t = Table(["id"], [{"id": "a"}, {"id": "b"}, {"id": None}])
    out = flag(t, [False, True, True], "R99", "FAIL", "x", "bad x", id_col="id")
    assert [(v.record_id, v.source_row) for v in out] == [("b", 3), (None, 4)]
    assert {v.rule_id for v in out} == {"R99"}


def test_finalize_sends_fail_rows_to_quarantine_and_flags_warn_rows():
    t = Table(["id"], [{"id": "a"}, {"id": "b"}, {"id": "c"}])
    vs = [Violation("R01", "FAIL", 1, "b", 3, "id", "bad"),
          Violation("W01", "WARN", 2, "c", 4, "x", "odd"),
          Violation("W02", "WARN", 2, "c", 4, "y", "odd")]
    passed, quarantine = finalize(t, vs)
    assert [(r["id"], r["dq_flags"]) for r in passed] == [("a", ""), ("c", "W01;W02")]
    assert [(r["id"], r["rule_ids"]) for r in quarantine] == [("b", "R01")]


def test_suppress_hides_counts_between_one_and_four():
    assert [suppress(n) for n in (0, 1, 4, 5, 81)] == ["0", "<5", "<5", "5", "81"]


def test_quarantine_rate_above_threshold_fails_batch():
    assert quarantine_rate_violation(2, 10, 0.10).rule_id == "B06"
    assert quarantine_rate_violation(1, 10, 0.10) is None


def test_decimals_counts_digits_as_written_and_ignores_binary_noise():
    from core import decimals
    assert [decimals(v) for v in (13.734, 14.0, 100, "13.73", 13.734000000000002, 13.7345678, None, "x")] == \
        [3, 0, 0, 2, 3, 7, 0, 0]
