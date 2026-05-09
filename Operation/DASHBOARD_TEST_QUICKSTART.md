# Dashboard Testing Quick Start

## Test Status: ✅ READY

Both dashboards are validated and ready to test:
- **Level 1 Dashboard** (`dashboard/app.py`): ✓ VALID (16 KB, 15+ functions)
- **Level 2 Dashboard** (`dashboard/technical_app.py`): ✓ VALID (31 KB, 20+ functions)
- **Dependencies**: ✓ streamlit, requests, pandas installed

---

## Launch Test Environment (3 Terminals)

### Terminal 1: Start Engine 1 API Server
```bash
cd d:\Research\Operation\green-devops-operation-component
python run_live_api.py
```
**Wait for:** `INFO: Uvicorn running on http://0.0.0.0:8000`

### Terminal 2: Launch Level 1 Dashboard
```bash
cd d:\Research\Operation\green-devops-operation-component
streamlit run dashboard/app.py --server.port 8501
```
**Wait for:** `Local URL: http://localhost:8501`

**Access in browser:** [http://localhost:8501](http://localhost:8501)

### Terminal 3: Launch Level 2 Dashboard
```bash
cd d:\Research\Operation\green-devops-operation-component
streamlit run dashboard/technical_app.py --server.port 8502
```
**Wait for:** `Local URL: http://localhost:8502`

**Access in browser:** [http://localhost:8502](http://localhost:8502)

---

## Level 1 Dashboard - Non-Technical User Test

**URL:** http://localhost:8501

### What You Should See:

1. **Header**
   - Title: "Green DevOps System Dashboard"
   - Subtitle: "Real-Time System Monitoring"

2. **System Status Cards** (4 metrics)
   - System Status (color-coded: 🟢 RUNNING, 🟡 WARNING, 🔴 ERROR)
   - Mode (Cold Start = Learning phase, Runtime = Normal operation)
   - Last Updated (age in seconds)
   - Data Source (indicates data collection status)

3. **Workload Metrics** (3 large cards)
   - Current CPU Usage (% - real value from API)
   - Predicted CPU (next 30 seconds - real prediction)
   - Load Level (🟢 LOW, 🟡 NORMAL, 🔴 HIGH)

4. **Scaling Recommendation**
   - Current Pods (running)
   - Recommended Pods (based on load)
   - Action (SCALE UP / SCALE DOWN / NO CHANGE)

5. **CPU Trend Chart**
   - Historical CPU line chart
   - Rolling window of recent data

6. **Alerts & Notifications**
   - System status messages
   - Scaling recommendations
   - Data collection status

### Test Checklist - Level 1:
- [ ] Page loads without errors
- [ ] All 6 sections display
- [ ] Values are **real** (not hardcoded)
- [ ] Colors match status (green/yellow/red)
- [ ] Auto-refreshes every 7 seconds
- [ ] Manual refresh button works
- [ ] Non-technical language used

---

## Level 2 Dashboard - Technical User Test

**URL:** http://localhost:8502

### Tab 1: System Overview

**Section 1: System Overview Cards**
- API Status (✓ OK or ✗ ERROR)
- Mode (cold_start or runtime)
- Records (count of collected data)
- Model (version)
- Timestep (30s default)
- Sequence (12 default)
- Retrain Ready (YES/NO)
- Data Age (seconds)

**Section 2: Current Prediction**
- Predicted CPU (%)
- Load Level
- Recommended Pods
- Confidence score
- Data Source (cold_start or runtime)
- Prediction Timestamp

### Tab 2: Metrics & Trends

**Section 1: Runtime Metrics**
- Latest CPU (real value)
- Latest Memory (real value)
- Collection Time
- Records Stored (total)
- Recent Metrics Table (12 latest readings)

**Section 2: Trend Graphs**
- CPU Usage Trend (historical)
- Predicted CPU Trend (forecast history)

**Section 3: Prediction History Table**
- Timestamp, Predicted CPU, Load Level, Recommended Pods, Data Source

### Tab 3: Diagnostics

**Section 1: Mode Analysis**
- Current mode (cold_start or runtime)
- Status and record count
- Progress to runtime mode

**Section 2: Sequence Configuration**
- Sequence Length (12)
- Timestep (30s)
- Total Window (seq_len × timestep)

**Section 3: Runtime Readiness**
- Ready for runtime? (based on record count)
- Retrain information

**Section 4: Runtime Storage Status**
- Predictions directory
- Metrics directory
- Config file

### Tab 4: Backend Health

**Section 1: API Endpoint**
- Reachable? (✓ or ✗)
- URL

**Section 2: Data Storage**
- All sources available?
- Individual source status

**Section 3: Endpoints**
- `/health` status
- `/predict` status
- `/status` status
- `/metrics` status

### Test Checklist - Level 2:
- [ ] All 4 tabs load without errors
- [ ] **ALL VALUES ARE REAL** (from API, not hardcoded)
- [ ] API endpoints show reachability
- [ ] Metrics table shows actual data
- [ ] Trend charts show historical data
- [ ] Diagnostics match actual system state
- [ ] All status indicators accurate
- [ ] Auto-refreshes every 8 seconds
- [ ] Error messages clear and actionable

---

## Data Source Verification

### Real Data Sources (Level 2 validates all):

1. **API Endpoints** (/health, /predict, /status, /metrics)
   - Used by both dashboards
   - Check responses in browser dev tools

2. **Runtime CSV Storage**
   - Path: `data/predictions/{system_id}.csv`
   - Path: `data/runtime_metrics/{system_id}_runtime_metrics.csv`
   - Level 2 dashboard reads these files

3. **Configuration**
   - Path: `src/workload_prediction_engine/config.py`
   - Level 2 dashboard parses this file

### Real Data Indicators:

✅ **Level 1 shows real data when:**
- System status matches API health
- CPU values match actual metrics
- Predictions come from API /predict response
- Load level changes based on CPU

✅ **Level 2 shows real data when:**
- Metrics table populates from CSV files
- Trend charts show historical patterns
- Mode shows actual system state (cold_start/runtime)
- Data Source column shows where data came from
- Record counts match stored files

❌ **You'd see fake data if:**
- Numbers never change
- They're hardcoded (0, 50, 100)
- Charts don't show history
- Status doesn't match API

---

## Troubleshooting

### Dashboard shows "No data available"
1. Check API is running: Terminal 1 should show `Uvicorn running`
2. Wait 5 seconds - may be first-time initialization
3. Click "Refresh Now" button in dashboard

### Dashboard shows "API unavailable"
1. Verify Terminal 1 is still running
2. Check port 8000 is not blocked: `netstat -an | findstr 8000`
3. Restart API: `python run_live_api.py`

### Trend charts are empty
1. System needs 30+ seconds of data collection
2. Wait 1-2 minutes with API running
3. Refresh dashboard

### Values are all zeros or N/A
1. Check runtime metrics directory exists: `dir data/runtime_metrics`
2. Ensure API has collected at least 1 record
3. Wait for cold-start phase (12 records needed)

### Dashboard won't load
1. Check Python 3.8+ installed: `python --version`
2. Reinstall streamlit: `pip install --upgrade streamlit`
3. Try different port: `streamlit run dashboard/app.py --server.port 8503`

---

## What to Verify

### Critical Tests:
- [ ] Level 1 shows **real** CPU/memory from API
- [ ] Level 2 shows **real** data from all sources
- [ ] Both use actual Engine 1 system data
- [ ] No hardcoded or fake values
- [ ] API unavailability handled gracefully
- [ ] Error messages are clear

### Feature Tests:
- [ ] Auto-refresh works
- [ ] Manual refresh button works
- [ ] Pagination works (if tables are long)
- [ ] Charts render correctly
- [ ] Color coding is consistent
- [ ] Responsive design (window resize)

### Data Accuracy Tests:
- [ ] CPU values match between dashboards
- [ ] Mode (cold_start/runtime) is correct
- [ ] Record counts are accurate
- [ ] Timestamps make sense
- [ ] Predictions are reasonable

---

## Stop Testing

**In each terminal, press:** `Ctrl+C`

Expected output: `Shutting down...` (or similar)

---

## Test Complete ✅

document next results:
- Which dashboard version tested
- Data sources verified
- Any issues found
- Observations about real data

