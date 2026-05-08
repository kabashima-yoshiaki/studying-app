# Study Finish Planner

本や教材のページ学習を、現在ページ・目標ページ・締切から逆算して進められる学習計画アプリです。

## 公開URL

[https://kabashima-yoshiaki.github.io/studying-app/](https://kabashima-yoshiaki.github.io/studying-app/)

## できること

- 教材名、現在ページ、目標ページ、開始日、締切日の設定
- 残りページ数、残り日数、1日あたりの必要ページ数の自動計算
- 指定日までに何ページ必要かの確認
- 週ごとの到達ライン表示
- 直近14日の学習目安表示
- 進捗のローカル保存
- 静的版の PWA 対応

## 保存について

- 公開向けの静的版はブラウザの `localStorage` に保存します
- ほかの人の設定や進捗と混ざることはありません
- 別のブラウザや別の端末には自動同期されません

## 主なファイル

- `index.html`
- `styles.css`
- `app.js`
- `manifest.json`
- `service-worker.js`
- `icons/icon.svg`
- `app.py`

## 静的版の使い方

`index.html` をブラウザで開くと使えます。  
GitHub Pages に公開する場合は `DEPLOY.md` を参照してください。

## Python版

`app.py` にはローカル専用の Python 版もあります。  
ただし、外部公開は静的版を使う前提にしています。
