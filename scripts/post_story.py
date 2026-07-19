import csv
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests


GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0")
GRAPH_API_BASE = os.getenv("GRAPH_API_BASE", f"https://graph.instagram.com/{GRAPH_API_VERSION}")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def graph_post(path: str, data: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{GRAPH_API_BASE}/{path}", data=data, timeout=60)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Graph API returned non-JSON response: {response.text}") from exc

    if not response.ok:
        raise RuntimeError(f"Graph API error {response.status_code}: {payload}")

    return payload


def build_story_url(row: dict[str, str]) -> str:
    direct_url = row.get("asset_url", "").strip()
    if direct_url:
        return direct_url

    asset_path = row.get("asset_path", "").strip().lstrip("/")
    public_base_url = os.getenv("PUBLIC_ASSET_BASE_URL", "").strip().rstrip("/")
    if asset_path and public_base_url:
        return f"{public_base_url}/{asset_path}"

    return ""


def select_story_from_csv(path: str) -> dict[str, str]:
    start_date = date.fromisoformat(os.getenv("STORY_START_DATE", "2026-07-15"))
    today = date.fromisoformat(os.getenv("POST_DATE", local_today().isoformat()))
    posts_per_day = int(os.getenv("POSTS_PER_DAY", "1"))
    post_slot = int(os.getenv("POST_SLOT", str(detect_post_slot(posts_per_day))))

    with open(path, newline="", encoding="utf-8") as csv_file:
        rows = [row for row in csv.DictReader(csv_file) if row.get("enabled", "true").lower() == "true"]

    if not rows:
        raise RuntimeError(f"No enabled rows found in {path}")

    if post_slot < 0 or post_slot >= posts_per_day:
        raise RuntimeError(f"POST_SLOT must be between 0 and {posts_per_day - 1}")

    index = (((today - start_date).days * posts_per_day) + post_slot) % len(rows)
    return rows[index]


def detect_post_slot(posts_per_day: int) -> int:
    if posts_per_day <= 1:
        return 0

    schedule = os.getenv("GITHUB_EVENT_SCHEDULE", "").strip()
    if schedule == "0 22 * * *":
        return 0
    if schedule == "0 9 * * *":
        return 1

    current_hour = datetime.now(local_timezone()).hour
    return 0 if current_hour < 12 else 1


def local_timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("POST_TIMEZONE", "Asia/Tokyo"))


def local_today() -> date:
    return datetime.now(local_timezone()).date()


def apply_random_delay() -> None:
    max_minutes = int(os.getenv("RANDOM_DELAY_MAX_MINUTES", "0"))
    if max_minutes <= 0:
        return

    if os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch" and os.getenv("ENABLE_JITTER_ON_MANUAL") != "true":
        print("Skipping random delay for manual workflow_dispatch run.")
        return

    posts_per_day = int(os.getenv("POSTS_PER_DAY", "1"))
    post_slot = int(os.getenv("POST_SLOT", str(detect_post_slot(posts_per_day))))
    offset_seconds = random.SystemRandom().randint(0, max_minutes * 60)
    now = datetime.now(local_timezone())

    if posts_per_day == 2 and post_slot in {0, 1}:
        window_start_hour = 7 if post_slot == 0 else 18
        window_start = now.replace(hour=window_start_hour, minute=0, second=0, microsecond=0)
        target_time = window_start + timedelta(seconds=offset_seconds)
        sleep_seconds = max(0, int((target_time - now).total_seconds()))
    else:
        target_time = now + timedelta(seconds=offset_seconds)
        sleep_seconds = offset_seconds

    print(f"Random target time: {target_time.isoformat(timespec='minutes')}")
    if sleep_seconds <= 0:
        print("Target time has already passed; publishing now.")
        return

    print(f"Sleeping for {sleep_seconds / 60:.1f} minutes")
    time.sleep(sleep_seconds)


def main() -> None:
    ig_user_id = require_env("IG_USER_ID")
    access_token = require_env("IG_ACCESS_TOKEN")
    schedule_path = os.getenv("STORY_SCHEDULE_CSV")

    apply_random_delay()

    if schedule_path:
        selected_story = select_story_from_csv(schedule_path)
        story_url = build_story_url(selected_story)
        media_kind = selected_story.get("media_kind", "image").strip().lower()
        print(f"Selected story: {selected_story.get('title', '(untitled)')}")
    else:
        story_url = require_env("STORY_URL")
        media_kind = os.getenv("STORY_MEDIA_KIND", "image").strip().lower()

    if media_kind not in {"image", "video"}:
        raise RuntimeError("STORY_MEDIA_KIND must be either 'image' or 'video'")
    if not story_url:
        raise RuntimeError("Story asset URL is empty")

    create_payload = {"media_type": "STORIES", "access_token": access_token}
    if media_kind == "image":
        create_payload["image_url"] = story_url
    else:
        create_payload["video_url"] = story_url

    container = graph_post(f"{ig_user_id}/media", create_payload)
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError(f"Container response did not include an id: {container}")

    time.sleep(int(os.getenv("PUBLISH_DELAY_SECONDS", "10")))

    published = graph_post(
        f"{ig_user_id}/media_publish",
        {"creation_id": creation_id, "access_token": access_token},
    )
    print(f"Published Instagram story: {published}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
