"""The demo's sample prescription must pass the checker exactly as recorded."""

import json
from pathlib import Path

from carecircle.meds import check_prescription, schedule_markdown

SAMPLE = Path(__file__).parents[1] / "demo" / "samples" / "prescription-cardiology.transcript.json"


def test_sample_prescription_is_accepted_in_full():
    r = check_prescription(json.loads(SAMPLE.read_text(encoding="utf-8")))
    assert [m.label() for m in r.accepted] == [
        "Amlodipine 5 mg",
        "Metformin 500 mg",
        "Atorvastatin 10 mg",
        "Paracetamol 650 mg",
    ]
    assert r.rejected == []
    md = schedule_markdown(r.accepted, "Ma")
    # morning: amlodipine + metformin; night: amlodipine + metformin + atorvastatin
    morning = md.split("## 🌅")[1].split("##")[0]
    night = md.split("## 🌙")[1].split("##")[0]
    assert "Amlodipine" in morning and "Metformin" in morning and "Atorvastatin" not in morning
    assert all(n in night for n in ("Amlodipine", "Metformin", "Atorvastatin"))
