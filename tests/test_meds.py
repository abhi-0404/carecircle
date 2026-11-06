import pytest

from carecircle.meds import (
    DoseError,
    card_text,
    check_prescription,
    parse_dose,
    parse_duration,
    schedule_markdown,
)

# A synthetic prescription, as the @meds agent would transcribe it.
TRANSCRIPT = {
    "lines": [
        {"verbatim": "Tab. Amlodipine 5mg 1-0-1 x 30 days after food",
         "name": "Amlodipine", "strength": "5mg", "form": "tablet",
         "dose": "1-0-1", "duration": "30 days", "timing": "after food"},
        {"verbatim": "Tab. Metformin 500 mg BD with meals",
         "name": "Metformin", "strength": "500 mg", "form": "tablet",
         "dose": "BD", "timing": "with meals"},
        {"verbatim": "Syp. Cough syrup 5 ml TDS x 5 days",
         "name": "Cough syrup", "strength": "", "form": "syrup", "dose": "5 ml TDS",
         "duration": "5 days"},
        {"verbatim": "Tab. Paracetamol 650 mg SOS for fever",
         "name": "Paracetamol", "strength": "650 mg", "form": "tablet", "dose": "SOS",
         "timing": "for fever"},
    ]
}


@pytest.mark.parametrize(
    "dose, slots, as_needed",
    [
        ("1-0-1", {"morning": 1, "night": 1}, False),
        ("1 - 1 - 1", {"morning": 1, "afternoon": 1, "night": 1}, False),
        ("½-0-½", {"morning": 0.5, "night": 0.5}, False),
        ("1/2-0-0", {"morning": 0.5}, False),
        ("1-0-0-1", {"morning": 1, "night": 1}, False),
        ("0-0-1", {"night": 1}, False),
        ("BD", {"morning": 1, "night": 1}, False),
        ("tds", {"morning": 1, "afternoon": 1, "night": 1}, False),
        ("HS", {"night": 1}, False),
        ("5 ml TDS", {"morning": 5, "afternoon": 5, "night": 5}, False),
        ("2 tabs od", {"morning": 2}, False),
        ("SOS", {}, True),
        ("1 tab prn", {}, True),
    ],
)
def test_parse_dose(dose, slots, as_needed):
    assert parse_dose(dose) == (slots, as_needed)


@pytest.mark.parametrize("dose", ["", "as directed", "0-0-0", "1-x-1", "three"])
def test_parse_dose_refuses_unclear(dose):
    with pytest.raises(DoseError):
        parse_dose(dose)


@pytest.mark.parametrize(
    "text, days",
    [("x 30 days", 30), ("for 2 weeks", 14), ("1 month", 30), ("5d", 5),
     ("continue", None), ("long term", None), (None, None), ("", None)],
)
def test_parse_duration(text, days):
    assert parse_duration(text) == days


def test_clean_prescription_is_accepted():
    r = check_prescription(TRANSCRIPT)
    assert [m.name for m in r.accepted] == ["Amlodipine", "Metformin", "Cough syrup", "Paracetamol"]
    assert r.rejected == []
    aml = r.accepted[0]
    assert aml.strength == "5 mg" and aml.slots == {"morning": 1, "night": 1}
    assert aml.duration_days == 30
    assert aml.describe() == "Amlodipine 5 mg — 1 tablet morning, 1 tablet night · 30 days · after food"
    assert r.accepted[2].describe().startswith("Cough syrup — 5 ml morning, 5 ml afternoon, 5 ml night")
    assert r.accepted[3].as_needed
    # no strength on the syrup is flagged; the photo wasn't double-read
    assert any("No strength is written for Cough syrup" in f for f in r.flags)
    assert any("wasn't read a second time" in f for f in r.flags)


@pytest.mark.parametrize("form, verbatim, canon", [
    ("Tab.", "Tab. X 5mg OD", "tablet"), ("caps", "", "capsule"), ("", "Syp. X 5 ml TDS", "syrup"),
    (None, "X 5mg OD", "tablet"), ("ointment", "", "ointment"),
])
def test_normalize_form(form, verbatim, canon):
    from carecircle.meds import normalize_form
    assert normalize_form(form, verbatim) == canon


def test_tab_abbreviation_reads_as_tablets():
    t = {"lines": [{"verbatim": "Tab. Amlodipine 5mg 1-0-1", "name": "Amlodipine", "strength": "5mg",
                    "form": "Tab.", "dose": "1-0-1"}]}
    assert check_prescription(t).accepted[0].describe().startswith("Amlodipine 5 mg — 1 tablet morning")


def test_hallucinated_name_is_kept_out():
    bad = {"lines": [{"verbatim": "Tab. Amlodipine 5mg 1-0-1", "name": "Atenolol",
                      "strength": "5mg", "dose": "1-0-1"}]}
    r = check_prescription(bad)
    assert r.accepted == []
    assert "isn't in this line" in r.rejected[0][1]


def test_changed_strength_is_kept_out():
    bad = {"lines": [{"verbatim": "Tab. Amlodipine 5mg 1-0-1", "name": "Amlodipine",
                      "strength": "10 mg", "dose": "1-0-1"}]}
    assert check_prescription(bad).accepted == []


def test_invented_dose_is_kept_out():
    bad = {"lines": [{"verbatim": "Tab. Amlodipine 5mg as directed", "name": "Amlodipine",
                      "strength": "5mg", "dose": "1-0-1"}]}
    r = check_prescription(bad)
    assert r.accepted == [] and "dose isn't written" in r.rejected[0][1]


def test_unreadable_dose_is_kept_out_with_advice_to_ask():
    bad = {"lines": [{"verbatim": "Tab. Amlodipine 5mg as directed", "name": "Amlodipine",
                      "strength": "5mg", "dose": "as directed"}]}
    r = check_prescription(bad)
    assert r.accepted == [] and "ask the doctor or pharmacist" in r.rejected[0][1]


def test_duplicate_and_frequency_are_flagged():
    t = {"lines": [
        {"verbatim": "Tab Pantoprazole 40mg OD", "name": "Pantoprazole", "strength": "40mg", "dose": "OD"},
        {"verbatim": "Tab Pantoprazole 40mg 1-0-1", "name": "Pantoprazole", "strength": "40mg", "dose": "1-0-1"},
        {"verbatim": "Tab Vitamin C 500mg 2-2-2", "name": "Vitamin C", "strength": "500mg", "dose": "2-2-2"},
    ]}
    r = check_prescription(t)
    assert any("written twice" in f for f in r.flags)
    assert any("6 doses a day" in f for f in r.flags)


def test_independent_photo_read_confirms_or_holds_back():
    ocr = "Dr. A. Mehta\nTab. Amlodipine 5mg 1-0-1 x 30 days after food\nTab Metformin 500mg BD with meals\n"
    r = check_prescription(TRANSCRIPT, ocr_text=ocr)
    assert [m.name for m in r.accepted] == ["Amlodipine", "Metformin"]
    assert all("against the photo" in why for _, why in r.rejected)
    assert not any("wasn't read a second time" in f for f in r.flags)


def test_card_and_schedule_text():
    r = check_prescription(TRANSCRIPT)
    title, detail = card_text(r, "Ma")
    assert title == "Add 4 medicines to Ma's schedule?"
    assert "• Metformin 500 mg — 1 tablet morning, 1 tablet night · with meals" in detail
    assert "not medical advice" in detail
    md = schedule_markdown(r.accepted, "Ma")
    assert "## 🌅 Morning — 8:00 AM" in md and "## 🌙 Night — 9:00 PM" in md
    assert "**Amlodipine 5 mg** — 1 tablet (after food)" in md
    assert "## 🩹 Only when needed" in md and "**Paracetamol 650 mg** — for fever" in md
