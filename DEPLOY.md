# External Deploy Guide

このアプリを外部公開するなら、**静的 Web 版** を GitHub Pages に載せるのがおすすめです。

## 理由

- `index.html` / `styles.css` / `app.js` だけで動く
- サーバーやデータベースが不要
- ユーザーごとの設定は各ブラウザの `localStorage` に保存される

## GitHub Pages 向けに入っているもの

- `.nojekyll`
- `.github/workflows/deploy-pages.yml`

## いちばん簡単な公開方法

### 1. Branch から公開する

1. GitHub のリポジトリを開く
2. `Settings > Pages`
3. `Build and deployment`
4. `Source` を `Deploy from a branch` にする
5. `Branch` を `main`
6. `Folder` を `/(root)` にする
7. `Save`

この方法では、リポジトリ直下の `index.html` がそのまま公開されます。

### 2. GitHub Actions で公開する

`.github/workflows/deploy-pages.yml` を push できるなら、`Settings > Pages` の `Source` を `GitHub Actions` にすれば公開できます。

## 公開 URL

リポジトリが `https://github.com/<user>/<repo>` の場合、通常の公開 URL は:

`https://<user>.github.io/<repo>/`

例:

`https://kabashima-yoshiaki.github.io/studying-app/`

## 補足

- 公開サイトに反映されるのは、GitHub 上の更新です
- 誰かが `main` を更新して公開元に反映されれば、公開サイトも更新されます
- 各ユーザーの入力値はブラウザごとに保存されるため、他人の設定が見えることはありません
