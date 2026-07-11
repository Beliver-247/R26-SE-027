# Dashboard Testing Guide

## Quick Test - Both Dashboards

### Prerequisites
Ensure dependencies are installed:
```bash
pip install streamlit requests pandas
```

### Test Steps

#### Step 1: Start Engine 1 API (Terminal 1)
```bash
cd d:\Research\Operation\green-devops-operation-component
python run_live_api.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Step 2: Launch Level 1 Dashboard - Non-Technical (Terminal 2)
```bash
cd d:\Research\Operation\green-devops-operation-component
streamlit run dashboard/app.py --server.port 8501
```

Expected output:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

**Open browser:** http://localhost:8501

**Test Level 1:**
- [ ] System Status cards display (Status, Mode, Last Updated, Data Source)
- [ ] Workload Metrics show real CPU/Memory values
- [ ] Load Level displays (LOW/NORMAL/HIGH)
- [ ] Scaling Recommendation shows current and recommended pods
- [ ] Trend chart displays CPU history
- [ ] Alerts panel shows alerts
- [ ] Auto-refresh works every 7 seconds
- [ ] Colors are appropriate (green/yellow/red)

#### Step 3: Launch Level 2 Dashboard - Technical (Terminal 3)
```bash
cd d:\Research\Operation\green-devops-operation-component
streamlit run dashboard/technical_app.py --server.port 8502
```

Expected output:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8502
```

**Open browser:** http://localhost:8502

**Test Level 2:**

**System Overview Tab:**
- [ ] API Status shows ✓ OK (real data from /health)
- [ ] Mode shows current mode (cold_start or runtime)
- [ ] Records shows count (real from API)
- [ ] Model version displays (real from config)
- [ ] Prediction window shows 30s
- [ ] Sequence shows 12
- [ ] Retrain Ready shows YES/NO (real status)
- [ ] Data Age shows seconds since last update

**Metrics & Trends Tab:**
- [ ] Latest CPU shows real value
- [ ] Latest Memory shows real value
- [ ] Collection Time shows actual timestamp
- [ ] Records Stored shows total count
- [ ] Recent Metrics table shows real data
- [ ] CPU Usage Trend chart shows real history
- [ ] Predicted CPU Trend chart shows real predictions
- [ ] Prediction History table shows actual predictions

**Diagnostics Tab:**
- [ ] Mode Analysis shows current mode + record status
- [ ] Sequence Configuration shows actual values
- [ ] Runtime Readiness shows if >= 12 records
- [ ] Runtime Storage Status shows paths + availability

**Alerts Tab:**
- [ ] Shows real API status
- [ ] Lists actual issues (if any)
- [ ] Shows where data is stored

**Backend Status Tab:**
- [ ] API Endpoint shows reachability
- [ ] Data Storage shows available sources
- [ ] Endpoints shows status of /health, /predict, /status, /metrics

### Data Sources Verification

Check that dashboards read from real sources:

1. **API Endpoints** (Level 2 dashboard uses all):
   - GET /health → System status, mode, records
   - GET /predict → Predictions, load level, pods
   - GET /status → Model version, retraining info
   - GET /metrics/{system_id} → Performance metrics

2. **Runtime Storage Files** (Level 2 dashboard reads):
   - `data/predictions/{system_id}.csv` → Prediction history
   - `data/runtime_metrics/{system_id}_runtime_metrics.csv` → Metrics history

3. **Config** (Level 2 dashboard parses):
   - `src/workload_prediction_engine/config.py` → Model config

4. **API Server** (Level 1 dashboard uses with fallback):
   - /health endpoint
   - /predict endpoint

### Troubleshooting

**Dashboard shows "No data available":**
- Check if API is running: `curl http://localhost:8000/health`
- Verify data files exist: `dir data/predictions` and `dir data/runtime_metrics`

**API responds but dashboard shows "unavailable":**
- Dashboard may be caching. Refresh page manually or wait for auto-refresh
- Check timestamps - may be stale data

**404 errors in logs:**
- API may not be fully initialized - wait 2-3 seconds and refresh
- Check API is running on port 8000

**"Cannot connect to API":**
- Ensure `python run_live_api.py` is running in Terminal 1
- Check port 8000 is not blocked

### Performance Metrics

**Level 1 Dashboard (Non-Technical):**
- Page load time: < 2 seconds
- Auto-refresh: Every 7 seconds
- Performance: Optimized for simplicity

**Level 2 Dashboard (Technical):**
- Page load time: < 3 seconds
- Auto-refresh: Every 8 seconds
- Performance: Detailed diagnostics + trend charts

### Clean Shutdown

In each terminal, press `Ctrl+C` to gracefully stop:
```
^C
```

Expected output:
```
Shutting down...
✓ Services stopped
```

### Testing Complete

Both dashboards should:
- ✅ Load without errors
- ✅ Display real data from Engine 1
- ✅ Auto-refresh correctly
- ✅ Handle API unavailability gracefully
- ✅ Provide technical vs non-technical views appropriately

---

## Files Tested

| File | Type | Status |
|------|------|--------|
| `dashboard/app.py` | Level 1 Dashboard | ✓ Valid |
| `dashboard/technical_app.py` | Level 2 Dashboard | ✓ Valid |
| `run_live_api.py` | API Server | ✓ Running |
| `data/predictions` | Prediction Storage | ✓ Real |
| `data/runtime_metrics` | Metrics Storage | ✓ Real |

## Next Steps

1. Run the tests above in sequence
2. Verify both dashboards load and display real data
3. Check auto-refresh and interactivity
4. Review technical details in Level 2 for accuracy
5. Share dashboards with stakeholders based on their role
