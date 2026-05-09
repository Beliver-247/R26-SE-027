# 🚀 Green DevOps Dashboard - Quick Start Guide

## Problem Fixed ✅
- ✓ API script location corrected (`scripts/run_live_api.py`)
- ✓ Streamlit command fixed (use `python -m streamlit`)
- ✓ Launcher script created with correct paths

---

## ⚡ Quick Start (30 seconds)

### Option 1: Unified Dashboard (Recommended)

**Terminal 1 - Start API:**
```bash
cd d:\Research\Operation\green-devops-operation-component
python run_dashboard.py --api
```

**Terminal 2 - Start Unified Dashboard:**
```bash
cd d:\Research\Operation\green-devops-operation-component
python run_dashboard.py --unified
```

**Open Browser:**
```
http://localhost:8503
```

**Switch Views:**
- Look at left sidebar
- Select "Overview Dashboard" or "Technical Dashboard"

---

## 📊 All Startup Options

### Option A: Unified Dashboard (Single Entry Point)
```bash
# Terminal 1
python run_dashboard.py --api

# Terminal 2
python run_dashboard.py --unified

# Access at: http://localhost:8503
```

### Option B: Individual Dashboards (Lightweight)
```bash
# Terminal 1
python run_dashboard.py --api

# Terminal 2
python run_dashboard.py --level 1

# Terminal 3
python run_dashboard.py --level 2

# Access at:
# - http://localhost:8501  (Level 1 - Overview)
# - http://localhost:8502  (Level 2 - Technical)
```

### Option C: Without Launcher (Manual Commands)
```bash
# Terminal 1 - API
python scripts/run_live_api.py

# Terminal 2 - Unified Dashboard
python -m streamlit run dashboard/unified_app.py --server.port 8503

# Terminal 3 - Level 1 Only
python -m streamlit run dashboard/app.py --server.port 8501

# Terminal 4 - Level 2 Only
python -m streamlit run dashboard/technical_app.py --server.port 8502
```

---

## ✅ Verification

Make sure everything is set up correctly:

```bash
# Check dashboards are valid
python verify_unified_dashboard.py

# Expected output:
# ✓ Syntax Check: PASS
# ✓ Function Exports: PASS
# ✓ Import Test: PASS
# ✅ ALL TESTS PASSED
```

---

## 🎯 Dashboards Available

| Dashboard | Port | Audience | URL |
|-----------|------|----------|-----|
| **Unified** | 8503 | Mixed (sidebar to switch) | http://localhost:8503 |
| **Level 1** | 8501 | Non-technical (Execs, NOC) | http://localhost:8501 |
| **Level 2** | 8502 | Technical (Engineers) | http://localhost:8502 |
| **API** | 8000 | Backend | http://localhost:8000 |

---

## 🛠️ Troubleshooting

### "Can't open file run_live_api.py"
**Fix:** API is in `scripts/` subdirectory
```bash
# Use the launcher script:
python run_dashboard.py --api

# Or run directly:
python scripts/run_live_api.py
```

### "streamlit not recognized" error
**Fix:** Use Python module syntax
```bash
# Use the launcher script:
python run_dashboard.py --unified

# Or run directly:
python -m streamlit run dashboard/unified_app.py --server.port 8503
```

### "http://localhost:8000 not reachable"
**Fix:** Start API first in Terminal 1
```bash
python run_dashboard.py --api
```
Wait for: `INFO: Uvicorn running on http://0.0.0.0:8000`

### Dashboard shows "No data available"
**Fix:** 
1. Make sure API is running
2. Wait 5 seconds for API to initialize
3. Click "Refresh Now" button in dashboard

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `UNIFIED_DASHBOARD_GUIDE.md` | Full integration documentation |
| `UNIFIED_DASHBOARD_COMPLETE.md` | Refactoring summary |
| `DASHBOARD_TEST_QUICKSTART.md` | Testing procedures |
| `TESTING_DASHBOARDS.md` | Detailed test guide |
| `run_dashboard.py` | Launcher script (use this!) |
| `QUICK_REFERENCE.py` | Quick reference guide |

---

## 🚀 Next Steps

### Step 1: Start API (Terminal 1)
```bash
python run_dashboard.py --api
```
✓ Wait for: `Uvicorn running on http://0.0.0.0:8000`

### Step 2: Start Dashboard (Terminal 2)
```bash
python run_dashboard.py --unified
```
✓ Wait for: `Local URL: http://localhost:8503`

### Step 3: Open Browser
```
http://localhost:8503
```
✓ See the unified dashboard

### Step 4: Switch Views
- Click sidebar on left
- Select "Overview Dashboard" or "Technical Dashboard"

---

## ✨ Features

### Unified Dashboard
- **Sidebar Navigation** - Switch between Level 1 & Level 2
- **Real Data** - Both dashboards use live Engine 1 API
- **No Hardcoding** - All values from actual backend
- **Error Handling** - Graceful fallback if API unavailable
- **Auto-Refresh** - Updates every 7-8 seconds

### Level 1 - Overview (Non-Technical)
- System Status Cards
- Workload Metrics
- Scaling Recommendations
- CPU Trend Charts
- Alerts & Notifications

### Level 2 - Technical (Engineers)
- System Overview (4 tabs)
- Runtime Metrics & Trends
- Diagnostics & Mode Analysis
- Backend Health Monitoring
- Retraining Readiness

---

## 🎬 Demo Walkthrough

### 1. Start Services
```bash
# Terminal 1
python run_dashboard.py --api

# Terminal 2
python run_dashboard.py --unified
```

### 2. Access Dashboard
Open browser: http://localhost:8503

### 3. Explore Level 1
- Sidebar: Select "Overview Dashboard"
- See: Status cards, metrics, trends, alerts
- For: Executives, NOC, non-technical stakeholders

### 4. Explore Level 2
- Sidebar: Select "Technical Dashboard"
- See: Detailed diagnostics, metrics, backend health
- For: Engineers, operators, technical teams

### 5. Test Switching
- Switch back and forth between views
- Verify data updates correctly
- Check both use same API source

---

## 📋 Checklist

- [ ] API running: `python run_dashboard.py --api`
- [ ] Dashboard running: `python run_dashboard.py --unified`
- [ ] Browser open at http://localhost:8503
- [ ] Sidebar visible on left
- [ ] Can click "Overview Dashboard"
- [ ] Can click "Technical Dashboard"
- [ ] Data displays correctly
- [ ] Auto-refresh works

---

## 🆘 Support

### Check Status
```bash
python verify_unified_dashboard.py
```

### View Logs
- Check terminal output for errors
- API logs: Terminal 1
- Dashboard logs: Terminal 2

### Restart Services
- Press `Ctrl+C` in each terminal
- Wait 2 seconds
- Restart with correct commands

---

## 🎯 Success Criteria

✅ **Unified dashboard loads**
- URL: http://localhost:8503
- Sidebar visible
- No errors in console

✅ **Both views work**
- Level 1: Simple, non-technical UI
- Level 2: Technical, detailed UI
- Can switch between them

✅ **Data is real**
- Values from API, not hardcoded
- Updates every 7-8 seconds
- Consistent across views

✅ **Error handling works**
- Shows message if API unavailable
- Graceful degradation
- Clear error messages

---

## 🎉 Ready!

Your Green DevOps Dashboard is ready to use!

**Quick Start:**
```bash
# Terminal 1
python run_dashboard.py --api

# Terminal 2
python run_dashboard.py --unified

# Then open: http://localhost:8503
```

---

**Status: ✅ READY FOR DEPLOYMENT**
