# Terraform Directory

Terraform configuration for provisioning cloud infrastructure.

## Structure

- `main.tf` - Main Terraform configuration
- `variables.tf` - Variable definitions
- `outputs.tf` - Output values
- `kubernetes.tf` - Kubernetes specific config
- `monitoring.tf` - Prometheus and Grafana setup
- `environments/` - Environment-specific tfvars

## Usage

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file=environments/prod.tfvars

# Apply configuration
terraform apply -var-file=environments/prod.tfvars

# Destroy infrastructure
terraform destroy -var-file=environments/prod.tfvars
```

## Requirements

- Terraform 1.0+
- AWS/GCP/Azure CLI configured (depending on provider)
- kubectl configured

## Customization

Edit `environments/prod.tfvars` with your settings:
- Cluster name and size
- Instance types
- Region
- Custom tags

See individual .tf files for detailed configuration.
