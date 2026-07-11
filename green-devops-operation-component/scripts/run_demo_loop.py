#!/usr/bin/env python3
"""
Full real pipeline loop runner for the Green DevOps system.

Every iteration:
- Calls Engine 1 GET /predict for the real latest prediction
- Generates job metadata for Engine 3 input
- Calls Engine 3 POST /jobs/evaluate
- Calls Engine 2 POST /carbon/evaluate using Engine 1 + Engine 3 outputs
- Calls Decision Layer POST /decision/evaluate using all engine outputs
- Applies final_required_pods to the next loop's current_pods state
- Writes data/demo/latest.json and data/demo/history.csv for the dashboard
"""

import argparse
import csv
import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEMO_DIR = Path("data/demo")
DEMO_LATEST = DEMO_DIR / "latest.json"
DEMO_HISTORY = DEMO_DIR / "history.csv"
JOB_TYPES = ["batch", "analytics", "ml-training", "inference", "reporting"]


class LoopingScenarioRunner:
    """Continuously runs the real API pipeline with Engine 1 as the source."""

    def __init__(
        self,
        api_url: str,
        system_id: str = "demo-system",
        interval: int = 5,
        max_retries: int = 3,
        initial_pods: int = 1,
    ):
        self.api_url = api_url.rstrip("/")
        self.system_id = system_id
        self.interval = interval
        self.max_retries = max_retries
        self.current_pods = max(1, min(20, initial_pods))
        self.cycle_count = 0

        DEMO_DIR.mkdir(parents=True, exist_ok=True)
        if not DEMO_HISTORY.exists():
            self._init_csv()

        logger.info("LoopingScenarioRunner initialized")
        logger.info("  API URL: %s", self.api_url)
        logger.info("  System ID: %s", self.system_id)
        logger.info("  Interval: %ss", self.interval)
        logger.info("  Initial pods: %s", self.current_pods)

    def _init_csv(self) -> None:
        headers = [
            "timestamp",
            "scenario_name",
            "predicted_cpu",
            "load_level",
            "current_pods",
            "raw_required_pods",
            "delayable_jobs",
            "workload_reduction_percent",
            "carbon_saving_gco2",
            "carbon_saving_percent",
            "final_action",
            "final_pods",
            "sla_preserved",
        ]
        with open(DEMO_HISTORY, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        logger.info("Initialized CSV: %s", DEMO_HISTORY)

    def _api_call(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.api_url}{endpoint}"
        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    response = requests.get(url, timeout=5)
                else:
                    response = requests.post(url, json=payload, timeout=5)

                if response.status_code == 200:
                    return response.json()

                logger.warning(
                    "API %s returned %s (attempt %s/%s): %s",
                    endpoint,
                    response.status_code,
                    attempt + 1,
                    self.max_retries,
                    response.text[:200],
                )
            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "API %s error: %s (attempt %s/%s)",
                    endpoint,
                    exc,
                    attempt + 1,
                    self.max_retries,
                )

            if attempt < self.max_retries - 1:
                time.sleep(1)

        logger.error("API %s failed after %s retries", endpoint, self.max_retries)
        return None

    def _normalize_prediction(self, engine1_response: Dict[str, Any]) -> Dict[str, Any]:
        prediction = engine1_response.get("prediction", engine1_response)
        predicted_cpu = prediction.get("predicted_cpu", prediction.get("predicted_cpu_percent"))
        load_level = prediction.get("predicted_load_level")
        recommended_pods = prediction.get("recommended_pods")

        if predicted_cpu is None or load_level is None or recommended_pods is None:
            raise ValueError(f"Invalid /predict response shape: {engine1_response}")

        return {
            "system_id": prediction.get("system_id", self.system_id),
            "predicted_cpu": float(predicted_cpu),
            "predicted_load_level": str(load_level),
            "recommended_pods": int(recommended_pods),
            "confidence": float(prediction.get("confidence", 0.0)),
            "data_source": prediction.get("data_source", "engine1"),
            "model_version": prediction.get("model_version", "unknown"),
            "timestamp": engine1_response.get(
                "timestamp",
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
        }

    def _call_engine1_predict(self) -> Dict[str, Any]:
        logger.info("[ENGINE 1 REQUEST] GET /predict")
        response = self._api_call("GET", "/predict")
        if not response:
            raise RuntimeError("Engine 1 /predict failed; cannot run full real pipeline")

        prediction = self._normalize_prediction(response)
        logger.info(
            "[ENGINE 1 RESPONSE] CPU=%.2f%% Load=%s RecommendedPods=%s Source=%s",
            prediction["predicted_cpu"],
            prediction["predicted_load_level"],
            prediction["recommended_pods"],
            prediction["data_source"],
        )
        return response

    def _engine1_output_for_decision(self, engine1_response: Dict[str, Any], prediction: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": engine1_response.get("status", "success"),
            "timestamp": prediction["timestamp"],
            "prediction": {
                "system_id": prediction["system_id"],
                "predicted_cpu": prediction["predicted_cpu"],
                "predicted_load_level": prediction["predicted_load_level"],
                "recommended_pods": prediction["recommended_pods"],
                "confidence": prediction["confidence"],
                "data_source": prediction["data_source"],
                "model_version": prediction["model_version"],
            },
            "data_source": prediction["data_source"],
        }

    def _generate_jobs(self, prediction: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.cycle_count += 1
        load_level = prediction["predicted_load_level"]
        job_count = {"LOW": 3, "NORMAL": 4, "HIGH": 5}.get(load_level, 4)
        jobs = []

        for index in range(job_count):
            if load_level == "HIGH":
                priority = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[5, 3, 2], k=1)[0]
            elif load_level == "NORMAL":
                priority = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[2, 4, 3], k=1)[0]
            else:
                priority = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[1, 3, 6], k=1)[0]

            jobs.append(
                {
                    "job_id": f"live_job_{self.cycle_count}_{index + 1}",
                    "job_type": random.choice(JOB_TYPES),
                    "priority": priority,
                    "estimated_runtime_seconds": random.randint(45, 900),
                    "estimated_cpu_percent": round(random.uniform(5.0, 35.0), 2),
                    "deadline_seconds": random.choice([900, 1800, 3600, 7200, 10800]),
                    "already_delayed_seconds": 0,
                }
            )

        return jobs

    def _call_jobs_evaluate(
        self,
        prediction: Dict[str, Any],
        jobs: List[Dict[str, Any]],
        current_pods: int,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "jobs": jobs,
            "backlog_size": len(jobs),
            "current_load_level": prediction["predicted_load_level"],
            "current_cpu": prediction["predicted_cpu"],
            "current_pods": current_pods,
        }

        logger.info(
            "[ENGINE 3 REQUEST] POST /jobs/evaluate jobs=%s load=%s cpu=%.2f pods=%s",
            len(jobs),
            prediction["predicted_load_level"],
            prediction["predicted_cpu"],
            current_pods,
        )
        response = self._api_call("POST", "/jobs/evaluate", payload)
        if response:
            logger.info(
                "[ENGINE 3 RESPONSE] delayable_jobs=%s workload_reduction=%.2f%%",
                response.get("delayable_jobs", "N/A"),
                response.get("workload_reduction_percent", 0.0) * 100,
            )
        return response

    def _call_carbon_evaluate(
        self,
        prediction: Dict[str, Any],
        engine3_output: Optional[Dict[str, Any]],
        current_pods: int,
    ) -> Optional[Dict[str, Any]]:
        delayable_jobs = engine3_output.get("delayable_jobs", 0) if engine3_output else 0
        workload_reduction = engine3_output.get("workload_reduction_percent", 0.0) if engine3_output else 0.0
        payload = {
            "system_id": self.system_id,
            "predicted_cpu": prediction["predicted_cpu"],
            "predicted_load_level": prediction["predicted_load_level"],
            "recommended_pods": prediction["recommended_pods"],
            "current_pods": current_pods,
            "prediction_window_seconds": 30,
            "delayable_jobs": delayable_jobs,
            "workload_reduction_percent": workload_reduction,
        }

        logger.info(
            "[ENGINE 2 REQUEST] POST /carbon/evaluate cpu=%.2f load=%s raw_pods=%s current_pods=%s delayable_jobs=%s",
            prediction["predicted_cpu"],
            prediction["predicted_load_level"],
            prediction["recommended_pods"],
            current_pods,
            delayable_jobs,
        )
        response = self._api_call("POST", "/carbon/evaluate", payload)
        if response:
            logger.info(
                "[ENGINE 2 RESPONSE] recommended_action=%s carbon_saving=%.2fg",
                response.get("recommended_action", "N/A"),
                response.get("carbon_saving_gco2", 0.0) or 0.0,
            )
        return response

    def _call_decision_evaluate(
        self,
        engine1_output: Dict[str, Any],
        prediction: Dict[str, Any],
        engine3_output: Optional[Dict[str, Any]],
        engine2_output: Optional[Dict[str, Any]],
        current_pods: int,
    ) -> Optional[Dict[str, Any]]:
        engine2_data = engine2_output if engine2_output else {
            "raw_scenario": {"required_pods": prediction["recommended_pods"]},
            "optimized_scenario": {"required_pods": current_pods},
            "recommended_action": "no_action",
            "carbon_saving_gco2": 0.0,
            "carbon_saving_percent": 0.0,
        }
        engine3_data = engine3_output if engine3_output else {
            "delayable_jobs": 0,
            "delayable_job_ids": [],
            "workload_reduction_percent": 0.0,
        }
        payload = {
            "system_id": self.system_id,
            "current_pods": current_pods,
            "engine1_output": engine1_output,
            "engine2_output": engine2_data,
            "engine3_output": engine3_data,
        }

        logger.info("[DECISION REQUEST] POST /decision/evaluate current_pods=%s", current_pods)
        response = self._api_call("POST", "/decision/evaluate", payload)
        if response:
            decision = response.get("decision", {})
            logger.info(
                "[DECISION RESPONSE] final_action=%s final_required_pods=%s sla_preserved=%s",
                decision.get("final_action", decision.get("action", "N/A")),
                decision.get("final_required_pods", decision.get("final_pods", "N/A")),
                decision.get("sla_preserved", "N/A"),
            )
        return response

    def _save_results(
        self,
        prediction: Dict[str, Any],
        jobs: List[Dict[str, Any]],
        engine1_output: Dict[str, Any],
        engine3_output: Optional[Dict[str, Any]],
        engine2_output: Optional[Dict[str, Any]],
        decision_output: Optional[Dict[str, Any]],
        current_pods_before: int,
        final_pods: int,
        final_action: str,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        delayable_jobs = engine3_output.get("delayable_jobs", 0) if engine3_output else 0
        workload_reduction = engine3_output.get("workload_reduction_percent", 0.0) if engine3_output else 0.0
        carbon_saving = engine2_output.get("carbon_saving_gco2", 0.0) if engine2_output else 0.0
        carbon_percent = engine2_output.get("carbon_saving_percent", 0.0) if engine2_output else 0.0
        decision = decision_output.get("decision", {}) if decision_output else {}
        jobs_to_delay = decision.get("jobs_to_delay", [])
        sla_preserved = decision.get("sla_preserved", True)

        result = {
            "timestamp": timestamp,
            "scenario_name": f"REAL PIPELINE - {prediction['predicted_load_level']}",
            "predicted_cpu": prediction["predicted_cpu"],
            "load_level": prediction["predicted_load_level"],
            "current_pods": current_pods_before,
            "raw_required_pods": prediction["recommended_pods"],
            "final_required_pods": final_pods,
            "final_action": final_action,
            "jobs_to_delay": jobs_to_delay,
            "delayable_jobs": delayable_jobs,
            "carbon_saving": carbon_saving,
            "sla_preserved": sla_preserved,
            "jobs": jobs,
            "steps": {
                "engine1": engine1_output,
                "engine3": engine3_output or {},
                "engine2": engine2_output or {},
                "decision": decision_output or {},
            },
            "engine1": {
                "predicted_cpu": prediction["predicted_cpu"],
                "predicted_load_level": prediction["predicted_load_level"],
                "recommended_pods": prediction["recommended_pods"],
                "confidence": prediction["confidence"],
                "data_source": prediction["data_source"],
                "model_version": prediction["model_version"],
            },
            "engine2": {
                "carbon_saving_gco2": carbon_saving,
                "carbon_saving_percent": carbon_percent,
                "recommended_action": engine2_output.get("recommended_action", "N/A") if engine2_output else "N/A",
            },
            "engine3": {
                "delayable_jobs": delayable_jobs,
                "workload_reduction_percent": workload_reduction,
            },
            "decision": {
                "action": final_action,
                "final_pods": final_pods,
                "sla_preserved": sla_preserved,
            },
        }

        with open(DEMO_LATEST, "w") as f:
            json.dump(result, f, indent=2)

        csv_row = {
            "timestamp": timestamp,
            "scenario_name": result["scenario_name"],
            "predicted_cpu": prediction["predicted_cpu"],
            "load_level": prediction["predicted_load_level"],
            "current_pods": current_pods_before,
            "raw_required_pods": prediction["recommended_pods"],
            "delayable_jobs": delayable_jobs,
            "workload_reduction_percent": workload_reduction,
            "carbon_saving_gco2": carbon_saving,
            "carbon_saving_percent": carbon_percent,
            "final_action": final_action,
            "final_pods": final_pods,
            "sla_preserved": sla_preserved,
        }
        with open(DEMO_HISTORY, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_row.keys())
            writer.writerow(csv_row)

        logger.info("[DASHBOARD WRITE] %s updated", DEMO_LATEST)

    def run_pipeline_once(self) -> None:
        logger.info("")
        logger.info("=" * 80)
        logger.info("[PIPELINE] FULL REAL ENGINE PIPELINE")
        logger.info("=" * 80)

        current_pods_before = self.current_pods

        raw_engine1_output = self._call_engine1_predict()
        prediction = self._normalize_prediction(raw_engine1_output)
        engine1_output = self._engine1_output_for_decision(raw_engine1_output, prediction)

        jobs = self._generate_jobs(prediction)
        engine3_output = self._call_jobs_evaluate(prediction, jobs, current_pods_before)
        engine2_output = self._call_carbon_evaluate(prediction, engine3_output, current_pods_before)
        decision_output = self._call_decision_evaluate(
            engine1_output,
            prediction,
            engine3_output,
            engine2_output,
            current_pods_before,
        )

        decision = decision_output.get("decision", {}) if decision_output else {}
        final_action = decision.get("final_action", decision.get("action", "N/A"))
        final_pods = int(decision.get("final_required_pods", decision.get("final_pods", current_pods_before)))
        final_pods = max(1, min(20, final_pods))

        self.current_pods = final_pods

        self._save_results(
            prediction,
            jobs,
            engine1_output,
            engine3_output,
            engine2_output,
            decision_output,
            current_pods_before,
            final_pods,
            final_action,
        )

        logger.info("")

    def run_continuous(self) -> None:
        logger.info("")
        logger.info("=" * 80)
        logger.info("FULL REAL PIPELINE LOOP STARTED")
        logger.info("=" * 80)
        logger.info("Interval: %s seconds", self.interval)
        logger.info("Press CTRL+C to stop")
        logger.info("")

        try:
            while True:
                self.run_pipeline_once()
                logger.info("Sleeping %ss before next pipeline run...", self.interval)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("")
            logger.info("=" * 80)
            logger.info("Loop stopped by user (CTRL+C)")
            logger.info("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Full real pipeline loop runner for Green DevOps")
    parser.add_argument("--api-url", default="http://localhost:5050", help="API base URL")
    parser.add_argument("--system-id", default="demo-system", help="System ID for API requests")
    parser.add_argument("--interval", type=int, default=5, help="Sleep interval in seconds")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum API retry attempts")
    parser.add_argument("--initial-pods", type=int, default=1, help="Initial current pod count")
    parser.add_argument("--once", action="store_true", help="Run one pipeline iteration and exit")

    args = parser.parse_args()
    runner = LoopingScenarioRunner(
        api_url=args.api_url,
        system_id=args.system_id,
        interval=args.interval,
        max_retries=args.max_retries,
        initial_pods=args.initial_pods,
    )

    if args.once:
        runner.run_pipeline_once()
    else:
        runner.run_continuous()


if __name__ == "__main__":
    main()
