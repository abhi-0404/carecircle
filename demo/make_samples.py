"""Draw the synthetic documents the demo uses: a prescription and a lab bill.

Every image carries a SAMPLE watermark and a fictional clinic. CareCircle's demo
never uses real medical or financial records.

    uv run --group demo python demo/make_samples.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "samples"
W, H = 1240, 1754  # A4 at 150 dpi

PRESCRIPTION = {
    "clinic": "Sunrise Heart Clinic (fictional)",
    "address": "12 Station Road, Patna  ·  +91 00000 00000",
    "doctor": "Dr. R. Kapoor, MD (Cardiology)  ·  sample doctor",
    "patient": "Mrs. S. Sharma (sample)   Age 68   F",
    "date": "03/11/2026",
    "lines": [
        "1. Tab. Amlodipine 5mg 1-0-1 x 30 days after food",
        "2. Tab. Metformin 500 mg BD with meals",
        "3. Tab. Atorvastatin 10mg 0-0-1 x 30 days",
        "4. Tab. Paracetamol 650 mg SOS for fever",
    ],
    "advice": "Walk 30 min daily. Low salt diet. Review after 1 month with lipid profile.",
}

# What the @meds agent is expected to transcribe from the image above. Used by
# tests and by the offline demo, which replays it instead of calling a model.
TRANSCRIPT = {
    "lines": [
        {"verbatim": "Tab. Amlodipine 5mg 1-0-1 x 30 days after food", "name": "Amlodipine",
         "strength": "5mg", "form": "tablet", "dose": "1-0-1", "duration": "30 days",
         "timing": "after food"},
        {"verbatim": "Tab. Metformin 500 mg BD with meals", "name": "Metformin",
         "strength": "500 mg", "form": "tablet", "dose": "BD", "timing": "with meals"},
        {"verbatim": "Tab. Atorvastatin 10mg 0-0-1 x 30 days", "name": "Atorvastatin",
         "strength": "10mg", "form": "tablet", "dose": "0-0-1", "duration": "30 days"},
        {"verbatim": "Tab. Paracetamol 650 mg SOS for fever", "name": "Paracetamol",
         "strength": "650 mg", "form": "tablet", "dose": "SOS", "timing": "for fever"},
    ]
}

BILL = {
    "lab": "CityCare Diagnostics (fictional)",
    "patient": "Mrs. S. Sharma (sample)",
    "date": "05/11/2026",
    "items": [("Lipid profile", 900), ("HbA1c", 650), ("Kidney function test", 850)],
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _watermark(img: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = img.width / 2, img.height / 2
    for text, size, dy in (("SAMPLE", 150, -110), ("NOT A REAL DOCUMENT", 58, 70)):
        f = _font(size, bold=True)
        tw = d.textlength(text, font=f)
        d.text((cx - tw / 2, cy + dy), text, font=f, fill=(200, 30, 30, 70))
    layer = layer.rotate(24, center=(cx, cy))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def _photo_look(img: Image.Image, seed: int) -> Image.Image:
    """A slight tilt and blur, like a phone photo of paper."""
    rnd = random.Random(seed)
    img = img.rotate(rnd.uniform(-1.5, 1.5), expand=True, fillcolor=(236, 232, 224))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def prescription() -> Image.Image:
    p = PRESCRIPTION
    img = Image.new("RGB", (W, H), (252, 251, 247))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 190], fill=(23, 92, 128))
    d.text((60, 40), p["clinic"], font=_font(54, True), fill="white")
    d.text((60, 115), p["address"], font=_font(28), fill=(220, 236, 245))
    d.text((60, 230), p["doctor"], font=_font(32, True), fill=(30, 30, 30))
    d.text((60, 300), f"Patient: {p['patient']}", font=_font(30), fill=(30, 30, 30))
    d.text((W - 360, 300), f"Date: {p['date']}", font=_font(30), fill=(30, 30, 30))
    d.line([60, 360, W - 60, 360], fill=(23, 92, 128), width=3)
    d.text((60, 400), "Rx", font=_font(72, True), fill=(23, 92, 128))
    y = 520
    for line in p["lines"]:
        d.text((90, y), line, font=_font(38), fill=(20, 20, 60))
        y += 90
    d.text((60, y + 40), "Advice:", font=_font(32, True), fill=(30, 30, 30))
    d.text((60, y + 90), p["advice"], font=_font(30), fill=(40, 40, 40))
    d.text((W - 420, H - 220), "Signature (sample)", font=_font(28), fill=(80, 80, 80))
    d.line([W - 440, H - 240, W - 80, H - 240], fill=(80, 80, 80), width=2)
    return _photo_look(_watermark(img), seed=7)


def lab_bill() -> Image.Image:
    b = BILL
    img = Image.new("RGB", (W, 1100), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((60, 50), b["lab"], font=_font(50, True), fill=(20, 110, 60))
    d.text((60, 130), f"Bill to: {b['patient']}     Date: {b['date']}", font=_font(30), fill=(30, 30, 30))
    d.line([60, 200, W - 60, 200], fill=(20, 110, 60), width=3)
    y = 250
    for name, amount in b["items"]:
        d.text((80, y), name, font=_font(36), fill=(30, 30, 30))
        d.text((W - 300, y), f"Rs {amount:,}", font=_font(36), fill=(30, 30, 30))
        y += 80
    total = sum(a for _, a in b["items"])
    d.line([60, y + 10, W - 60, y + 10], fill=(120, 120, 120), width=2)
    d.text((80, y + 40), "TOTAL (paid by UPI)", font=_font(40, True), fill=(20, 20, 20))
    d.text((W - 300, y + 40), f"Rs {total:,}", font=_font(40, True), fill=(20, 20, 20))
    return _photo_look(_watermark(img), seed=11)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prescription().save(OUT / "prescription-cardiology.png")
    lab_bill().save(OUT / "lab-bill.png")
    (OUT / "prescription-cardiology.transcript.json").write_text(
        json.dumps(TRANSCRIPT, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote samples to {OUT}")


if __name__ == "__main__":
    main()
