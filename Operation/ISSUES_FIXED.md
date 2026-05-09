# ✅ FIXED: Green DevOps Dashboard Startup Issues

## Problems You Encountered

### ❌ Problem 1: `run_live_api.py` not found
```
Error: can't open file 'run_live_api.py': [Errno 2] No such file or directory
```
**Root Cause:** File is in `scripts/` subdirectory, not at root

**Solutions:**
- ✅ Use launcher: `python run_dashboard.py --api`
- ✅ Direct path: `python scripts/run_live_api.py`

---

### ❌ Problem 2: `streamlit` not recognized
```
Error: The term 'streamlit' is not recognized as a cmdlet, function, script file, or program
```
**Root Cause:** `streamlit` command not in PATH. Need to use Python module syntax.

**Solutions:**
- ✅ Use launcher: `python run_dashboard.py --unified`
- ✅ Python module: `python -m streamlit run dashboard/unified_app.py --server.port 8503`

---

## Solutions Provided

### 🎯 Solution 1: Launcher Script
Created `run_dashboard.py` - handles all paths and commands automatically

**Usage:**
```bash
python run_dashboard.py --api              # Start API
python run_dashboard.py --unified          # Start unified dashboard
python run_dashboard.py --level 1          # Start Level 1
python run_dashboard.py --level 2          # Start Level 2
python run_dashboard.py --all              # Show all options
```

**Why this works:**
- ✓ Correctly resolves `scripts/run_live_api.py` path
- ✓ Uses `python -m streamlit` module syntax
- ✓ Sets correct working directory
- ✓ Simple, memorable commands

---

### 🎯 Solution 2: Quick Start Guide
Created `START.md` and `STARTUP_INSTRUCTIONS.py`

**Shows:**
- ✓ Correct commands with proper paths
- ✓ Step-by-step setup (30 seconds)
- ✓ All available options
- ✓ Troubleshooting guide

---

## ✨ What You Can Do Now

### Option A: Easy (Use Launcher - Recommended)
```powershell
# Terminal 1
cd d:\Research\Operation\green-devops-operation-component
python run_dashboard.py --api

# Terminal 2
cd d:\Research\Operation\green-devops-operation-component
python run_dashboard.py --unified

# Browser
http://localhost:8503
```

### Option B: Manual (Correct Commands)
```powershell
# Terminal 1
cd d:\Research\Operation\green-devops-operation-component
python scripts/run_live_api.py

# Terminal 2 - Unified Dashboard
python -m streamlit run dashboard/unified_app.py --server.port 8503

# Terminal 2 - Level 1 Only
python -m streamlit run dashboard/app.py --server.port 8501

# Terminal 2 - Level 2 Only
python -m streamlit run dashboard/technical_app.py --server.port 8502
```

---

## 📊 Dashboards Available

| Dashboard | Port | Command | URL |
|-----------|------|---------|-----|
| **Unified (NEW)** | 8503 | `python run_dashboard.py --unified` | http://localhost:8503 |
| Level 1 (Overview) | 8501 | `python run_dashboard.py --level 1` | http://localhost:8501 |
| Level 2 (Technical) | 8502 | `python run_dashboard.py --level 2` | http://localhost:8502 |
| API Server | 8000 | `python run_dashboard.py --api` | http://localhost:8000 |

---

## 🚀 Quick Start (30 Seconds)

### Step 1: Terminal 1 - Start API
```bash
python run_dashboard.py --api
```
**Wait for:** `INFO: Uvicorn running on http://0.0.0.0:8000`

### Step 2: Terminal 2 - Start Dashboard
```bash
python run_dashboard.py --unified
```
**Wait for:** `Local URL: http://localhost:8503`

### Step 3: Open Browser
```
http://localhost:8503
```

### Step 4: Explore
- **Level 1:** Click "Overview Dashboard" in sidebar
- **Level 2:** Click "Technical Dashboard" in sidebar
- **Switch:** Your data updates instantly

---

## ✅ Verification

Run this to verify everything works:
```bash
python verify_unified_dashboard.py
```

**Expected Output:**
```
✓ Syntax Check: PASS
✓ Function Exports: PASS
✓ Import Test: PASS
✅ ALL TESTS PASSED
```

---

## 📁 Files Created/Updated

| File | Purpose | Type |
|------|---------|------|
| `run_dashboard.py` | Launcher script (use this!) | Script |
| `dashboard/unified_app.py` | Unified dashboard | App |
| `dashboard/app.py` | Level 1 dashboard (updated) | App |
| `dashboard/technical_app.py` | Level 2 dashboard (updated) | App |
| `START.md` | Quick start guide | Guide |
| `STARTUP_INSTRUCTIONS.py` | Detailed instructions | Guide |
| `verify_unified_dashboard.py` | Verification script | Utility |
| `QUICK_REFERENCE.py` | Quick reference | Utility |

---

## 🎯 Key Points

✅ **All dashboards work**
- Level 1 (Overview) → Non-technical UI
- Level 2 (Technical) → Detailed diagnostics
- Unified → Switch between both in one app

✅ **Real data only**
- No hardcoded values
- All data from Engine 1 API
- Graceful error handling if API down

✅ **Easy to launch**
- Use `python run_dashboard.py --api`
- Use `python run_dashboard.py --unified`
- Or: `python run_dashboard.py --all` for all options

✅ **Fully backward compatible**
- Individual dashboards still work standalone
- No breaking changes
- All existing functionality preserved

---

## 🆘 Troubleshooting

### "streamlit not recognized"
```powershell
# Use launcher instead
python run_dashboard.py --unified

# Or use Python module syntax
python -m streamlit run dashboard/unified_app.py --server.port 8503
```

### "Can't find run_live_api.py"
```powershell
# Use launcher instead
python run_dashboard.py --api

# Or use correct path
python scripts/run_live_api.py
```

### Dashboard shows "No data available"
1. Verify API is running: `python run_dashboard.py --api`
2. Check http://localhost:8000/health in browser
3. Wait 5 seconds for initialization
4. Click "Refresh Now" button

### Port already in use
1. Press `Ctrl+C` to stop service
2. Wait 5 seconds
3. Start fresh in new terminal

---

## 🎬 Demo

### See Level 1 (Non-technical)
```bash
python run_dashboard.py --api        # Terminal 1
python run_dashboard.py --level 1    # Terminal 2
```
→ http://localhost:8501 - Simple executive dashboard

### See Level 2 (Technical)
```bash
python run_dashboard.py --api        # Terminal 1
python run_dashboard.py --level 2    # Terminal 2
```
→ http://localhost:8502 - Detailed technical diagnostics

### See Unified (Both in One)
```bash
python run_dashboard.py --api        # Terminal 1
python run_dashboard.py --unified    # Terminal 2
```
→ http://localhost:8503 - Switch views with sidebar

---

## 📚 Documentation

| File | Contains |
|------|----------|
| `START.md` | Quick start in 30 seconds |
| `STARTUP_INSTRUCTIONS.py` | Detailed setup guide |
| `UNIFIED_DASHBOARD_GUIDE.md` | Full integration documentation |
| `UNIFIED_DASHBOARD_COMPLETE.md` | Refactoring summary |
| `DASHBOARD_TEST_QUICKSTART.md` | Testing procedures |
| `QUICK_REFERENCE.py` | Quick reference guide |

---

## ✨ Status

🟢 **READY FOR DEPLOYMENT**

All issues fixed:
- ✅ File paths corrected
- ✅ Python module syntax fixed
- ✅ Launcher script created
- ✅ All dashboards verified
- ✅ Documentation complete

---

## 🎉 Next Steps

1. **Quick Verification:**
   ```bash
   python verify_unified_dashboard.py
   ```

2. **Start Using:**
   ```bash
   python run_dashboard.py --api        # Terminal 1
   python run_dashboard.py --unified    # Terminal 2
   ```

3. **Open Browser:**
   ```
   http://localhost:8503
   ```

4. **Explore:**
   - Click "Overview Dashboard" → Level 1
   - Click "Technical Dashboard" → Level 2
   - Switch back and forth
   - Use sidebar to navigate

---

## 💡 Tips

- **Use launcher script** - simplest way to start
- **Read START.md** - quick 30-second guide
- **Run verify script** - ensures everything works
- **Check QUICK_REFERENCE.py** - all commands in one place

---

**Everything is fixed and ready to go! 🚀**

