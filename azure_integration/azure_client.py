"""
Azure Client for Container Management and Blob Storage Operations
"""

import os
import logging
from typing import Dict, List, Optional
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (
    ContainerGroup, Container, ResourceRequests, ResourceRequirements,
    EnvironmentVariable, ContainerPort, IpAddress, Port
)

logger = logging.getLogger(__name__)

class AzureClient:
    """Azure client for managing containers and blob storage operations"""
    
    def __init__(self, config: Dict):
        """
        Initialize Azure client with configuration
        
        Args:
            config: Azure configuration dictionary
        """
        self.config = config
        self.subscription_id = config.get('subscription_id')
        self.resource_group = config.get('resource_group')
        self.location = config.get('location', 'eastus')
        
        # Initialize credentials
        try:
            # Use default credential (works for local development with az login)
            self.credential = DefaultAzureCredential()
            logger.info("Using default credential for Azure authentication")
        except Exception as e:
            logger.error(f"Failed to initialize Azure credentials: {e}")
            raise
        
        # Initialize clients
        self._init_blob_client()
        self._init_container_client()
    
    def _init_blob_client(self):
        """Initialize Azure Blob Storage client"""
        # Try to use connection string first, fall back to credential
        connection_string = self._get_storage_connection_string()
        if connection_string:
            self.blob_client = BlobServiceClient.from_connection_string(connection_string)
            logger.info("Initialized Blob Storage client using connection string")
        else:
            storage_account = self.config.get('storage_account')
            if not storage_account:
                raise ValueError("storage_account is required in Azure configuration")
            
            account_url = f"https://{storage_account}.blob.core.windows.net"
            self.blob_client = BlobServiceClient(
                account_url=account_url,
                credential=self.credential
            )
            logger.info(f"Initialized Blob Storage client for account: {storage_account}")
    
    def _get_storage_connection_string(self) -> str:
        """
        Get Azure Storage connection string
        
        Returns:
            str: Storage connection string
        """
        try:
            import subprocess
            result = subprocess.run([
                'az', 'storage', 'account', 'show-connection-string',
                '--name', self.config.get('storage_account', ''),
                '--resource-group', self.config.get('resource_group', '')
            ], capture_output=True, text=True, check=True)
            
            import json
            data = json.loads(result.stdout)
            return data.get('connectionString', '')
            
        except Exception as e:
            logger.error(f"Failed to get storage connection string: {e}")
            return ''
    
    def _init_container_client(self):
        """Initialize Azure Container Instances client"""
        if not self.subscription_id:
            raise ValueError("subscription_id is required in Azure configuration")
        
        self.aci_client = ContainerInstanceManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        logger.info(f"Initialized Container Instances client for subscription: {self.subscription_id}")
    
    def upload_file(self, container_name: str, blob_name: str, file_path: str) -> bool:
        """
        Upload file to Azure Blob Storage
        
        Args:
            container_name: Name of the blob container
            blob_name: Name of the blob (including path)
            file_path: Local path to the file
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            container_client = self.blob_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            logger.info(f"Uploaded {file_path} to {container_name}/{blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            return False
    
    def download_file(self, container_name: str, blob_name: str, local_path: str) -> bool:
        """
        Download file from Azure Blob Storage
        
        Args:
            container_name: Name of the blob container
            blob_name: Name of the blob (including path)
            local_path: Local path to save the file
            
        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            container_client = self.blob_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, "wb") as data:
                download_stream = blob_client.download_blob()
                data.write(download_stream.readall())
            
            logger.info(f"Downloaded {container_name}/{blob_name} to {local_path}")
            return True
            
        except Exception as e:
            # Check if it's a "blob not found" error
            if "BlobNotFound" in str(e) or "The specified blob does not exist" in str(e):
                logger.debug(f"Optional file not found: {container_name}/{blob_name}")
            else:
                logger.error(f"Failed to download {container_name}/{blob_name}: {e}")
            return False
    
    def list_blobs(self, container_name: str, prefix: str = "") -> List[str]:
        """
        List blobs in a container with optional prefix
        
        Args:
            container_name: Name of the blob container
            prefix: Optional prefix to filter blobs
            
        Returns:
            List[str]: List of blob names
        """
        try:
            container_client = self.blob_client.get_container_client(container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
            
        except Exception as e:
            logger.error(f"Failed to list blobs in {container_name}: {e}")
            return []
    
    def create_container_group(self, name: str, image: str, env_vars: Dict[str, str], 
                              resources: Dict, container_name: str = None, ports: List[int] = None) -> Optional[ContainerGroup]:
        """
        Create Azure Container Instance group
        
        Args:
            name: Name of the container group
            image: Docker image to use
            env_vars: Environment variables
            resources: Resource requirements (cpu, memory)
            container_name: Name of the container inside the group (defaults to group name)
            ports: List of ports to expose
            
        Returns:
            ContainerGroup: Created container group or None if failed
        """
        try:
            # Convert environment variables
            environment_variables = [
                EnvironmentVariable(name=k, value=v) 
                for k, v in env_vars.items()
            ]
            
            # Set up resource requirements
            resource_requests = ResourceRequests(
                memory_in_gb=resources.get('memory', 1.0),
                cpu=resources.get('cpu', 1.0)
            )
            resource_requirements = ResourceRequirements(requests=resource_requests)
            
            # Set up container ports
            container_ports = []
            if ports:
                container_ports = [ContainerPort(port=port) for port in ports]
            
            # Use provided container name or default to group name
            actual_container_name = container_name if container_name else name
            
            # Create container
            container = Container(
                name=actual_container_name,
                image=image,
                resources=resource_requirements,
                environment_variables=environment_variables,
                ports=container_ports
            )
            
            # Set up IP address if ports are specified
            ip_address = None
            if ports:
                ip_address = IpAddress(
                    type="Public",
                    ports=[Port(port=port) for port in ports]
                )
            
            # Get registry credentials if image is from our ACR
            registry_credentials = None
            if "azurecr.io" in image:
                registry_credentials = self._get_registry_credentials()
            
            # Create container group
            container_group = ContainerGroup(
                location=self.location,
                containers=[container],
                os_type="Linux",
                ip_address=ip_address,
                image_registry_credentials=registry_credentials,
                restart_policy="Never"
            )
            
            # Deploy container group
            poller = self.aci_client.container_groups.begin_create_or_update(
                resource_group_name=self.resource_group,
                container_group_name=name,
                container_group=container_group
            )
            
            result = poller.result()
            logger.info(f"Created container group: {name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create container group {name}: {e}")
            return None
    
    def delete_container_group(self, name: str) -> bool:
        """
        Delete Azure Container Instance group
        
        Args:
            name: Name of the container group to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            poller = self.aci_client.container_groups.begin_delete(
                resource_group_name=self.resource_group,
                container_group_name=name
            )
            poller.result()
            logger.info(f"Deleted container group: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete container group {name}: {e}")
            return False
    
    def get_container_group_status(self, name: str) -> Optional[str]:
        """
        Get status of container group
        
        Args:
            name: Name of the container group
            
        Returns:
            str: Container group state or None if not found
        """
        try:
            container_group = self.aci_client.container_groups.get(
                resource_group_name=self.resource_group,
                container_group_name=name
            )
            
            # Get detailed status information
            if container_group.containers and len(container_group.containers) > 0:
                container = container_group.containers[0]
                if container.instance_view and container.instance_view.current_state:
                    state = container.instance_view.current_state.state
                    logger.info(f"Container {name} state: {state}")
                    
                    # Log additional details for debugging
                    if hasattr(container.instance_view.current_state, 'detail_status'):
                        detail = container.instance_view.current_state.detail_status
                        logger.info(f"Container {name} detail: {detail}")
                    
                    return state
                else:
                    logger.warning(f"Container {name} has no instance view or current state")
                    return None
            else:
                logger.warning(f"Container group {name} has no containers")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get status for container group {name}: {e}")
            return None
    
    def wait_for_container_completion(self, name: str, timeout_minutes: int = 60) -> bool:
        """
        Wait for container group to complete
        
        Args:
            name: Name of the container group
            timeout_minutes: Maximum time to wait in minutes
            
        Returns:
            bool: True if completed successfully, False if failed or timed out
        """
        import time
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            status = self.get_container_group_status(name)
            
            if status == "Succeeded":
                logger.info(f"Container group {name} completed successfully")
                return True
            elif status == "Failed":
                logger.error(f"Container group {name} failed")
                return False
            elif status in ["Running", "Pending"]:
                logger.info(f"Container group {name} status: {status}")
                time.sleep(30)  # Wait 30 seconds before checking again
            else:
                logger.warning(f"Unknown container group {name} status: {status}")
                time.sleep(30)
        
        logger.error(f"Container group {name} timed out after {timeout_minutes} minutes")
        return False
    
    def _get_registry_credentials(self):
        """
        Get Azure Container Registry credentials
        
        Returns:
            List of ImageRegistryCredential objects
        """
        try:
            from azure.mgmt.containerinstance.models import ImageRegistryCredential
            
            # Get ACR credentials using Azure CLI
            import subprocess
            result = subprocess.run([
                'az', 'acr', 'credential', 'show', 
                '--name', 'poploadtestregistry'
            ], capture_output=True, text=True, check=True)
            
            import json
            credentials = json.loads(result.stdout)
            
            return [ImageRegistryCredential(
                server='poploadtestregistry.azurecr.io',
                username=credentials['username'],
                password=credentials['passwords'][0]['value']
            )]
            
        except Exception as e:
            logger.error(f"Failed to get registry credentials: {e}")
            return None
    
    def check_blob_exists(self, blob_path: str) -> bool:
        """
        Check if a blob exists in Azure Storage
        
        Args:
            blob_path: Path to the blob (e.g., "run_id/completion_0.txt")
            
        Returns:
            bool: True if blob exists, False otherwise
        """
        try:
            container_name = self.config.get('azure', {}).get('container_name', 'results')
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_path
            )
            
            # Try to get blob properties - if it exists, this will succeed
            blob_client.get_blob_properties()
            return True
            
        except Exception as e:
            # Blob doesn't exist or other error
            return False
