import csv
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


CANVAS_SIZE = (1080, 1920)
SAFE_MARGIN_X = 92
OUTPUT_QUALITY = 92
THEME_COLORS = {
    "concept": ("#f6efe7", "#4a2a20"),
    "product": ("#f3eadf", "#4a2a20"),
    "social-proof": ("#f5eee8", "#4a2a20"),
    "donation": ("#f7efe9", "#4a2a20"),
}


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
    background, ink = THEME_COLORS.get(row.get("theme", "concept"), THEME_COLORS["concept"])
    canvas = Image.new("RGB", CANVAS_SIZE, background)
    draw = ImageDraw.Draw(canvas)

    source_path = row.get("source_image", "").strip()
    if source_path and (root / source_path).exists():
        place_photo(canvas, root / source_path)
    else:
        draw_photo_placeholder(draw, ink)

    draw_copy(draw, row.get("overlay_copy", ""), ink)
    return canvas


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if bold else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
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


def draw_photo_placeholder(draw: ImageDraw.ImageDraw, ink: str) -> None:
    draw.rectangle((0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1]), fill="#f3eadf")
    draw.text((540, 860), "andew", font=font(72, bold=True), fill=ink, anchor="mm")
    draw.text((540, 936), "商品写真を配置してください", font=font(34), fill=ink, anchor="mm")
    draw.text((540, 994), "assets/product_photos", font=font(28), fill=ink, anchor="mm")


def draw_copy(draw: ImageDraw.ImageDraw, copy: str, ink: str) -> None:
    if not copy:
        return
    wrapped = textwrap.wrap(copy, width=20, break_long_words=True, replace_whitespace=False)
    box_top = 1360
    box_bottom = 1666
    line_height = 68
    draw.rounded_rectangle((64, box_top, 1016, box_bottom), radius=36, fill=(255, 250, 245))
    y = box_top + 52
    for line in wrapped:
        draw.text((SAFE_MARGIN_X, y), line, font=font(46, bold=True), fill=ink)
        y += line_height


if __name__ == "__main__":
    main()
