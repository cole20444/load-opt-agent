# Azure Integration Module

This module extends the Load Testing & Optimization Agent to support distributed load testing in Azure using Azure Container Instances (ACI).

## Overview

The Azure integration enables running large-scale load tests by distributing the workload across multiple worker containers in Azure. This allows for:

- **Scalability**: Run tests with hundreds or thousands of virtual users
- **Cost Efficiency**: Pay only for the resources used during testing
- **Reliability**: Azure-managed infrastructure with automatic failover
- **Flexibility**: Support for both protocol (k6) and browser (xk6-browser) testing

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Orchestrator  │    │  Azure Client   │    │  Container      │
│   (Local)       │◄──►│  (Azure SDK)    │◄──►│  Manager        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Workload        │    │ Result          │    │ Azure Container │
│ Distributor     │    │ Aggregator      │    │ Instances       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components

### 1. Azure Client (`azure_client.py`)

Handles Azure authentication and provides interfaces for:
- Azure Container Instances management
- Azure Blob Storage operations
- Container lifecycle management

**Key Features:**
- Managed identity authentication
- Container group creation and monitoring
- Blob storage upload/download
- Automatic cleanup

### 2. Workload Distributor (`workload_distributor.py`)

Calculates and distributes test workload across multiple containers:
- Determines optimal number of worker containers
- Distributes virtual users evenly
- Generates container-specific configurations
- Validates distribution settings

**Key Features:**
- Dynamic worker count calculation
- VU distribution algorithms
- Resource requirement mapping
- Configuration validation

### 3. Container Manager (`container_manager.py`)

Manages the lifecycle of Azure Container Instances:
- Creates worker containers in parallel
- Monitors container status and completion
- Handles container cleanup
- Provides container metrics and logs

**Key Features:**
- Asynchronous container creation
- Parallel status monitoring
- Automatic cleanup on completion
- Error handling and recovery

### 4. Result Aggregator (`result_aggregator.py`)

Downloads and merges results from multiple worker containers:
- Downloads summary files from Azure Blob Storage
- Merges k6 summary data
- Calculates aggregated metrics
- Uploads final results back to Azure

**Key Features:**
- Parallel file download
- k6 summary aggregation
- Metric calculation and merging
- Result storage management

## Usage

### 1. Install Dependencies

```bash
pip install -r requirements-azure.txt
```

### 2. Configure Azure Infrastructure

Follow the setup guide in `docs/azure-setup.md` to create:
- Azure Container Registry (ACR)
- Azure Storage Account
- Managed Identity
- Required permissions

### 3. Build and Push Worker Images

```bash
# Build worker images
docker build -f docker/Dockerfile.worker -t yourregistry.azurecr.io/k6-worker:latest .
docker build -f docker/Dockerfile.browser-worker -t yourregistry.azurecr.io/xk6-browser-worker:latest .

# Push to ACR
docker push yourregistry.azurecr.io/k6-worker:latest
docker push yourregistry.azurecr.io/xk6-browser-worker:latest
```

### 4. Configure Test

Edit `configs/azure_distributed_test.yaml`:

```yaml
azure:
  subscription_id: "your-subscription-id"
  resource_group: "load-test-rg"
  location: "eastus"
  storage_account: "yourstorageaccount"
  container_name: "results"
  container_registry: "yourregistry.azurecr.io"

distribution:
  total_vus: 100
  duration: "5m"
  vus_per_container:
    protocol: 20
    browser: 10
  resources:
    protocol:
      cpu: 1.0
      memory: 2.0
    browser:
      cpu: 2.0
      memory: 4.0
```

### 5. Run Distributed Test

```bash
python run_test.py configs/azure_distributed_test.yaml --mode azure
```

## Configuration Options

### Azure Configuration

| Field | Description | Required |
|-------|-------------|----------|
| `subscription_id` | Azure subscription ID | Yes |
| `resource_group` | Resource group name | Yes |
| `location` | Azure region | Yes |
| `storage_account` | Storage account name | Yes |
| `container_name` | Blob container name | Yes |
| `container_registry` | ACR login server | Yes |

### Distribution Configuration

| Field | Description | Default |
|-------|-------------|---------|
| `total_vus` | Total virtual users across all workers | 10 |
| `duration` | Test duration (k6 format) | "1m" |
| `vus_per_container.protocol` | VUs per protocol worker | 10 |
| `vus_per_container.browser` | VUs per browser worker | 10 |
| `resources.protocol.cpu` | CPU cores for protocol workers | 1.0 |
| `resources.protocol.memory` | Memory (GB) for protocol workers | 2.0 |
| `resources.browser.cpu` | CPU cores for browser workers | 2.0 |
| `resources.browser.memory` | Memory (GB) for browser workers | 4.0 |

## Worker Container Behavior

### Environment Variables

Worker containers receive the following environment variables:

- `WORKER_INDEX`: Worker index (0-based)
- `WORKER_COUNT`: Total number of workers
- `TOTAL_VUS`: Total virtual users across all workers
- `DURATION`: Test duration
- `RUN_ID`: Unique run identifier
- `TEST_TYPE`: Test type (protocol/browser)
- `VUS`: Virtual users for this worker
- `TARGET_URL`: Target URL for testing
- `STORAGE_ACCOUNT`: Azure storage account name
- `CONTAINER_NAME`: Blob container name

### Test Execution

1. **Protocol Tests**: Run k6 with distributed VUs
2. **Browser Tests**: Run xk6-browser with distributed VUs
3. **Result Upload**: Upload summary files to Azure Blob Storage
4. **Completion**: Create completion marker file

## Error Handling

### Container Failures

- Individual container failures don't stop the entire test
- Failed containers are logged and reported
- Test continues with successful containers
- Partial results are still aggregated

### Network Issues

- Retry logic for blob storage operations
- Timeout handling for container operations
- Graceful degradation for partial failures

### Resource Limits

- Automatic cleanup of containers on completion
- Resource monitoring and alerts
- Cost optimization through efficient resource allocation

## Monitoring and Debugging

### Container Logs

```bash
# Get container logs
az container logs --name <container-name> --resource-group <resource-group>
```

### Azure Storage

```bash
# List result files
az storage blob list --container-name results --account-name <storage-account>
```

### Metrics and Monitoring

- Container resource usage
- Test execution time
- Success/failure rates
- Cost tracking

## Security

### Authentication

- Uses Azure Managed Identity for secure authentication
- No credentials stored in code or configuration
- Automatic token refresh and renewal

### Network Security

- Private endpoints for storage and ACR (recommended)
- Network security groups for container isolation
- Secure transfer for all data

### Data Protection

- Encryption at rest for all stored data
- Secure transfer for blob storage operations
- Access control through Azure RBAC

## Cost Optimization

### Resource Sizing

- Start with smaller VU counts and scale up
- Monitor actual resource usage
- Adjust CPU/memory allocation based on needs

### Storage Optimization

- Use Standard_LRS for cost efficiency
- Implement lifecycle policies for old results
- Compress large result files

### Container Management

- Automatic cleanup after test completion
- Use spot instances for cost savings (future enhancement)
- Implement resource quotas and limits

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check managed identity permissions
   - Verify Azure CLI login status
   - Ensure correct subscription access

2. **Container Startup Failures**
   - Verify ACR image exists and is accessible
   - Check container resource limits
   - Review container logs for errors

3. **Blob Storage Errors**
   - Ensure storage account and container exist
   - Verify managed identity has blob data permissions
   - Check network connectivity

### Debug Commands

```bash
# Check ACR access
az acr repository list --name <registry-name>

# Test blob storage access
az storage blob list --container-name results --account-name <storage-account>

# Check managed identity
az identity show --name <identity-name> --resource-group <resource-group>
```

## Future Enhancements

1. **AKS Support**: Add support for Azure Kubernetes Service
2. **Spot Instances**: Use spot instances for cost optimization
3. **Auto-scaling**: Dynamic scaling based on load
4. **Advanced Monitoring**: Integration with Azure Monitor
5. **CI/CD Integration**: Automated deployment pipelines
