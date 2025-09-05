"""
Container Manager for Azure Container Instances
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from azure_integration.azure_client import AzureClient
from azure_integration.workload_distributor import WorkloadDistributor

logger = logging.getLogger(__name__)

class ContainerManager:
    """Manages Azure Container Instances for distributed load testing"""
    
    def __init__(self, azure_client: AzureClient, workload_distributor: WorkloadDistributor):
        """
        Initialize container manager
        
        Args:
            azure_client: Azure client for container operations
            workload_distributor: Workload distributor for configuration
        """
        self.azure_client = azure_client
        self.workload_distributor = workload_distributor
        self.active_containers = []
    
    async def create_workers(self, test_type: str, run_id: str) -> List[str]:
        """
        Create multiple worker containers for a test type
        
        Args:
            test_type: 'protocol' or 'browser'
            run_id: Unique run identifier
            
        Returns:
            List[str]: List of created container names
        """
        # Calculate number of workers needed
        worker_count = self.workload_distributor.calculate_worker_count(test_type)
        logger.info(f"Creating {worker_count} workers for {test_type} test")
        
        # Create containers in parallel
        tasks = []
        for worker_index in range(worker_count):
            task = self._create_worker(worker_index, worker_count, test_type, run_id)
            tasks.append(task)
        
        # Wait for all containers to be created
        container_names = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed containers
        successful_containers = []
        for i, result in enumerate(container_names):
            if isinstance(result, Exception):
                logger.error(f"Failed to create worker {i}: {result}")
            else:
                successful_containers.append(result)
                self.active_containers.append(result)
        
        logger.info(f"Successfully created {len(successful_containers)}/{worker_count} workers")
        return successful_containers
    
    async def _create_worker(self, worker_index: int, worker_count: int, 
                           test_type: str, run_id: str) -> str:
        """
        Create a single worker container
        
        Args:
            worker_index: Index of the worker (0-based)
            worker_count: Total number of workers
            test_type: 'protocol' or 'browser'
            run_id: Unique run identifier
            
        Returns:
            str: Name of the created container
        """
        try:
            # Generate worker configuration
            env_vars = self.workload_distributor.generate_worker_config(
                worker_index, worker_count, test_type, run_id
            )
            
            # Get resource requirements
            resources = self.workload_distributor.get_resource_requirements(test_type)
            
            # Get container image
            image = self.workload_distributor.get_container_image(test_type)
            
            # Generate container group name
            container_group_name = f"worker-{test_type}-{worker_index}-{run_id}".lower()
            
            # Generate container name (shorter, unique name)
            container_name = f"k6-{test_type}-{worker_index}"
            
            # Create container group
            container_group = self.azure_client.create_container_group(
                name=container_group_name,
                container_name=container_name,
                image=image,
                env_vars=env_vars,
                resources=resources
            )
            
            if container_group:
                logger.info(f"Created container group: {container_group_name}")
                return container_group_name
            else:
                raise Exception(f"Failed to create container group: {container_group_name}")
                
        except Exception as e:
            logger.error(f"Failed to create worker {worker_index}: {e}")
            raise
    
    async def wait_for_completion(self, container_names: List[str], 
                                timeout_minutes: int = 30) -> Dict[str, bool]:
        """
        Wait for all containers to complete
        
        Args:
            container_names: List of container names to monitor
            timeout_minutes: Maximum time to wait in minutes
            
        Returns:
            Dict[str, bool]: Container completion status
        """
        logger.info(f"Waiting for {len(container_names)} containers to complete")
        
        # Monitor containers in parallel
        tasks = []
        for container_name in container_names:
            task = self._monitor_container(container_name, timeout_minutes)
            tasks.append(task)
        
        # Wait for all containers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Create result dictionary
        completion_status = {}
        for i, result in enumerate(results):
            container_name = container_names[i]
            if isinstance(result, Exception):
                logger.error(f"Error monitoring container {container_name}: {result}")
                completion_status[container_name] = False
            else:
                completion_status[container_name] = result
        
        # Log completion summary
        successful = sum(1 for status in completion_status.values() if status)
        total = len(completion_status)
        logger.info(f"Container completion: {successful}/{total} successful")
        
        return completion_status
    
    async def _monitor_container(self, container_name: str, 
                               timeout_minutes: int) -> bool:
        """
        Monitor a single container until completion
        
        Args:
            container_name: Name of the container to monitor
            timeout_minutes: Maximum time to wait in minutes
            
        Returns:
            bool: True if container completed successfully
        """
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        # Extract run_id and worker_index from container name
        # Format: worker-protocol-0-run_20250815_165116
        parts = container_name.split('-')
        if len(parts) >= 4:
            worker_index = parts[2]
            run_id = parts[3]
        else:
            logger.error(f"Invalid container name format: {container_name}")
            return False
        
        while time.time() - start_time < timeout_seconds:
            # Check Azure container status
            status = self.azure_client.get_container_group_status(container_name)
            logger.info(f"Container {container_name} status: {status}")
            
            # Check for completion marker in blob storage
            completion_marker = f"completion_{worker_index}.txt"
            if self.azure_client.check_blob_exists(f"{run_id}/{completion_marker}"):
                logger.info(f"Container {container_name} completed (found completion marker)")
                return True
            
            # Check for summary file in blob storage
            summary_file = f"summary_{worker_index}.json"
            if self.azure_client.check_blob_exists(f"{run_id}/{summary_file}"):
                logger.info(f"Container {container_name} completed (found summary file)")
                return True
            
            if status in ["Succeeded", "Terminated"]:
                logger.info(f"Container {container_name} completed successfully")
                return True
            elif status in ["Failed", "Canceled"]:
                logger.error(f"Container {container_name} failed")
                return False
            elif status in ["Running", "Pending", "Creating"]:
                logger.debug(f"Container {container_name} status: {status}")
                await asyncio.sleep(30)  # Wait 30 seconds before checking again
            else:
                logger.warning(f"Unknown container {container_name} status: {status}")
                await asyncio.sleep(30)
        
        logger.error(f"Container {container_name} timed out after {timeout_minutes} minutes")
        return False
    
    def cleanup_containers(self, container_names: List[str]) -> Dict[str, bool]:
        """
        Clean up all containers
        
        Args:
            container_names: List of container names to delete
            
        Returns:
            Dict[str, bool]: Cleanup status for each container
        """
        logger.info(f"Cleaning up {len(container_names)} containers")
        
        cleanup_status = {}
        for container_name in container_names:
            try:
                success = self.azure_client.delete_container_group(container_name)
                cleanup_status[container_name] = success
                
                if success:
                    # Remove from active containers list
                    if container_name in self.active_containers:
                        self.active_containers.remove(container_name)
                        
            except Exception as e:
                logger.error(f"Failed to cleanup container {container_name}: {e}")
                cleanup_status[container_name] = False
        
        # Log cleanup summary
        successful = sum(1 for status in cleanup_status.values() if status)
        total = len(cleanup_status)
        logger.info(f"Container cleanup: {successful}/{total} successful")
        
        return cleanup_status
    
    def cleanup_all_active_containers(self) -> Dict[str, bool]:
        """
        Clean up all active containers (emergency cleanup)
        
        Returns:
            Dict[str, bool]: Cleanup status for each container
        """
        logger.warning(f"Emergency cleanup of {len(self.active_containers)} active containers")
        return self.cleanup_containers(self.active_containers.copy())
    
    def get_container_logs(self, container_name: str) -> Optional[str]:
        """
        Get logs from a container
        
        Args:
            container_name: Name of the container
            
        Returns:
            str: Container logs or None if failed
        """
        try:
            # This would require additional Azure Container Instances API calls
            # For now, we'll return None and implement this later if needed
            logger.info(f"Log retrieval not yet implemented for {container_name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get logs for container {container_name}: {e}")
            return None
    
    def get_container_metrics(self, container_name: str) -> Optional[Dict]:
        """
        Get metrics from a container
        
        Args:
            container_name: Name of the container
            
        Returns:
            Dict: Container metrics or None if failed
        """
        try:
            # This would require additional Azure Container Instances API calls
            # For now, we'll return None and implement this later if needed
            logger.info(f"Metrics retrieval not yet implemented for {container_name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get metrics for container {container_name}: {e}")
            return None
