const STORAGE_KEY = "study-finish-planner-v2";
const DAY_MS = 1000 * 60 * 60 * 24;

const elements = {
  plannerForm: document.getElementById("plannerForm"),
  logForm: document.getElementById("logForm"),
  studyTitle: document.getElementById("studyTitle"),
  currentPage: document.getElementById("currentPage"),
  targetPage: document.getElementById("targetPage"),
  startDate: document.getElementById("startDate"),
  deadlineDate: document.getElementById("deadlineDate"),
  logPage: document.getElementById("logPage"),
  saveProgress: document.getElementById("saveProgress"),
  heroTitle: document.getElementById("heroTitle"),
  heroRemaining: document.getElementById("heroRemaining"),
  heroDaily: document.getElementById("heroDaily"),
  remainingPages: document.getElementById("remainingPages"),
  remainingDays: document.getElementById("remainingDays"),
  dailyPace: document.getElementById("dailyPace"),
  weeklyPace: document.getElementById("weeklyPace"),
  statusBanner: document.getElementById("statusBanner"),
  progressPercent: document.getElementById("progressPercent"),
  checkpointLabel: document.getElementById("checkpointLabel"),
  miniGoal: document.getElementById("miniGoal"),
  savedProgressText: document.getElementById("savedProgressText"),
  resetProgress: document.getElementById("resetProgress"),
  resetAll: document.getElementById("resetAll"),
  milestoneList: document.getElementById("milestoneList"),
  sprintList: document.getElementById("sprintList"),
  milestoneTemplate: document.getElementById("milestoneTemplate"),
  sprintTemplate: document.getElementById("sprintTemplate"),
  progressRing: document.querySelector(".progress-ring")
};

let state = loadState();

hydrateForm();
bindEvents();
render();
registerServiceWorker();

function createDefaultState() {
  const today = getTodayString();

  return {
    studyTitle: "",
    currentPage: 0,
    targetPage: 0,
    startDate: today,
    deadlineDate: getOffsetDateString(today, 60),
    progressLog: []
  };
}

function cloneData(value) {
  return JSON.parse(JSON.stringify(value));
}

function loadState() {
  const defaults = createDefaultState();

  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (!saved) {
      return normalizeState(defaults);
    }

    return normalizeState({
      ...defaults,
      ...saved
    });
  } catch (error) {
    console.warn("Failed to load saved plan:", error);
    return normalizeState(defaults);
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function normalizeState(rawState) {
  const defaults = createDefaultState();
  const studyTitle = typeof rawState.studyTitle === "string"
    ? rawState.studyTitle.trim().slice(0, 120)
    : "";
  const currentPage = sanitizeWholeNumber(rawState.currentPage, defaults.currentPage, 0);
  const targetPage = Math.max(
    currentPage,
    sanitizeWholeNumber(rawState.targetPage, defaults.targetPage, 0)
  );
  const startDate = isValidIsoDate(rawState.startDate) ? rawState.startDate : defaults.startDate;
  const deadlineDateCandidate = isValidIsoDate(rawState.deadlineDate)
    ? rawState.deadlineDate
    : defaults.deadlineDate;
  const deadlineDate = deadlineDateCandidate >= startDate ? deadlineDateCandidate : startDate;
  const ready = isPlanReady({ currentPage, targetPage });
  let progressLog = ready
    ? sanitizeProgressLog(rawState.progressLog, currentPage, targetPage)
    : [];

  if (ready && progressLog.length === 0) {
    progressLog = [{ date: getTodayString(), page: currentPage }];
  }

  if (ready && getLatestProgressFromLog(progressLog, currentPage).page < currentPage) {
    const today = getTodayString();
    progressLog = progressLog.filter((entry) => entry.date !== today);
    progressLog.push({ date: today, page: currentPage });
    progressLog.sort((a, b) => a.date.localeCompare(b.date));
  }

  return {
    studyTitle,
    currentPage,
    targetPage,
    startDate,
    deadlineDate,
    progressLog
  };
}

function sanitizeProgressLog(progressLog, currentPage, targetPage) {
  if (!Array.isArray(progressLog)) {
    return [];
  }

  const byDate = new Map();

  progressLog
    .filter((entry) => entry && entry.date && Number.isFinite(Number(entry.page)))
    .forEach((entry) => {
      byDate.set(entry.date, {
        date: entry.date,
        page: clampNumber(Math.round(Number(entry.page)), currentPage, targetPage)
      });
    });

  return Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
}

function hydrateForm() {
  elements.studyTitle.value = state.studyTitle;
  elements.currentPage.value = state.currentPage;
  elements.targetPage.value = state.targetPage;
  elements.startDate.value = state.startDate;
  elements.deadlineDate.value = state.deadlineDate;
  elements.logPage.value = getLatestProgress().page;
}

function bindEvents() {
  elements.plannerForm.addEventListener("submit", (event) => {
    event.preventDefault();
  });

  elements.plannerForm.addEventListener("input", () => {
    updateStateFromInputs();
    saveState();
    render();
  });

  elements.logForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!isPlanReady(state)) {
      return;
    }

    const page = clampNumber(
      sanitizeWholeNumber(elements.logPage.value, state.currentPage, state.currentPage),
      state.currentPage,
      state.targetPage
    );
    const today = getTodayString();

    state.progressLog = state.progressLog.filter((entry) => entry.date !== today);
    state.progressLog.push({ date: today, page });
    state.progressLog.sort((a, b) => a.date.localeCompare(b.date));
    saveState();
    render();
  });

  elements.resetProgress.addEventListener("click", () => {
    if (!isPlanReady(state)) {
      return;
    }

    state.progressLog = [{ date: getTodayString(), page: state.currentPage }];
    saveState();
    render();
  });

  elements.resetAll.addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    state = loadState();
    hydrateForm();
    render();
  });
}

function updateStateFromInputs() {
  state = normalizeState({
    ...state,
    studyTitle: elements.studyTitle.value,
    currentPage: Number(elements.currentPage.value),
    targetPage: Number(elements.targetPage.value),
    startDate: elements.startDate.value,
    deadlineDate: elements.deadlineDate.value
  });

  elements.deadlineDate.value = state.deadlineDate;
  elements.logPage.value = getLatestProgress().page;
}

function render() {
  const plan = buildPlan(state);
  const displayTitle = state.studyTitle || "自分の教材をここから設定";

  document.title = state.studyTitle
    ? `${state.studyTitle} | Study Finish Planner`
    : "Study Finish Planner";

  elements.heroTitle.textContent = displayTitle;
  elements.progressRing.style.setProperty("--progress", `${plan.progressPercent}%`);
  elements.progressPercent.textContent = `${plan.progressPercent}%`;

  if (!plan.isReady) {
    elements.heroRemaining.textContent = "未設定";
    elements.heroDaily.textContent = "未設定";
    elements.remainingPages.textContent = "-";
    elements.remainingDays.textContent = "-";
    elements.dailyPace.textContent = "-";
    elements.weeklyPace.textContent = "-";
    elements.logPage.value = state.currentPage;
    elements.logPage.min = String(state.currentPage);
    elements.checkpointLabel.textContent = "まずは現在ページ、目標ページ、期間を入れてください。";
    elements.miniGoal.textContent = "設定すると、次の小目標が自動で表示されます。";
    elements.savedProgressText.textContent = "まだ記録はありません";
    elements.statusBanner.className = "status-banner";
    elements.statusBanner.innerHTML = `
      <strong>最初の設定をすると計画が始まります。</strong><br>
      目標ページを現在ページより大きく入れると、残りページ数、1日あたりの目安、週ごとの到達ラインを自動で作ります。
    `;

    setLogDisabledState(true);
    renderEmptyState(
      elements.milestoneList,
      "設定が終わるとここに週ごとの到達ラインが出ます。"
    );
    renderEmptyState(
      elements.sprintList,
      "設定が終わるとここに直近2週間の進め方が出ます。"
    );
    return;
  }

  const latestProgress = getLatestProgress();

  elements.heroRemaining.textContent = `${plan.remainingPages}ページ`;
  elements.heroDaily.textContent = `${plan.dailyPace}ページ/日`;
  elements.remainingPages.textContent = String(plan.remainingPages);
  elements.remainingDays.textContent = String(plan.daysLeft);
  elements.dailyPace.textContent = String(plan.dailyPace);
  elements.weeklyPace.textContent = String(plan.weeklyPace);
  elements.checkpointLabel.textContent = `今日の理想到達点: ${plan.todayTargetPage}ページ`;
  elements.miniGoal.textContent = `次の小目標: ${plan.nextMiniGoal}ページまで`;
  elements.savedProgressText.textContent = `${latestProgress.date} / ${latestProgress.page}ページ`;
  elements.statusBanner.className = `status-banner ${plan.statusTone}`;
  elements.statusBanner.innerHTML = plan.statusText;

  setLogDisabledState(false);
  elements.logPage.min = String(state.currentPage);
  elements.logPage.max = String(state.targetPage);
  elements.logPage.value = clampNumber(
    sanitizeWholeNumber(elements.logPage.value, latestProgress.page, state.currentPage),
    state.currentPage,
    state.targetPage
  );

  renderMilestones(plan.milestones);
  renderSprint(plan.sprint);
}

function buildPlan(planState) {
  if (!isPlanReady(planState)) {
    return {
      isReady: false,
      progressPercent: 0
    };
  }

  const currentPage = planState.currentPage;
  const targetPage = planState.targetPage;
  const startDate = parseLocalDate(planState.startDate);
  const deadlineDate = parseLocalDate(planState.deadlineDate);
  const latest = getLatestProgress();
  const remainingPages = Math.max(0, targetPage - latest.page);
  const totalSpanDays = daysBetween(startDate, deadlineDate);
  const today = parseLocalDate(getTodayString());
  const studyWindowStart = today < startDate ? startDate : today;
  const daysLeft = deadlineDate >= studyWindowStart ? daysBetween(studyWindowStart, deadlineDate) + 1 : 0;
  const paceWindowDays = Math.max(1, daysLeft);
  const dailyPace = remainingPages === 0 ? 0 : Math.max(1, Math.ceil(remainingPages / paceWindowDays));
  const weeklyPace = dailyPace === 0 ? 0 : dailyPace * 7;
  const baselineTotal = targetPage - currentPage;
  const progressPercent = baselineTotal <= 0
    ? 100
    : clampNumber(Math.round(((latest.page - currentPage) / baselineTotal) * 100), 0, 100);
  const todayIndex = clampNumber(daysBetween(startDate, today), 0, totalSpanDays);
  const elapsedRate = totalSpanDays === 0 ? 1 : todayIndex / totalSpanDays;
  const todayTargetPage = Math.min(
    targetPage,
    currentPage + Math.round((targetPage - currentPage) * elapsedRate)
  );
  const nextMiniGoal = Math.min(targetPage, latest.page + Math.max(1, dailyPace));
  const delta = latest.page - todayTargetPage;

  let statusTone = "ok";
  let statusText = `
    <strong>オンペースです。</strong><br>
    今日の理想ラインは <strong>${todayTargetPage}ページ</strong>、最新記録は <strong>${latest.page}ページ</strong> です。このまま続ければ締切までに到達できます。
  `;

  if (remainingPages === 0) {
    statusText = `
      <strong>目標達成です。</strong><br>
      <strong>${targetPage}ページ</strong> まで到達しています。残り期間は復習や演習に回せます。
    `;
  } else if (daysLeft === 0 && latest.page < targetPage) {
    statusTone = "error";
    statusText = `
      <strong>締切日を過ぎています。</strong><br>
      目標の <strong>${targetPage}ページ</strong> まであと <strong>${remainingPages}ページ</strong> です。締切を延ばすか、短期集中の計画に切り替えるのがおすすめです。
    `;
  } else if (delta >= Math.max(1, dailyPace * 2)) {
    statusText = `
      <strong>かなり前倒しです。</strong><br>
      今日の理想ラインより <strong>${delta}ページ</strong> 進んでいます。復習日を入れても余裕があります。
    `;
  } else if (delta < 0) {
    statusTone = Math.abs(delta) > Math.max(1, dailyPace * 3) ? "error" : "warning";
    statusText = `
      <strong>少し巻き返しが必要です。</strong><br>
      今日の理想ラインは <strong>${todayTargetPage}ページ</strong>、最新記録は <strong>${latest.page}ページ</strong> です。あと <strong>${Math.abs(delta)}ページ</strong> 取り戻せば計画線に戻れます。
    `;
  }

  return {
    isReady: true,
    currentPage,
    targetPage,
    remainingPages,
    daysLeft,
    dailyPace,
    weeklyPace,
    progressPercent,
    todayTargetPage,
    nextMiniGoal,
    statusTone,
    statusText,
    milestones: buildMilestones(currentPage, targetPage, startDate, deadlineDate),
    sprint: buildSprint(currentPage, targetPage, startDate, deadlineDate, latest.page)
  };
}

function buildMilestones(currentPage, targetPage, startDate, deadlineDate) {
  const milestones = [];
  const totalSpan = daysBetween(startDate, deadlineDate);
  const totalPages = Math.max(0, targetPage - currentPage);
  let weekIndex = 0;
  let weekStart = new Date(startDate);

  while (weekStart <= deadlineDate) {
    const weekEnd = addDays(weekStart, 6);
    const safeWeekEnd = weekEnd < deadlineDate ? weekEnd : deadlineDate;
    const progress = totalSpan === 0 ? 1 : daysBetween(startDate, safeWeekEnd) / totalSpan;
    const target = Math.min(targetPage, currentPage + Math.round(totalPages * progress));

    milestones.push({
      weekLabel: `Week ${weekIndex + 1}`,
      rangeLabel: `${formatMonthDay(weekStart)} - ${formatMonthDay(safeWeekEnd)}`,
      target
    });

    weekStart = addDays(safeWeekEnd, 1);
    weekIndex += 1;
  }

  return milestones;
}

function buildSprint(currentPage, targetPage, startDate, deadlineDate, latestPage) {
  const sprint = [];
  const today = parseLocalDate(getTodayString());
  const startPoint = today < startDate ? startDate : today;
  const totalSpan = daysBetween(startDate, deadlineDate);
  const totalPages = Math.max(0, targetPage - currentPage);
  let previousTarget = latestPage;

  for (let index = 0; index < 14; index += 1) {
    const date = addDays(startPoint, index);
    if (date > deadlineDate) {
      break;
    }

    const progress = totalSpan === 0 ? 1 : daysBetween(startDate, date) / totalSpan;
    const target = Math.min(targetPage, currentPage + Math.round(totalPages * progress));
    const stepPages = Math.max(0, target - previousTarget);
    const focus = stepPages === 0 ? "復習と演習の日" : `${stepPages}ページ進める日`;

    sprint.push({
      dateLabel: `${formatWeekday(date)} ${formatMonthDay(date)}`,
      focus,
      page: target
    });

    previousTarget = target;
  }

  return sprint;
}

function renderMilestones(milestones) {
  elements.milestoneList.replaceChildren();

  milestones.forEach((milestone) => {
    const node = elements.milestoneTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".milestone-week").textContent = milestone.weekLabel;
    node.querySelector(".milestone-range").textContent = milestone.rangeLabel;
    node.querySelector(".milestone-target").textContent = `${milestone.target}ページ`;
    elements.milestoneList.appendChild(node);
  });
}

function renderSprint(sprint) {
  elements.sprintList.replaceChildren();

  sprint.forEach((day) => {
    const node = elements.sprintTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".sprint-date").textContent = day.dateLabel;
    node.querySelector(".sprint-focus").textContent = day.focus;
    node.querySelector(".sprint-page").textContent = `${day.page}ページ`;
    elements.sprintList.appendChild(node);
  });
}

function renderEmptyState(container, message) {
  container.innerHTML = `<article class="empty-state">${message}</article>`;
}

function setLogDisabledState(disabled) {
  elements.logPage.disabled = disabled;
  elements.saveProgress.disabled = disabled;
  elements.resetProgress.disabled = disabled;
}

function getLatestProgress() {
  return getLatestProgressFromLog(state.progressLog, state.currentPage);
}

function getLatestProgressFromLog(progressLog, fallbackPage) {
  if (!Array.isArray(progressLog) || progressLog.length === 0) {
    return {
      date: getTodayString(),
      page: fallbackPage
    };
  }

  return progressLog[progressLog.length - 1];
}

function isPlanReady(plan) {
  return Number.isFinite(plan.currentPage)
    && Number.isFinite(plan.targetPage)
    && plan.targetPage > plan.currentPage;
}

function sanitizeWholeNumber(value, fallback, min = 0) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return Math.max(min, Math.round(parsed));
}

function clampNumber(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function daysBetween(from, to) {
  return Math.round((to.getTime() - from.getTime()) / DAY_MS);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function parseLocalDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatMonthDay(date) {
  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric"
  }).format(date);
}

function formatWeekday(date) {
  return new Intl.DateTimeFormat("ja-JP", {
    weekday: "short"
  }).format(date);
}

function isValidIsoDate(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function getTodayString() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(new Date());
}

function getOffsetDateString(baseIsoDate, offsetDays) {
  return formatIsoDate(addDays(parseLocalDate(baseIsoDate), offsetDays));
}

function formatIsoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function registerServiceWorker() {
  const isSupported = "serviceWorker" in navigator;
  const isWebContext = window.location.protocol === "https:" || window.location.hostname === "localhost";

  if (!isSupported || !isWebContext) {
    return;
  }

  navigator.serviceWorker.register("./service-worker.js").catch((error) => {
    console.warn("Failed to register service worker:", error);
  });
}
