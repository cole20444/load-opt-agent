# Azure Distributed Testing Setup Guide

This guide explains how to set up Azure infrastructure for distributed load testing with the Load Testing & Optimization Agent.

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed and configured
- Docker installed locally for building images
- Python 3.8+ with pip

## Azure Infrastructure Setup

### 1. Create Resource Group

```bash
# Create resource group
az group create --name load-test-rg --location eastus

# Set as default resource group
az config set defaults.group=load-test-rg
```

### 2. Create Azure Container Registry (ACR)

```bash
# Create ACR
az acr create --name loadtestregistry --resource-group load-test-rg --sku Basic --admin-enabled true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name loadtestregistry --query loginServer --output tsv)

# Login to ACR
az acr login --name loadtestregistry
```

### 3. Create Azure Storage Account

```bash
# Create storage account
az storage account create \
    --name loadteststorage \
    --resource-group load-test-rg \
    --location eastus \
    --sku Standard_LRS \
    --kind StorageV2

# Create blob container for results
az storage container create \
    --name results \
    --account-name loadteststorage
```

### 4. Create Managed Identity

```bash
# Create user-assigned managed identity
az identity create --name load-test-identity --resource-group load-test-rg

# Get identity details
IDENTITY_ID=$(az identity show --name load-test-identity --resource-group load-test-rg --query id --output tsv)
IDENTITY_PRINCIPAL_ID=$(az identity show --name load-test-identity --resource-group load-test-rg --query principalId --output tsv)
```

### 5. Assign Permissions

```bash
# Get subscription ID
SUBSCRIPTION_ID=$(az account show --query id --output tsv)

# Assign ACR pull role to managed identity
az role assignment create \
    --assignee $IDENTITY_PRINCIPAL_ID \
    --role AcrPull \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/load-test-rg/providers/Microsoft.ContainerRegistry/registries/loadtestregistry

# Assign storage blob data contributor role
az role assignment create \
    --assignee $IDENTITY_PRINCIPAL_ID \
    --role Storage Blob Data Contributor \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/load-test-rg/providers/Microsoft.Storage/storageAccounts/loadteststorage
```

## Build and Push Docker Images

### 1. Build Worker Images

```bash
# Navigate to docker directory
cd docker

# Build protocol worker image
docker build -f Dockerfile.worker -t loadtestregistry.azurecr.io/k6-worker:latest .

# Build browser worker image
docker build -f Dockerfile.playwright-worker -t loadtestregistry.azurecr.io/playwright-worker:latest .
```

### 2. Push Images to ACR

```bash
# Push protocol worker image
docker push loadtestregistry.azurecr.io/k6-worker:latest

# Push browser worker image
docker push loadtestregistry.azurecr.io/playwright-worker:latest
```

## Install Azure Dependencies

```bash
# Install Azure Python dependencies
pip install -r requirements-azure.txt
```

## Configure Test

### 1. Update Configuration File

Edit `configs/azure_distributed_test.yaml` with your Azure details:

```yaml
# Azure Configuration
azure:
  subscription_id: "your-subscription-id"
  resource_group: "load-test-rg"
  location: "eastus"
  storage_account: "loadteststorage"
  container_name: "results"
  container_registry: "loadtestregistry.azurecr.io"

# Distribution settings
distribution:
  total_vus: 100  # Total VUs across all workers
  duration: "5m"  # Test duration
  vus_per_container:
    protocol: 20  # VUs per protocol worker container
    browser: 10   # VUs per browser worker container
  resources:
    protocol:
      cpu: 1.0
      memory: 2.0
    browser:
      cpu: 2.0
      memory: 4.0
```

### 2. Get Your Subscription ID

```bash
az account show --query id --output tsv
```

## Run Distributed Test

### 1. Local Development

```bash
# Run in Azure mode
python run_test.py configs/azure_distributed_test.yaml --mode azure
```

### 2. Azure Authentication

For local development, you can authenticate using:

```bash
# Interactive login
az login

# Or use service principal
az login --service-principal -u <app-id> -p <password> --tenant <tenant-id>
```

## Monitoring and Results

### 1. Monitor Container Instances

```bash
# List container groups
az container list --resource-group load-test-rg --output table

# Get container logs
az container logs --name <container-name> --resource-group load-test-rg
```

### 2. View Results in Azure Storage

```bash
# List blobs in results container
az storage blob list --container-name results --account-name loadteststorage --output table

# Download specific result file
az storage blob download \
    --container-name results \
    --name <blob-name> \
    --file <local-file> \
    --account-name loadteststorage
```

## Cost Optimization

### 1. Resource Sizing

- Start with smaller VU counts per container
- Use Standard_LRS storage for cost efficiency
- Monitor actual resource usage and adjust

### 2. Cleanup

```bash
# Clean up all container groups
az container delete --resource-group load-test-rg --name <container-name> --yes

# Or delete entire resource group
az group delete --name load-test-rg --yes
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure managed identity has correct permissions
   - Check Azure CLI login status

2. **Container Startup Failures**
   - Verify ACR image exists and is accessible
   - Check container resource limits

3. **Blob Storage Errors**
   - Ensure storage account and container exist
   - Verify managed identity has blob data permissions

### Debug Commands

```bash
# Check ACR access
az acr repository list --name loadtestregistry

# Test blob storage access
az storage blob list --container-name results --account-name loadteststorage

# Check managed identity
az identity show --name load-test-identity --resource-group load-test-rg
```

## Security Considerations

1. **Network Security**
   - Use private endpoints for storage and ACR
   - Implement network security groups

2. **Access Control**
   - Use managed identities instead of service principals
   - Follow principle of least privilege

3. **Data Protection**
   - Enable encryption at rest
   - Use secure transfer for blob storage

## Next Steps

1. Set up monitoring and alerting
2. Implement automated cleanup
3. Create CI/CD pipeline for image updates
4. Add cost monitoring and budgeting
