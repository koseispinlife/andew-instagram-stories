"""Drive公開フォルダから商品写真を取得する。

カテゴリ名のサブフォルダ(例: nama/)があれば、その中の画像を
日付ローテーションで1枚選んでダウンロードする。
サブフォルダがなければ、ルート直下の <category>.jpg を使う(後方互換)。
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT_FOLDER_ID = os.getenv("PHOTO_FOLDER_ID", "1_5yQ9fz4b7cHJ8vqPv41ExTTsi8J1ZX3")
OUTPUT_DIR = Path("assets/product_photos")

CATEGORIES = [
    "tablet", "ingredients", "gift", "cocoa", "flavors", "nama", "family",
    "egift", "donation", "praline", "fruit", "matcha", "icecocoa", "night",
    "concept", "variety", "nutrition", "wrapping", "voice", "andyou",
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


def download(file_id: str, dest: Path) -> None:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url, timeout=120, allow_redirects=True)
    response.raise_for_status()
    dest.write_bytes(response.content)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today_ordinal = datetime.now(ZoneInfo("Asia/Tokyo")).date().toordinal()

    root_files, root_folders = list_folder(ROOT_FOLDER_ID)

    for category in CATEGORIES:
        dest = OUTPUT_DIR / f"{category}.jpg"
        if category in root_folders:
            sub_files, _ = list_folder(root_folders[category])
            images = sorted(
                (name, fid) for name, fid in sub_files.items()
                if name.lower().endswith((".jpg", ".jpeg", ".png"))
            )
            if images:
                index = (today_ordinal + sum(ord(c) for c in category)) % len(images)
                name, file_id = images[index]
                download(file_id, dest)
                print(f"{category}: subfolder ({len(images)} photos) -> {name}")
                continue
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
