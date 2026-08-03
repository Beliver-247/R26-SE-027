"""
profiler.py
-----------
Combines deployment tracking + continuous metric collection.

Two modes:

    i
  INTEGRATED mode (with deployment_tracker.py running):
      Start deployment_tracker.py --serve in one terminal.
      Then run this script — it polls the tracker's /deployment/status
      endpoint and collects metrics from deployment start to finish.

      python3 profiler.py --integrated

  STANDALONE mode (self-contained, for testing):
      This script itself starts/stops the deployment cycle manually,
      collecting metrics throughout.

      python3 profiler.py --standalone

Requirements:
    pip3 install psutil requests
"""

import argparse
import datetime
import json
import statistics
import time

import psutil

# ---------------------------------------------------------------------------
# Low-level metric snapshots  (no time-window looping — just a single read)
# ---------------------------------------------------------------------------

def snapshot_cpu() -> float:
    """Single CPU % reading."""
    return psutil.cpu_percent(interval=1)


def snapshot_memory() -> float:
    """Single memory % reading."""
    return psutil.virtual_memory().percent


def snapshot_network() -> dict:
    """Single network throughput reading (bytes over 1 second)."""
    n1 = psutil.net_io_counters()
    time.sleep(1)
    n2 = psutil.net_io_counters()
    sent = n2.bytes_sent - n1.bytes_sent
    recv = n2.bytes_recv - n1.bytes_recv
    return {
        "mbps_sent": round(sent * 8 / 1_000_000, 4),
        "mbps_recv": round(recv * 8 / 1_000_000, 4),
    }


# ---------------------------------------------------------------------------
# Profiler core
# ---------------------------------------------------------------------------

class Profiler:
    """
    Collects CPU + Memory every `interval` seconds between
    record_start() and record_end(), then produces a summary.
    """

    def __init__(self, interval_seconds: int = 60):
        self.interval      = interval_seconds
        self.start_time    = None
        self.end_time      = None
        self.cpu_readings  = []
        self.mem_readings  = []
        self._collecting   = False

    # -----------------------------------------------------------------------
    def record_start(self):
        self.start_time  = datetime.datetime.now()
        self.cpu_readings = []
        self.mem_readings = []
        self._collecting  = True
        print(f"[PROFILER] Monitoring started  @ {self._fmt(self.start_time)}")

    # -----------------------------------------------------------------------
    def collect_one_sample(self):
        """Read one CPU + Memory sample and append to internal lists."""
        cpu = snapshot_cpu()
        mem = snapshot_memory()
        ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cpu_readings.append(cpu)
        self.mem_readings.append(mem)
        print(f"  [{ts}]  CPU={cpu:.1f}%   MEM={mem:.1f}%")
        return cpu, mem

    # -----------------------------------------------------------------------
    def record_end(self) -> dict:
        self.end_time   = datetime.datetime.now()
        self._collecting = False
        print(f"[PROFILER] Monitoring finished @ {self._fmt(self.end_time)}")
        return self.build_summary()

    # -----------------------------------------------------------------------
    def build_summary(self) -> dict:
        dur = (self.end_time - self.start_time).total_seconds() / 60 \
              if (self.start_time and self.end_time) else None

        def safe_avg(lst):
            return round(statistics.mean(lst), 2) if lst else 0

        return {
            "start_time":       self._fmt(self.start_time),
            "end_time":         self._fmt(self.end_time),
            "duration_minutes": round(dur, 4) if dur else None,
            "samples_collected": len(self.cpu_readings),
            "cpu_readings":     self.cpu_readings,
            "memory_readings":  self.mem_readings,
            "avg_cpu":          safe_avg(self.cpu_readings),
            "avg_memory":       safe_avg(self.mem_readings),
            "peak_cpu":         max(self.cpu_readings,  default=0),
            "peak_memory":      max(self.mem_readings,  default=0),
            "min_cpu":          min(self.cpu_readings,  default=0),
            "min_memory":       min(self.mem_readings,  default=0),
        }

    @staticmethod
    def _fmt(dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


# ---------------------------------------------------------------------------
# MODE A — Integrated with deployment_tracker.py HTTP server
# ---------------------------------------------------------------------------

def run_integrated(tracker_url="http://localhost:5001", interval=60):
    """
    Polls deployment_tracker's /deployment/status endpoint.
    Starts collecting when status == 'running', stops when 'finished'.
    """
    try:
        import requests
    except ImportError:
        print("[ERROR] requests not installed.  Run:  pip3 install requests")
        return

    profiler = Profiler(interval_seconds=interval)

    print("=" * 60)
    print("  Profiler  —  Integrated Mode")
    print(f"  Polling tracker at {tracker_url}/deployment/status")
    print("=" * 60)
    print("\n  Waiting for deployment to start...")

    # Wait for deployment to start
    while True:
        try:
            r      = requests.get(f"{tracker_url}/deployment/status", timeout=5)
            status = r.json().get("status", "idle")
        except Exception as e:
            print(f"  [warn] Cannot reach tracker: {e}  (retrying in 5s)")
            time.sleep(5)
            continue

        if status == "running":
            print(f"\n  Deployment detected as running — starting metric collection.")
            profiler.record_start()
            break
        time.sleep(3)

    # Collect while running
    while True:
        profiler.collect_one_sample()

        try:
            r      = requests.get(f"{tracker_url}/deployment/status", timeout=5)
            status = r.json().get("status", "running")
        except Exception:
            status = "running"   # assume still running if unreachable

        if status in ("SUCCESS", "FAILURE", "finished"):
            print("\n  Deployment finished — stopping collection.")
            break

        # Sleep remaining time (2s already spent on cpu+net reads)
        time.sleep(max(0, interval - 2))

    summary = profiler.record_end()
    _print_and_save(summary)


# ---------------------------------------------------------------------------
# MODE B — Standalone (self-contained, manual start/stop)
# ---------------------------------------------------------------------------

def run_standalone(interval=10):
    """
    Prompts user to start, collects metrics, prompts user to stop.
    Uses a shorter default interval (10s) so testing is fast.
    """
    profiler = Profiler(interval_seconds=interval)

    print("=" * 55)
    print("  Profiler  —  Standalone Mode")
    print("=" * 55)
    input("\n  Press ENTER to START deployment monitoring...\n")

    profiler.record_start()
    print(f"  Collecting a sample every {interval} seconds.")
    print("  Press Ctrl+C to stop when deployment finishes.\n")

    try:
        while True:
            profiler.collect_one_sample()
            time.sleep(max(0, interval - 2))   # 2s already used by psutil
    except KeyboardInterrupt:
        print("\n  Stop signal received.")

    summary = profiler.record_end()
    _print_and_save(summary)


# ---------------------------------------------------------------------------
# Shared output helper
# ---------------------------------------------------------------------------

def _print_and_save(summary: dict, path="profiler_results.json"):
    print("\n" + "=" * 55)
    print("  DEPLOYMENT PROFILING SUMMARY")
    print("=" * 55)
    print(f"  Start time    : {summary['start_time']}")
    print(f"  End time      : {summary['end_time']}")
    print(f"  Duration      : {summary['duration_minutes']} minutes")
    print(f"  Samples       : {summary['samples_collected']}")
    print(f"  Average CPU   : {summary['avg_cpu']}%")
    print(f"  Peak CPU      : {summary['peak_cpu']}%")
    print(f"  Average Mem   : {summary['avg_memory']}%")
    print(f"  Peak Mem      : {summary['peak_memory']}%")
    print(f"\n  CPU readings  : {summary['cpu_readings']}")
    print(f"  Mem readings  : {summary['memory_readings']}")

    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Full results saved to {path}")
    print("\n[OK] profiler.py verification complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deployment Profiler")
    group  = parser.add_mutually_exclusive_group()
    group.add_argument("--integrated", action="store_true",
                       help="Integrate with deployment_tracker.py HTTP server")
    group.add_argument("--standalone", action="store_true",
                       help="Self-contained manual start/stop mode (default)")
    parser.add_argument("--interval", type=int, default=60,
                        help="Seconds between samples (default 60; use 10 for testing)")
    parser.add_argument("--tracker-url", default="http://localhost:5001",
                        help="Tracker base URL for integrated mode")
    args = parser.parse_args()

    if args.integrated:
        run_integrated(tracker_url=args.tracker_url, interval=args.interval)
    else:
        run_standalone(interval=args.interval)
