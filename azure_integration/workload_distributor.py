"""
Workload Distribution Logic for Distributed Load Testing
"""

import math
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class WorkloadDistributor:
    """Distributes virtual users across multiple worker containers"""
    
    def __init__(self, config: Dict):
        """
        Initialize workload distributor with configuration
        
        Args:
            config: Test configuration dictionary
        """
        self.config = config
        self.distribution_config = config.get('distribution', {})
        
    def calculate_worker_count(self, test_type: str) -> int:
        """
        Calculate number of workers needed for a test type
        
        Args:
            test_type: 'protocol' or 'browser'
            
        Returns:
            int: Number of workers needed
        """
        total_vus = self.distribution_config.get('total_vus', 10)
        vus_per_container = self.distribution_config.get('vus_per_container', {}).get(test_type, 10)
        
        if vus_per_container <= 0:
            raise ValueError(f"vus_per_container for {test_type} must be greater than 0")
        
        worker_count = math.ceil(total_vus / vus_per_container)
        logger.info(f"Calculated {worker_count} workers for {test_type} test "
                   f"(total_vus={total_vus}, vus_per_container={vus_per_container})")
        
        return worker_count
    
    def calculate_worker_vus(self, worker_index: int, worker_count: int, test_type: str) -> int:
        """
        Calculate VUs for a specific worker
        
        Args:
            worker_index: Index of the worker (0-based)
            worker_count: Total number of workers
            test_type: 'protocol' or 'browser'
            
        Returns:
            int: Number of VUs for this worker
        """
        total_vus = self.distribution_config.get('total_vus', 10)
        
        # Distribute VUs evenly across workers
        base_vus = total_vus // worker_count
        extra_vus = total_vus % worker_count
        
        if worker_index < extra_vus:
            vus = base_vus + 1
        else:
            vus = base_vus
        
        logger.info(f"Worker {worker_index}: {vus} VUs (total: {total_vus}, workers: {worker_count})")
        return vus
    
    def generate_worker_config(self, worker_index: int, worker_count: int, 
                             test_type: str, run_id: str) -> Dict[str, str]:
        """
        Generate configuration for a specific worker
        
        Args:
            worker_index: Index of the worker (0-based)
            worker_count: Total number of workers
            test_type: 'protocol' or 'browser'
            run_id: Unique run identifier
            
        Returns:
            Dict[str, str]: Environment variables for the worker
        """
        vus = self.calculate_worker_vus(worker_index, worker_count, test_type)
        
        # Base environment variables
        env_vars = {
            'WORKER_INDEX': str(worker_index),
            'WORKER_COUNT': str(worker_count),
            'TOTAL_VUS': str(self.distribution_config.get('total_vus', 10)),
            'DURATION': self.distribution_config.get('duration', '1m'),
            'RUN_ID': run_id,
            'TEST_TYPE': test_type,
            'VUS': str(vus),
            'TARGET_URL': self.config.get('target', 'https://example.com'),
            
            # Azure Blob Storage configuration
            'STORAGE_ACCOUNT': self.config.get('azure', {}).get('storage_account', ''),
            'CONTAINER_NAME': self.config.get('azure', {}).get('container_name', 'results'),
            'AZURE_STORAGE_CONNECTION_STRING': self._get_storage_connection_string(),
        }
        
        # Add test-specific environment variables
        if test_type == 'protocol':
            protocol_settings = self.config.get('protocol_settings', {})
            env_vars.update({
                'K6_VUS': str(vus),
                'K6_DURATION': self.distribution_config.get('duration', '1m'),
                'K6_OUT': f'json=summary_{worker_index}.json',
            })
        elif test_type == 'browser':
            browser_settings = self.config.get('browser_settings', {})
            env_vars.update({
                'K6_VUS': str(vus),
                'K6_DURATION': self.distribution_config.get('duration', '1m'),
                'K6_OUT': f'json=summary_{worker_index}.json',
                'BROWSER_TIMEOUT': browser_settings.get('timeout', '30s'),
                'BROWSER_VIEWPORT_WIDTH': str(browser_settings.get('viewport', {}).get('width', 1920)),
                'BROWSER_VIEWPORT_HEIGHT': str(browser_settings.get('viewport', {}).get('height', 1080)),
            })
        
        logger.info(f"Generated worker config for worker {worker_index} ({test_type}): {vus} VUs")
        return env_vars
    
    def get_resource_requirements(self, test_type: str) -> Dict[str, float]:
        """
        Get resource requirements for a test type
        
        Args:
            test_type: 'protocol' or 'browser'
            
        Returns:
            Dict[str, float]: CPU and memory requirements
        """
        # Default resource requirements
        default_resources = {
            'protocol': {'cpu': 1.0, 'memory': 2.0},
            'browser': {'cpu': 2.0, 'memory': 4.0}
        }
        
        # Get custom resource requirements from config
        custom_resources = self.distribution_config.get('resources', {}).get(test_type, {})
        
        resources = default_resources.get(test_type, {'cpu': 1.0, 'memory': 2.0})
        resources.update(custom_resources)
        
        logger.info(f"Resource requirements for {test_type}: CPU={resources['cpu']}, Memory={resources['memory']}GB")
        return resources
    
    def get_container_image(self, test_type: str) -> str:
        """
        Get container image for a test type
        
        Args:
            test_type: 'protocol' or 'browser'
            
        Returns:
            str: Container image name
        """
        azure_config = self.config.get('azure', {})
        container_registry = azure_config.get('container_registry', '')
        
        if not container_registry:
            raise ValueError("container_registry is required in Azure configuration")
        
        # Remove trailing slash if present
        container_registry = container_registry.rstrip('/')
        
        if test_type == 'protocol':
            image = f"{container_registry}/k6-worker:latest"
        elif test_type == 'browser':
            image = f"{container_registry}/k6-playwright-worker:latest"
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        logger.info(f"Container image for {test_type}: {image}")
        return image
    
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
                '--name', self.config.get('azure', {}).get('storage_account', ''),
                '--resource-group', self.config.get('azure', {}).get('resource_group', '')
            ], capture_output=True, text=True, check=True)
            
            import json
            data = json.loads(result.stdout)
            return data.get('connectionString', '')
            
        except Exception as e:
            logger.error(f"Failed to get storage connection string: {e}")
            return ''
    
    def generate_run_id(self) -> str:
        """
        Generate a unique run identifier
        
        Returns:
            str: Unique run ID
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        run_id = f"run_{timestamp}"
        logger.info(f"Generated run ID: {run_id}")
        return run_id
    
    def validate_configuration(self) -> bool:
        """
        Validate the distribution configuration
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Check required fields
            required_fields = ['total_vus', 'duration', 'vus_per_container']
            for field in required_fields:
                if field not in self.distribution_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Check vus_per_container structure
            vus_per_container = self.distribution_config['vus_per_container']
            if not isinstance(vus_per_container, dict):
                raise ValueError("vus_per_container must be a dictionary")
            
            # Check test types - allow 0 for disabled test types
            test_types = ['protocol', 'browser']
            for test_type in test_types:
                if test_type in vus_per_container:
                    vus = vus_per_container[test_type]
                    if not isinstance(vus, int) or vus < 0:
                        raise ValueError(f"vus_per_container.{test_type} must be a non-negative integer")
            
            # Check Azure configuration
            azure_config = self.config.get('azure', {})
            required_azure_fields = ['subscription_id', 'resource_group', 'storage_account', 'container_registry']
            for field in required_azure_fields:
                if field not in azure_config:
                    raise ValueError(f"Missing required Azure field: {field}")
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
