# Full System Fix Plan

This plan is ordered by impact on the intended workflow:

`Real or Generated Workload -> Kubernetes Pods -> Prometheus Runtime Metrics -> Data Preprocessing -> LSTM Workload Prediction -> Carbon Emission Evaluation -> Job Prioritization -> Runtime Decision -> Kubernetes Scaling Recommendation or Scaling Action -> Dashboard Update`

## P0 - Required for a Real Kubernetes Workflow

1. Implement Kubernetes automatic scaling.

   Add `src/kubernetes_integration/deployment_scaler.py` with:

   - `DeploymentScaler.get_current_replicas(namespace, deployment)`
   - `DeploymentScaler.patch_scale(namespace, deployment, replicas, dry_run=True)`
   - `DeploymentScaler.apply_decision(decision_output, namespace, deployment, dry_run=True)`
   - `DeploymentScaler.wait_for_rollout(namespace, deployment, expected_replicas, timeout_seconds)`
   - `DeploymentScaler.rollback(namespace, deployment, previous_replicas)`

   Start with dry-run only. Add API/demo flags for `--k8s-namespace`, `--k8s-deployment`, and `--apply-scaling`.

2. Fix Prometheus CPU query and unit conversion.

   Current CPU query uses a cumulative counter:

   ```python
   container_cpu_usage_seconds_total{pod="{self.system_id}"}
   ```

   Replace it with a rate-based query aligned to the training CPU percentage semantics, for example:

   ```python
   cpu_query = (
       'sum(rate(container_cpu_usage_seconds_total{'
       f'pod=~"{self.system_id}.*",container!="POD",image!=""'
       '}[1m])) * 100'
   )
   ```

   Then normalize CPU and memory through the same two-feature scaler used during training.

3. Fix Docker runtime.

   `infrastructure/docker/Dockerfile` currently runs missing module `src.api.main:app`. Either:

   - expose an ASGI app module matching the Docker CMD, or
   - update the container command to the real API entry point.

   Also copy active assets:

   - `models/trained/workload_predictor_balanced.pt`
   - `data/preprocessed/balanced_dataset/scaler.pkl`
   - required config files

## P1 - Correctness and Research Validity

4. Fix runtime/manual LSTM preprocessing.

   RuntimeAdapter currently attempts one-feature transforms with a two-feature MinMaxScaler and logs:

   `X has 1 features, but MinMaxScaler is expecting 2 features as input.`

   Change runtime and manual prediction paths to build a two-column array `[cpu_percent, memory_kb]` and call the active scaler once across both features.

5. Resolve Engine 2 output contract ambiguity.

   Add explicit fields:

   - `raw_scenario`
   - `workload_optimized_scenario`
   - `selected_scenario`
   - `selected_required_pods`

   Keep `optimized_required_pods` only as a backward-compatible alias if needed.

6. Add normal stable load hysteresis.

   Current normal policy can scale down when the user expectation is maintain/no-action if current capacity is sufficient. Add a guard such as:

   - maintain when `current_pods == raw_required_pods` and carbon saving is below a configured threshold
   - require sustained low/normal load for N windows before scale-down
   - do not scale below raw required pods without explicit delayable workload evidence

7. Revalidate the preprocessed test split.

   `X_test.max()` is 1.0124. Decide whether to clip test values, keep out-of-range values intentionally, or regenerate splits using a scaler policy that handles held-out maxima. Re-run validation and record updated metrics.

## P2 - Test Suite and Operability

8. Create real pytest tests under `tests/`.

   Minimum test files:

   - `tests/test_workload_prediction_engine.py`
   - `tests/test_carbon_engine.py`
   - `tests/test_job_prioritization_engine.py`
   - `tests/test_decision_layer.py`
   - `tests/test_api.py`
   - `tests/test_dashboard_helpers.py`
   - `tests/test_kubernetes_scaler_dry_run.py`

9. Parameterize all standalone validation scripts.

   Replace hardcoded API URLs in old scripts with one of:

   - CLI flag `--api-url`
   - env var `GREEN_DEVOPS_API_URL`
   - shared config defaulting to `http://localhost:5002`

10. Make test output Windows-safe.

   Either remove Unicode checkmarks/box drawing from test scripts or document:

   ```powershell
   $env:PYTHONIOENCODING='utf-8'
   $env:PYTHONUTF8='1'
   ```

11. Pin or regenerate sklearn artifacts.

   The scaler was pickled with sklearn 1.8.0 and loaded with sklearn 1.9.0. Pin `scikit-learn==1.8.*` or regenerate `scaler.pkl` with the currently supported version and revalidate metrics.

12. Replace deprecated UTC calls.

   Replace `datetime.utcnow()` with timezone-aware `datetime.now(datetime.UTC)` in runtime/API/test code.

## P3 - Infrastructure Validation Once Services Are Available

13. Start Docker Desktop and rerun:

   ```powershell
   docker info
   docker build -f infrastructure/docker/Dockerfile -t green-devops-operation-qa:latest .
   ```

14. Start K3s or provide a kubeconfig and rerun:

   ```powershell
   kubectl get nodes -o wide
   kubectl apply --dry-run=server -f infrastructure/k8s_manifests
   kubectl apply -f infrastructure/k8s_manifests
   kubectl get deployment -n green-devops
   kubectl get pods -n green-devops
   ```

15. Start Prometheus and validate:

   ```powershell
   Invoke-WebRequest http://localhost:9090/-/healthy
   Invoke-WebRequest http://localhost:9090/api/v1/targets
   ```

   Then verify CPU and memory values change over time and match the model preprocessing contract.

16. Run end-to-end live scaling in this order:

   - API with Prometheus metrics, scaling disabled
   - API with Kubernetes scaler dry-run
   - API with Kubernetes scaler enabled against a disposable test Deployment
   - verify replicas before/after and rollback behavior

## Acceptance Criteria

The system should not be marked fully complete until all are true:

1. Prometheus returns rate-based CPU and memory data for the target pods.
2. Runtime data is normalized with the same scaler contract as training.
3. Engine 1 real inference runs from Prometheus-fed sequences.
4. Engines 2 and 3 run real calculations from Engine 1 output.
5. Decision Layer emits a safe final action and final pod count.
6. Kubernetes dry-run scaling shows the exact intended patch.
7. Live scaling changes a test Deployment and rollout verification passes.
8. Dashboard updates from the live API without relying on stale/demo-only files.
9. Pytest suite has meaningful passing tests in `tests/`.
