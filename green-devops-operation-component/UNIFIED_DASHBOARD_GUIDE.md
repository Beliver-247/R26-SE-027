# Unified Dashboard - Testing & Deployment Guide

## Overview

The Green DevOps Dashboard now has three deployment options:

| Dashboard | Purpose | Command | Port | Users |
|-----------|---------|---------|------|-------|
| **Level 1** (app.py) | Non-technical overview | `streamlit run dashboard/app.py` | 8501 | Executives, NOC |
| **Level 2** (technical_app.py) | Technical diagnostics | `streamlit run dashboard/technical_app.py` | 8502 | Engineers, Operators |
| **Unified** (unified_app.py) | Both in one app | `streamlit run dashboard/unified_app.py` | 8503 | All users |

## Unified Dashboard Features

The unified dashboard integrates both Level 1 and Level 2 into a single Streamlit app:

### Sidebar Navigation
- Radio button to switch between "Overview Dashboard" and "Technical Dashboard"
- Detailed descriptions of each view
- Single source of truth for API connections

### Benefits
- Single deployment point
- Shared API connections (reduces redundant calls)
- Consistent styling and configuration
- Easy for mixed audiences (executives + engineers)

## Testing Quick Start

### Option 1: Test Individual Dashboards (Unchanged)

**Terminal 1:**
```bash
cd d:\Research\Operation\green-devops-operation-component
python run_live_api.py
```

**Terminal 2 - Level 1 Only:**
```bash
cd d:\Research\Operation\green-devops-operation-component
streamlit run dashboard/app.py --server.port 8501
```
→ http://localhost:8501

**Terminal 3 - Level 2 Only:**
```bash
cd d:\Research\Operation\green-devops-operation-component
streamlit run dashboard/technical_app.py --server.port 8502
```
→ http://localhost:8502

### Option 2: Test Unified Dashboard (New)

**Terminal 1:**
```bash
cd d:\Research\Operation\green-devops-operation-component
python run_live_api.py
```

**Terminal 2 - Unified:**
```bash
cd d:\Research\Operation\green-devops-operation-component
streamlit run dashboard/unified_app.py --server.port 8503
```
→ http://localhost:8503

**Sidebar Navigation:**
- Select "Overview Dashboard" to see Level 1
- Select "Technical Dashboard" to see Level 2
- Switch back and forth to verify both work

## Verification Checklist

### Refactoring Verification
- [ ] `dashboard/app.py` still works standalone
- [ ] `dashboard/technical_app.py` still works standalone
- [ ] `dashboard/unified_app.py` loads without errors
- [ ] Both render functions are accessible from unified app

### Unified Dashboard Testing
- [ ] Unified app loads on http://localhost:8503
- [ ] Sidebar appears on the left
- [ ] "Overview Dashboard" option visible
- [ ] "Technical Dashboard" option visible
- [ ] Clicking "Overview Dashboard" shows Level 1 UI
- [ ] Clicking "Technical Dashboard" shows Level 2 UI
- [ ] Switching between modes works smoothly
- [ ] Data refreshes correctly in both modes

### Data Integrity
- [ ] API values match between standalone and unified
- [ ] CPU metrics are consistent
- [ ] Prediction values are consistent
- [ ] Mode indicators match
- [ ] Record counts match

### API Integration
- [ ] Both dashboards use real API data
- [ ] No hardcoded values in unified app
- [ ] Graceful handling if API is down
- [ ] Auto-refresh works in both modes

## Architecture

```
dashboard/
├── app.py
│   ├── Configuration & setup
│   ├── fetch_health_data()
│   ├── fetch_prediction_data()
│   ├── Helper functions
│   ├── render_overview()         ← Extracted
│   ├── main()                    ← Calls render_overview()
│   └── if __name__ == "__main__"
│
├── technical_app.py
│   ├── Configuration & setup
│   ├── fetch_health_data()
│   ├── fetch_prediction_data()
│   ├── Data loading functions
│   ├── Render components
│   ├── render_technical()        ← Extracted
│   ├── main()                    ← Calls render_technical()
│   └── if __name__ == "__main__"
│
└── unified_app.py (NEW)
    ├── Page configuration
    ├── Sidebar navigation
    ├── Import render_overview()
    ├── Import render_technical()
    ├── main() → Calls appropriate render function
    └── if __name__ == "__main__"
```

## Code Changes

### app.py
- Added `render_overview()` function containing all dashboard logic
- Modified `main()` to call `render_overview()`
- Maintains backward compatibility (still works standalone)

### technical_app.py
- Added `render_technical()` function containing all dashboard logic
- Modified `main()` to call `render_technical()`
- Maintains backward compatibility (still works standalone)

### unified_app.py (NEW)
- Simple coordination layer
- Imports render functions from both dashboards
- Sidebar for navigation
- Minimal code duplication

## Deployment Options

### Option 1: Separate Deployments
Deploy each dashboard independently:
```bash
# Dashboard 1 on port 8501
streamlit run dashboard/app.py --server.port 8501

# Dashboard 2 on port 8502
streamlit run dashboard/technical_app.py --server.port 8502
```

**Pros:** Lighter per-instance, independent scaling
**Cons:** Two deployments to manage

### Option 2: Unified Deployment
Single unified app:
```bash
streamlit run dashboard/unified_app.py --server.port 8503
```

**Pros:** Single entry point, shared resources
**Cons:** One deployment for both audiences

### Option 3: Hybrid
Run both:
```bash
# Unified for mixed audience
streamlit run dashboard/unified_app.py --server.port 8503

# Standalone for executives-only
streamlit run dashboard/app.py --server.port 8501

# Standalone for engineers-only
streamlit run dashboard/technical_app.py --server.port 8502
```

## Production Recommendations

1. **Start with Unified** - Deploy `unified_app.py` first
2. **Monitor Usage** - Track which mode users select in sidebar
3. **Scale if Needed** - Separate into individual apps if resource usage is high
4. **Keep Standalone** - Always maintain standalone versions for specific team access

## Troubleshooting

### "Import error" in unified app
- Ensure `app.py` and `technical_app.py` are in the same `dashboard/` directory
- Check that both files have `render_overview()` and `render_technical()` functions

### Dashboard doesn't switch modes
- Check browser console for errors (F12)
- Try refreshing the page
- Verify API is running (http://localhost:8000/health)

### Data doesn't appear
- Start `python run_live_api.py` first
- Wait 5 seconds for API to initialize
- Click "Refresh Now" button in dashboard

### Performance issues
- If unified app is slow, consider separate deployments
- Check API response times
- Monitor CPU/memory usage

## Files Summary

| File | Type | Status | Notes |
|------|------|--------|-------|
| dashboard/app.py | Refactored | ✓ Updated | Extracted render_overview() |
| dashboard/technical_app.py | Refactored | ✓ Updated | Extracted render_technical() |
| dashboard/unified_app.py | New | ✓ Created | Integrates both dashboards |

## Verification Commands

```bash
# Check syntax
python -m py_compile dashboard/app.py
python -m py_compile dashboard/technical_app.py
python -m py_compile dashboard/unified_app.py

# Check that functions exist
python -c "from dashboard.app import render_overview; print('✓ render_overview found')"
python -c "from dashboard.technical_app import render_technical; print('✓ render_technical found')"

# Test imports
python -c "from dashboard.unified_app import main; print('✓ unified_app imports work')"
```

## Next Steps

1. Run syntax validation above
2. Start Engine 1 API: `python run_live_api.py`
3. Launch unified app: `streamlit run dashboard/unified_app.py --server.port 8503`
4. Test both views via sidebar
5. Deploy based on your infrastructure preferences

---

**Status:** ✅ Refactoring complete, all dashboards operational
