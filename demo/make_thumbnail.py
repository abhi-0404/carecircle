"""Draw CareCircle's YouTube thumbnail (1280x720) and dev.to cover (1000x420).

    uv run --no-project --with pillow python demo/make_thumbnail.py

The approval card in the picture is a mock-up of what Switch shows on Discord;
every name and number on it is fictional.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets"
NAVY, SLATE = (15, 23, 42), (30, 41, 59)
AMBER, GREEN, GREY = (251, 191, 36), (22, 163, 74), (203, 213, 225)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def gradient(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), NAVY)
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        row = tuple(int(NAVY[i] + (SLATE[i] - NAVY[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = row
    return img


def card(img: Image.Image, x: int, y: int, w: int, s: float) -> int:
    """The mock approval card; returns its bottom edge. `s` scales the type."""
    d = ImageDraw.Draw(img, "RGBA")
    pad, line = int(26 * s), int(40 * s)
    lines = ["Amlodipine 5 mg: morning, night", "Metformin 500 mg: morning, night", "Atorvastatin 10 mg: night",
             "Paracetamol 650 mg: if needed"]
    h = pad * 2 + int(46 * s) + int(18 * s) + line * len(lines) + int(24 * s) + int(64 * s)
    d.rounded_rectangle([x + 8, y + 12, x + w + 8, y + h + 12], 28, fill=(0, 0, 0, 90))  # shadow
    d.rounded_rectangle([x, y, x + w, y + h], 28, fill=(248, 250, 252))
    cy = y + pad
    d.text((x + pad, cy), "Add 4 medicines to Ma's schedule?", font=font(int(25 * s), True), fill=(15, 23, 42))
    cy += int(46 * s) + int(18 * s)
    for t in lines:
        d.text((x + pad, cy), "•  " + t, font=font(int(25 * s)), fill=(51, 65, 85))
        cy += line
    cy += int(24 * s)
    bw = int(190 * s)
    d.rounded_rectangle([x + pad, cy, x + pad + bw, cy + int(64 * s)], 14, fill=GREEN)
    d.text((x + pad + bw / 2, cy + 32 * s), "Approve", font=font(int(28 * s), True), fill="white", anchor="mm")
    d.rounded_rectangle([x + pad + bw + 16, cy, x + pad + 2 * bw + 16, cy + int(64 * s)], 14, fill=GREY)
    d.text((x + pad + bw * 1.5 + 16, cy + 32 * s), "Reject", font=font(int(28 * s), True), fill=(51, 65, 85), anchor="mm")
    tap = (x + pad + bw * 0.99, cy + 58 * s)  # a fingertip ring on the button's corner, clear of the label
    d.ellipse([tap[0] - 26 * s, tap[1] - 26 * s, tap[0] + 26 * s, tap[1] + 26 * s], fill=(255, 255, 255, 70),
              outline=(255, 255, 255, 230), width=max(3, int(4 * s)))
    d.text((x + 4, y + h + 18 * s), "Illustration of an approval card · fictional data", font=font(int(19 * s)), fill=(148, 163, 184))
    return y + h


def thumbnail() -> Image.Image:
    img = gradient(1280, 720)
    d = ImageDraw.Draw(img)
    y = 110
    for text, colour in (("Three siblings.", "white"), ("Three cities.", "white"), ("One Ma.", AMBER)):
        d.text((70, y), text, font=font(78, True), fill=colour)
        y += 104
    d.rounded_rectangle([70, 500, 70 + 520, 500 + 62], 31, fill=(255, 255, 255, 255))
    d.text((70 + 260, 500 + 31), "AI proposes. People decide.", font=font(32, True), fill=NAVY, anchor="mm")
    d.text((70, 600), "CareCircle", font=font(64, True), fill=AMBER)
    d.text((70, 676), "built on Switch · Discord · Claude", font=font(28), fill=GREY)
    card(img, 720, 170, 500, 1.0)
    return img


def cover() -> Image.Image:
    img = gradient(1000, 420)
    d = ImageDraw.Draw(img)
    y = 70
    for text, colour in (("Three siblings.", "white"), ("Three cities.", "white"), ("One Ma.", AMBER)):
        d.text((50, y), text, font=font(58, True), fill=colour)
        y += 70
    d.text((50, 300), "CareCircle", font=font(46, True), fill=AMBER)
    d.text((50, 360), "AI proposes. People decide.  ·  built on Switch", font=font(22), fill=GREY)
    card(img, 560, 60, 380, 0.75)
    return img


def linkedin() -> Image.Image:
    """1200x627, the size LinkedIn shows without cropping."""
    img = gradient(1200, 627)
    d = ImageDraw.Draw(img)
    y = 62
    for text, colour in (("Three siblings.", "white"), ("Three cities.", "white"), ("One Ma.", AMBER)):
        d.text((64, y), text, font=font(68, True), fill=colour)
        y += 88
    d.rounded_rectangle([64, 340, 64 + 470, 340 + 56], 28, fill=(255, 255, 255, 255))
    d.text((64 + 235, 340 + 28), "AI proposes. People decide.", font=font(29, True), fill=NAVY, anchor="mm")
    d.text((64, 440), "CareCircle", font=font(58, True), fill=AMBER)
    d.text((64, 512), "built on Switch · Discord · Claude", font=font(26), fill=GREY)
    d.text((64, 560), "github.com/abhi-0404/carecircle", font=font(24), fill=GREY)
    card(img, 660, 118, 480, 0.95)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    thumbnail().save(OUT / "thumbnail.png")
    cover().save(OUT / "cover.png")
    linkedin().save(OUT / "linkedin.png")
    print(f"wrote thumbnail.png, cover.png and linkedin.png in {OUT}")


if __name__ == "__main__":
    main()
