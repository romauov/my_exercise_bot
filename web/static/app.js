"use strict";

const TOKEN_KEY = "weight_web_token";
const COLOR_KEY = "weight_line_color";
const DEFAULT_COLOR = "#3b82f6";
const TREND_COLOR = "#e74c3c"; // SMA line: red dashed
const GOAL_COLOR = "#f59e0b";
const API_BASE = "/api";

let token = localStorage.getItem(TOKEN_KEY) || "";
let lineColor = localStorage.getItem(COLOR_KEY) || DEFAULT_COLOR;
let chart = null;
let currentPeriod = "last";
let currentData = []; // raw weighings, sorted by date
let goalWeight = null;

const $ = (id) => document.getElementById(id);
const MONTHS_SHORT = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }

function todayLocalISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/* Hex (#rgb or #rrggbb) -> rgba() CSS string. */
function rgba(hex, alpha) {
  let h = hex.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  if (!/^[0-9a-f]{6}$/i.test(h)) h = DEFAULT_COLOR.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/* Trailing SMA: arithmetic mean of all weighings within the last
   `windowDays` (inclusive of gaps, like a "last 7 days" average). */
function sma(data, windowDays) {
  const result = [];
  let start = 0;
  for (let i = 0; i < data.length; i++) {
    const cutoff = new Date(data[i].date).getTime() - (windowDays - 1) * 86400000;
    while (new Date(data[start].date).getTime() < cutoff) start++;
    let sum = 0;
    for (let j = start; j <= i; j++) sum += data[j].weight;
    result.push({ date: data[i].date, weight: sum / (i - start + 1) });
  }
  return result;
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

/* Vertical span: 1 kg of breathing room beyond the data on each side. */
function yScaleRange() {
  const values = currentData.map((r) => r.weight);
  if (goalWeight !== null) values.push(goalWeight);
  if (!values.length) return {};
  const min = Math.min(...values);
  const max = Math.max(...values);
  return {
    min: Math.floor((min - 1) * 2) / 2,
    max: Math.ceil((max + 1) * 2) / 2,
    step: max - min > 4 ? 1 : 0.5,
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

/* ---------- chart ---------- */

async function loadPeriod() {
  const [res, goalRes] = await Promise.all([
    api(`/weights?period=${currentPeriod}`),
    api("/goal"),
  ]);
  currentData = await res.json();
  goalWeight = (await goalRes.json())?.weight ?? null;
  if (goalWeight !== null) $("goal-input").value = goalWeight;

  const labels = shortLabels(currentData);
  const rawValues = currentData.map((r) => r.weight);
  const smaValues = sma(currentData, 7).map((r) => r.weight);
  const range = yScaleRange();

  if (chart) chart.destroy();
  chart = new Chart($("chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Вес (кг)",
          data: rawValues,
          borderColor: lineColor,
          borderWidth: 2,
          pointRadius: 0,
          pointHitRadius: 12,
          pointHoverRadius: 5,
          pointBackgroundColor: rgba(lineColor, 0.85),
          fill: "start",
          backgroundColor: (ctx) => fillGradient(ctx),
          tension: 0.2,
        },
        {
          label: "SMA (7 дн.)",
          data: smaValues,
          borderColor: TREND_COLOR,
          borderWidth: 2,
          borderDash: [6, 4],
          pointRadius: 0,
          pointHitRadius: 0,
          pointHoverRadius: 0,
          tension: 0.3,
        },
        ...(goalWeight !== null && currentData.length
          ? [
              {
                label: `Цель ${goalWeight.toFixed(1)}`,
                data: labels.map(() => goalWeight),
                pointRadius: 0,
                pointHitRadius: 0,
                borderWidth: 1.5,
                borderDash: [4, 4],
                borderColor: GOAL_COLOR,
                tension: 0,
              },
            ]
          : []),
      ],
    },
    options: {
      onClick,
      interaction: { mode: "nearest", intersect: false },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            autoSkip: true,
            maxRotation: 0,
            padding: 8,
          },
        },
        y: {
          min: range.min,
          max: range.max,
          grid: { color: "rgba(0,0,0,0.06)" },
          ticks: {
            stepSize: range.step,
            callback: (v) => v.toFixed(1),
          },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            title: (items) => items[0] ? currentData[items[0].dataIndex]?.date ?? "" : "",
            label: (item) =>
              `${item.dataset.label}: ${item.parsed.y.toFixed(1)} кг`,
            filter: (item) =>
              item.datasetIndex === 0 || item.datasetIndex === 1,
          },
        },
      },
    },
  });
  if (currentData.length) hide("empty-msg"); else show("empty-msg");
}

/* Vertical gradient under the main (raw) line: strongest near the max of
   the data and fading to transparent toward the bottom axis. */
function fillGradient(ctx) {
  const area = ctx.chart.chartArea;
  if (!area || !currentData.length) return rgba(lineColor, 0.15);
  const yScale = ctx.chart.scales.y;
  const dataMax = Math.max(...currentData.map((r) => r.weight));
  const tTop = (dataMax - yScale.min) / (yScale.max - yScale.min);
  const g = ctx.chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
  g.addColorStop(0, rgba(lineColor, 0.01));
  g.addColorStop(Math.min(1, Math.max(0.01, tTop)), rgba(lineColor, 0.22));
  g.addColorStop(1, rgba(lineColor, 0.22));
  return g;
}

function onClick(event) {
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

/* ---------- goal ---------- */

async function saveGoal() {
  const value = parseFloat($("goal-input").value);
  if (Number.isNaN(value)) return;
  const res = await api("/goal", { method: "PUT", body: { weight: value } });
  if (res.ok) loadPeriod();
}

/* ---------- color ---------- */

/* Recolor the main (raw) line without refetching the data; the gradient
   is scriptable and re-evaluates on update(). */
function applyLineColor() {
  if (!chart) return;
  chart.data.datasets[0].borderColor = lineColor;
  chart.data.datasets[0].pointBackgroundColor = rgba(lineColor, 0.85);
  chart.update();
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

  $("login-btn").addEventListener("click", login);
  $("token-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") login();
  });
  $("line-color").value = lineColor;
  $("line-color").addEventListener("input", (e) => {
    lineColor = e.target.value;
    localStorage.setItem(COLOR_KEY, lineColor);
    applyLineColor();
  });
  $("goal-input").addEventListener("change", saveGoal);
  $("add-btn").addEventListener("click", openAddModal);
  $("backup-btn").addEventListener("click", downloadBackup);
  $("add-save").addEventListener("click", saveNewWeight);
  $("edit-save").addEventListener("click", saveEditWeight);
  $("edit-delete").addEventListener("click", deleteWeight);
}

function init() {
  wire();
  if (token) {
    loadPeriod().catch(() => show("login-overlay"));
  } else {
    show("login-overlay");
  }
}

init();
