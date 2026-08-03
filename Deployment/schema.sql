-- schema.sql
-- Updated with deployment strategy support

CREATE TABLE IF NOT EXISTS deployments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name        TEXT,
    build_number    TEXT,
    status          TEXT,
    strategy        TEXT,           -- NEW: rolling, recreate, canary
    canary_weight   TEXT,           -- NEW: % traffic to canary (if applicable)
    carbon_profile  TEXT,           -- NEW: low_gradual, low_burst, medium_transient
    image           TEXT,           -- NEW: Docker image used
    start_time      TEXT,
    end_time        TEXT,
    duration_minutes REAL,
    recorded_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiler_results (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    deployment_id       INTEGER REFERENCES deployments(id),
    start_time          TEXT,
    end_time            TEXT,
    duration_minutes    REAL,
    samples_collected   INTEGER,
    avg_cpu             REAL,
    peak_cpu            REAL,
    min_cpu             REAL,
    avg_memory          REAL,
    peak_memory         REAL,
    min_memory          REAL,
    cpu_readings        TEXT,   -- JSON array stored as text
    memory_readings     TEXT,   -- JSON array stored as text
    recorded_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS carbon_reports (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    deployment_id           INTEGER REFERENCES deployments(id),
    job_name                TEXT,
    build_number            TEXT,
    strategy                TEXT,           -- NEW: deployment strategy used
    total_g_co2             REAL,
    total_kg_co2            REAL,
    total_energy_kwh        REAL,
    carbon_intensity_gco2   REAL,
    intensity_source        TEXT,
    strategy_carbon_profile TEXT,           -- NEW: carbon profile type
    infra_multiplier        REAL,           -- NEW: avg infrastructure multiplier
    computed_at             TEXT,
    full_report             TEXT,   -- full JSON blob for safety
    recorded_at             TEXT DEFAULT (datetime('now'))
);

-- NEW: Carbon snapshots table for tracking per-phase carbon data
CREATE TABLE IF NOT EXISTS carbon_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    deployment_id       INTEGER REFERENCES deployments(id),
    build_number        TEXT,
    phase               TEXT,           -- before, during, after, canary_live, promoted
    strategy            TEXT,
    infra_multiplier    REAL,
    downtime_seconds    REAL,           -- for recreate strategy
    canary_weight       TEXT,           -- for canary strategy
    note                TEXT,
    snapshot_timestamp  TEXT,
    recorded_at         TEXT DEFAULT (datetime('now'))
);

-- Unique indexes to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS ux_deployments ON deployments(job_name, build_number, start_time);
CREATE UNIQUE INDEX IF NOT EXISTS ux_carbon ON carbon_reports(job_name, build_number, computed_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_snapshots ON carbon_snapshots(deployment_id, phase);

-- Strategy performance view for easy comparison
CREATE VIEW IF NOT EXISTS strategy_comparison AS
SELECT 
    d.strategy,
    COUNT(*) as deployment_count,
    AVG(d.duration_minutes) as avg_duration_min,
    AVG(cr.total_g_co2) as avg_co2_g,
    AVG(cr.total_energy_kwh) as avg_energy_kwh,
    AVG(cr.infra_multiplier) as avg_infra_multiplier,
    MIN(cr.total_g_co2) as min_co2_g,
    MAX(cr.total_g_co2) as max_co2_g
FROM deployments d
LEFT JOIN carbon_reports cr ON d.id = cr.deployment_id
WHERE d.strategy IS NOT NULL
GROUP BY d.strategy
ORDER BY avg_co2_g ASC;
