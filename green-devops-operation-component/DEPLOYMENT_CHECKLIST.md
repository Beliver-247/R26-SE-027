# Deployment Checklist

Use this checklist before deploying to production.

## Pre-Deployment

### Code & Testing
- [ ] Unit tests passing (pytest tests/ -v)
- [ ] Integration tests passing
- [ ] Code linted (flake8 src tests)
- [ ] Type checking passing (mypy src)
- [ ] No merge conflicts
- [ ] Git commit message clear and descriptive

### Configuration
- [ ] `config/prod.yaml` reviewed and correct
- [ ] `config/carbon_config.yaml` validated
- [ ] `config/sla_config.yaml` matches requirements
- [ ] `config/scaling_config.yaml` appropriate for production
- [ ] `config/job_policies.yaml` reviewed
- [ ] `.env` file updated with production values
- [ ] All secrets in Kubernetes Secrets (not in config)
- [ ] Logging level set to INFO (not DEBUG)

### Models & Data
- [ ] Models in `models/trained/` verified
- [ ] Model metadata up to date
- [ ] Public datasets downloaded and validated
- [ ] Feature scalers in `models/scalers/` verified
- [ ] Evaluation metrics in `models/metrics/` reviewed

### Infrastructure
- [ ] Kubernetes cluster ready
- [ ] Prometheus configured and accessible
- [ ] Grafana dashboards prepared
- [ ] Terraform plan reviewed and approved
- [ ] Docker image built and tested
- [ ] Image pushed to registry (if using)
- [ ] Storage volumes configured
- [ ] Network policies reviewed

### Security
- [ ] RBAC roles reviewed and appropriate
- [ ] ServiceAccount created with least privileges
- [ ] Secrets encrypted
- [ ] API authentication configured (if required)
- [ ] Rate limiting enabled
- [ ] Image scanning for vulnerabilities

### Documentation
- [ ] Deployment guide reviewed
- [ ] API documentation up to date
- [ ] Runbooks prepared for operations team
- [ ] Troubleshooting guide reviewed
- [ ] Team trained on operations

## Deployment

### Phase 1: Staging
- [ ] Deploy to staging environment first
- [ ] Run smoke tests on staging
- [ ] Monitor staging for 24+ hours
- [ ] Validate predictions accuracy
- [ ] Check carbon calculations
- [ ] Verify Kubernetes integration

### Phase 2: Production Deployment
- [ ] Backup existing configurations
- [ ] Deploy during planned maintenance window
- [ ] Monitor deployment progress
- [ ] Verify pod startup and readiness
- [ ] Check health endpoints
- [ ] Verify metrics being exported

## Post-Deployment

### Immediate (First Hour)
- [ ] Pod running successfully
- [ ] API responding (test /health endpoint)
- [ ] Prometheus scraping metrics
- [ ] Logs showing no errors
- [ ] Grafana dashboards showing data
- [ ] Initial predictions working

### Short-term (First Day)
- [ ] No memory leaks in pod
- [ ] Prediction accuracy reasonable
- [ ] Scaling decisions working correctly
- [ ] Carbon calculations valid
- [ ] Job prioritization functioning
- [ ] No API errors in logs

### Long-term (After 7 Days)
- [ ] Cold-start transition complete
- [ ] Model retraining triggered and successful
- [ ] SLA compliance maintained
- [ ] Carbon metrics tracking correctly
- [ ] Performance metrics stable
- [ ] No resource exhaustion

## Rollback Plan

If issues detected:
- [ ] Have previous version tag ready
- [ ] Know how to scale down pods
- [ ] Have configuration backup
- [ ] Clear communication plan with stakeholders

Rollback command:
```bash
kubectl rollout undo deployment/operation-phase -n green-devops
```

## Sign-off

- Deployed by: _________________ Date: _________
- Reviewed by: _________________ Date: _________
- Approved by: ________________ Date: _________

## Post-Deployment Notes

Document any issues, workarounds, or special configurations needed for this deployment.
