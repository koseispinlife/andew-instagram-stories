"""Drive公開フォルダから商品写真を取得する。

カテゴリごとに写真プール(CATEGORY_SOURCESの元写真フォルダ群)を持ち、
「そのカテゴリが投稿に登場するたびに次の写真へ進む」ローテーションで
1枚選んでダウンロードする。プールに無いカテゴリは従来どおり
andew-story-photos のサブフォルダ / ルート直下 <category>.jpg を使う。
"""

import csv
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT_FOLDER_ID = os.getenv("PHOTO_FOLDER_ID", "1_5yQ9fz4b7cHJ8vqPv41ExTTsi8J1ZX3")
OUTPUT_DIR = Path("assets/product_photos")
SCHEDULE_CSV = Path(os.getenv("STORY_SCHEDULE_CSV", "content/story_schedule.csv"))
START_DATE = os.getenv("STORY_START_DATE", "2026-07-15")

# カテゴリ → 元写真フォルダ(公開)のIDリスト。複数指定可(順に連結)。
CATEGORY_SOURCES = {
    "variety": ["1MIKkk3mvaHZbrysnHJ_jJBXoYS8jG88c"],   # ミルクタブレット
    "flavors": ["179rA_-dM2QHkHqcw6lsAkSSyDW7hkU7b",    # 5種類セット
                "1y9V3V0o-3OJRrw2G7yrHUb7dlMhBLgbs"],   # 新パッケージ/5種類セット
    "nama": ["1pRJIe9kIzdsaHVX13UAIjMkUT7w_Xo3p"],      # 生チョコノーマル
    "matcha": ["1LpU6vVaXuaUucZNIy_Ew4Pc9PhvQ7r8-"],    # 新パッケージ/抹茶
    "fruit": ["18kSdy1Q8yRgoWT1nJ8xiFKrDLCRMv-mX",      # フルーツタブレット
              "1n3yyZlW7Q5SyiyQwwBaMh4g2B6Cgzflx"],     # 新パッケージ/フルーツ
    "strawberry": ["1yIk1cotYN3uPPI_nJ2yxfCdeEup7djak", # いちごキューブチョコ
                   "1jxiuyH6YWpgfvJtA-BiA1_DRr-yxywCF"],# 新パッケージ/いちご
    "gift": ["1nOmEf2JNWd_YpIEyfWib2c9N5AAmTJXx"],      # ギフトセット
    "wrapping": ["1Xxgn5km4N3mwG3A_m159NRRsOMJ0ytQs"],  # 紙袋
    "donation": ["1sKZu5-mRJW7nqtdvzduEvmeYPJ3v3LKi"],  # 寄付パッケージ
    "night": ["1DXJgQkDP_cedJQE-w3w3tiwm0K-tRX4_"],     # ナイトショコラ
    "icecocoa": ["13aj8swmNvaUSbpNuacZkkpVns4Wts0pQ"],  # ココア/アイスココア
    "cocoa": ["1NsSZ1NUESIP6VVIYzUYI_GBYSuUJVwgS"],     # ココア/ミルクココア
}

# カテゴリ別の除外ファイル名(目視監査で商品と合わないと判定したもの)
CATEGORY_EXCLUDES = {
    # 生チョコノーマル内に同居しているフルーツタブレットのカット
    "nama": {
        "DSC_8161.jpg", "DSC_8162.jpg", "DSC_8163.jpg", "DSC_8164.jpg",
        "DSC_8165.jpg", "DSC_8166.jpg", "DSC_8167.jpg", "DSC_8175.jpg",
        "DSC_8176.jpg", "DSC_8177.jpg", "DSC_8179.jpg", "DSC_8180.jpg",
        "DSC_8181.jpg", "DSC_8182.jpg",
        # 旧キュレーションフォルダ由来(保険)
        "nama-02.jpg", "nama-03.jpg", "nama-04.jpg", "nama-05.jpg", "nama-06.jpg",
    },
    "family": {"family-01.jpg"},      # キーボード写真(使いすぎ)
    "materials": {"materials-01.jpg"}, # fruit枠と同構図
}

CATEGORIES = [
    "tablet", "materials", "gift", "cocoa", "flavors", "nama", "family",
    "egift", "donation", "praline", "fruit", "matcha", "icecocoa", "night",
    "concept", "variety", "nutrition", "wrapping", "voice", "andyou", "strawberry",
]

ENTRY_RE = re.compile(
    r'href="https://drive\.google\.com/(file/d/|drive/folders/)([\w-]+)[^"]*"[^>]*>.*?'
    r'<div class="flip-entry-title">([^<]+)</div>',
    re.DOTALL,
)


def list_folder(folder_id: str) -> tuple[dict[str, str], dict[str, str]]:
    """公開フォルダ内の {name: id} を (files, folders) で返す。"""
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    html = requests.get(url, timeout=60).text
    files: dict[str, str] = {}
    folders: dict[str, str] = {}
    for kind, entry_id, name in ENTRY_RE.findall(html):
        if kind.startswith("file"):
            files[name.strip()] = entry_id
        else:
            folders[name.strip()] = entry_id
    return files, folders


def image_entries(files: dict[str, str], category: str) -> list[tuple[str, str]]:
    excludes = CATEGORY_EXCLUDES.get(category, set())
    return sorted(
        (name, fid) for name, fid in files.items()
        if name.lower().endswith((".jpg", ".jpeg", ".png")) and name not in excludes
    )


def download(file_id: str, dest: Path) -> None:
    urls = [
        f"https://drive.google.com/uc?export=download&id={file_id}",
        # 大容量ファイルはウイルススキャン警告HTMLが返るため confirm 付きで再試行
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
    ]
    for url in urls:
        response = requests.get(url, timeout=180, allow_redirects=True)
        response.raise_for_status()
        content = response.content
        if not content[:5].lstrip().startswith(b"<"):
            dest.write_bytes(content)
            return
    raise RuntimeError(f"HTML response for {file_id} (not an image)")


def load_schedule_positions() -> tuple[dict[str, int], int]:
    """有効な行の並びから カテゴリ → 行位置 と 総行数 を返す。"""
    if not SCHEDULE_CSV.exists():
        return {}, 0
    with SCHEDULE_CSV.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("enabled", "true").lower() == "true"]
    positions: dict[str, int] = {}
    for i, row in enumerate(rows):
        stem = Path(row.get("source_image", "")).stem
        if stem:
            positions.setdefault(stem, i)
    return positions, len(rows)


def pick_index(category: str, today_ordinal: int, n: int,
               positions: dict[str, int], total_rows: int) -> int:
    """このカテゴリの「何回目の登場か」を写真番号にする。

    登場のたびに必ず次の写真へ進むので、プールの枚数だけ登場するまで
    同じ写真は使われない(n枚 × 登場間隔日数の間、重複なし)。
    """
    start_ord = date.fromisoformat(START_DATE).toordinal()
    days = today_ordinal - start_ord
    if category in positions and total_rows > 0 and days >= 0:
        r = positions[category]
        half_steps = days * 2 + 1  # 今日の夜スロットまで
        appearances = (half_steps - r) // total_rows
        if appearances < 0:
            appearances = 0
        return appearances % n
    return (today_ordinal + sum(ord(c) for c in category)) % n


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today_ordinal = int(os.getenv("FAKE_ORD") or datetime.now(ZoneInfo("Asia/Tokyo")).date().toordinal())
    positions, total_rows = load_schedule_positions()

    root_files, root_folders = list_folder(ROOT_FOLDER_ID)

    for category in CATEGORIES:
        dest = OUTPUT_DIR / f"{category}.jpg"

        # 1) 元写真フォルダのプール(最優先)
        if category in CATEGORY_SOURCES:
            pool: list[tuple[str, str]] = []
            for fid in CATEGORY_SOURCES[category]:
                sub_files, _ = list_folder(fid)
                pool.extend(image_entries(sub_files, category))
            if pool:
                index = pick_index(category, today_ordinal, len(pool), positions, total_rows)
                name, file_id = pool[index]
                download(file_id, dest)
                print(f"{category}: pool ({len(pool)} photos) #{index} -> {name}")
                continue
            print(f"{category}: pool EMPTY, falling back", file=sys.stderr)

        # 2) andew-story-photos のサブフォルダ(従来)
        if category in root_folders:
            sub_files, _ = list_folder(root_folders[category])
            images = image_entries(sub_files, category)
            if images:
                index = pick_index(category, today_ordinal, len(images), positions, total_rows)
                name, file_id = images[index]
                download(file_id, dest)
                print(f"{category}: subfolder ({len(images)} photos) #{index} -> {name}")
                continue

        # 3) ルート直下の <category>.jpg (後方互換)
        if f"{category}.jpg" in root_files:
            download(root_files[f"{category}.jpg"], dest)
            print(f"{category}: flat file")
        else:
            print(f"{category}: NOT FOUND", file=sys.stderr)

    missing = [c for c in CATEGORIES if not (OUTPUT_DIR / f"{c}.jpg").exists()]
    if missing:
        raise SystemExit(f"Missing photos: {missing}")


if __name__ == "__main__":
    main()
