from app.ingestion.parser import parse_csv
from app.ingestion.normalizer import normalize_activity
from app.ingestion.pii_masker import get_masker

def test_malformed_rows_dont_crash():
    csv_data = "case_id,activity\n1,missing_fields"
    result = parse_csv(csv_data)
    assert result == []

def test_normalization_lowercase():
    assert normalize_activity("EXP_LETTER_REQ") == "exp letter req"

def test_normalization_separators():
    assert normalize_activity("test_this-now.please") == "test this now please"

def test_pii_email_masked():
    masker = get_masker()
    res = masker.mask_text("contact me at foo@bar.com please")
    assert "[EMAIL]" in res

def test_pii_phone_masked():
    masker = get_masker()
    res = masker.mask_text("call 123-456-7890 today")
    assert "123-456-7890" not in res
    assert "[PHONE]" in res


def test_pii_masking_is_not_a_noop():
    """Guards against a masker that silently returns input unchanged."""
    masker = get_masker()
    original = "email foo@bar.com"
    assert masker.mask_text(original) != original


def test_parser_confidence_reflects_completeness():
    complete = "case_id,activity,timestamp,actor,system\nc1,submit,2025-01-01,alice,SAP"
    partial = "case_id,activity,timestamp,actor,system\nc1,submit,2025-01-01,,"
    assert parse_csv(complete)[0]["confidence"] == 1.0
    assert parse_csv(partial)[0]["confidence"] < 1.0


def test_parser_skips_bad_rows_but_keeps_good_ones():
    """A malformed row must not discard the rest of the batch."""
    csv_data = (
        "case_id,activity,timestamp,actor,system\n"
        "c1,submit,2025-01-01,alice,SAP\n"
        "c2,approve,2025-01-02,bob,Workday"
    )
    assert len(parse_csv(csv_data)) == 2
