from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timedelta, timezone
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    ZoneInfo = None

    class ZoneInfoNotFoundError(Exception):
        pass

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "planner_data.json"


def build_tokyo_timezone():
    # Asia/Tokyo has no daylight saving time, so UTC+9 is a safe fallback.
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Tokyo")
        except ZoneInfoNotFoundError:
            pass

    return timezone(timedelta(hours=9), name="JST")


TOKYO = build_tokyo_timezone()

DEFAULT_STATE = {
    "current_page": 100,
    "target_page": 495,
    "start_date": "2026-04-24",
    "deadline_date": "2026-06-24",
    "progress_log": [
        {"date": "2026-04-24", "page": 100},
    ],
}

FLASH_MESSAGES = {
    "plan-saved": "学習条件を保存しました。",
    "progress-saved": "今日の進捗を保存しました。",
    "progress-reset": "進捗記録をリセットしました。",
}

STYLE_CSS = """
:root {
  --bg: #f7f1e5;
  --bg-deep: #efe2c4;
  --panel: rgba(255, 250, 240, 0.9);
  --text: #1f2a1d;
  --muted: #5c6651;
  --accent: #bc5a2c;
  --accent-soft: #efd8ca;
  --green: #426a4f;
  --green-soft: #dce6d9;
  --line: rgba(31, 42, 29, 0.12);
  --shadow: 0 22px 55px rgba(76, 53, 18, 0.12);
  --radius-xl: 28px;
  --radius-lg: 20px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  font-family: "BIZ UDPGothic", "Yu Gothic UI", "Hiragino Sans", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(188, 90, 44, 0.14), transparent 30%),
    radial-gradient(circle at top right, rgba(66, 106, 79, 0.15), transparent 28%),
    linear-gradient(160deg, var(--bg) 0%, var(--bg-deep) 100%);
}

.page-shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 32px 0 48px;
}

.hero,
.card,
.flash-banner {
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: var(--shadow);
}

.hero {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 20px;
  padding: 28px;
  border-radius: 36px;
  background: linear-gradient(135deg, rgba(255, 247, 236, 0.94), rgba(255, 243, 228, 0.76));
}

.hero-copy h1,
.section-heading h2,
.summary-card strong,
.progress-ring-inner span,
.milestone-range,
.sprint-focus {
  font-family: Georgia, "Yu Mincho", serif;
}

.eyebrow,
.section-kicker {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.78rem;
  color: var(--accent);
}

.hero-copy h1 {
  margin: 10px 0 12px;
  font-size: clamp(2rem, 4vw, 3.5rem);
  line-height: 1.04;
}

.hero-text,
.python-note,
.summary-card p,
.status-banner,
.saved-progress,
.milestone-week,
.sprint-date {
  color: var(--muted);
}

.hero-text,
.python-note,
.status-banner {
  line-height: 1.7;
}

.python-note {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.62);
}

.hero-panel {
  display: grid;
  gap: 14px;
}

.hero-stat,
.summary-card,
.milestone-item,
.sprint-item,
.saved-progress,
.flash-banner {
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
}

.hero-stat {
  padding: 18px 20px;
}

.hero-stat.accent {
  background: linear-gradient(135deg, rgba(188, 90, 44, 0.18), rgba(255, 250, 240, 0.92));
}

.hero-stat-label,
.saved-progress-label,
.checkpoint-label,
.milestone-target-label,
.sprint-page-label {
  display: block;
  font-size: 0.9rem;
  color: var(--muted);
}

.hero-stat strong {
  display: block;
  margin-top: 6px;
  font-size: clamp(1.5rem, 3vw, 2rem);
}

.flash-banner {
  margin: 18px 0 0;
  padding: 14px 18px;
}

.layout {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 20px;
  margin-top: 20px;
}

.card {
  padding: 24px;
  border-radius: var(--radius-xl);
  background: var(--panel);
}

.section-heading {
  margin-bottom: 18px;
}

.section-heading h2 {
  margin: 8px 0 0;
  font-size: 1.8rem;
}

.planner-form,
.log-form {
  display: grid;
  gap: 14px;
}

.planner-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.log-form {
  grid-template-columns: 1fr auto;
  align-items: end;
  margin-top: 22px;
}

label {
  display: grid;
  gap: 8px;
  font-size: 0.95rem;
}

input,
button {
  font: inherit;
}

input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(31, 42, 29, 0.12);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--text);
}

button {
  border: none;
  border-radius: 999px;
  padding: 14px 18px;
  cursor: pointer;
  color: #fffdf9;
  background: linear-gradient(135deg, var(--accent), #d27a4f);
}

.ghost-button {
  background: transparent;
  color: var(--green);
  border: 1px solid rgba(66, 106, 79, 0.22);
}

.status-banner {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(66, 106, 79, 0.12), rgba(255, 255, 255, 0.62));
  border: 1px solid rgba(66, 106, 79, 0.12);
}

.status-banner.warning {
  background: linear-gradient(135deg, rgba(188, 90, 44, 0.18), rgba(255, 255, 255, 0.62));
  border-color: rgba(188, 90, 44, 0.22);
}

.status-banner.error {
  background: linear-gradient(135deg, rgba(167, 62, 62, 0.18), rgba(255, 255, 255, 0.62));
  border-color: rgba(167, 62, 62, 0.22);
}

.status-banner.success {
  background: linear-gradient(135deg, rgba(66, 106, 79, 0.18), rgba(255, 255, 255, 0.72));
  border-color: rgba(66, 106, 79, 0.22);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.summary-card {
  padding: 18px;
}

.summary-card span {
  font-size: 0.88rem;
  color: var(--muted);
}

.summary-card strong {
  display: block;
  margin: 10px 0 6px;
  font-size: 2rem;
}

.summary-card p {
  margin: 0;
}

.progress-wrap {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 18px;
  align-items: center;
}

.progress-ring {
  width: 164px;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, rgba(255, 248, 238, 0.96) 56%, transparent 57%),
    conic-gradient(var(--accent) 0 var(--progress), rgba(66, 106, 79, 0.16) var(--progress) 100%);
  display: grid;
  place-items: center;
}

.progress-ring-inner {
  display: grid;
  place-items: center;
  width: 116px;
  aspect-ratio: 1;
  border-radius: 50%;
  background: rgba(255, 251, 246, 0.96);
}

.progress-ring-inner span {
  font-size: 2rem;
}

.progress-copy p {
  margin: 0;
  line-height: 1.7;
}

.mini-goal {
  margin-top: 8px !important;
  font-size: 1.1rem;
  color: var(--text) !important;
}

.saved-progress {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: 18px;
  padding: 16px 18px;
}

.saved-progress strong {
  display: block;
  margin-top: 6px;
  color: var(--text);
}

.milestone-list,
.sprint-list {
  display: grid;
  gap: 12px;
}

.milestone-item,
.sprint-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 16px 18px;
}

.milestone-range,
.milestone-target,
.sprint-focus,
.sprint-page {
  display: block;
  margin-top: 6px;
  font-size: 1.08rem;
}

.milestone-target-wrap,
.sprint-page-wrap {
  text-align: right;
}

.footer-note {
  margin-top: 20px;
  font-size: 0.95rem;
  color: var(--muted);
}

@media (max-width: 980px) {
  .hero,
  .layout {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .page-shell {
    width: min(100% - 20px, 100%);
    padding-top: 16px;
  }

  .hero,
  .card {
    padding: 20px;
    border-radius: 24px;
  }

  .planner-form,
  .summary-grid,
  .log-form,
  .progress-wrap {
    grid-template-columns: 1fr;
  }

  .progress-ring {
    margin-inline: auto;
  }

  .saved-progress,
  .milestone-item,
  .sprint-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .milestone-target-wrap,
  .sprint-page-wrap {
    text-align: left;
  }
}
"""


def clone_data(value):
    return json.loads(json.dumps(value))


def today_jst() -> date:
    return datetime.now(TOKYO).date()


def today_iso() -> str:
    return today_jst().isoformat()


def default_start_date() -> date:
    return date.fromisoformat(DEFAULT_STATE["start_date"])


def default_deadline_date() -> date:
    return date.fromisoformat(DEFAULT_STATE["deadline_date"])


def e(value) -> str:
    return escape(str(value), quote=True)


def parse_iso_date(value: str, fallback: date) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


def sanitize_int(value, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def clamp(value: int, minimum: int, maximum: int) -> int:
    return min(max(value, minimum), maximum)


def sanitize_progress_log(progress_log, current_page: int, target_page: int):
    items = []

    if isinstance(progress_log, list):
        for entry in progress_log:
            if not isinstance(entry, dict):
                continue

            entry_date = parse_iso_date(str(entry.get("date", "")), today_jst()).isoformat()
            page = sanitize_int(entry.get("page"), current_page, minimum=1)
            items.append({"date": entry_date, "page": clamp(page, 1, target_page)})

    if not items:
        items = [{"date": today_iso(), "page": current_page}]

    items.sort(key=lambda item: item["date"])
    return items


def latest_progress(progress_log):
    return progress_log[-1]


def normalize_state(raw_state):
    state = clone_data(DEFAULT_STATE)

    if isinstance(raw_state, dict):
        state.update(raw_state)

    current_page = sanitize_int(state.get("current_page"), DEFAULT_STATE["current_page"])
    target_page = max(current_page, sanitize_int(state.get("target_page"), DEFAULT_STATE["target_page"]))
    start_date = parse_iso_date(str(state.get("start_date", "")), default_start_date())
    deadline_date = parse_iso_date(str(state.get("deadline_date", "")), default_deadline_date())

    if deadline_date < start_date:
        deadline_date = start_date

    progress_log = sanitize_progress_log(state.get("progress_log"), current_page, target_page)

    if latest_progress(progress_log)["page"] < current_page:
        today = today_iso()
        progress_log = [entry for entry in progress_log if entry["date"] != today]
        progress_log.append({"date": today, "page": current_page})
        progress_log.sort(key=lambda item: item["date"])

    return {
        "current_page": current_page,
        "target_page": target_page,
        "start_date": start_date.isoformat(),
        "deadline_date": deadline_date.isoformat(),
        "progress_log": progress_log,
    }


def load_state():
    if DATA_FILE.exists():
        try:
            raw_state = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw_state = clone_data(DEFAULT_STATE)
    else:
        raw_state = clone_data(DEFAULT_STATE)

    state = normalize_state(raw_state)

    if not DATA_FILE.exists():
        save_state(state)

    return state


def save_state(state):
    normalized = normalize_state(state)
    DATA_FILE.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_progress_entry(state, page: int):
    today = today_iso()
    progress_log = [entry for entry in state["progress_log"] if entry["date"] != today]
    progress_log.append({"date": today, "page": clamp(page, state["current_page"], state["target_page"])})
    progress_log.sort(key=lambda item: item["date"])
    state["progress_log"] = progress_log
    return normalize_state(state)


def build_milestones(current_page: int, target_page: int, start_date: date, deadline_date: date):
    milestones = []
    total_span = (deadline_date - start_date).days
    total_pages = max(0, target_page - current_page)
    week_index = 0
    week_start = start_date

    while week_start <= deadline_date:
        week_end = min(week_start + timedelta(days=6), deadline_date)
        progress_ratio = 1 if total_span == 0 else (week_end - start_date).days / total_span
        target = min(target_page, current_page + round(total_pages * progress_ratio))
        milestones.append(
            {
                "week_label": f"Week {week_index + 1}",
                "range_label": f"{format_month_day(week_start)} - {format_month_day(week_end)}",
                "target": target,
            }
        )
        week_start = week_end + timedelta(days=1)
        week_index += 1

    return milestones


def build_sprint(current_page: int, target_page: int, start_date: date, deadline_date: date, latest_page: int):
    sprint = []
    total_span = (deadline_date - start_date).days
    total_pages = max(0, target_page - current_page)
    start_point = max(today_jst(), start_date)
    previous_target = latest_page

    for day_index in range(14):
        current_date = start_point + timedelta(days=day_index)
        if current_date > deadline_date:
            break

        progress_ratio = 1 if total_span == 0 else (current_date - start_date).days / total_span
        target = min(target_page, current_page + round(total_pages * progress_ratio))
        step_pages = max(0, target - previous_target)
        sprint.append(
            {
                "date_label": f"{format_weekday(current_date)} {format_month_day(current_date)}",
                "focus": "復習と演習の日" if step_pages == 0 else f"{step_pages}ページ進める日",
                "page": target,
            }
        )
        previous_target = target

    return sprint


def build_plan(state):
    current_page = state["current_page"]
    target_page = state["target_page"]
    start_date = parse_iso_date(state["start_date"], default_start_date())
    deadline_date = parse_iso_date(state["deadline_date"], default_deadline_date())
    latest = latest_progress(state["progress_log"])
    latest_page = latest["page"]
    remaining_pages = max(0, target_page - latest_page)
    total_span_days = max(0, (deadline_date - start_date).days)
    today = today_jst()
    study_window_start = max(today, start_date)
    days_left = (deadline_date - study_window_start).days + 1 if deadline_date >= study_window_start else 0
    pace_window_days = max(1, days_left)
    daily_pace = 0 if remaining_pages == 0 else max(1, math.ceil(remaining_pages / pace_window_days))
    weekly_pace = 0 if daily_pace == 0 else daily_pace * 7
    baseline_total = target_page - current_page
    progress_percent = 100 if baseline_total <= 0 else clamp(round(((latest_page - current_page) / baseline_total) * 100), 0, 100)
    today_index = clamp((today - start_date).days, 0, total_span_days) if total_span_days else 0
    elapsed_ratio = 1 if total_span_days == 0 else today_index / total_span_days
    today_target_page = min(target_page, current_page + round((target_page - current_page) * elapsed_ratio))
    next_mini_goal = target_page if remaining_pages == 0 else min(target_page, latest_page + max(1, daily_pace))
    delta = latest_page - today_target_page

    status_class = "success"
    status_title = "オンペースです。"
    status_body = f"今日の理想ラインは {today_target_page}ページ、最新記録は {latest_page}ページです。このまま続ければ締切までに到達できます。"

    if remaining_pages == 0:
        status_title = "目標達成です。"
        status_body = f"{target_page}ページまで到達しています。残り期間は復習や演習に回せます。"
    elif days_left == 0 and latest_page < target_page:
        status_class = "error"
        status_title = "締切日を過ぎています。"
        status_body = f"目標の {target_page}ページ まであと {remaining_pages}ページです。締切を延ばすか、数日集中の計画に切り替えるのがおすすめです。"
    elif delta >= max(1, daily_pace * 2):
        status_title = "かなり前倒しです。"
        status_body = f"今日の理想ラインより {delta}ページ進んでいます。復習日を入れても余裕があります。"
    elif delta < 0:
        status_class = "error" if abs(delta) > max(1, daily_pace * 3) else "warning"
        status_title = "少し巻き返しが必要です。"
        status_body = f"今日の理想ラインは {today_target_page}ページ、最新記録は {latest_page}ページです。あと {abs(delta)}ページ 取り戻せば計画線に戻れます。"

    return {
        "current_page": current_page,
        "target_page": target_page,
        "remaining_pages": remaining_pages,
        "days_left": days_left,
        "daily_pace": daily_pace,
        "weekly_pace": weekly_pace,
        "progress_percent": progress_percent,
        "today_target_page": today_target_page,
        "next_mini_goal": next_mini_goal,
        "status_class": status_class,
        "status_title": status_title,
        "status_body": status_body,
        "latest_progress": latest,
        "milestones": build_milestones(current_page, target_page, start_date, deadline_date),
        "sprint": build_sprint(current_page, target_page, start_date, deadline_date, latest_page),
    }


def format_month_day(value: date) -> str:
    return f"{value.month}/{value.day}"


def format_weekday(value: date) -> str:
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return f"({weekdays[value.weekday()]})"


def render_flash_banner(flash_key: str) -> str:
    message = FLASH_MESSAGES.get(flash_key)
    if not message:
        return ""
    return f'<div class="flash-banner">{e(message)}</div>'


def render_milestones(items) -> str:
    return "".join(
        f"""
        <article class="milestone-item">
          <div>
            <p class="milestone-week">{e(item["week_label"])}</p>
            <strong class="milestone-range">{e(item["range_label"])}</strong>
          </div>
          <div class="milestone-target-wrap">
            <span class="milestone-target-label">目標ページ</span>
            <strong class="milestone-target">{e(item["target"])}ページ</strong>
          </div>
        </article>
        """
        for item in items
    )


def render_sprint(items) -> str:
    return "".join(
        f"""
        <article class="sprint-item">
          <div>
            <p class="sprint-date">{e(item["date_label"])}</p>
            <strong class="sprint-focus">{e(item["focus"])}</strong>
          </div>
          <div class="sprint-page-wrap">
            <span class="sprint-page-label">目安ページ</span>
            <strong class="sprint-page">{e(item["page"])}ページ</strong>
          </div>
        </article>
        """
        for item in items
    )


def render_page(state, plan, flash_key: str = "") -> str:
    latest = plan["latest_progress"]
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Deep Learning 3 Python Planner</title>
  <style>{STYLE_CSS}</style>
</head>
<body>
  <div class="page-shell">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Python First Study Planner</p>
        <h1>2か月で495ページまで走り切る学習プラン</h1>
        <p class="hero-text">
          進捗計算、画面描画、保存処理まで、できるだけ Python 側で持たせたローカルWebアプリです。
        </p>
        <div class="python-note">
          標準ライブラリだけで動くので、追加のパッケージなしでも始められます。進捗は
          <code>{e(DATA_FILE.name)}</code> に保存されます。
        </div>
      </div>
      <section class="hero-panel" aria-label="現在の目標サマリー">
        <div class="hero-stat">
          <span class="hero-stat-label">いまの目標</span>
          <strong>{e(plan["target_page"])}ページ</strong>
        </div>
        <div class="hero-stat">
          <span class="hero-stat-label">残りページ</span>
          <strong>{e(plan["remaining_pages"])}ページ</strong>
        </div>
        <div class="hero-stat accent">
          <span class="hero-stat-label">今日の目安</span>
          <strong>{e(plan["daily_pace"])}ページ/日</strong>
        </div>
      </section>
    </header>

    {render_flash_banner(flash_key)}

    <main class="layout">
      <section class="card">
        <div class="section-heading">
          <p class="section-kicker">Plan Setup</p>
          <h2>学習条件</h2>
        </div>

        <form class="planner-form" method="post" action="/save-plan">
          <label>
            <span>現在のページ</span>
            <input name="current_page" type="number" min="1" step="1" value="{e(state["current_page"])}" required>
          </label>

          <label>
            <span>目標ページ</span>
            <input name="target_page" type="number" min="1" step="1" value="{e(state["target_page"])}" required>
          </label>

          <label>
            <span>スタート日</span>
            <input name="start_date" type="date" value="{e(state["start_date"])}" required>
          </label>

          <label>
            <span>締切日</span>
            <input name="deadline_date" type="date" value="{e(state["deadline_date"])}" required>
          </label>

          <div>
            <button type="submit">条件を保存</button>
          </div>
        </form>

        <div class="status-banner {e(plan["status_class"])}">
          <strong>{e(plan["status_title"])}</strong><br>
          {e(plan["status_body"])}
        </div>

        <div class="summary-grid">
          <article class="summary-card">
            <span>残りページ</span>
            <strong>{e(plan["remaining_pages"])}</strong>
            <p>目標までに読み切る分量</p>
          </article>
          <article class="summary-card">
            <span>残り日数</span>
            <strong>{e(plan["days_left"])}</strong>
            <p>今日から締切日までの残り学習日数</p>
          </article>
          <article class="summary-card">
            <span>必要ペース</span>
            <strong>{e(plan["daily_pace"])}</strong>
            <p>1日あたりの目安ページ</p>
          </article>
          <article class="summary-card">
            <span>今週の目標</span>
            <strong>{e(plan["weekly_pace"])}</strong>
            <p>7日で進めたいページ数</p>
          </article>
        </div>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="section-kicker">Live Tracker</p>
          <h2>進捗チェック</h2>
        </div>

        <div class="progress-wrap">
          <div class="progress-ring" style="--progress: {e(plan["progress_percent"])}%;" role="img" aria-label="全体の進捗">
            <div class="progress-ring-inner">
              <span>{e(plan["progress_percent"])}%</span>
              <small>completed</small>
            </div>
          </div>
          <div class="progress-copy">
            <p class="checkpoint-label">今日の理想到達点: {e(plan["today_target_page"])}ページ</p>
            <p class="mini-goal">次の小目標: {e(plan["next_mini_goal"])}ページまで</p>
          </div>
        </div>

        <form class="log-form" method="post" action="/log-progress">
          <label>
            <span>今日の到達ページ</span>
            <input name="page" type="number" min="{e(state["current_page"])}" step="1" value="{e(latest["page"])}" required>
          </label>
          <button type="submit">進捗を保存</button>
        </form>

        <div class="saved-progress">
          <div>
            <span class="saved-progress-label">保存済みの最新記録</span>
            <strong>{e(latest["date"])} / {e(latest["page"])}ページ</strong>
          </div>
          <form method="post" action="/reset-progress">
            <button type="submit" class="ghost-button">記録をリセット</button>
          </form>
        </div>

        <p class="footer-note">
          ブラウザで入力した内容は、同じフォルダの <code>{e(DATA_FILE.name)}</code> に保存されます。
        </p>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="section-kicker">Weekly Roadmap</p>
          <h2>週ごとの到達ライン</h2>
        </div>
        <div class="milestone-list">
          {render_milestones(plan["milestones"])}
        </div>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="section-kicker">Next 14 Days</p>
          <h2>直近2週間の進め方</h2>
        </div>
        <div class="sprint-list">
          {render_sprint(plan["sprint"])}
        </div>
      </section>
    </main>
  </div>
</body>
</html>
"""


class PlannerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/healthz":
            self.send_text("ok")
            return

        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        state = load_state()
        flash_key = parse_qs(parsed.query).get("flash", [""])[0]
        content = render_page(state, build_plan(state), flash_key)
        encoded = content.encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/save-plan":
            self.handle_save_plan()
            return

        if parsed.path == "/log-progress":
            self.handle_log_progress()
            return

        if parsed.path == "/reset-progress":
            self.handle_reset_progress()
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_save_plan(self):
        form = self.read_form()
        state = load_state()
        current_page = sanitize_int(form.get("current_page"), state["current_page"])
        target_page = max(current_page, sanitize_int(form.get("target_page"), state["target_page"]))
        start_date = parse_iso_date(form.get("start_date", ""), parse_iso_date(state["start_date"], default_start_date()))
        deadline_date = parse_iso_date(form.get("deadline_date", ""), parse_iso_date(state["deadline_date"], default_deadline_date()))

        state.update(
            {
                "current_page": current_page,
                "target_page": target_page,
                "start_date": start_date.isoformat(),
                "deadline_date": deadline_date.isoformat(),
            }
        )

        save_state(state)
        self.redirect("/?flash=plan-saved")

    def handle_log_progress(self):
        form = self.read_form()
        state = load_state()
        page = sanitize_int(form.get("page"), latest_progress(state["progress_log"])["page"])
        updated_state = add_progress_entry(state, page)
        save_state(updated_state)
        self.redirect("/?flash=progress-saved")

    def handle_reset_progress(self):
        state = load_state()
        state["progress_log"] = [{"date": today_iso(), "page": state["current_page"]}]
        save_state(state)
        self.redirect("/?flash=progress-reset")

    def read_form(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8")
        parsed = parse_qs(payload)
        return {key: values[0] if values else "" for key, values in parsed.items()}

    def redirect(self, location: str):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def send_text(self, body: str):
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


def create_server(host: str, port: int):
    return ThreadingHTTPServer((host, port), PlannerHandler)


def main():
    parser = argparse.ArgumentParser(description="Deep Learning 3 planner web app powered by Python.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    args = parser.parse_args()

    save_state(load_state())

    with create_server(args.host, args.port) as server:
        print(f"Deep Learning 3 planner is running at http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\\nStopped.")


if __name__ == "__main__":
    main()
