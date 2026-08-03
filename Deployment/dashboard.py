"""
dashboard.py
------------
Comprehensive deployment energy & carbon dashboard with:
- Real-time deployment stats
- Strategy comparison charts
- Live log viewer for all services (FIXED)
- Carbon footprint visualization
- Deployment history

Run:
    python3 dashboard.py --watch-dir /opt/energy-profiller-hiran --port 5050
"""

import argparse
import datetime
import json
import sqlite3
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
WATCH_DIR       = Path("/opt/energy-profiller-hiran")
DEPLOYMENT_FILE = WATCH_DIR / "deployment_last.json"
PROFILER_FILE   = WATCH_DIR / "profiler_results.json"
CARBON_FILE     = WATCH_DIR / "carbon_report.json"
DB_PATH         = WATCH_DIR / "deployments.db"

# Live log buffer (last 300 lines per service)
log_buffers = {
    "deployment-tracker": deque(maxlen=300),
    "profiler":           deque(maxlen=300),
    "carbon-service":     deque(maxlen=300),
    "db-sync":            deque(maxlen=300),
    "dashboard":          deque(maxlen=300),
}
log_lock       = threading.Lock()
log_last_fetch = {}   # service -> last fetched timestamp for delta fetches

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

def get_history(limit: int = 50):
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT
                d.id, d.job_name, d.build_number, d.status, d.strategy,
                d.carbon_profile, d.image, d.start_time, d.end_time,
                d.duration_minutes,
                p.avg_cpu, p.peak_cpu, p.min_cpu,
                p.avg_memory, p.peak_memory, p.min_memory,
                p.samples_collected,
                c.total_g_co2, c.total_kg_co2, c.total_energy_kwh,
                c.carbon_intensity_gco2, c.intensity_source,
                c.strategy_carbon_profile, c.infra_multiplier
            FROM deployments d
            LEFT JOIN profiler_results p ON p.deployment_id = d.id
            LEFT JOIN carbon_reports   c ON c.deployment_id = d.id
            ORDER BY d.recorded_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"DB error: {e}")
        return []

def get_strategy_stats():
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT
                d.strategy,
                COUNT(d.id) as count,
                ROUND(AVG(d.duration_minutes), 2) as avg_duration,
                ROUND(AVG(c.total_g_co2), 4) as avg_co2,
                ROUND(AVG(c.total_energy_kwh), 8) as avg_energy,
                ROUND(AVG(c.infra_multiplier), 2) as avg_infra,
                ROUND(MIN(c.total_g_co2), 4) as min_co2,
                ROUND(MAX(c.total_g_co2), 4) as max_co2,
                SUM(CASE WHEN d.status='SUCCESS' THEN 1 ELSE 0 END) as success_count
            FROM deployments d
            LEFT JOIN carbon_reports c ON c.deployment_id = d.id
            WHERE d.strategy IS NOT NULL AND d.strategy != 'unknown'
            GROUP BY d.strategy
            ORDER BY avg_co2 ASC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Strategy stats error: {e}")
        return []

def get_totals():
    if not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT
                COUNT(DISTINCT d.id) as total_builds,
                SUM(CASE WHEN d.status='SUCCESS' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN d.status='FAILURE' THEN 1 ELSE 0 END) as failure_count,
                ROUND(AVG(d.duration_minutes), 2) as avg_duration,
                ROUND(SUM(c.total_g_co2), 4) as total_co2_g,
                ROUND(SUM(c.total_energy_kwh), 8) as total_energy_kwh,
                COUNT(DISTINCT d.strategy) as strategy_count
            FROM deployments d
            LEFT JOIN carbon_reports c ON c.deployment_id = d.id
        """).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as e:
        print(f"Totals error: {e}")
        return {}

def get_recent_snapshots(limit: int = 10):
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT cs.*, d.job_name
            FROM carbon_snapshots cs
            LEFT JOIN deployments d ON cs.deployment_id = d.id
            ORDER BY cs.recorded_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def fetch_service_logs():
    """Fetch recent logs from systemd journal for each service."""
    services = {
        "deployment-tracker": "deployment-tracker.service",
        "profiler":           "profiler.service",
        "carbon-service":     "carbon-service.service",
        "db-sync":            "db-sync.service",
        "dashboard":          "dashboard.service",
    }

    for name, unit in services.items():
        try:
            result = subprocess.run(
                ["journalctl", "-u", unit, "--no-pager", "-n", "50", "-o", "short-iso"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                with log_lock:
                    log_buffers[name].extend(lines)
            elif result.returncode != 0 and not list(log_buffers[name]):
                # Only add placeholder if buffer is empty
                ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                with log_lock:
                    log_buffers[name].append(
                        f"{ts} INFO {unit}: No journal entries found (service may not be running)"
                    )
        except FileNotFoundError:
            ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            with log_lock:
                if not list(log_buffers[name]):
                    log_buffers[name].append(
                        f"{ts} WARN {unit}: journalctl not available on this system"
                    )
        except Exception as e:
            ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            with log_lock:
                log_buffers[name].append(f"{ts} ERROR {unit}: {e}")

def log_polling_thread():
    while True:
        fetch_service_logs()
        time.sleep(5)

log_thread = threading.Thread(target=log_polling_thread, daemon=True)
log_thread.start()

# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/data")
def api_data():
    return jsonify({
        "deployment":     read_json(DEPLOYMENT_FILE),
        "profiler":       read_json(PROFILER_FILE),
        "carbon":         read_json(CARBON_FILE),
        "history":        get_history(),
        "totals":         get_totals(),
        "strategy_stats": get_strategy_stats(),
        "snapshots":      get_recent_snapshots(),
        "updated_at":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

@app.route("/api/logs")
def api_logs():
    """Return buffered logs for all services as a dict."""
    with log_lock:
        return jsonify({svc: list(buf) for svc, buf in log_buffers.items()})

@app.route("/api/logs/<service>")
def api_service_logs(service):
    """Return logs for a specific service as a list."""
    with log_lock:
        buf = log_buffers.get(service)
        if buf is None:
            return jsonify({"error": f"Unknown service: {service}"}), 404
        return jsonify(list(buf))

# ── Frontend ──────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Green DevOps · Energy Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:         #f0f4f8;
    --surface:    #ffffff;
    --surface2:   #f8fafc;
    --border:     #e2e8f0;
    --border2:    #cbd5e1;
    --text:       #0f172a;
    --muted:      #64748b;
    --muted2:     #94a3b8;
    --primary:    #2563eb;
    --primary-lt: #dbeafe;
    --success:    #16a34a;
    --success-lt: #dcfce7;
    --warning:    #d97706;
    --warning-lt: #fef3c7;
    --danger:     #dc2626;
    --danger-lt:  #fee2e2;
    --purple:     #7c3aed;
    --purple-lt:  #ede9fe;
    --cyan:       #0891b2;
    --cyan-lt:    #cffafe;
    --green:      #059669;
    --mono:       'DM Mono', 'Fira Code', Consolas, monospace;
    --sans:       'DM Sans', system-ui, sans-serif;
    --radius:     14px;
    --radius-sm:  8px;
    --shadow:     0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.04);
    --shadow-md:  0 4px 12px rgba(15,23,42,0.1), 0 2px 4px rgba(15,23,42,0.06);
  }

  html { font-size: 16px; }
  body {
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    font-size: 15px;
    line-height: 1.6;
    min-height: 100vh;
  }

  /* ── Navigation ── */
  nav {
    background: var(--surface);
    border-bottom: 2px solid var(--border);
    padding: 0 2rem;
    height: 68px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 200;
    box-shadow: var(--shadow-md);
  }
  .nav-left  { display: flex; align-items: center; gap: 16px; }
  .nav-logo  {
    font-size: 20px; font-weight: 700; letter-spacing: -0.03em;
    color: var(--text);
    display: flex; align-items: center; gap: 10px;
  }
  .nav-logo-leaf {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, #16a34a, #059669);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(22,163,74,0.3);
  }
  .nav-badge {
    font-family: var(--mono); font-size: 12px;
    background: var(--surface2); border: 1px solid var(--border2);
    padding: 5px 14px; border-radius: 20px; color: var(--muted);
    max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .nav-right { display: flex; align-items: center; gap: 14px; }
  .nav-tabs  { display: flex; gap: 4px; background: var(--bg); padding: 4px; border-radius: 12px; border: 1px solid var(--border); }
  .nav-tab {
    background: transparent; border: none; color: var(--muted);
    padding: 8px 18px; border-radius: 9px; cursor: pointer;
    font-size: 14px; font-weight: 600; transition: all 0.18s;
    font-family: var(--sans);
  }
  .nav-tab:hover { background: var(--surface); color: var(--text); }
  .nav-tab.active { background: var(--surface); color: var(--primary); box-shadow: var(--shadow); }
  .live-pill {
    display: flex; align-items: center; gap: 6px;
    background: var(--success-lt); border: 1px solid #bbf7d0;
    padding: 5px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 600; color: var(--success);
  }
  .live-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--success); animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.85)} }

  /* ── Layout ── */
  .page { display: none; padding: 2rem; max-width: 1600px; margin: 0 auto; }
  .page.active { display: block; animation: fadeIn 0.2s ease; }
  @keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }

  section { margin-bottom: 2rem; }
  .section-header {
    display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
  }
  .section-title {
    font-size: 13px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted);
  }
  .section-line { flex: 1; height: 1px; background: var(--border); }
  .section-count {
    font-family: var(--mono); font-size: 11px; color: var(--muted2);
    background: var(--bg); border: 1px solid var(--border);
    padding: 2px 8px; border-radius: 10px;
  }

  /* ── Cards ── */
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.5rem;
    box-shadow: var(--shadow);
  }

  /* ── Stat Grid ── */
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.25rem 1.4rem;
    box-shadow: var(--shadow); transition: all 0.2s; position: relative; overflow: hidden;
  }
  .stat-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
  .stat-card-accent { position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: var(--radius) var(--radius) 0 0; }
  .stat-label { font-size: 12px; font-weight: 600; color: var(--muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.06em; }
  .stat-val   { font-family: var(--mono); font-size: 28px; font-weight: 700; line-height: 1.1; color: var(--text); }
  .stat-sub   { font-size: 12px; color: var(--muted2); margin-top: 5px; font-family: var(--mono); }

  /* ── Badges ── */
  .badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 12px; border-radius: 6px;
    font-size: 12px; font-weight: 700; letter-spacing: 0.05em; font-family: var(--mono);
  }
  .badge::before { content:''; width:6px; height:6px; border-radius:50%; background:currentColor; }
  .badge-success  { background: var(--success-lt); color: var(--success); }
  .badge-failure  { background: var(--danger-lt);  color: var(--danger); }
  .badge-running  { background: var(--primary-lt); color: var(--primary); }
  .badge-idle     { background: var(--bg); color: var(--muted); border: 1px solid var(--border); }
  .badge-rolling  { background: var(--success-lt); color: var(--success); }
  .badge-recreate { background: var(--warning-lt); color: var(--warning); }
  .badge-canary   { background: var(--purple-lt);  color: var(--purple); }

  /* ── Charts ── */
  .charts-row { display: grid; grid-template-columns: 3fr 2fr; gap: 14px; }
  @media (max-width: 1100px) { .charts-row { grid-template-columns: 1fr; } }
  .chart-wrap { position: relative; height: 300px; }
  .chart-title { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 16px; }

  /* ── Carbon Hero ── */
  .carbon-panel {
    display: flex; flex-direction: column; gap: 16px;
    justify-content: space-between;
  }
  .carbon-big-num {
    font-family: var(--mono); font-size: 52px; font-weight: 700;
    color: var(--success); line-height: 1; letter-spacing: -0.02em;
  }
  .carbon-unit  { font-size: 15px; color: var(--muted); margin-top: 4px; font-weight: 500; }
  .carbon-meta  { font-size: 12px; color: var(--muted2); margin-top: 8px; font-family: var(--mono); }

  .equiv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .equiv-card {
    background: var(--success-lt); border: 1px solid #bbf7d0;
    border-radius: 10px; padding: 10px 12px;
    display: flex; align-items: center; gap: 10px;
  }
  .equiv-icon { font-size: 22px; flex-shrink: 0; }
  .equiv-text { font-size: 12px; color: var(--success); line-height: 1.4; }
  .equiv-text strong { display: block; font-size: 13px; font-weight: 700; color: var(--text); }

  /* ── Strategy Cards ── */
  .strategy-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
  .strategy-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.5rem;
    box-shadow: var(--shadow); position: relative; overflow: hidden;
    transition: all 0.2s;
  }
  .strategy-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
  .strategy-card-top { position: absolute; top: 0; left: 0; right: 0; height: 4px; border-radius: var(--radius) var(--radius) 0 0; }
  .strategy-card.rolling  .strategy-card-top { background: linear-gradient(90deg, var(--success), #4ade80); }
  .strategy-card.recreate .strategy-card-top { background: linear-gradient(90deg, var(--warning), #fcd34d); }
  .strategy-card.canary   .strategy-card-top { background: linear-gradient(90deg, var(--purple), #a78bfa); }
  .strategy-name { font-size: 20px; font-weight: 700; margin-bottom: 6px; }
  .strategy-desc { font-size: 13px; color: var(--muted); margin-bottom: 16px; line-height: 1.5; }
  .strategy-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
  .strategy-stat-val { font-family: var(--mono); font-size: 20px; font-weight: 700; }
  .strategy-stat-lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px; }
  .strategy-bar-lbl { font-size: 11px; color: var(--muted); margin-bottom: 5px; }
  .strategy-bar-bg   { height: 8px; border-radius: 4px; background: var(--bg); border: 1px solid var(--border); overflow: hidden; }
  .strategy-bar-fill { height: 100%; border-radius: 4px; transition: width 1.2s cubic-bezier(0.34,1.56,0.64,1); }
  .strategy-card.rolling  .strategy-bar-fill { background: var(--success); }
  .strategy-card.recreate .strategy-bar-fill { background: var(--warning); }
  .strategy-card.canary   .strategy-bar-fill { background: var(--purple); }
  .strategy-footer { font-size: 11px; color: var(--muted2); font-family: var(--mono); margin-top: 10px; }

  /* ── Log Viewer ── */
  #page-logs {
    display: none;
    padding: 1.5rem 2rem;
    max-width: 1600px;
    margin: 0 auto;
  }
  #page-logs.active { display: flex; flex-direction: column; }

  .log-shell {
    display: flex; flex-direction: column;
    height: calc(100vh - 180px);
    min-height: 600px;
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(15,23,42,0.18);
    border: 1px solid #1e293b;
  }

  /* Top chrome bar */
  .log-chrome {
    background: #1e293b;
    padding: 10px 16px;
    display: flex; align-items: center; gap: 10px;
    flex-shrink: 0; border-bottom: 1px solid #334155;
  }
  .log-chrome-dots { display: flex; gap: 6px; }
  .log-chrome-dot {
    width: 12px; height: 12px; border-radius: 50%;
  }
  .log-chrome-dot.red    { background: #ef4444; }
  .log-chrome-dot.yellow { background: #f59e0b; }
  .log-chrome-dot.green  { background: #22c55e; }
  .log-chrome-title {
    font-family: var(--mono); font-size: 12px; color: #64748b;
    margin-left: 8px; flex: 1;
  }
  .log-live-badge {
    font-family: var(--mono); font-size: 11px; font-weight: 600;
    background: rgba(34,197,94,0.15); color: #22c55e;
    border: 1px solid rgba(34,197,94,0.3);
    padding: 2px 10px; border-radius: 20px;
    display: flex; align-items: center; gap: 5px;
  }
  .log-live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #22c55e; animation: pulse 2s infinite;
  }

  /* Service filter bar */
  .log-filterbar {
    background: #162032;
    padding: 10px 16px;
    display: flex; align-items: center; gap: 8px;
    flex-wrap: wrap; flex-shrink: 0;
    border-bottom: 1px solid #1e293b;
  }
  .log-filterbar-label {
    font-family: var(--mono); font-size: 11px;
    color: #475569; text-transform: uppercase; letter-spacing: 0.08em;
    white-space: nowrap;
  }
  .log-btn {
    background: transparent; border: 1px solid #334155;
    color: #64748b; padding: 5px 14px; border-radius: 6px;
    cursor: pointer; font-size: 12px; font-weight: 600;
    font-family: var(--mono); transition: all 0.15s; white-space: nowrap;
  }
  .log-btn:hover  { border-color: #3b82f6; color: #93c5fd; background: rgba(59,130,246,0.08); }
  .log-btn.active { background: #1d4ed8; border-color: #2563eb; color: #fff; }

  /* Search box */
  .log-search {
    margin-left: auto;
    background: #0f172a; border: 1px solid #334155;
    border-radius: 6px; padding: 5px 12px;
    font-family: var(--mono); font-size: 12px; color: #e2e8f0;
    width: 220px; outline: none;
  }
  .log-search::placeholder { color: #475569; }
  .log-search:focus { border-color: #3b82f6; }

  /* Status strip */
  .log-statusbar {
    background: #0f172a;
    padding: 6px 16px;
    display: flex; align-items: center; justify-content: space-between;
    flex-shrink: 0; border-bottom: 1px solid #1e293b;
  }
  .log-status-svc  { font-family: var(--mono); font-size: 12px; color: #94a3b8; }
  .log-status-svc strong { color: #60a5fa; }
  .log-status-meta { font-family: var(--mono); font-size: 11px; color: #475569; display: flex; gap: 16px; }
  .log-status-meta span { display: flex; align-items: center; gap: 4px; }

  /* The actual terminal output area */
  .log-viewer {
    flex: 1;
    background: #0d1117;
    padding: 12px 18px;
    font-family: var(--mono); font-size: 13.5px;
    overflow-y: auto;
    overflow-x: hidden;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.75;
    color: #c9d1d9;
    min-height: 0;
  }
  .log-viewer::-webkit-scrollbar { width: 8px; }
  .log-viewer::-webkit-scrollbar-track { background: #161b22; }
  .log-viewer::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
  .log-viewer::-webkit-scrollbar-thumb:hover { background: #484f58; }

  .log-line       { display: block; padding: 0; }
  .log-line:hover { background: rgba(255,255,255,0.03); border-radius: 2px; }
  .log-line.error {
    color: #ff7b72;
    background: rgba(255,123,114,0.06);
    border-left: 2px solid #ff7b72; padding-left: 6px; border-radius: 0 2px 2px 0;
  }
  .log-line.warn  {
    color: #e3b341;
    background: rgba(227,179,65,0.05);
    border-left: 2px solid #e3b341; padding-left: 6px; border-radius: 0 2px 2px 0;
  }
  .log-line.info    { color: #79c0ff; }
  .log-line.success { color: #56d364; }
  .log-line.hidden  { display: none; }

  .log-svc-header {
    display: block;
    margin: 16px 0 6px;
    font-size: 11px; font-weight: 700;
    color: #58a6ff; letter-spacing: 0.1em; text-transform: uppercase;
    border-bottom: 1px solid #21262d; padding-bottom: 5px;
  }
  .log-svc-header:first-child { margin-top: 4px; }

  .log-timestamp  { color: #484f58; margin-right: 10px; user-select: none; }
  .log-empty {
    display: flex; align-items: center; justify-content: center;
    height: 100%; min-height: 200px;
    color: #484f58; font-size: 14px; font-style: italic;
  }

  /* Bottom control bar */
  .log-bottombar {
    background: #1e293b;
    padding: 8px 16px;
    display: flex; align-items: center; gap: 12px;
    flex-shrink: 0; border-top: 1px solid #334155;
  }
  .log-ctrl-btn {
    background: transparent; border: 1px solid #334155;
    color: #64748b; padding: 4px 12px; border-radius: 5px;
    cursor: pointer; font-size: 12px; font-family: var(--mono);
    transition: all 0.15s;
  }
  .log-ctrl-btn:hover   { border-color: #3b82f6; color: #93c5fd; }
  .log-ctrl-btn.on      { background: rgba(34,197,94,0.12); border-color: #22c55e; color: #22c55e; }
  .log-ctrl-btn.danger  { border-color: #ef4444; color: #ef4444; }
  .log-last-update { margin-left: auto; font-family: var(--mono); font-size: 11px; color: #475569; }

  /* ── Table ── */
  .table-wrap { overflow-x: auto; border-radius: var(--radius); border: 1px solid var(--border); box-shadow: var(--shadow); }
  table { width: 100%; border-collapse: collapse; background: var(--surface); font-size: 14px; }
  thead { background: var(--bg); }
  th {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted);
    padding: 12px 14px; text-align: left; border-bottom: 2px solid var(--border);
    white-space: nowrap;
  }
  td { padding: 10px 14px; border-bottom: 1px solid var(--border); white-space: nowrap; font-family: var(--mono); font-size: 13px; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--bg); }
  .co2-cell { font-weight: 700; color: var(--success); }

  /* ── Totals ── */
  .totals-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }
  .total-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.4rem;
    box-shadow: var(--shadow); transition: all 0.2s;
  }
  .total-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
  .total-label { font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px; }
  .total-val   { font-family: var(--mono); font-size: 26px; font-weight: 700; color: var(--text); }

  /* ── Timeline ── */
  .timeline { position: relative; padding-left: 28px; }
  .timeline::before { content: ''; position: absolute; left: 10px; top: 0; bottom: 0; width: 2px; background: var(--border); }
  .timeline-item { position: relative; padding: 10px 0 10px 12px; }
  .timeline-item::before {
    content: ''; position: absolute; left: -22px; top: 50%;
    width: 12px; height: 12px; border-radius: 50%; background: var(--primary);
    transform: translateY(-50%); border: 2px solid white; box-shadow: 0 0 0 2px var(--primary);
  }
  .timeline-item.phase-before::before  { background: var(--cyan);    box-shadow: 0 0 0 2px var(--cyan); }
  .timeline-item.phase-during::before  { background: var(--warning); box-shadow: 0 0 0 2px var(--warning); }
  .timeline-item.phase-after::before   { background: var(--success); box-shadow: 0 0 0 2px var(--success); }
  .timeline-title { font-size: 14px; font-weight: 600; color: var(--text); }
  .timeline-meta  { font-size: 12px; color: var(--muted); font-family: var(--mono); margin-top: 3px; }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    nav { padding: 0 1rem; }
    .nav-tabs .nav-tab { padding: 7px 10px; font-size: 12px; }
    .stat-grid { grid-template-columns: repeat(2, 1fr); }
    .charts-row { grid-template-columns: 1fr; }
    .page { padding: 1rem; }
  }

  .mono    { font-family: var(--mono); }
  .green   { color: var(--success); }
  .orange  { color: var(--warning); }
  .red     { color: var(--danger); }
  .muted   { color: var(--muted); }
  .divider { height: 1px; background: var(--border); margin: 8px 0; }
</style>
</head>
<body>

<nav>
  <div class="nav-left">
    <div class="nav-logo">
      <div class="nav-logo-leaf">🌿</div>
      Green DevOps
    </div>
    <div class="nav-badge" id="navJob">No active deployment</div>
  </div>
  <div class="nav-right">
    <div class="nav-tabs">
      <button class="nav-tab active" onclick="switchTab('overview', this)">Overview</button>
      <button class="nav-tab" onclick="switchTab('strategy', this)">Strategy</button>
      <button class="nav-tab" onclick="switchTab('history', this)">History</button>
      <button class="nav-tab" onclick="switchTab('logs', this)">Logs</button>
    </div>
    <div class="live-pill">
      <div class="live-dot"></div>
      LIVE
    </div>
    <span class="mono" style="font-size:12px;color:var(--muted)" id="hdrTime">--</span>
  </div>
</nav>

<!-- ══ OVERVIEW ══ -->
<div class="page active" id="page-overview">

  <section>
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-card-accent" style="background:linear-gradient(90deg,#2563eb,#60a5fa)"></div>
        <div class="stat-label">Status</div>
        <div id="statStatus"><span class="badge badge-idle">IDLE</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-card-accent" style="background:linear-gradient(90deg,#7c3aed,#a78bfa)"></div>
        <div class="stat-label">Strategy</div>
        <div id="statStrategy"><span class="badge badge-idle">--</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-card-accent" style="background:linear-gradient(90deg,#0891b2,#67e8f9)"></div>
        <div class="stat-label">Duration</div>
        <div class="stat-val" id="statDuration">--</div>
        <div class="stat-sub">minutes</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-accent" style="background:linear-gradient(90deg,#d97706,#fcd34d)"></div>
        <div class="stat-label">Avg CPU</div>
        <div class="stat-val" id="statAvgCpu">--</div>
        <div class="stat-sub" id="statPeakCpu">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-accent" style="background:linear-gradient(90deg,#16a34a,#4ade80)"></div>
        <div class="stat-label">CO₂ Emitted</div>
        <div class="stat-val green" id="statCo2">--</div>
        <div class="stat-sub">grams</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-accent" style="background:linear-gradient(90deg,#059669,#34d399)"></div>
        <div class="stat-label">Energy Used</div>
        <div class="stat-val" id="statEnergy">--</div>
        <div class="stat-sub">kWh</div>
      </div>
    </div>
  </section>

  <section>
    <div class="charts-row">
      <div class="card">
        <div class="chart-title">CPU & Memory Usage</div>
        <div class="chart-wrap"><canvas id="cpuMemChart"></canvas></div>
      </div>
      <div class="card">
        <div class="chart-title">Carbon Footprint</div>
        <div class="carbon-panel">
          <div>
            <div class="carbon-big-num" id="carboBig">--</div>
            <div class="carbon-unit">grams CO₂e</div>
            <div class="carbon-meta" id="carboMeta">--</div>
          </div>
          <div class="equiv-grid" id="equivGrid">
            <div class="equiv-card" style="grid-column:1/-1"><span class="muted" style="font-size:13px">No data yet</span></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section>
    <div class="section-header">
      <div class="section-title">All-time Totals</div>
      <div class="section-line"></div>
    </div>
    <div class="totals-grid">
      <div class="total-card">
        <div class="total-label">Total Builds</div>
        <div class="total-val" id="totBuilds">--</div>
      </div>
      <div class="total-card">
        <div class="total-label">Success Rate</div>
        <div class="total-val green" id="totSuccess">--</div>
      </div>
      <div class="total-card">
        <div class="total-label">Total CO₂</div>
        <div class="total-val green" id="totCo2">--</div>
      </div>
      <div class="total-card">
        <div class="total-label">Total Energy</div>
        <div class="total-val" id="totEnergy">--</div>
      </div>
      <div class="total-card">
        <div class="total-label">Strategies Used</div>
        <div class="total-val" id="totStrategies">--</div>
      </div>
    </div>
  </section>
</div>

<!-- ══ STRATEGY ══ -->
<div class="page" id="page-strategy">

  <section>
    <div class="section-header">
      <div class="section-title">Strategy Comparison</div>
      <div class="section-line"></div>
    </div>
    <div class="strategy-grid" id="strategyGrid">
      <div class="card" style="text-align:center;padding:3rem;grid-column:1/-1">
        <p style="color:var(--muted);font-size:15px">No strategy data yet — run deployments to compare.</p>
      </div>
    </div>
  </section>

  <section>
    <div class="section-header">
      <div class="section-title">Average CO₂ per Strategy</div>
      <div class="section-line"></div>
    </div>
    <div class="card">
      <div class="chart-wrap"><canvas id="strategyBarChart"></canvas></div>
    </div>
  </section>

  <section>
    <div class="section-header">
      <div class="section-title">Recent Carbon Snapshots</div>
      <div class="section-line"></div>
    </div>
    <div class="card">
      <div class="timeline" id="snapshotTimeline">
        <p style="color:var(--muted)">No snapshots recorded</p>
      </div>
    </div>
  </section>
</div>

<!-- ══ HISTORY ══ -->
<div class="page" id="page-history">

  <section>
    <div class="section-header">
      <div class="section-title">Deployment History</div>
      <div class="section-line"></div>
      <div class="section-count" id="historyCount">0 builds</div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Build</th><th>Job</th><th>Strategy</th><th>Status</th>
            <th>Started</th><th>Duration</th><th>CPU (avg/peak)</th>
            <th>Memory (avg/peak)</th><th>CO₂ (g)</th>
            <th>Energy (kWh)</th><th>Intensity</th><th>Infra</th>
          </tr>
        </thead>
        <tbody id="historyBody">
          <tr><td colspan="12" style="text-align:center;color:var(--muted);padding:2.5rem;font-size:14px">Loading…</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</div>

<!-- LOG PAGE -->
<div class="page" id="page-logs">

  <div class="section-header" style="margin-bottom:12px">
    <div class="section-title">Live Log Viewer</div>
    <div class="section-line"></div>
  </div>

  <div class="log-shell">

    <div class="log-chrome">
      <div class="log-chrome-dots">
        <div class="log-chrome-dot red"></div>
        <div class="log-chrome-dot yellow"></div>
        <div class="log-chrome-dot green"></div>
      </div>
      <div class="log-chrome-title" id="logChromeTitle">green-devops &mdash; all services &mdash; journalctl</div>
      <div class="log-live-badge"><div class="log-live-dot"></div>LIVE</div>
    </div>

    <div class="log-filterbar">
      <span class="log-filterbar-label">svc:</span>
      <button class="log-btn active" onclick="showLogs('all', this)">all</button>
      <button class="log-btn" onclick="showLogs('deployment-tracker', this)">deployment-tracker</button>
      <button class="log-btn" onclick="showLogs('profiler', this)">profiler</button>
      <button class="log-btn" onclick="showLogs('carbon-service', this)">carbon-service</button>
      <button class="log-btn" onclick="showLogs('db-sync', this)">db-sync</button>
      <button class="log-btn" onclick="showLogs('dashboard', this)">dashboard</button>
      <input class="log-search" id="logSearch" type="text" placeholder="filter logs..." oninput="filterLogs(this.value)">
    </div>

    <div class="log-statusbar">
      <div class="log-status-svc">service: <strong id="logStatusSvc">all</strong></div>
      <div class="log-status-meta">
        <span>lines: <span id="logStatusCount">0</span></span>
        <span style="color:#ff7b72">errors: <span id="logErrCount">0</span></span>
        <span style="color:#e3b341">warns: <span id="logWarnCount">0</span></span>
      </div>
    </div>

    <div class="log-viewer" id="logViewer">
      <div class="log-empty">Connecting to log streams...</div>
    </div>

    <div class="log-bottombar">
      <button class="log-ctrl-btn on" id="autoScrollBtn" onclick="toggleAutoScroll()">&#8595; auto-scroll ON</button>
      <button class="log-ctrl-btn" onclick="fetchLogs()">&#8635; refresh</button>
      <button class="log-ctrl-btn" onclick="copyLogs()">&#10004; copy all</button>
      <button class="log-ctrl-btn danger" onclick="clearViewer()">&#10005; clear</button>
      <span class="log-last-update">last update: <span id="logLastUpdate">--</span></span>
    </div>

  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
// ── State ──────────────────────────────────────────────────────────────────
var cpuMemChartInst    = null;
var strategyBarInst    = null;
var currentLogService  = 'all';
var autoScrollLogs     = true;

// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(tab, btn) {
  document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
  document.querySelectorAll('.nav-tab').forEach(function(t) { t.classList.remove('active'); });
  document.getElementById('page-' + tab).classList.add('active');
  if (btn) btn.classList.add('active');
  if (tab === 'logs') {
    fetchLogs();
    startLogPolling();
  } else {
    stopLogPolling();
  }
}

// ── Formatting helpers ─────────────────────────────────────────────────────
function fmt(v, d) {
  if (v == null) return '--';
  return Number(v).toFixed(d != null ? d : 1);
}

function badge(status) {
  var s = (status || 'idle').toUpperCase();
  if (s === 'SUCCESS') return '<span class="badge badge-success">SUCCESS</span>';
  if (s === 'FAILURE') return '<span class="badge badge-failure">FAILURE</span>';
  if (s === 'RUNNING') return '<span class="badge badge-running">RUNNING</span>';
  return '<span class="badge badge-idle">IDLE</span>';
}

function strategyBadge(strategy) {
  if (!strategy || strategy === 'unknown') return '<span class="badge badge-idle">--</span>';
  var cls = 'badge-' + strategy.toLowerCase();
  return '<span class="badge ' + cls + '">' + strategy.toUpperCase() + '</span>';
}

// ── CPU/Mem Chart ──────────────────────────────────────────────────────────
function renderCpuMemChart(cpu, mem) {
  var canvas = document.getElementById('cpuMemChart');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var labels = (cpu || []).map(function(_, i) { return 'S' + (i + 1); });
  if (cpuMemChartInst) cpuMemChartInst.destroy();
  cpuMemChartInst = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'CPU %', data: cpu,
          borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.08)',
          borderWidth: 2.5, tension: 0.4, fill: true,
          pointRadius: (cpu||[]).length > 30 ? 0 : 3, pointHoverRadius: 5,
        },
        {
          label: 'Memory %', data: mem,
          borderColor: '#7c3aed', backgroundColor: 'rgba(124,58,237,0.06)',
          borderWidth: 2.5, tension: 0.4, fill: true, borderDash: [5,4],
          pointRadius: (mem||[]).length > 30 ? 0 : 3, pointHoverRadius: 5,
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#475569', font: { size: 13, family: "'DM Sans'" }, usePointStyle: true, padding: 20 } }
      },
      scales: {
        x: { grid: { color: '#e2e8f0' }, ticks: { color: '#94a3b8', font: { size: 11 } } },
        y: {
          min: 0, max: 100,
          grid: { color: '#e2e8f0' },
          ticks: { color: '#94a3b8', font: { size: 11 }, callback: function(v) { return v + '%'; } }
        }
      }
    }
  });
}

// ── Strategy Bar Chart ─────────────────────────────────────────────────────
function renderStrategyBarChart(stats) {
  var canvas = document.getElementById('strategyBarChart');
  if (!canvas || !stats || !stats.length) return;
  var ctx = canvas.getContext('2d');
  if (strategyBarInst) strategyBarInst.destroy();
  var colors = { rolling: '#16a34a', recreate: '#d97706', canary: '#7c3aed' };
  strategyBarInst = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: stats.map(function(s) { return (s.strategy || '?').toUpperCase(); }),
      datasets: [{
        label: 'Avg CO₂ (g)',
        data: stats.map(function(s) { return s.avg_co2 || 0; }),
        backgroundColor: stats.map(function(s) { return colors[s.strategy] || '#94a3b8'; }),
        borderRadius: 8, borderSkipped: false,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#475569', font: { size: 13 } } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 13, weight: '600' } } },
        y: {
          grid: { color: '#e2e8f0' },
          ticks: { color: '#94a3b8', font: { size: 12 }, callback: function(v) { return v + ' g'; } }
        }
      }
    }
  });
}

// ── Strategy Cards ─────────────────────────────────────────────────────────
function renderStrategyCards(stats) {
  var grid = document.getElementById('strategyGrid');
  if (!grid) return;
  if (!stats || !stats.length) {
    grid.innerHTML = '<div class="card" style="text-align:center;padding:3rem;grid-column:1/-1"><p style="color:var(--muted);font-size:15px">No strategy data yet — run deployments to compare.</p></div>';
    return;
  }
  var info = {
    rolling:  { icon: '🔄', desc: 'Gradual replacement with brief overlap — minimal downtime.' },
    recreate: { icon: '⏸',  desc: 'Full stop-and-restart cycle with brief service interruption.' },
    canary:   { icon: '🐤', desc: 'Incremental rollout; extended dual-running window.' }
  };
  var maxCo2 = Math.max.apply(null, stats.map(function(s) { return s.avg_co2 || 0; })) || 0.001;
  grid.innerHTML = stats.map(function(s) {
    var inf = info[s.strategy] || { icon: '📦', desc: 'Deployment strategy.' };
    var pct = ((s.avg_co2 || 0) / maxCo2 * 100).toFixed(1);
    return '<div class="strategy-card ' + (s.strategy || '') + '">' +
      '<div class="strategy-card-top"></div>' +
      '<div class="strategy-name">' + inf.icon + ' ' + (s.strategy || 'unknown').toUpperCase() + '</div>' +
      '<div class="strategy-desc">' + inf.desc + '</div>' +
      '<div class="strategy-stats">' +
        '<div><div class="strategy-stat-val green">' + fmt(s.avg_co2, 2) + ' g</div><div class="strategy-stat-lbl">Avg CO₂</div></div>' +
        '<div><div class="strategy-stat-val">' + fmt(s.avg_duration, 1) + ' min</div><div class="strategy-stat-lbl">Avg Duration</div></div>' +
        '<div><div class="strategy-stat-val">' + s.count + '</div><div class="strategy-stat-lbl">Deployments</div></div>' +
        '<div><div class="strategy-stat-val">' + (s.success_count||0) + '/' + s.count + '</div><div class="strategy-stat-lbl">Successes</div></div>' +
      '</div>' +
      '<div class="strategy-bar-lbl">CO₂ relative to highest emitter</div>' +
      '<div class="strategy-bar-bg"><div class="strategy-bar-fill" style="width:' + pct + '%"></div></div>' +
      '<div class="strategy-footer">Avg Infra: ' + fmt(s.avg_infra, 2) + 'x &nbsp;·&nbsp; Min: ' + fmt(s.min_co2, 2) + 'g &nbsp;·&nbsp; Max: ' + fmt(s.max_co2, 2) + 'g</div>' +
    '</div>';
  }).join('');
}

// ── History Table ──────────────────────────────────────────────────────────
function renderHistory(history) {
  var countEl = document.getElementById('historyCount');
  if (countEl) countEl.textContent = (history ? history.length : 0) + ' builds';
  if (!history || !history.length) {
    return '<tr><td colspan="12" style="text-align:center;color:var(--muted);padding:2.5rem;font-size:14px">No deployments recorded yet</td></tr>';
  }
  return history.map(function(r) {
    return '<tr>' +
      '<td style="font-weight:700">#' + (r.build_number || '?') + '</td>' +
      '<td>' + (r.job_name || '--') + '</td>' +
      '<td>' + strategyBadge(r.strategy) + '</td>' +
      '<td>' + badge(r.status) + '</td>' +
      '<td style="color:var(--muted);font-size:12px">' + (r.start_time || '--') + '</td>' +
      '<td>' + (r.duration_minutes != null ? fmt(r.duration_minutes, 1) + ' m' : '--') + '</td>' +
      '<td>' + (r.avg_cpu != null ? fmt(r.avg_cpu) + '%' : '--') + ' <span style="color:var(--muted2)">/ ' + fmt(r.peak_cpu) + '%</span></td>' +
      '<td>' + (r.avg_memory != null ? fmt(r.avg_memory) + '%' : '--') + ' <span style="color:var(--muted2)">/ ' + fmt(r.peak_memory) + '%</span></td>' +
      '<td class="co2-cell">' + (r.total_g_co2 != null ? fmt(r.total_g_co2, 3) : '--') + '</td>' +
      '<td>' + (r.total_energy_kwh != null ? Number(r.total_energy_kwh).toFixed(6) : '--') + '</td>' +
      '<td>' + (r.carbon_intensity_gco2 != null ? fmt(r.carbon_intensity_gco2, 0) + '<br><span style="color:var(--muted2);font-size:11px">' + (r.intensity_source||'') + '</span>' : '--') + '</td>' +
      '<td>' + (r.infra_multiplier != null ? fmt(r.infra_multiplier, 2) + 'x' : '--') + '</td>' +
    '</tr>';
  }).join('');
}

// ── Snapshot Timeline ──────────────────────────────────────────────────────
function renderSnapshots(snapshots) {
  var tl = document.getElementById('snapshotTimeline');
  if (!tl) return;
  if (!snapshots || !snapshots.length) {
    tl.innerHTML = '<p style="color:var(--muted)">No carbon snapshots recorded yet</p>';
    return;
  }
  tl.innerHTML = snapshots.map(function(s) {
    return '<div class="timeline-item phase-' + (s.phase || 'unknown') + '">' +
      '<div class="timeline-title">Phase: ' + (s.phase || '?').toUpperCase() + '</div>' +
      '<div class="timeline-meta">' +
        (s.job_name || '') + ' #' + (s.build_number || '?') +
        '  ·  ' + (s.strategy || '?') +
        '  ·  ' + (s.snapshot_timestamp || '') +
      '</div>' +
      '<div class="timeline-meta">' +
        'Infra: ' + fmt(s.infra_multiplier, 2) + 'x' +
        (s.downtime_seconds  ? '  ·  Downtime: ' + s.downtime_seconds + 's' : '') +
        (s.canary_weight     ? '  ·  Canary: ' + s.canary_weight + '%'     : '') +
        (s.note              ? '  ·  ' + s.note                            : '') +
      '</div>' +
    '</div>';
  }).join('');
}

// ══════════════════════════════════════════════════════════════════
//  LOG VIEWER — fully rewritten
// ══════════════════════════════════════════════════════════════════

var _logRawData    = null;   // last fetched raw data (obj or array)
var _logFilterText = '';

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function colorizeLine(line) {
  if (!line && line !== 0) return '';
  var s   = String(line);
  var low = s.toLowerCase();
  var cls = '';
  if (/error|fail|traceback|exception|critical/.test(low)) cls = 'error';
  else if (/warn|warning/.test(low))                       cls = 'warn';
  else if (/success|completed|done|\bok\b/.test(low))      cls = 'success';
  else if (/info|started|processing|running|fetching|listening/.test(low)) cls = 'info';

  // Pull timestamp prefix out so it gets dimmed
  var timeRx = /^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[+\-]\d{4})?)\s*/;
  var tm     = s.match(timeRx);
  var tsHtml = tm ? '<span class="log-timestamp">' + escHtml(tm[1]) + '</span>' : '';
  var rest   = tm ? s.slice(tm[0].length) : s;

  // Apply filter — hide line if it doesn't match
  var filterClass = '';
  if (_logFilterText && s.toLowerCase().indexOf(_logFilterText) === -1) {
    filterClass = ' hidden';
  }

  return '<span class="log-line' + (cls ? ' ' + cls : '') + filterClass + '">'
       + tsHtml + escHtml(rest)
       + '</span>\n';
}

function buildHtml(data) {
  var html      = '';
  var total     = 0;
  var errCount  = 0;
  var warnCount = 0;

  if (currentLogService === 'all') {
    var svcs = Object.keys(data || {});
    if (!svcs.length) return { html: '<div class="log-empty">No log data — are the services running?</div>', total: 0, err: 0, warn: 0 };

    svcs.forEach(function(svc) {
      var lines = Array.isArray(data[svc]) ? data[svc] : [];
      html += '<span class="log-svc-header">&#9658; ' + escHtml(svc) + ' &nbsp;(' + lines.length + ' lines)</span>';
      if (!lines.length) {
        html += '<span class="log-line" style="color:#484f58">  (no entries yet)</span>\n';
      } else {
        lines.slice(-60).forEach(function(l) {
          var rendered = colorizeLine(l);
          html += rendered;
          var low = String(l).toLowerCase();
          if (/error|fail|traceback|exception/.test(low)) errCount++;
          else if (/warn/.test(low)) warnCount++;
        });
        total += lines.length;
      }
    });
  } else {
    var lines = Array.isArray(data) ? data : [];
    if (!lines.length) return { html: '<div class="log-empty">No entries for this service yet</div>', total: 0, err: 0, warn: 0 };
    lines.slice(-200).forEach(function(l) {
      html += colorizeLine(l);
      var low = String(l).toLowerCase();
      if (/error|fail|traceback|exception/.test(low)) errCount++;
      else if (/warn/.test(low)) warnCount++;
    });
    total = lines.length;
  }

  return { html: html, total: total, err: errCount, warn: warnCount };
}

function renderLogs(data) {
  _logRawData = data;
  var viewer  = document.getElementById('logViewer');
  if (!viewer) return;

  var wasAtBottom = (viewer.scrollHeight - viewer.clientHeight - viewer.scrollTop) < 40;
  var result = buildHtml(data);

  viewer.innerHTML = result.html || '<div class="log-empty">No logs to display</div>';

  // Update status counts
  var el;
  el = document.getElementById('logStatusCount'); if (el) el.textContent = result.total;
  el = document.getElementById('logErrCount');    if (el) el.textContent = result.err;
  el = document.getElementById('logWarnCount');   if (el) el.textContent = result.warn;
  el = document.getElementById('logLastUpdate');
  if (el) el.textContent = new Date().toLocaleTimeString();

  // Auto-scroll
  if (autoScrollLogs && wasAtBottom) {
    viewer.scrollTop = viewer.scrollHeight;
  }
}

function filterLogs(text) {
  _logFilterText = (text || '').trim().toLowerCase();
  if (_logRawData) renderLogs(_logRawData);
}

function fetchLogs() {
  var url = currentLogService === 'all'
    ? '/api/logs'
    : '/api/logs/' + encodeURIComponent(currentLogService);

  fetch(url)
    .then(function(res) {
      if (!res.ok) throw new Error('HTTP ' + res.status + ' from ' + url);
      return res.json();
    })
    .then(function(data) {
      renderLogs(data);
    })
    .catch(function(err) {
      var viewer = document.getElementById('logViewer');
      if (viewer) {
        viewer.innerHTML = '<div class="log-empty" style="color:#ff7b72">&#9888; ' + escHtml(String(err)) + '</div>';
      }
    });
}

function showLogs(service, btn) {
  currentLogService = service;
  _logFilterText    = '';
  var searchEl = document.getElementById('logSearch');
  if (searchEl) searchEl.value = '';

  document.querySelectorAll('.log-btn').forEach(function(b) { b.classList.remove('active'); });
  if (btn) btn.classList.add('active');

  var svcEl = document.getElementById('logStatusSvc');
  if (svcEl) svcEl.textContent = service;

  var titleEl = document.getElementById('logChromeTitle');
  if (titleEl) titleEl.textContent = 'green-devops \u2014 ' + service + ' \u2014 journalctl';

  fetchLogs();
}

function toggleAutoScroll() {
  autoScrollLogs = !autoScrollLogs;
  var btn = document.getElementById('autoScrollBtn');
  if (btn) {
    btn.textContent = autoScrollLogs ? '\u2193 auto-scroll ON' : '\u2193 auto-scroll OFF';
    btn.className   = autoScrollLogs ? 'log-ctrl-btn on' : 'log-ctrl-btn';
  }
}

function copyLogs() {
  var viewer = document.getElementById('logViewer');
  if (!viewer) return;
  var text = viewer.innerText || viewer.textContent || '';
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(function() {});
  }
}

function clearViewer() {
  _logRawData = null;
  var viewer  = document.getElementById('logViewer');
  if (viewer) viewer.innerHTML = '<div class="log-empty">Viewer cleared. Next refresh will reload logs.</div>';
}

// Only poll logs when on the logs tab — saves bandwidth
var logInterval = null;
function startLogPolling()  {
  if (!logInterval) logInterval = setInterval(fetchLogs, 5000);
}
function stopLogPolling() {
  if (logInterval) { clearInterval(logInterval); logInterval = null; }
}

// ── Main Data Fetch ────────────────────────────────────────────────────────
function fetchData() {
  fetch('/api/data')
    .then(function(res) { return res.json(); })
    .then(function(data) {
      var dep   = data.deployment     || {};
      var prof  = data.profiler       || {};
      var carb  = data.carbon         || {};
      var tots  = data.totals         || {};
      var stats = data.strategy_stats || [];
      var em    = (carb.emissions)    || {};

      // Nav
      document.getElementById('navJob').textContent = dep.job_name
        ? dep.job_name + ' #' + (dep.build_number || '?') + '  ' + (dep.strategy || '')
        : 'No active deployment';
      document.getElementById('hdrTime').textContent = data.updated_at || '--';

      // Stats
      document.getElementById('statStatus').innerHTML   = badge(dep.status || 'idle');
      document.getElementById('statStrategy').innerHTML = strategyBadge(dep.strategy);
      document.getElementById('statDuration').textContent = prof.duration_minutes != null
        ? fmt(prof.duration_minutes)
        : (dep.duration_minutes != null ? fmt(dep.duration_minutes) : '--');
      document.getElementById('statAvgCpu').textContent = prof.avg_cpu  != null ? fmt(prof.avg_cpu) + '%'         : '--';
      document.getElementById('statPeakCpu').textContent = prof.peak_cpu != null ? 'peak ' + fmt(prof.peak_cpu) + '%' : '--';
      document.getElementById('statCo2').textContent   = em.total_g_co2 != null ? fmt(em.total_g_co2, 3)         : '--';
      document.getElementById('statEnergy').textContent = (carb.energy || {}).total_energy_kwh != null
        ? Number(carb.energy.total_energy_kwh).toFixed(6) : '--';

      // CPU/Mem chart
      if (prof.cpu_readings && prof.cpu_readings.length) {
        renderCpuMemChart(prof.cpu_readings, prof.memory_readings || []);
      }

      // Carbon big number
      var co2g = em.total_g_co2;
      document.getElementById('carboBig').textContent = co2g != null ? fmt(co2g, 2) : '--';
      var ci = carb.carbon_intensity || {};
      document.getElementById('carboMeta').textContent = ci.intensity_gco2_kwh != null
        ? ci.intensity_gco2_kwh + ' gCO₂/kWh  (' + (ci.source || 'unknown') + ')'
        : 'No intensity data';

      // Equivalences
      var equiv = carb.equivalences;
      var icons = { driving: '🚗', phone: '📱', searches: '🔍' };
      var equivHtml = '';
      if (equiv && Object.keys(equiv).length) {
        Object.keys(equiv).forEach(function(k) {
          var v = equiv[k];
          equivHtml += '<div class="equiv-card">' +
            '<div class="equiv-icon">' + (icons[k] || '📊') + '</div>' +
            '<div class="equiv-text"><strong>' + k + '</strong>' + (v.description || v) + '</div></div>';
        });
      } else {
        equivHtml = '<div class="equiv-card" style="grid-column:1/-1"><span style="color:var(--muted);font-size:13px">No equivalence data</span></div>';
      }
      document.getElementById('equivGrid').innerHTML = equivHtml;

      // Totals
      document.getElementById('totBuilds').textContent    = tots.total_builds != null ? tots.total_builds : '--';
      document.getElementById('totSuccess').textContent   = tots.total_builds
        ? Math.round((tots.success_count / tots.total_builds) * 100) + '%' : '--';
      document.getElementById('totCo2').textContent       = tots.total_co2_g    != null ? fmt(tots.total_co2_g, 2) + ' g'   : '--';
      document.getElementById('totEnergy').textContent    = tots.total_energy_kwh != null ? Number(tots.total_energy_kwh).toFixed(4) + ' kWh' : '--';
      document.getElementById('totStrategies').textContent = tots.strategy_count != null ? tots.strategy_count : '--';

      // Strategy
      renderStrategyCards(stats);
      renderStrategyBarChart(stats);
      renderSnapshots(data.snapshots || []);

      // History
      document.getElementById('historyBody').innerHTML = renderHistory(data.history);
    })
    .catch(function(err) { console.error('Data fetch error:', err); });
}

// ── Boot ───────────────────────────────────────────────────────────────────
fetchData();
setInterval(fetchData, 15000);
// Log polling starts only when user opens the Logs tab (see switchTab)
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Green DevOps Dashboard")
    parser.add_argument("--port",      type=int, default=5050)
    parser.add_argument("--watch-dir", type=str, default="/opt/energy-profiller-hiran")
    parser.add_argument("--host",      type=str, default="0.0.0.0")
    args = parser.parse_args()

    WATCH_DIR       = Path(args.watch_dir)
    DEPLOYMENT_FILE = WATCH_DIR / "deployment_last.json"
    PROFILER_FILE   = WATCH_DIR / "profiler_results.json"
    CARBON_FILE     = WATCH_DIR / "carbon_report.json"
    DB_PATH         = WATCH_DIR / "deployments.db"

    print("=" * 60)
    print("  Green DevOps — Deployment Energy Dashboard")
    print("=" * 60)
    print(f"\n  Dashboard:  http://{args.host}:{args.port}")
    print(f"  API Data:   http://{args.host}:{args.port}/api/data")
    print(f"  Logs (all): http://{args.host}:{args.port}/api/logs")
    print(f"  Watch dir:  {args.watch_dir}")
    print("\n  Auto-refresh: 15s (data) / 5s (logs)")
    print("=" * 60 + "\n")

    app.run(host=args.host, port=args.port, debug=False)
