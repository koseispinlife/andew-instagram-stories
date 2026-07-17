import csv
import math
import os
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


CANVAS_SIZE = (1080, 1920)
OUTPUT_QUALITY = 92

STICKER_ORANGE = (250, 126, 30)
STICKER_TEXT = (255, 255, 255)
MENTION_BG = (255, 255, 255, 235)
MENTION_TEXT = (60, 42, 32)
CONCEPT_BG = "#f6efe7"
CONCEPT_INK = "#4a2a20"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    schedule_path = root / os.getenv("STORY_SCHEDULE_CSV", "content/story_schedule.csv")
    output_root = root / os.getenv("STORY_OUTPUT_DIR", "public")

    with schedule_path.open(newline="", encoding="utf-8") as csv_file:
        rows = [row for row in csv.DictReader(csv_file) if row.get("enabled", "true").lower() == "true"]

    for index, row in enumerate(rows, start=1):
        asset_path = row.get("asset_path") or f"stories/story-{index:02}.jpg"
        output_path = output_root / asset_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = render_story(root, row)
        image.save(output_path, quality=OUTPUT_QUALITY, optimize=True)
        print(f"Wrote {output_path}")


def render_story(root: Path, row: dict[str, str]) -> Image.Image:
    canvas = Image.new("RGB", CANVAS_SIZE, CONCEPT_BG)

    source_path = row.get("source_image", "").strip()
    has_photo = bool(source_path) and (root / source_path).exists()
    if has_photo:
        place_photo(canvas, root / source_path)
    else:
        draw_concept_background(canvas)

    paste_sticker_copy(canvas, row.get("overlay_copy", ""), top=210 if has_photo else 640)
    paste_mention_pill(canvas)
    return canvas


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if bold else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def place_photo(canvas: Image.Image, photo_path: Path) -> None:
    photo = Image.open(photo_path).convert("RGB")
    scale = max(CANVAS_SIZE[0] / photo.width, CANVAS_SIZE[1] / photo.height)
    resized = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - CANVAS_SIZE[0]) // 2
    top = (resized.height - CANVAS_SIZE[1]) // 2
    cropped = resized.crop((left, top, left + CANVAS_SIZE[0], top + CANVAS_SIZE[1]))
    canvas.paste(cropped.filter(ImageFilter.SHARPEN), (0, 0))


def draw_concept_background(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.text((540, 1050), "andew", font=font(96, bold=True), fill=CONCEPT_INK, anchor="mm")
    draw.text((540, 1150), "世界一やさしいチョコレート", font=font(34, bold=False), fill=CONCEPT_INK, anchor="mm")


def wrap_japanese(text: str, max_chars: int = 13) -> list[str]:
    """句読点(、。！？)の直後を優先して、きりのいい位置で改行する。"""
    segments = [s for s in re.split(r"(?<=[、。！？!?])", text) if s]
    lines: list[str] = []
    current = ""
    for seg in segments:
        while len(seg) > max_chars:
            if current:
                lines.append(current)
                current = ""
            lines.append(seg[:max_chars])
            seg = seg[max_chars:]
        if current and len(current) + len(seg) > max_chars:
            lines.append(current)
            current = seg
        else:
            current += seg
    if current:
        lines.append(current)
    return lines


def paste_sticker_copy(canvas: Image.Image, copy: str, top: int) -> None:
    copy = (copy or "").strip()
    if not copy:
        return
    lines = wrap_japanese(copy, max_chars=13)

    text_font = font(58, bold=True)
    pad_x, pad_y, gap = 34, 20, 14
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    pills = []
    for line in lines:
        bbox = probe.textbbox((0, 0), line, font=text_font)
        w = bbox[2] - bbox[0] + pad_x * 2
        h = bbox[3] - bbox[1] + pad_y * 2
        pills.append((line, w, h, bbox[1]))

    block_w = max(p[1] for p in pills) + 40
    block_h = sum(p[2] for p in pills) + gap * (len(pills) - 1) + 40
    layer = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)

    y = 20
    for line, w, h, oy in pills:
        x = (block_w - w) // 2
        ldraw.rounded_rectangle((x, y, x + w, y + h), radius=16, fill=STICKER_ORANGE + (255,))
        ldraw.text((x + pad_x, y + pad_y - oy), line, font=text_font, fill=STICKER_TEXT)
        y += h + gap

    paste_x = (CANVAS_SIZE[0] - layer.width) // 2
    canvas.paste(layer, (paste_x, top), layer)


def paste_mention_pill(canvas: Image.Image) -> None:
    text = "@andew_chocolate"
    text_font = font(38, bold=True)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = probe.textbbox((0, 0), text, font=text_font)
    w = bbox[2] - bbox[0] + 56
    h = bbox[3] - bbox[1] + 34
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)
    ldraw.rounded_rectangle((0, 0, w, h), radius=h // 2, fill=MENTION_BG)
    ldraw.text((28, 17 - bbox[1]), text, font=text_font, fill=MENTION_TEXT)
    canvas.paste(layer, ((CANVAS_SIZE[0] - w) // 2, 1770), layer)


if __name__ == "__main__":
    main()
