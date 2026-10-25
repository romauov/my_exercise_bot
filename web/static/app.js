"use strict";

const TOKEN_KEY = "weight_web_token";
const CONFIG_KEY = "weight_chart_config";
const DEFAULT_COLOR = "#3b82f6";
const DEFAULT_GOAL_COLOR = "#f59e0b";
const DEFAULT_EXTRA_COLOR = "#e74c3c";
const API_BASE = "/api";

/* Every selectable line kind for the panel.
   calc(data) -> array of values (null = no point at that label),
   same length as the labels array. */
const LINE_KINDS = {
  sma3: { label: "SMA 3 дня", calc: (d) => sma(d, 3) },
  sma7: { label: "SMA 7 дней", calc: (d) => sma(d, 7) },
  sma14: { label: "SMA 14 дней", calc: (d) => sma(d, 14) },
  sma30: { label: "SMA 30 дней", calc: (d) => sma(d, 30) },
  ema7: { label: "EMA 7 дней", calc: (d) => ema(d, 7) },
  ema14: { label: "EMA 14 дней", calc: (d) => ema(d, 14) },
  delta7: {
    label: "Изменение за 7 дней",
    calc: (d) => delta(d, 7),
    axis: "yDelta",
    sign: "кг/нед",
  },
  delta30: {
    label: "Изменение за 30 дней",
    calc: (d) => delta(d, 30),
    axis: "yDelta",
    sign: "кг/мес",
  },
  trend: { label: "Тренд (прямая)", calc: (d) => fitTrend(d.map((r) => r.weight)) },
  median7: { label: "Медиана 7 дней", calc: (d) => median(d, 7) },
  forecast: { label: "Прогноз тренда", calc: null }, // handled separately
};

const DEFAULT_CONFIG = {
  lineColor: DEFAULT_COLOR,
  goalColor: DEFAULT_GOAL_COLOR,
  extra: [{ kind: "sma7", color: DEFAULT_EXTRA_COLOR }],
};

const EXTRA_PALETTE = ["#e74c3c", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"];

let token = localStorage.getItem(TOKEN_KEY) || "";
let chart = null;
let currentPeriod = "last";
let currentData = []; // raw weighings, sorted by date
let goalWeight = null;
let currentConfig = loadConfig();
let lastLabels = [];
let currentTips = []; // tooltip title per displayed point
let weeklyView = false; // true when points are weekly buckets
let currentTickTexts = null; // Map: ISO bucket date -> ["мес", "год"] | ["мес"]

const $ = (id) => document.getElementById(id);
const MONTHS_SHORT = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }

function todayLocalISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function hexOk(hex) {
  return /^#[0-9a-f]{6}$/i.test(hex);
}

/* Per-device chart config (localStorage): main line color, goal color,
   and the list of extra lines [{kind, color}]. Unknown kinds are dropped
   so an updated server never breaks an old device config. */
function loadConfig() {
  let cfg;
  try {
    cfg = JSON.parse(localStorage.getItem(CONFIG_KEY) || "{}");
  } catch {
    cfg = {};
  }
  const config = {
    lineColor: hexOk(cfg.lineColor) ? cfg.lineColor : DEFAULT_CONFIG.lineColor,
    goalColor: hexOk(cfg.goalColor) ? cfg.goalColor : DEFAULT_CONFIG.goalColor,
    extra: Array.isArray(cfg.extra)
      ? cfg.extra.filter(
          (x) => x && typeof x.kind === "string" && hexOk(x.color) && LINE_KINDS[x.kind]
        )
      : [...DEFAULT_CONFIG.extra],
  };
  return config;
}

function saveConfig() {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(currentConfig));
}

/* Hex (#rgb or #rrggbb) -> rgba() CSS string. */
function rgba(hex, alpha) {
  let h = hex.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  if (!/^[0-9a-f]{6}$/i.test(h)) h = DEFAULT_COLOR.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/* ---------- line calculations ---------- */

/* Trailing SMA: arithmetic mean of all weighings within the last
   `windowDays` (null until at least `minPoints` fall in the window). */
function sma(data, windowDays, minPoints = 2) {
  const result = [];
  let start = 0;
  for (let i = 0; i < data.length; i++) {
    const cutoff = new Date(data[i].date).getTime() - (windowDays - 1) * 86400000;
    while (new Date(data[start].date).getTime() < cutoff) start++;
    const count = i - start + 1;
    if (count < Math.min(minPoints, data.length)) {
      result.push(null);
      continue;
    }
    let sum = 0;
    for (let j = start; j <= i; j++) sum += data[j].weight;
    result.push(sum / count);
  }
  return result;
}

/* Time-aware EMA with a `halfLifeDays` time constant: recent weighings
   count more, gaps in days reduce the weight of old points. */
function ema(data, halfLifeDays) {
  const result = [];
  let prev = null;
  for (const row of data) {
    if (prev === null) {
      result.push(row.weight);
    } else {
      const dt = (new Date(row.date) - new Date(prev.date)) / 86400000;
      const alpha = 1 - Math.pow(0.5, Math.max(dt, 0) / halfLifeDays);
      result.push(result[result.length - 1] + alpha * (row.weight - result[result.length - 1]));
    }
    prev = row;
  }
  return result;
}

/* Weight now minus the last weighing at least `days` ago (kg/period).
   null until there is a point far enough back. */
function delta(data, days) {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    const cutoff = new Date(data[i].date).getTime() - days * 86400000;
    let j = i - 1;
    while (j >= 0 && new Date(data[j].date).getTime() > cutoff) j--;
    result.push(j >= 0 ? data[i].weight - data[j].weight : null);
  }
  return result;
}

/* Rolling median over weighings of the last `windowDays` — resistant
   to a single bad weighing. */
function median(data, windowDays) {
  const result = [];
  let start = 0;
  for (let i = 0; i < data.length; i++) {
    const cutoff = new Date(data[i].date).getTime() - (windowDays - 1) * 86400000;
    while (start <= i && new Date(data[start].date).getTime() < cutoff) start++;
    const values = data.slice(start, i + 1).map((r) => r.weight).sort((a, b) => a - b);
    const mid = values.length >> 1;
    result.push(
      values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2
    );
  }
  return result;
}

/* Least-squares fit over point indices: y[i] = slope*i + intercept. */
function fitTrend(values) {
  const n = values.length;
  if (n < 2) return null;
  const sumX = (n * (n - 1)) / 2;
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = values.reduce((a, y, i) => a + i * y, 0);
  const sumXX = values.reduce((a, _, i) => a + i * i, 0);
  const denom = n * sumXX - sumX * sumX;
  if (denom === 0) return null;
  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;
  return values.map((_, i) => slope * i + intercept);
}

/* X labels: "07.10" for short periods; for year/all a month name only
   on the first point of each month (no month repeated 10 times). */
function shortLabels(data) {
  const yearView = currentPeriod === "year" || currentPeriod === "all";
  let prevMonth = null;
  return data.map((r) => {
    const [y, m, d] = r.date.split("-");
    if (yearView) {
      const label = m === prevMonth ? "" : MONTHS_SHORT[Number(m) - 1];
      prevMonth = m;
      return label;
    }
    return `${d}.${m}`;
  });
}

/* Displayed series: on "Год"/"Всё" the daily weighings collapse into
   weekly buckets (mean per calendar week); other periods stay daily. */
function weeklyMode() {
  return currentPeriod === "year" || currentPeriod === "all";
}

function fmtDDMM(dateStr) {
  const [, m, d] = dateStr.split("-");
  return `${d}.${m}`;
}

function mondayISO(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function aggregateWeekly(rows) {
  const buckets = [];
  const idxForRow = [];
  let cur = null;
  for (const row of rows) {
    const key = mondayISO(row.date);
    if (!cur || cur.key !== key) {
      cur = { key, from: row.date, to: row.date, sum: 0, n: 0 };
      buckets.push(cur);
    }
    cur.to = row.date;
    cur.sum += row.weight;
    cur.n += 1;
    idxForRow.push(buckets.length - 1);
  }
  return { buckets, idxForRow };
}

function weeklyWeights(agg) {
  return agg.buckets.map((b) => b.sum / b.n);
}

/* Per-bucket average of a value array computed on daily data
   (nulls in the daily line stay absent in buckets without points). */
function mapToBuckets(agg, dailyValues) {
  const acc = agg.buckets.map(() => ({ s: 0, n: 0 }));
  agg.idxForRow.forEach((bucketIndex, i) => {
    const v = dailyValues[i];
    if (Number.isFinite(v)) {
      acc[bucketIndex].s += v;
      acc[bucketIndex].n += 1;
    }
  });
  return acc.map((x) => (x.n ? x.s / x.n : null));
}

/* Tick texts for weekly buckets: a month name on the first bucket of the
   month, plus a second line with the year in January and on the very
   first tick (ISO date -> ["дек", "2024"] / ["дек"] / null). */
function monthTickTexts(buckets) {
  const map = new Map();
  let prevYear = null;
  let prevMonth = null;
  for (const b of buckets) {
    const y = Number(b.from.slice(0, 4));
    const m = Number(b.from.slice(5, 7));
    let lines;
    if (prevYear === null) {
      lines = [MONTHS_SHORT[m - 1], String(y)];
    } else if (m !== prevMonth) {
      lines = m === 1 ? [MONTHS_SHORT[m - 1], String(y)] : [MONTHS_SHORT[m - 1]];
    } else {
      lines = null;
    }
    map.set(b.from, lines);
    prevYear = y;
    prevMonth = m;
  }
  return map;
}

/* buildSeries() — the view model behind the chart. */
function buildSeries() {
  const daily = currentData;
  if (weeklyMode()) {
    const agg = aggregateWeekly(daily);
    return {
      weekly: true,
      labels: agg.buckets.map((b) => b.from),
      tickTexts: monthTickTexts(agg.buckets),
      tips: agg.buckets.map((b) =>
        b.from === b.to
          ? b.from
          : b.from.slice(0, 4) === b.to.slice(0, 4)
            ? `${fmtDDMM(b.from)}–${fmtDDMM(b.to)}`
            : `${fmtDDMM(b.from)}.${b.from.slice(2, 4)}–${fmtDDMM(b.to)}.${b.to.slice(2, 4)}`
      ),
      raw: weeklyWeights(agg),
      agg,
    };
  }
  return {
    weekly: false,
    labels: shortLabels(daily),
    tickTexts: null,
    tips: daily.map((r) => r.date),
    raw: daily.map((r) => r.weight),
    agg: null,
  };
}

/* Vertical span: 1 kg of breathing room beyond the displayed values
   on each side. */
function yScaleRange(values) {
  const vals = [...values];
  if (goalWeight !== null) vals.push(goalWeight);
  if (!vals.length) return {};
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  return {
    min: Math.floor((min - 1) * 2) / 2,
    max: Math.ceil((max + 1) * 2) / 2,
    step: max - min > 4 ? 1 : 0.5,
  };
}

/* Roomy scale for the "delta" lines (kg over a week/month); centered
   on zero by default, or centered on the data when it drifts. */
function deltaScale(values) {
  const finite = values.filter((v) => Number.isFinite(v));
  if (!finite.length) return null;
  let min = Math.min(0, ...finite);
  let max = Math.max(0, ...finite);
  const pad = Math.max(0.5, (max - min) * 0.15);
  return {
    min: min - pad,
    max: max + pad,
  };
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "X-Auth-Token": token,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    token = "";
    show("login-overlay");
    throw new Error("unauthorized");
  }
  return res;
}

/* ---------- login ---------- */

async function login() {
  const value = $("token-input").value.trim();
  const res = await fetch(`${API_BASE}/check`, {
    headers: { "X-Auth-Token": value },
  });
  if (res.ok) {
    token = value;
    localStorage.setItem(TOKEN_KEY, value);
    hide("login-overlay");
    loadPeriod();
  } else {
    show("login-error");
  }
}

/* ---------- panel (line configuration) ---------- */

function panelRow(inner) {
  const row = document.createElement("div");
  row.className = "panel-row";
  row.innerHTML = inner; // all content is built by us, not by the user
  return row;
}

function colorInput(cls, value, title, attrs = "") {
  return `<input type="color" class="${cls}" value="${value}" title="${title}" ${attrs}>`;
}

function renderPanel() {
  const panel = $("lines-panel");
  panel.replaceChildren();

  /* 1. Real values */
  panel.appendChild(
    panelRow(`
      <span class="line-label">Вес</span>
      ${colorInput("color-main", currentConfig.lineColor, "Цвет линии веса")}
    `)
  );

  /* 2. Goal: value + color */
  panel.appendChild(
    panelRow(`
      <span class="line-label">Цель, кг</span>
      <input type="number" id="goal-value" class="goal-input" step="0.1"
             value="${goalWeight ?? ""}" placeholder="нет" title="Горизонтальная линия цели">
      ${colorInput("color-goal", currentConfig.goalColor, "Цвет линии цели")}
    `)
  );

  /* 3+. Extra lines */
  currentConfig.extra.forEach((line, index) => {
    const options =
      `<option value="" ${line.kind ? "" : "selected"}>— линия —</option>` +
      Object.entries(LINE_KINDS)
        .map(([kind, k]) => `<option value="${kind}" ${kind === line.kind ? "selected" : ""}>${k.label}</option>`)
        .join("");
    panel.appendChild(
      panelRow(`
        <select class="line-kind" data-index="${index}" title="Тип доп. линии">
          ${options}
        </select>
        ${colorInput("color-extra", line.color, "Цвет доп. линии", `data-index="${index}"`)}
        <button class="remove-line" data-index="${index}" title="Убрать линию">×</button>
      `)
    );
  });

  /* Add button */
  const add = document.createElement("button");
  add.id = "add-line";
  add.className = "ghost add-line-btn";
  add.textContent = "+ линия";
  add.title = "Добавить ещё один график";
  panel.appendChild(add);
}

async function saveGoal() {
  const value = parseFloat($("goal-value").value);
  if (Number.isNaN(value)) return; // empty input keeps the current goal
  const res = await api("/goal", { method: "PUT", body: { weight: value } });
  if (!res.ok) return;
  goalWeight = value;
  rebuildChart();
}

function onPanelInput(e) {
  const target = e.target;
  if (target.classList.contains("color-main")) {
    currentConfig.lineColor = target.value;
    saveConfig();
    rebuildChart();
  } else if (target.classList.contains("color-goal")) {
    currentConfig.goalColor = target.value;
    saveConfig();
    rebuildChart();
  } else if (target.classList.contains("color-extra")) {
    currentConfig.extra[Number(target.dataset.index)].color = target.value;
    saveConfig();
    rebuildChart();
  } else if (target.id === "goal-value") {
    // handled on 'change' (after blur/Enter), not on every keystroke
  } else if (target.classList.contains("line-kind")) {
    currentConfig.extra[Number(target.dataset.index)].kind = target.value || null;
    saveConfig();
    rebuildChart();
  }
}

function onPanelChange(e) {
  if (e.target.id === "goal-value") saveGoal();
}

function onPanelClick(e) {
  if (e.target.classList.contains("remove-line")) {
    const index = Number(e.target.dataset.index);
    currentConfig.extra.splice(index, 1);
    saveConfig();
    renderPanel();
    rebuildChart();
  } else if (e.target.id === "add-line") {
    const usedColors = new Set(currentConfig.extra.map((x) => x.color));
    const color = EXTRA_PALETTE.find((c) => !usedColors.has(c)) || EXTRA_PALETTE[0];
    currentConfig.extra.push({ kind: null, color });
    saveConfig();
    renderPanel();
    rebuildChart();
  }
}

/* ---------- chart ---------- */

async function loadPeriod() {
  const [res, goalRes] = await Promise.all([
    api(`/weights?period=${currentPeriod}`),
    api("/goal"),
  ]);
  currentData = await res.json();
  goalWeight = (await goalRes.json())?.weight ?? null;
  if (goalWeight === null) $("goal-value").value = "";
  renderPanel();
  rebuildChart();
}

function rebuildChart() {
  const series = buildSeries();
  lastLabels = series.labels;
  currentTips = series.tips;
  weeklyView = series.weekly;
  currentTickTexts = series.tickTexts;

  /* "Прогноз тренда" extends the X axis by 2 steps; on weekly buckets
     a step is a week, on daily data a day. */
  const hasForecast = currentConfig.extra.some((x) => x.kind === "forecast");
  const stepTitles = series.weekly ? ["+1 нед", "+2 нед"] : ["+1 день", "+2 дня"];
  if (hasForecast && currentData.length >= 2) {
    lastLabels = lastLabels.concat(stepTitles);
  }

  if (chart) chart.destroy();

  if (!currentData.length) {
    chart = null;
    show("empty-msg");
    return;
  }
  hide("empty-msg");

  const rawValues = series.raw;
  const datasets = [];
  const deltaDatasets = [];

  /* Raw values are always dataset 0 (click-to-edit maps to it). */
  datasets.push({
    label: series.weekly ? "Вес (среднее за нед.)" : "Вес (кг)",
    data: rawValues,
    borderColor: currentConfig.lineColor,
    borderWidth: 2,
    pointRadius: 0,
    pointHitRadius: 12,
    pointHoverRadius: 5,
    pointBackgroundColor: rgba(currentConfig.lineColor, 0.85),
    fill: "start",
    backgroundColor: (ctx) => fillGradient(ctx),
    tension: 0.2,
  });

  for (const line of currentConfig.extra) {
    const kind = LINE_KINDS[line.kind];
    if (!kind) continue;
    let values;
    if (line.kind === "forecast") {
      const trend = fitTrend(rawValues);
      if (!trend || lastLabels.length <= currentData.length) continue;
      const step = trend[trend.length - 1] - trend[trend.length - 2];
      values = [
        ...Array(currentData.length - 1).fill(null),
        trend[trend.length - 1],
        trend[trend.length - 1] + step,
        trend[trend.length - 1] + 2 * step,
      ];
    } else {
      values = kind.calc(currentData);
      if (!Array.isArray(values)) continue;
      if (series.weekly) values = mapToBuckets(series.agg, values);
    }
    const dataset = {
      label: kind.label,
      data: values,
      borderColor: line.color,
      borderWidth: 2,
      borderDash: kind.axis ? undefined : [6, 4],
      pointRadius: 0,
      pointHitRadius: 0,
      pointHoverRadius: 0,
      tension: 0.3,
    };
    if (kind.axis) {
      dataset.yAxisID = "yDelta";
      deltaDatasets.push(dataset);
    }
    datasets.push(dataset);
  }

  if (goalWeight !== null) {
    datasets.push({
      label: `Цель ${goalWeight.toFixed(1)}`,
      data: datasets[0].data.map(() => goalWeight),
      pointRadius: 0,
      pointHitRadius: 0,
      borderWidth: 1.5,
      borderDash: [4, 4],
      borderColor: currentConfig.goalColor,
      tension: 0,
    });
  }

  const range = yScaleRange(rawValues);
  const deltaRange = deltaScale(deltaDatasets.flatMap((d) => d.data));
  const scales = {
    x: {
      grid: { display: false },
      ticks: {
        /* Weekly buckets: every tick gets a slot (autoSkip off) and the
           callback is what decides whether it shows a month/year — empty
           texts would otherwise make autoSkip drop month names. */
        ...(weeklyView
          ? {
              autoSkip: false,
              callback: (_value, index) => {
                const label = String(lastLabels[index] ?? "");
                const lines = currentTickTexts?.get(label);
                if (lines) return lines;
                return /^\d{4}-/.test(label) ? "" : label;
              },
            }
          : { autoSkip: true }),
        maxRotation: 0,
        padding: 8,
      },
    },
    y: {
      min: range.min,
      max: range.max,
      grid: { color: "rgba(0,0,0,0.06)" },
      ticks: { stepSize: range.step, callback: (v) => v.toFixed(1) },
    },
  };
  if (deltaDatasets.length) {
    scales.yDelta = {
      position: "right",
      ...(deltaRange || {}),
      grid: { display: false },
      border: { display: false },
      ticks: { callback: (v) => v.toFixed(1) },
    };
  }

  chart = new Chart($("chart"), {
    type: "line",
    data: { labels: lastLabels, datasets },
    options: {
      onClick,
      interaction: { mode: "nearest", intersect: false },
      scales,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => {
              const idx = items[0]?.dataIndex;
              return idx === undefined ? "" : currentTips[idx] ?? lastLabels[idx] ?? "";
            },
            label: (item) => `${item.dataset.label}: ${item.parsed.y.toFixed(1)} ${item.dataset.yAxisID === "yDelta" ? "кг/" + (item.dataset.label.includes("30") ? "мес" : "нед") : "кг"}`,
            filter: (item) =>
              !item.dataset.label.startsWith("Цель"),
          },
        },
      },
    },
  });
}

/* Vertical gradient under the main (raw) line: strongest near the max of
   the data and fading to transparent toward the bottom axis. */
function fillGradient(ctx) {
  const area = ctx.chart.chartArea;
  if (!area || !currentData.length) return rgba(currentConfig.lineColor, 0.15);
  const yScale = ctx.chart.scales.y;
  const dataMax = Math.max(...currentData.map((r) => r.weight));
  const tTop = (dataMax - yScale.min) / (yScale.max - yScale.min);
  const g = ctx.chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
  g.addColorStop(0, rgba(currentConfig.lineColor, 0.01));
  g.addColorStop(Math.min(1, Math.max(0.01, tTop)), rgba(currentConfig.lineColor, 0.22));
  g.addColorStop(1, rgba(currentConfig.lineColor, 0.22));
  return g;
}

function onClick(event) {
  /* Weekly buckets are averages — there is no single record to edit. */
  if (weeklyView) return;
  const points = chart.getElementsAtEventForMode(
    event, "nearest", { intersect: true }, true
  );
  const weightPoint = points.find((p) => p.datasetIndex === 0);
  if (!weightPoint) return;
  const record = currentData[weightPoint.index];
  openEditModal(record);
}

/* ---------- toolbar ---------- */

function selectPeriod(button) {
  document
    .querySelectorAll("#periods button")
    .forEach((b) => b.classList.remove("active"));
  button.classList.add("active");
  currentPeriod = button.dataset.period;
  loadPeriod();
}

/* ---------- weight step buttons ---------- */

function stepWeight(button) {
  const input = $(button.dataset.target);
  const step = parseFloat(button.dataset.step);
  const value = parseFloat(input.value) || 0;
  const next = Math.round((value + step) * 100) / 100;
  input.value = next.toFixed(1);
}

/* ---------- add modal ---------- */

async function openAddModal() {
  let lastWeight = "";
  try {
    const res = await api("/summary");
    const summary = await res.json();
    if (summary && summary.weight) lastWeight = summary.weight.toFixed(1);
  } catch (e) {
    if (e.message === "unauthorized") return;
  }
  hide("add-error");
  $("add-date").value = todayLocalISO();
  $("add-weight").value = lastWeight;
  show("add-overlay");
}

async function saveNewWeight() {
  const date = $("add-date").value;
  const weight = parseFloat($("add-weight").value);
  if (!date || Number.isNaN(weight)) return;
  const res = await api("/weights", { method: "POST", body: { date, weight } });
  if (res.ok) {
    hide("add-overlay");
    loadPeriod();
  } else {
    showError("add-error", res.status === 409
      ? "На эту дату уже есть запись"
      : "Ошибка сохранения");
  }
}

/* ---------- edit modal ---------- */

let editId = null;

function openEditModal(record) {
  editId = record.id;
  $("edit-date").value = record.date;
  $("edit-weight").value = record.weight.toFixed(1);
  hide("edit-error");
  show("edit-overlay");
}

async function saveEditWeight() {
  const date = $("edit-date").value;
  const weight = parseFloat($("edit-weight").value);
  if (!date || Number.isNaN(weight)) return;
  const res = await api(`/weights/${editId}`, {
    method: "PATCH",
    body: { date, weight },
  });
  if (res.ok) {
    hide("edit-overlay");
    loadPeriod();
  } else {
    showError("edit-error", res.status === 409
      ? "На эту дату уже есть запись"
      : "Ошибка сохранения");
  }
}

function showError(id, message) {
  $(id).textContent = message;
  show(id);
}

async function deleteWeight() {
  if (!confirm("Удалить запись?")) return;
  const res = await api(`/weights/${editId}`, { method: "DELETE" });
  if (res.ok) {
    hide("edit-overlay");
    loadPeriod();
  } else {
    showError("edit-error", "Ошибка удаления");
  }
}

/* ---------- backup ---------- */

async function downloadBackup() {
  const res = await api("/backup");
  if (!res.ok) return;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `weights_${todayLocalISO()}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/* ---------- wiring ---------- */

function wire() {
  $("periods").addEventListener("click", (e) => {
    const button = e.target.closest("button[data-period]");
    if (button) selectPeriod(button);
  });

  document.querySelectorAll("button.step").forEach((button) =>
    button.addEventListener("click", () => stepWeight(button))
  );

  document.querySelectorAll("button[data-close]").forEach((button) =>
    button.addEventListener("click", () => hide(button.dataset.close))
  );

  $("lines-panel").addEventListener("input", onPanelInput);
  $("lines-panel").addEventListener("change", onPanelChange);
  $("lines-panel").addEventListener("click", onPanelClick);

  $("login-btn").addEventListener("click", login);
  $("token-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") login();
  });

  $("add-btn").addEventListener("click", openAddModal);
  $("backup-btn").addEventListener("click", downloadBackup);
  $("add-save").addEventListener("click", saveNewWeight);
  $("edit-save").addEventListener("click", saveEditWeight);
  $("edit-delete").addEventListener("click", deleteWeight);
}

function init() {
  wire();
  renderPanel();
  if (token) {
    loadPeriod().catch(() => show("login-overlay"));
  } else {
    show("login-overlay");
  }
}

init();
