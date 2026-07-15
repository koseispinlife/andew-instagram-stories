# Instagram Story Auto Posting for andew

GitHub Actionsを使って、andewのInstagramストーリーを毎日2回自動投稿する構成です。

## できること

- `content/story_schedule.csv` から投稿内容を選ぶ
- 商品写真 + コメントの1080x1920pxストーリー画像を生成する
- GitHub Pagesでストーリー画像を公開する
- Instagram Graph APIでストーリー投稿する
- 投稿時間を07:00-11:00 JST、18:00-22:00 JSTの範囲でランダムに揺らす

## GitHub Secrets

`Settings` -> `Secrets and variables` -> `Actions` -> `Secrets` に登録します。

| Secret | 内容 |
| --- | --- |
| `IG_USER_ID` | Instagram professional account ID |
| `IG_ACCESS_TOKEN` | Instagram Graph APIのアクセストークン |

## GitHub Variables

`Settings` -> `Secrets and variables` -> `Actions` -> `Variables` に登録します。

| Variable | 内容 |
| --- | --- |
| `PUBLIC_ASSET_BASE_URL` | GitHub PagesのURL。例: `https://koseispinlife.github.io/andew-instagram-stories` |

## 商品写真

Google Driveの商品写真をダウンロードし、`assets/product_photos/` に置きます。

`content/story_schedule.csv` の `source_image` に合わせて、まずは以下の名前にするとそのまま使えます。

- `tablet.jpg`
- `ingredients.jpg`
- `gift.jpg`
- `cocoa.jpg`
- `flavors.jpg`
- `nama.jpg`
- `family.jpg`
- `egift.jpg`
- `donation.jpg`

## ストーリー画像生成

ローカルで確認する場合:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_story_assets.py
```

出力先:

```text
public/stories/story-01.jpg
public/stories/story-02.jpg
...
```

GitHubでは `Build and Deploy Story Assets` ワークフローが画像生成とPages公開を行います。

## 投稿スケジュール

AM1:00-6:00を避け、毎日2回投稿します。

- 09:00 JSTの前後2時間: 07:00-11:00 JST
- 20:00 JSTの前後2時間: 18:00-22:00 JST

GitHub Actionsのcronは固定時刻しか指定できないため、ウィンドウ開始時刻に起動し、`0-240分` ランダム待機して投稿します。

## 手動テスト

1. `Build and Deploy Story Assets` を手動実行する
2. GitHub PagesのURLを `PUBLIC_ASSET_BASE_URL` に登録する
3. `Post Instagram Story` を手動実行する

手動実行時はランダム待機せず、すぐ投稿します。

## 注意

- Instagram Graph APIは、投稿素材を公開HTTPS URLから取得します。
- Google Driveの共有リンクを直接投稿素材URLにする運用は失敗しやすいため、GitHub Pagesなどで公開します。
- ログインID/パスワードを使う非公式Botやブラウザ自動操作は使いません。
- 寄付に触れる場合は、必ず寄付付き商品に限定します。
