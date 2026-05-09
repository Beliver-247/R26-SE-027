# Green DevOps Dashboard

Level 1 Overview Dashboard for non-technical users.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Dashboard
```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

### 3. Connect to API

The dashboard will automatically try to connect to Engine 1 API at:
- `http://localhost:8000/health`
- `http://localhost:8000/predict`

If API is unavailable, the dashboard automatically switches to **Demo Mode** with mock data.

## Features

✅ **System Status** - 4 quick status cards
✅ **Current & Predicted Workload** - Large, easy-to-read metrics
✅ **Scaling Recommendation** - Clear actions (SCALE UP / DOWN / NO CHANGE)
✅ **CPU Trend Chart** - Historical visualization
✅ **Alerts** - Simple, clear notifications
✅ **Auto-refresh** - Updates every 7 seconds
✅ **Mock Fallback** - Works without API

## Running with API Server

**Terminal 1 - Start API Server:**
```bash
cd src/workload_prediction_engine
python ../../scripts/run_live_api.py --system-id demo_pod --mock --port 8000
```

**Terminal 2 - Start Dashboard:**
```bash
cd dashboard
streamlit run app.py
```

## UI Design

- **Non-Technical** - No model internals or technical jargon
- **Color-Coded** - Green (good) → Yellow (caution) → Red (alert)
- **Large Numbers** - Easy to read at a glance
- **Clear Explanations** - Context for each metric

## Customization

Edit `app.py` to:
- Change API endpoint: `API_BASE_URL = "http://your-api:8000"`
- Adjust refresh interval: `REFRESH_INTERVAL = 5` (seconds)
- Modify colors/styling: CSS section at top of file

## Troubleshooting

**Dashboard shows "API Connection Unavailable"?**
- Make sure `run_live_api.py` is running
- Check API is on port 8000
- Dashboard will use mock data automatically

**Dashboard not refreshing?**
- Click "🔄 Refresh Now" or wait 7 seconds
- Check browser hasn't minimized the tab

**Port 8501 already in use?**
```bash
streamlit run app.py --server.port 8502
```
