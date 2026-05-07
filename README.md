# Study Finish Planner

本、参考書、講義資料、資格教材など、ページ数のある学習を自分の条件で計画できるアプリです。

## できること

- 教材名、現在ページ、目標ページ、開始日、締切日の設定
- 残りページ数、残り日数、1日あたりの必要ページ数の自動計算
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

## 使い方

[https://kabashima-yoshiaki.github.io/studying-app/](https://kabashima-yoshiaki.github.io/studying-app/)をブラウザで開くと使えます。

## Python 版

`app.py` にはローカル専用の Python 版もあります。
ただし、外部公開は静的版を使う前提にしています。
