"use strict";

const TOKEN_KEY = "weight_web_token";
const API_BASE = "/api";

let token = localStorage.getItem(TOKEN_KEY) || "";
let chart = null;
let currentPeriod = "last";
let currentData = [];

const $ = (id) => document.getElementById(id);

function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }

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

  if (chart) chart.destroy();
  chart = new Chart($("chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Вес (кг)",
          data: values,
          pointRadius: 5,
          pointHitRadius: 10,
          tension: 0.2,
        },
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

function onClick(event) {
  const points = chart.getElementsAtEventForMode(
    event, "nearest", { intersect: true }, true
  );
  if (!points.length) return;
  const record = currentData[points[0].index];
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
  $("add-date").value = new Date().toISOString().slice(0, 10);
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
  }
}

/* ---------- edit modal ---------- */

let editId = null;

function openEditModal(record) {
  editId = record.id;
  $("edit-date").value = record.date;
  $("edit-weight").value = record.weight.toFixed(1);
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
  }
}

async function deleteWeight() {
  const res = await api(`/weights/${editId}`, { method: "DELETE" });
  if (res.ok) {
    hide("edit-overlay");
    loadPeriod();
  }
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
  $("add-btn").addEventListener("click", openAddModal);
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
