"use strict";

const TOKEN_KEY = "weight_web_token";
const COLOR_KEY = "weight_line_color";
const DEFAULT_COLOR = "#3b82f6";
const TREND_COLOR = "#e74c3c";
const API_BASE = "/api";

let token = localStorage.getItem(TOKEN_KEY) || "";
let lineColor = localStorage.getItem(COLOR_KEY) || DEFAULT_COLOR;
let chart = null;
let currentPeriod = "last";
let currentData = [];

const $ = (id) => document.getElementById(id);

function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }

function todayLocalISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "X-Auth-Token": token,
      "Content-Type": "application/json",
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
  const res = await api(`/weights?period=${currentPeriod}`);
  currentData = await res.json();
  const labels = currentData.map((r) => r.date);
  const values = currentData.map((r) => r.weight);
  const trend = values.length > 1 ? fitTrend(values) : null;

  if (chart) chart.destroy();
  chart = new Chart($("chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Вес (кг)",
          data: values,
          borderColor: lineColor,
          backgroundColor: lineColor,
          pointRadius: 5,
          pointHitRadius: 10,
          tension: 0.2,
        },
        ...(trend
          ? [
              {
                label: "Тренд",
                data: trend,
                pointRadius: 0,
                pointHitRadius: 0,
                borderWidth: 2,
                borderDash: [6, 4],
                borderColor: TREND_COLOR,
                tension: 0,
              },
            ]
          : []),
      ],
    },
    options: {
      onClick,
      scales: {
        y: { title: { display: true, text: "кг" } },
      },
    },
  });
  if (currentData.length) hide("empty-msg"); else show("empty-msg");
}

/* Least-squares fit like the bot's matplotlib plot (np.polyfit over
   point indices): returns y[i] = slope*i + intercept for each i. */
function fitTrend(values) {
  const n = values.length;
  const sumX = (n * (n - 1)) / 2;
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = values.reduce((a, y, i) => a + i * y, 0);
  const sumXX = values.reduce((a, _, i) => a + i * i, 0);
  const denom = n * sumXX - sumX * sumX;
  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;
  return values.map((_, i) => slope * i + intercept);
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

/* ---------- color ---------- */

/* Recolor the chart line without refetching the data (trend stays red). */
function applyLineColor() {
  if (!chart) return;
  chart.data.datasets[0].borderColor = lineColor;
  chart.data.datasets[0].backgroundColor = lineColor;
  chart.update();
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
