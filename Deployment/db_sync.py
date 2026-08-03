"""
db_sync.py
----------
Watches deployment_last.json, profiler_results.json, carbon_report.json,
and carbon_snapshot_*.json files and syncs them into an SQLite database.

Now supports deployment strategy tracking (rolling, recreate, canary)
and per-phase carbon snapshots.

Run as a systemd service — does NOT modify any existing scripts.

    python3 db_sync.py --watch-dir /opt/energy-profiller-hiran
"""

import json
import logging
import os
import signal
import sqlite3
import time
import glob
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("db_sync")

# ── Config ────────────────────────────────────────────────────────────────────
WATCH_DIR   = Path("/opt/energy-profiller-hiran")
DB_PATH     = WATCH_DIR / "deployments.db"
SCHEMA_PATH = WATCH_DIR / "schema.sql"

DEPLOYMENT_FILE = WATCH_DIR / "deployment_last.json"
PROFILER_FILE   = WATCH_DIR / "profiler_results.json"
CARBON_FILE     = WATCH_DIR / "carbon_report.json"

POLL_INTERVAL = 5   # seconds between checks

# ── Database helpers ──────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables from schema.sql if they don't exist."""
    with get_connection() as conn:
        if SCHEMA_PATH.exists():
            conn.executescript(SCHEMA_PATH.read_text())
        else:
            logger.error(f"Schema file not found: {SCHEMA_PATH}")
            raise FileNotFoundError(SCHEMA_PATH)
    logger.info(f"Database ready at {DB_PATH}")


def read_json(path: Path):
    """Read a JSON file safely; return None if missing or corrupt."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"Cannot read {path}: {e}")
        return None


def file_mtime(path: Path) -> float:
    """Return file modification time, or 0 if missing."""
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


# ── Sync functions ────────────────────────────────────────────────────────────

def sync_deployment(data: dict) -> int | None:
    """
    Upsert a deployment record. Returns the row id (new or existing).
    Now includes strategy, canary_weight, carbon_profile, and image fields.
    """
    with get_connection() as conn:
        # Try insert; skip if duplicate (same job+build+start_time)
        cur = conn.execute("""
            INSERT OR IGNORE INTO deployments
                (job_name, build_number, status, strategy, canary_weight, 
                 carbon_profile, image, start_time, end_time, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("job_name"),
            str(data.get("build_number", "?")),
            data.get("status"),
            data.get("strategy"),
            data.get("canary_weight"),
            data.get("carbon_profile"),
            data.get("image"),
            data.get("start_time"),
            data.get("end_time"),
            data.get("duration_minutes"),
        ))

        if cur.rowcount:
            logger.info(f"  [deployments] Inserted row {cur.lastrowid}"
                        f" — {data.get('job_name')} #{data.get('build_number')}"
                        f" (strategy: {data.get('strategy', 'unknown')})")
            return cur.lastrowid

        # Already exists — update strategy info and fetch its id
        conn.execute("""
            UPDATE deployments 
            SET strategy = ?, canary_weight = ?, carbon_profile = ?, image = ?
            WHERE job_name=? AND build_number=? AND start_time=?
        """, (
            data.get("strategy"),
            data.get("canary_weight"),
            data.get("carbon_profile"),
            data.get("image"),
            data.get("job_name"),
            str(data.get("build_number","?")),
            data.get("start_time")
        ))
        
        row = conn.execute("""
            SELECT id FROM deployments
            WHERE job_name=? AND build_number=? AND start_time=?
        """, (data.get("job_name"), str(data.get("build_number","?")), data.get("start_time"))).fetchone()
        return row["id"] if row else None


def sync_profiler(data: dict, deployment_id: int | None):
    """Upsert a profiler_results record linked to a deployment."""
    with get_connection() as conn:
        # Use (start_time, end_time) as a natural unique key
        exists = conn.execute("""
            SELECT id FROM profiler_results
            WHERE start_time=? AND end_time=?
        """, (data.get("start_time"), data.get("end_time"))).fetchone()

        if exists:
            return   # already recorded

        conn.execute("""
            INSERT INTO profiler_results
                (deployment_id, start_time, end_time, duration_minutes,
                 samples_collected, avg_cpu, peak_cpu, min_cpu,
                 avg_memory, peak_memory, min_memory,
                 cpu_readings, memory_readings)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            deployment_id,
            data.get("start_time"),
            data.get("end_time"),
            data.get("duration_minutes"),
            data.get("samples_collected"),
            data.get("avg_cpu"),
            data.get("peak_cpu"),
            data.get("min_cpu"),
            data.get("avg_memory"),
            data.get("peak_memory"),
            data.get("min_memory"),
            json.dumps(data.get("cpu_readings", [])),
            json.dumps(data.get("memory_readings", [])),
        ))
        logger.info(f"  [profiler_results] Inserted"
                    f" — {data.get('samples_collected')} samples,"
                    f" avg CPU {data.get('avg_cpu')}%")


def sync_carbon(data: dict, deployment_id: int | None):
    """Upsert a carbon_report record with strategy information."""
    emissions   = data.get("emissions", {})
    energy      = data.get("energy", {})
    intensity   = data.get("carbon_intensity", {})
    deployment  = data.get("deployment", {})
    strategy_carbon = data.get("strategy_carbon", {})

    job_name     = deployment.get("job_name", data.get("job_name", "unknown"))
    build_number = str(deployment.get("build_number", data.get("build_number", "?")))
    strategy     = deployment.get("strategy", data.get("strategy", "unknown"))
    computed_at  = data.get("computed_at", datetime.utcnow().isoformat())
    
    # Extract strategy carbon profile
    strategy_carbon_profile = strategy_carbon.get("actual_profile", strategy_carbon.get("profile", "unknown"))
    infra_multiplier = strategy_carbon.get("avg_infra_multiplier", 1.0)

    with get_connection() as conn:
        exists = conn.execute("""
            SELECT id FROM carbon_reports
            WHERE job_name=? AND build_number=? AND computed_at=?
        """, (job_name, build_number, computed_at)).fetchone()

        if exists:
            # Update with strategy info if it wasn't there before
            conn.execute("""
                UPDATE carbon_reports
                SET strategy = ?, strategy_carbon_profile = ?, infra_multiplier = ?
                WHERE job_name=? AND build_number=? AND computed_at=?
            """, (strategy, strategy_carbon_profile, infra_multiplier, 
                  job_name, build_number, computed_at))
            return

        conn.execute("""
            INSERT INTO carbon_reports
                (deployment_id, job_name, build_number, strategy,
                 total_g_co2, total_kg_co2, total_energy_kwh,
                 carbon_intensity_gco2, intensity_source,
                 strategy_carbon_profile, infra_multiplier,
                 computed_at, full_report)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            deployment_id,
            job_name,
            build_number,
            strategy,
            emissions.get("total_g_co2"),
            emissions.get("total_kg_co2"),
            energy.get("total_energy_kwh"),
            intensity.get("intensity_gco2_kwh"),
            intensity.get("source"),
            strategy_carbon_profile,
            infra_multiplier,
            computed_at,
            json.dumps(data),   # full blob for future use
        ))
        logger.info(f"  [carbon_reports] Inserted"
                    f" — {emissions.get('total_g_co2'):.2f} g CO₂"
                    f" for {job_name} #{build_number}"
                    f" (strategy: {strategy}, profile: {strategy_carbon_profile})")


def sync_carbon_snapshots(deployment_id: int | None, build_number: str):
    """
    Scan for carbon_snapshot_*.json files and sync them into the database.
    These files are created by deployment_tracker.py for each phase.
    """
    if not build_number or build_number == "?":
        return
    
    snapshot_pattern = WATCH_DIR / f"carbon_snapshot_{build_number}_*.json"
    snapshot_files = glob.glob(str(snapshot_pattern))
    
    if not snapshot_files:
        logger.debug(f"No snapshot files found for build #{build_number}")
        return
    
    with get_connection() as conn:
        for snapshot_path in snapshot_files:
            try:
                with open(snapshot_path, 'r') as f:
                    snapshot = json.load(f)
                
                phase = snapshot.get("phase", "unknown")
                
                # Check if already synced
                exists = conn.execute("""
                    SELECT id FROM carbon_snapshots
                    WHERE deployment_id=? AND phase=?
                """, (deployment_id, phase)).fetchone()
                
                if exists:
                    continue
                
                conn.execute("""
                    INSERT INTO carbon_snapshots
                        (deployment_id, build_number, phase, strategy,
                         infra_multiplier, downtime_seconds, canary_weight,
                         note, snapshot_timestamp)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    deployment_id,
                    str(build_number),
                    phase,
                    snapshot.get("strategy"),
                    snapshot.get("infra_multiplier"),
                    snapshot.get("downtime_seconds"),
                    snapshot.get("canary_weight"),
                    snapshot.get("note"),
                    snapshot.get("timestamp"),
                ))
                logger.info(f"  [carbon_snapshots] Inserted phase '{phase}' for build #{build_number}")
                
            except Exception as e:
                logger.error(f"Failed to sync snapshot {snapshot_path}: {e}")


# ── Watcher loop ──────────────────────────────────────────────────────────────

class DbSyncService:
    def __init__(self):
        self.running  = True
        self._mtimes  = {DEPLOYMENT_FILE: 0.0, PROFILER_FILE: 0.0, CARBON_FILE: 0.0}
        self._snapshot_mtimes = {}  # Track snapshot file mtimes

    def _changed(self, path: Path) -> bool:
        """Return True if the file is newer than the last time we saw it."""
        mtime = file_mtime(path)
        if mtime > self._mtimes.get(path, 0.0):
            self._mtimes[path] = mtime
            return True
        return False
    
    def _snapshot_changed(self, path: str) -> bool:
        """Check if a snapshot file has been updated."""
        mtime = os.path.getmtime(path) if os.path.exists(path) else 0.0
        if mtime > self._snapshot_mtimes.get(path, 0.0):
            self._snapshot_mtimes[path] = mtime
            return True
        return False

    def tick(self):
        """Check all files and sync any that changed."""
        dep_data  = read_json(DEPLOYMENT_FILE)
        prof_data = read_json(PROFILER_FILE)
        carb_data = read_json(CARBON_FILE)

        dep_changed  = self._changed(DEPLOYMENT_FILE)
        prof_changed = self._changed(PROFILER_FILE)
        carb_changed = self._changed(CARBON_FILE)
        
        # Check for new snapshot files
        snapshot_files = glob.glob(str(WATCH_DIR / "carbon_snapshot_*_*.json"))
        snapshots_changed = any(self._snapshot_changed(f) for f in snapshot_files)

        if not (dep_changed or prof_changed or carb_changed or snapshots_changed):
            return   # nothing new

        logger.info("Change detected — syncing to database...")

        # 1. Deployment first (other tables reference it)
        deployment_id = None
        build_number = "?"
        if dep_data:
            deployment_id = sync_deployment(dep_data)
            build_number = dep_data.get("build_number", "?")

        # 2. Profiler result
        if prof_data and prof_changed:
            sync_profiler(prof_data, deployment_id)

        # 3. Carbon report
        if carb_data and carb_changed:
            sync_carbon(carb_data, deployment_id)
        
        # 4. Carbon snapshots (per-phase data)
        if snapshots_changed:
            sync_carbon_snapshots(deployment_id, str(build_number))

    def stop(self, *_):
        logger.info("Stopping db_sync service...")
        self.running = False

    def run(self):
        signal.signal(signal.SIGINT,  self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        logger.info(f"db_sync watching {WATCH_DIR}")
        logger.info(f"Database: {DB_PATH}")
        logger.info("Tracking deployment strategies: rolling, recreate, canary")

        while self.running:
            try:
                self.tick()
            except Exception as e:
                logger.error(f"Sync error: {e}", exc_info=True)
            time.sleep(POLL_INTERVAL)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="JSON → SQLite sync service")
    parser.add_argument("--watch-dir", default="/opt/energy-profiller-hiran")
    args = parser.parse_args()

    WATCH_DIR       = Path(args.watch_dir)
    DB_PATH         = WATCH_DIR / "deployments.db"
    SCHEMA_PATH     = WATCH_DIR / "schema.sql"
    DEPLOYMENT_FILE = WATCH_DIR / "deployment_last.json"
    PROFILER_FILE   = WATCH_DIR / "profiler_results.json"
    CARBON_FILE     = WATCH_DIR / "carbon_report.json"

    init_db()
    DbSyncService().run()
