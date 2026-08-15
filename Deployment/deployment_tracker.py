"""
deployment_tracker.py
---------------------
Tracks deployment start/end times and duration.
Supports two modes:

  MODE A — Jenkins Integration (recommended):
      Jenkins calls this script's HTTP endpoint at build start/end.
      Run:  python3 deployment_tracker.py --serve
      Then add the Jenkinsfile snippet printed on startup.

  MODE B — Manual trigger (for quick testing without Jenkins):
      Run:  python3 deployment_tracker.py --manual

Requirements:
    pip3 install flask
"""

import argparse
import datetime
import json


# ---------------------------------------------------------------------------
# Core tracker  (shared by both modes)
# ---------------------------------------------------------------------------

class DeploymentTracker:
    """Records a single deployment lifecycle."""

    def __init__(self):
        self.start_time    = None
        self.end_time      = None
        self.job_name      = "unknown"
        self.build_number  = "?"
        self.status        = "idle"   # idle | running | finished
        self.strategy      = "unknown"
        self.canary_weight = None
        self.carbon_profile = None
        self.image         = None

    def record_start(self, job_name="unknown", build_number="?", strategy="unknown", canary_weight=None):
        self.start_time   = datetime.datetime.now()
        self.job_name     = job_name
        self.build_number = build_number
        self.end_time     = None
        self.status       = "running"
        self.strategy     = strategy
        self.canary_weight = canary_weight
        print(f"[TRACKER] Deployment STARTED  | job={job_name} #{build_number}"
              f" | strategy={strategy}" + 
              (f" | canary_weight={canary_weight}%" if canary_weight else "") +
              f" | {self._fmt(self.start_time)}")

    def record_end(self, status="SUCCESS", carbon_profile=None, image=None):
        if self.start_time is None:
            print("[TRACKER] WARNING: record_end() called before record_start()")
            return
        self.end_time = datetime.datetime.now()
        self.status   = status
        self.carbon_profile = carbon_profile
        self.image = image
        dur = self._duration_minutes()
        print(f"[TRACKER] Deployment FINISHED | status={status}"
              f" | {self._fmt(self.end_time)}"
              f" | duration={dur:.2f} min"
              + (f" | carbon_profile={carbon_profile}" if carbon_profile else ""))

    def to_dict(self):
        dur = self._duration_minutes() if (self.start_time and self.end_time) else None
        return {
            "job_name":         self.job_name,
            "build_number":     self.build_number,
            "status":           self.status,
            "strategy":         self.strategy,
            "canary_weight":    self.canary_weight,
            "carbon_profile":   self.carbon_profile,
            "image":            self.image,
            "start_time":       self._fmt(self.start_time),
            "end_time":         self._fmt(self.end_time),
            "duration_minutes": round(dur, 4) if dur is not None else None,
        }

    def _duration_minutes(self):
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.datetime.now()
        return (end - self.start_time).total_seconds() / 60

    @staticmethod
    def _fmt(dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


# Global instance used by Flask routes
tracker = DeploymentTracker()


# ---------------------------------------------------------------------------
# MODE A — Flask HTTP server for Jenkins webhooks
# ---------------------------------------------------------------------------

def run_jenkins_server(host="0.0.0.0", port=5001):
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("[ERROR] Flask not installed.  Run:  pip3 install flask")
        return

    app = Flask(__name__)

    @app.route("/deployment/start", methods=["POST"])
    def deployment_start():
        data         = request.get_json(silent=True) or {}
        job_name     = data.get("job_name",     "jenkins-job")
        build_number = data.get("build_number", "?")
        strategy     = data.get("strategy",     "unknown")
        canary_weight = data.get("canary_weight", None)
        tracker.record_start(job_name, build_number, strategy, canary_weight)
        return jsonify({"ok": True, "recorded": tracker.to_dict()}), 200

    @app.route("/deployment/end", methods=["POST"])
    def deployment_end():
        data   = request.get_json(silent=True) or {}
        status = data.get("status", "SUCCESS")
        carbon_profile = data.get("carbon_profile", None)
        image = data.get("image", None)
        tracker.record_end(status, carbon_profile, image)
        result = tracker.to_dict()
        save_deployment(result)
        return jsonify({"ok": True, "deployment": result}), 200

    @app.route("/deployment/status", methods=["GET"])
    def deployment_status():
        return jsonify(tracker.to_dict()), 200

    @app.route("/carbon/snapshot", methods=["POST"])
    def carbon_snapshot():
        """Receive carbon snapshots from Jenkins pipeline stages."""
        data = request.get_json(silent=True) or {}
        phase = data.get("phase", "unknown")
        strategy = data.get("strategy", "unknown")
        build_number = data.get("build_number", "?")
        infra_multiplier = data.get("infra_multiplier", 1.0)
        downtime_seconds = data.get("downtime_seconds", None)
        canary_weight = data.get("canary_weight", None)
        note = data.get("note", "")
        
        print(f"[CARBON SNAPSHOT] phase={phase} | strategy={strategy} "
              f"| build=#{build_number} | infra_multiplier={infra_multiplier}"
              + (f" | downtime={downtime_seconds}s" if downtime_seconds else "")
              + (f" | canary_weight={canary_weight}%" if canary_weight else "")
              + (f" | note={note}" if note else ""))
        
        # Store snapshot for carbon calculation
        snapshot = {
            "phase": phase,
            "strategy": strategy,
            "build_number": build_number,
            "infra_multiplier": infra_multiplier,
            "timestamp": tracker._fmt(datetime.datetime.now()),
        }
        if downtime_seconds:
            snapshot["downtime_seconds"] = downtime_seconds
        if canary_weight:
            snapshot["canary_weight"] = canary_weight
        if note:
            snapshot["note"] = note
            
        save_carbon_snapshot(snapshot, build_number, phase)
        
        return jsonify({"ok": True, "snapshot": snapshot}), 200

    # Startup message with Jenkins snippet
    print("=" * 60)
    print("  Deployment Tracker  —  Jenkins Integration Mode")
    print("=" * 60)
    print(f"\n  Listening on  http://{host}:{port}")
    print("\n  Endpoints:")
    print(f"    POST /deployment/start    - Start deployment tracking")
    print(f"    POST /deployment/end      - End deployment tracking")
    print(f"    GET  /deployment/status   - Get current status")
    print(f"    POST /carbon/snapshot     - Record carbon snapshot")
    print("\n  Add these steps to your Jenkins Pipeline (Jenkinsfile):\n")
    print("""  pipeline {
    stages {
      stage('Deploy') {
        steps {
          sh '''
            curl -s -X POST http://localhost:5001/deployment/start \\
              -H "Content-Type: application/json" \\
              -d "{\\"job_name\\":\\"${JOB_NAME}\\",\\"build_number\\":\\"${BUILD_NUMBER}\\",\\"strategy\\":\\"${STRATEGY}\\",\\"canary_weight\\":\\"${CANARY_WEIGHT}\\",\\"carbon_profile\\":\\"${CARBON_PROFILE}\\",\\"image\\":\\"${DOCKER_IMAGE}:${DOCKER_TAG}\\"}"
          '''
          // ... your actual deploy commands here ...
        }
      }
    }
    post {
      success {
        sh 'curl -s -X POST http://localhost:5001/deployment/end -H "Content-Type: application/json" -d "{\\"status\\":\\"SUCCESS\\",\\"carbon_profile\\":\\"${CARBON_PROFILE}\\",\\"image\\":\\"${DOCKER_IMAGE}:${DOCKER_TAG}\\"}"'
      }
      failure {
        sh 'curl -s -X POST http://localhost:5001/deployment/end -H "Content-Type: application/json" -d "{\\"status\\":\\"FAILURE\\"}"'
      }
    }
  }
""")

    app.run(host=host, port=port)


# ---------------------------------------------------------------------------
# MODE B — Manual trigger
# ---------------------------------------------------------------------------

def run_manual_mode():
    print("=" * 55)
    print("  Deployment Tracker  —  Manual Mode")
    print("=" * 55)

    job_name     = input("\n  Job name      [Enter = 'manual-test']: ").strip() or "manual-test"
    build_number = input("  Build number  [Enter = '1']:            ").strip() or "1"
    strategy     = input("  Strategy (rolling/recreate/canary) [Enter = 'rolling']: ").strip() or "rolling"
    canary_weight = None
    if strategy == "canary":
        canary_weight = input("  Canary weight % [Enter = '20']: ").strip() or "20"

    tracker.record_start(job_name, build_number, strategy, canary_weight)

    input("\n  >>> Press ENTER when deployment finishes <<<\n")

    carbon_profile = input("  Carbon profile (low_gradual/low_burst/medium_transient) [Enter = 'low_gradual']: ").strip() or "low_gradual"
    tracker.record_end("SUCCESS", carbon_profile)
    result = tracker.to_dict()
    save_deployment(result)

    print("\n  Deployment summary:")
    print(f"    Job      : {result['job_name']} #{result['build_number']}")
    print(f"    Strategy : {result['strategy']}")
    if result['canary_weight']:
        print(f"    Canary   : {result['canary_weight']}%")
    print(f"    Start    : {result['start_time']}")
    print(f"    End      : {result['end_time']}")
    print(f"    Duration : {result['duration_minutes']} minutes")
    print(f"    Status   : {result['status']}")
    print(f"    Carbon   : {result['carbon_profile']}")
    print("\n[OK] deployment_tracker.py verification complete.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_deployment(data, path="deployment_last.json"):
    """Persist latest deployment info to disk so profiler.py can read it."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[TRACKER] Saved to {path}")


def save_carbon_snapshot(snapshot: dict, build_number: str, phase: str):
    """Save carbon snapshot for historical tracking."""
    path = f"carbon_snapshot_{build_number}_{phase}.json"
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"[TRACKER] Carbon snapshot saved to {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deployment Tracker")
    group  = parser.add_mutually_exclusive_group()
    group.add_argument("--serve",  action="store_true",
                       help="HTTP server mode for Jenkins (default)")
    group.add_argument("--manual", action="store_true",
                       help="Manual trigger mode for testing")
    parser.add_argument("--port", type=int, default=5001,
                        help="Port for --serve mode (default 5001)")
    args = parser.parse_args()

    if args.manual:
        run_manual_mode()
    else:
        run_jenkins_server(port=args.port)
