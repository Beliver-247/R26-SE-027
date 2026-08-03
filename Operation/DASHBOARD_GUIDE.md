# Green DevOps Dashboard - Getting Started Guide

## Overview

The **Green DevOps Dashboard** is a Level 1 monitoring interface designed for non-technical users. It provides real-time visualization of system workload predictions and scaling recommendations.

## Architecture

```
┌─────────────────────────────────────┐
│  Green DevOps Dashboard (Streamlit) │
│  - Non-technical UI                 │
│  - Real-time monitoring             │
│  - Color-coded alerts               │
└────────────────┬────────────────────┘
                 │ HTTP Requests
                 ▼
┌─────────────────────────────────────┐
│  Engine 1 API (FastAPI)             │
│  - /health                          │
│  - /predict                         │
└────────────────┬────────────────────┘
                 │ Python Calls
                 ▼
┌─────────────────────────────────────┐
│  Engine 1 Predictor                 │
│  - Metrics Collection (Prometheus)  │
│  - Live Prediction                  │
│  - Mode Management                  │
└─────────────────────────────────────┘
```

## Quick Start (3 Options)

### Option 1: Fast Start with One Command (Recommended)

```bash
python quickstart.py
```

This automatically:
1. Installs all dependencies
2. Starts the API server
3. Launches the dashboard
4. Opens it in your browser

### Option 2: Manual Multi-Terminal Setup

**Terminal 1 - Start API Server:**
```bash
python scripts/run_live_api.py \
  --system-id main_system \
  --prometheus-url http://localhost:9090 \
  --port 8000 \
  --interval 30 \
  --mock  # Use --mock for testing without Prometheus
```

**Terminal 2 - Start Dashboard:**
```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Option 3: Connect to Real Prometheus

**Terminal 1 - API Server (with real metrics):**
```bash
python scripts/run_live_api.py \
  --system-id production_system \
  --prometheus-url http://prometheus.example.com:9090 \
  --port 8000 \
  --interval 30
```

**Terminal 2 - Dashboard:**
```bash
streamlit run dashboard/app.py
```

## Dashboard Sections

### 1. Header
- Title: "Green DevOps System Dashboard"
- Subtitle: "Real-Time System Monitoring"

### 2. System Status (Top Cards)
Four quick-reference metrics:
- **System Status**: RUNNING / WARNING / ERROR
- **Mode**: Cold Start (learning) vs Runtime (normal operation)
- **Last Updated**: Time since last data refresh
- **Data Source**: Where predictions come from

### 3. Current & Predicted Workload (Large Metrics)
Three large, easy-to-read cards:
- **Current CPU Usage**: Real system CPU percentage
- **Predicted CPU**: Expected CPU in next 30 seconds
- **Load Level**: Color-coded (🟢 LOW / 🟡 NORMAL / 🔴 HIGH)

### 4. Scaling Recommendation
Clear action indicators:
- **Current Pods**: How many pods running now
- **Recommended Pods**: How many pods needed
- **Action**: SCALE UP / SCALE DOWN / NO CHANGE

### 5. CPU Trend Chart
Line chart showing:
- Current CPU usage over time
- Predicted CPU trend
- Visual trend for decision-makers

### 6. Alerts & Notifications
Simple alert messages:
- "✓ System Running Normally"
- "⚠️ High Load Detected"
- "⚠️ Scaling Recommended"
- "ℹ️ System Initializing"

## Color Scheme (Non-Technical)

| Color | Meaning | Action |
|-------|---------|--------|
| 🟢 Green | All Good | No action needed |
| 🟡 Yellow | Caution | Monitor closely |
| 🔴 Red | Alert | Take action |

## Data Refresh

- **Auto-refresh**: Every 7 seconds
- **Manual refresh**: Click "🔄 Refresh Now" button
- **API timeout**: 5 seconds (falls back to mock mode)

## API Fallback (Mock Mode)

If the API is unavailable:
- Dashboard displays ⚠️ warning
- Automatically switches to **Demo Mode**
- Shows realistic mock data
- Perfect for presentations or testing

## Using with Kubernetes

### Deploying Dashboard in Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: green-devops-dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dashboard
  template:
    metadata:
      labels:
        app: dashboard
    spec:
      containers:
      - name: dashboard
        image: green-devops:latest
        command: ["streamlit", "run", "dashboard/app.py"]
        ports:
        - containerPort: 8501
        env:
        - name: API_BASE_URL
          value: http://engine1-api:8000
```

### Accessing from Outside Cluster

```bash
# Port-forward to local machine
kubectl port-forward svc/green-devops-dashboard 8501:8501

# Open in browser
open http://localhost:8501
```

## Customization

### Change API Endpoint

Edit `dashboard/app.py`:
```python
API_BASE_URL = "http://your-api-server:8000"
```

### Change Refresh Interval

Edit `dashboard/app.py`:
```python
REFRESH_INTERVAL = 10  # seconds
```

### Change Port

```bash
streamlit run dashboard/app.py --server.port 8502
```

### Custom Styling

Edit the CSS section in `dashboard/app.py`:
```python
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        ...
    }
    </style>
""", unsafe_allow_html=True)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API Connection Unavailable" in dashboard | Make sure API server is running on port 8000 |
| Dashboard shows old data | Wait 7 seconds or click "🔄 Refresh Now" |
| Port 8501 already in use | Use `--server.port 8502` or kill existing process |
| Can't connect to Prometheus | Use `--mock` flag, dashboard will auto-fallback |
| Browser doesn't open | Manually visit `http://localhost:8501` |

## Building on This Dashboard

### Option 1: Add More Metrics
Edit `main()` function in `app.py`:
```python
# Add new API endpoint call
response = requests.get(f"{API_BASE_URL}/custom-endpoint")
# Display in new card
st.metric("Custom Metric", value)
```

### Option 2: Add Charts
Use Streamlit's built-in chart functions:
```python
st.bar_chart(data)
st.area_chart(data)
st.scatter_chart(data)
```

### Option 3: Add Interactivity
```python
selected_pod = st.selectbox("Choose Pod", ["pod1", "pod2", "pod3"])
# Filter data based on selection
filtered = api_data[api_data.pod == selected_pod]
```

## Performance Notes

- **Dashboard**: ~20 MB memory footprint
- **Refresh**: <100ms network call + render
- **Scalability**: Handles 100+ predictions/minute easily
- **Browser compatibility**: Chrome, Firefox, Safari, Edge (all modern versions)

## Security

**For Production:**
1. Use HTTPS for API endpoints
2. Add authentication (API key or OAuth)
3. Run behind reverse proxy (Nginx, HAProxy)
4. Restrict dashboard access to trusted networks
5. Monitor API rate limits

**Example with Auth:**
```python
import streamlit as st

# Add password protection
if not st.session_state.get('authenticated'):
    password = st.text_input("Enter password:", type="password")
    if password == "secure_password":
        st.session_state.authenticated = True
    else:
        st.stop()

# Rest of dashboard code
main()
```

## Integration with Autoscaler

**Use this flow:**

1. Dashboard reads `/predict` endpoint → gets `recommended_pods`
2. Autoscaler polls `/health` endpoint → gets `mode` and `records_collected`
3. Autoscaler compares: `recommended_pods` vs `current_pods`
4. If different → trigger scale action
5. Dashboard shows new pod count after 7 seconds

## Dashboard vs Full Monitoring

| Feature | Dashboard | Full Monitoring |
|---------|-----------|-----------------|
| User Audience | Non-technical | Engineers |
| Metrics | High-level | Detailed |
| Real-time | Yes (7s) | Yes (1s+) |
| Alerts | Simple | Complex |
| Learning Curve | <5 min | >1 hour |

**When to use Dashboard**: Executive/NOC presentations, client demos, non-technical stakeholders
**When to use Full Monitoring**: Troubleshooting, capacity planning, development teams

## Support & Feedback

For issues or feature requests:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [Production_ENHANCEMENTS.md](../PRODUCTION_ENHANCEMENTS.md)
3. Check logs: `logs/engine1_api_*.log`
4. Test with mock mode: `--mock` flag

---

**Next Steps:**
1. Run `python quickstart.py`
2. Open http://localhost:8501
3. Watch predictions update in real-time
4. Try scaling recommendations
5. Integrate with your autoscaler

Happy monitoring! 📊🟢
