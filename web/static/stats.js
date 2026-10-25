"use strict";

/* Statistics page: counts of incoming requests (own traffic with a valid
   token excluded by default — see web/main.py middleware). */

const TOKEN_KEY = "weight_web_token";
const API_BASE = "/api";
const CHART_COLOR = "#2f6fed";

let token = localStorage.getItem(TOKEN_KEY) || "";
let includeMine = false;
let chart = null;

const $ = (id) => document.getElementById(id);

function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }

async function api(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "X-Auth-Token": token },
  });
  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    token = "";
    show("login-overlay");
    throw new Error("unauthorized");
  }
  return res;
}

async function login() {
  const value = $("token-input").value.trim();
  const res = await fetch(`${API_BASE}/check`, {
    headers: { "X-Auth-Token": value },
  });
  if (res.ok) {
    token = value;
    localStorage.setItem(TOKEN_KEY, value);
    hide("login-overlay");
    load();
  } else {
    show("login-error");
  }
}

function fmtDay(iso) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
  const [, m, d] = iso.split("-");
  return `${d}.${m}`;
}

function statusCell(status) {
  const cls = status < 400 ? "st-ok" : "st-err";
  return `<span class="${cls}">${status}</span>`;
}

function fillTable(tableId, rows, cells) {
  $(tableId).innerHTML = rows
    .map((row) => `<tr>${cells(row).join("")}</tr>`)
    .join("");
}

function renderChart(perDay) {
  if (chart) chart.destroy();
  chart = new Chart($("stats-chart"), {
    type: "bar",
    data: {
      labels: perDay.map((d) => fmtDay(d.date)),
      datasets: [
        {
          label: "Запросов",
          data: perDay.map((d) => d.count),
          backgroundColor: CHART_COLOR,
          borderRadius: 4,
        },
      ],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: (item) => `${item.parsed.y} запр.` },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  });
}

async function load() {
  const [statsRes, logRes] = await Promise.all([
    api(`/stats${includeMine ? "?include_mine=1" : ""}`),
    api("/stats/log"),
  ]);
  const stats = await statsRes.json();
  const log = await logRes.json();

  $("total-count").textContent = String(stats.total);

  const day = includeMine ? "всего" : "чужих";
  $("total-label").textContent = includeMine ? "Всего запросов" : "Чужие запросы";
  renderChart(stats.per_day);

  fillTable(
    "stats-paths",
    stats.per_path.slice(0, 10),
    (row) => [`<td class="cell-path">${row.path}</td>`, `<td>${row.count}</td>`]
  );
  fillTable(
    "stats-ips",
    stats.per_ip.slice(0, 10),
    (row) => [`<td>${row.ip}</td>`, `<td>${row.count}</td>`]
  );
  fillTable(
    "stats-log",
    log,
    (row) => [
      `<td>${row.ts.replace("T", " ")}</td>`,
      `<td class="cell-path">${row.path}</td>`,
      `<td>${statusCell(row.status)}</td>`,
      `<td>${row.ip}${row.mine ? ' <span class="mine-badge">своё</span>' : ""}</td>`,
    ]
  );

  document.title = `Статистика — ${stats.total} ${day}`;
}

function init() {
  $("login-btn").addEventListener("click", login);
  $("token-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") login();
  });
  $("show-mine").addEventListener("change", (e) => {
    includeMine = e.target.checked;
    load().catch(() => {});
  });

  if (token) {
    load().catch(() => {});
  } else {
    show("login-overlay");
  }
}

init();
