"""
Result Aggregator for Distributed Load Testing Results
"""

import json
import logging
import os
from typing import Dict, List, Optional
from azure_integration.azure_client import AzureClient

logger = logging.getLogger(__name__)

class ResultAggregator:
    """Aggregates results from multiple worker containers"""
    
    def __init__(self, azure_client: AzureClient):
        """
        Initialize result aggregator
        
        Args:
            azure_client: Azure client for blob storage operations
        """
        self.azure_client = azure_client
    
    def download_worker_results(self, run_id: str, worker_count: int, 
                              test_type: str, local_output_dir: str) -> List[str]:
        """
        Download results from all worker containers
        
        Args:
            run_id: Unique run identifier
            worker_count: Number of workers that ran
            test_type: 'protocol' or 'browser'
            local_output_dir: Local directory to save results
            
        Returns:
            List[str]: List of downloaded file paths
        """
        logger.info(f"Downloading results for run {run_id} ({worker_count} workers)")
        
        container_name = self.azure_client.config.get('container_name', 'results')
        downloaded_files = []
        
        for worker_index in range(worker_count):
            # Download summary file
            blob_name = f"{run_id}/summary_{worker_index}.json"
            local_file = os.path.join(local_output_dir, f"summary_{worker_index}.json")
            
            if self.azure_client.download_file(container_name, blob_name, local_file):
                downloaded_files.append(local_file)
                logger.info(f"Downloaded summary from worker {worker_index}")
            else:
                logger.warning(f"Failed to download summary from worker {worker_index}")
            
            # Note: We only generate summary files, not trace/metrics/logs files
            # Additional files like trace_*.har, metrics_*.json, logs_*.txt are not created
            # by our worker containers, so we don't attempt to download them
        
        logger.info(f"Downloaded {len(downloaded_files)} files for run {run_id}")
        return downloaded_files
    
    def aggregate_summaries(self, summary_files: List[str], test_type: str) -> Optional[Dict]:
        """
        Aggregate multiple k6 summary files into a single summary
        
        Args:
            summary_files: List of summary file paths
            test_type: 'protocol' or 'browser'
            
        Returns:
            Dict: Aggregated summary or None if failed
        """
        if not summary_files:
            logger.error("No summary files provided for aggregation")
            return None
        
        logger.info(f"Aggregating {len(summary_files)} summary files for {test_type} test")
        
        try:
            # Load all summaries (handle both JSON and JSONL formats)
            summaries = []
            for file_path in summary_files:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            # Try to load as single JSON first
                            try:
                                summary = json.load(f)
                                summaries.append(summary)
                                logger.debug(f"Loaded JSON summary from {file_path}")
                            except json.JSONDecodeError:
                                # If that fails, try JSONL format
                                f.seek(0)  # Reset file pointer
                                jsonl_data = []
                                for line in f:
                                    line = line.strip()
                                    if line:
                                        try:
                                            jsonl_data.append(json.loads(line))
                                        except json.JSONDecodeError:
                                            continue
                                
                                if jsonl_data:
                                    summaries.append(jsonl_data)
                                    logger.debug(f"Loaded JSONL summary from {file_path} ({len(jsonl_data)} lines)")
                                else:
                                    logger.warning(f"No valid JSON data found in {file_path}")
                    except Exception as e:
                        logger.error(f"Error loading summary from {file_path}: {e}")
                else:
                    logger.warning(f"Summary file not found: {file_path}")
            
            if not summaries:
                logger.error("No valid summaries found")
                return None
            
            # Convert JSONL data to expected format if needed
            processed_summaries = []
            for summary in summaries:
                if isinstance(summary, list):  # JSONL data
                    processed_summary = self._convert_jsonl_to_summary(summary, test_type)
                    processed_summaries.append(processed_summary)
                else:  # Regular JSON data
                    processed_summaries.append(summary)
            
            # Aggregate the summaries
            aggregated = self._merge_summaries(processed_summaries, test_type)
            
            logger.info(f"Successfully aggregated {len(summaries)} summaries")
            return aggregated
            
        except Exception as e:
            logger.error(f"Failed to aggregate summaries: {e}")
            return None
    
    def _merge_summaries(self, summaries: List[Dict], test_type: str) -> Dict:
        """
        Merge multiple k6 summaries into a single summary
        
        Args:
            summaries: List of summary dictionaries
            test_type: 'protocol' or 'browser'
            
        Returns:
            Dict: Merged summary
        """
        if len(summaries) == 1:
            return summaries[0]
        
        # Start with the first summary as base
        merged = summaries[0].copy()
        
        # Merge metrics
        for summary in summaries[1:]:
            merged = self._merge_metrics(merged, summary)
        
        # Update metadata
        merged['state']['testRunDuration'] = self._calculate_total_duration(summaries)
        merged['state']['vus'] = self._calculate_total_vus(summaries)
        merged['state']['vusMax'] = self._calculate_total_vus(summaries)
        
        # Update custom metrics if they exist
        if 'custom' in merged:
            merged['custom'] = self._merge_custom_metrics(summaries)
        
        return merged
    
    def _merge_metrics(self, base: Dict, additional: Dict) -> Dict:
        """
        Merge metrics from additional summary into base summary
        
        Args:
            base: Base summary dictionary
            additional: Additional summary dictionary
            
        Returns:
            Dict: Merged summary
        """
        # Merge metrics
        for metric_name, metric_data in additional.get('metrics', {}).items():
            if metric_name in base.get('metrics', {}):
                base_metric = base['metrics'][metric_name]
                
                # Merge values (only if they are dictionaries)
                if 'values' in metric_data and 'values' in base_metric:
                    if isinstance(base_metric['values'], dict) and isinstance(metric_data['values'], dict):
                        base_metric['values'].update(metric_data['values'])
                
                # Merge thresholds (only if they are dictionaries)
                if 'thresholds' in metric_data and 'thresholds' in base_metric:
                    if isinstance(base_metric['thresholds'], dict) and isinstance(metric_data['thresholds'], dict):
                        base_metric['thresholds'].update(metric_data['thresholds'])
                
                # Update counts
                if 'count' in metric_data and 'count' in base_metric:
                    base_metric['count'] += metric_data['count']
                
                # Update sums
                if 'sum' in metric_data and 'sum' in base_metric:
                    base_metric['sum'] += metric_data['sum']
                
                # Update averages
                if 'avg' in metric_data and 'avg' in base_metric and base_metric['count'] > 0:
                    base_metric['avg'] = base_metric['sum'] / base_metric['count']
                
                # Update min/max
                if 'min' in metric_data and 'min' in base_metric:
                    base_metric['min'] = min(base_metric['min'], metric_data['min'])
                
                if 'max' in metric_data and 'max' in base_metric:
                    base_metric['max'] = max(base_metric['max'], metric_data['max'])
                
                # Update percentiles
                if 'p(50)' in metric_data and 'p(50)' in base_metric:
                    # For percentiles, we need to recalculate from all values
                    # This is a simplified approach - in practice, you might want to
                    # store all values and recalculate percentiles
                    pass
                
                # Update rates
                if 'rate' in metric_data and 'rate' in base_metric:
                    base_metric['rate'] += metric_data['rate']
            else:
                # Add new metric
                if 'metrics' not in base:
                    base['metrics'] = {}
                base['metrics'][metric_name] = metric_data
        
        return base
    
    def _merge_custom_metrics(self, summaries: List[Dict]) -> Dict:
        """
        Merge custom metrics from multiple summaries
        
        Args:
            summaries: List of summary dictionaries
            
        Returns:
            Dict: Merged custom metrics
        """
        merged_custom = {}
        
        for summary in summaries:
            custom_metrics = summary.get('custom', {})
            for metric_name, metric_data in custom_metrics.items():
                if metric_name in merged_custom:
                    # Merge custom metric data
                    if isinstance(metric_data, dict) and isinstance(merged_custom[metric_name], dict):
                        merged_custom[metric_name].update(metric_data)
                    elif isinstance(metric_data, (int, float)) and isinstance(merged_custom[metric_name], (int, float)):
                        merged_custom[metric_name] += metric_data
                else:
                    merged_custom[metric_name] = metric_data
        
        return merged_custom
    
    def _calculate_total_duration(self, summaries: List[Dict]) -> str:
        """
        Calculate total test duration from multiple summaries
        
        Args:
            summaries: List of summary dictionaries
            
        Returns:
            str: Maximum duration in k6 format (workers run in parallel)
        """
        max_duration_ms = 0
        
        for summary in summaries:
            duration_str = summary.get('state', {}).get('testRunDuration', '0ms')
            # Convert k6 duration format to milliseconds
            duration_ms = self._parse_k6_duration(duration_str)
            max_duration_ms = max(max_duration_ms, duration_ms)
        
        return self._format_k6_duration(max_duration_ms)
    
    def _calculate_total_vus(self, summaries: List[Dict]) -> int:
        """
        Calculate total virtual users from multiple summaries
        
        Args:
            summaries: List of summary dictionaries
            
        Returns:
            int: Total virtual users (sum of all workers)
        """
        total_vus = 0
        
        for summary in summaries:
            vus = summary.get('state', {}).get('vus', 0)
            total_vus += vus  # Add VUs from each worker since they run in parallel
        
        return total_vus
    
    def _parse_k6_duration(self, duration_str: str) -> int:
        """
        Parse k6 duration string to milliseconds
        
        Args:
            duration_str: Duration string (e.g., '1m30s', '500ms')
            
        Returns:
            int: Duration in milliseconds
        """
        import re
        
        total_ms = 0
        
        # Parse hours
        hours_match = re.search(r'(\d+)h', duration_str)
        if hours_match:
            total_ms += int(hours_match.group(1)) * 3600 * 1000
        
        # Parse minutes
        minutes_match = re.search(r'(\d+)m', duration_str)
        if minutes_match:
            total_ms += int(minutes_match.group(1)) * 60 * 1000
        
        # Parse seconds
        seconds_match = re.search(r'(\d+)s', duration_str)
        if seconds_match:
            total_ms += int(seconds_match.group(1)) * 1000
        
        # Parse milliseconds
        ms_match = re.search(r'(\d+)ms', duration_str)
        if ms_match:
            total_ms += int(ms_match.group(1))
        
        return total_ms
    
    def _format_k6_duration(self, ms: int) -> str:
        """
        Format milliseconds to k6 duration string
        
        Args:
            ms: Duration in milliseconds
            
        Returns:
            str: k6 duration string
        """
        if ms < 1000:
            return f"{ms}ms"
        
        seconds = ms // 1000
        remaining_ms = ms % 1000
        
        if seconds < 60:
            return f"{seconds}s{remaining_ms}ms" if remaining_ms > 0 else f"{seconds}s"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            result = f"{minutes}m"
            if remaining_seconds > 0:
                result += f"{remaining_seconds}s"
            if remaining_ms > 0:
                result += f"{remaining_ms}ms"
            return result
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        result = f"{hours}h"
        if remaining_minutes > 0:
            result += f"{remaining_minutes}m"
        if remaining_seconds > 0:
            result += f"{remaining_seconds}s"
        if remaining_ms > 0:
            result += f"{remaining_ms}ms"
        
        return result
    
    def upload_aggregated_result(self, aggregated_summary: Dict, run_id: str, 
                               test_type: str) -> bool:
        """
        Upload aggregated result back to Azure Blob Storage
        
        Args:
            aggregated_summary: Aggregated summary dictionary
            run_id: Unique run identifier
            test_type: 'protocol' or 'browser'
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            # Create temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(aggregated_summary, f, indent=2)
                temp_file = f.name
            
            # Upload to blob storage
            container_name = self.azure_client.config.get('container_name', 'results')
            blob_name = f"{run_id}/final_summary_{test_type}.json"
            
            success = self.azure_client.upload_file(container_name, blob_name, temp_file)
            
            # Clean up temporary file
            os.unlink(temp_file)
            
            if success:
                logger.info(f"Uploaded aggregated {test_type} summary for run {run_id}")
            else:
                logger.error(f"Failed to upload aggregated {test_type} summary for run {run_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to upload aggregated result: {e}")
            return False
    
    def _convert_jsonl_to_summary(self, jsonl_data: List[Dict], test_type: str) -> Dict:
        """
        Convert JSONL data to k6 summary format
        
        Args:
            jsonl_data: List of JSON objects from JSONL file
            test_type: 'protocol' or 'browser'
            
        Returns:
            Dict: k6 summary format
        """
        try:
            # Extract metrics from JSONL data
            metrics = {}
            state = {
                'testRunDuration': '0ms',
                'vus': 0,
                'vusMax': 0,
                'iterationCount': 0,
                'iterationDurations': {},
                'dataReceived': 0,
                'dataSent': 0,
                'checks': {},
                'thresholds': {},
                'groups': {},
                'rootGroup': {'name': '', 'groups': {}, 'checks': {}, 'scenarios': {}}
            }
            
            # Track metric definitions and data points separately
            metric_definitions = {}
            metric_data_points = {}
            start_time = None
            end_time = None
            
            # First pass: collect metric definitions and find time range
            for item in jsonl_data:
                if item.get('type') == 'Metric':
                    metric_name = item.get('metric', 'unknown')
                    metric_definitions[metric_name] = item.get('data', {})
                elif item.get('type') == 'Point':
                    metric_name = item.get('metric', 'unknown')
                    if metric_name not in metric_data_points:
                        metric_data_points[metric_name] = []
                    metric_data_points[metric_name].append(item.get('data', {}))
                    
                    # Track time range
                    time_str = item.get('data', {}).get('time', '')
                    if time_str:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            if start_time is None or dt < start_time:
                                start_time = dt
                            if end_time is None or dt > end_time:
                                end_time = dt
                        except:
                            pass
            
            # Calculate test duration
            if start_time and end_time:
                duration_seconds = (end_time - start_time).total_seconds()
                if duration_seconds > 0:
                    if duration_seconds >= 60:
                        minutes = int(duration_seconds // 60)
                        seconds = int(duration_seconds % 60)
                        state['testRunDuration'] = f"{minutes}m{seconds}s"
                    else:
                        state['testRunDuration'] = f"{int(duration_seconds)}s"
            
            # Process each metric type
            for metric_name, data_points in metric_data_points.items():
                if not data_points:
                    continue
                
                # Get metric definition
                metric_def = metric_definitions.get(metric_name, {})
                metric_type = metric_def.get('type', 'counter')
                
                # Initialize metric structure based on type
                if metric_type == 'counter':
                    metric = {
                        'type': 'counter',
                        'contains': metric_def.get('contains', 'default'),
                        'values': {},
                        'thresholds': metric_def.get('thresholds', {}),
                        'count': len(data_points),
                        'sum': 0,
                        'min': float('inf'),
                        'max': float('-inf'),
                        'avg': 0,
                        'rate': 0
                    }
                elif metric_type == 'trend':
                    metric = {
                        'type': 'trend',
                        'contains': metric_def.get('contains', 'default'),
                        'values': {},
                        'thresholds': metric_def.get('thresholds', {}),
                        'count': len(data_points),
                        'sum': 0,
                        'min': float('inf'),
                        'max': float('-inf'),
                        'avg': 0,
                        'p(50)': 0,
                        'p(75)': 0,
                        'p(90)': 0,
                        'p(95)': 0,
                        'p(99)': 0
                    }
                else:
                    metric = {
                        'type': metric_type,
                        'contains': metric_def.get('contains', 'default'),
                        'values': {},
                        'thresholds': metric_def.get('thresholds', {}),
                        'count': len(data_points),
                        'sum': 0,
                        'min': float('inf'),
                        'max': float('-inf'),
                        'avg': 0
                    }
                
                # Process data points
                values = []
                for data_point in data_points:
                    value = data_point.get('value', 0)
                    values.append(value)
                    metric['sum'] += value
                    metric['min'] = min(metric['min'], value)
                    metric['max'] = max(metric['max'], value)
                
                # Calculate averages and percentiles
                if values:
                    metric['avg'] = metric['sum'] / len(values)
                    
                    if metric_type == 'trend' and len(values) > 0:
                        values.sort()
                        metric['p(50)'] = values[int(len(values) * 0.50)]
                        metric['p(75)'] = values[int(len(values) * 0.75)]
                        metric['p(90)'] = values[int(len(values) * 0.90)]
                        metric['p(95)'] = values[int(len(values) * 0.95)]
                        metric['p(99)'] = values[int(len(values) * 0.99)]
                    
                    # Calculate rate for counters
                    if metric_type == 'counter' and state['testRunDuration'] != '0ms':
                        try:
                            duration_str = state['testRunDuration']
                            if 'm' in duration_str:
                                minutes = int(duration_str.split('m')[0])
                                seconds = int(duration_str.split(duration_str.split('m')[0] + 'm')[1].replace('s', '')) if 's' in duration_str.split(duration_str.split('m')[0] + 'm')[1] else 0
                                duration_seconds = minutes * 60 + seconds
                            else:
                                duration_seconds = int(duration_str.replace('s', ''))
                            
                            if duration_seconds > 0:
                                metric['rate'] = metric['count'] / duration_seconds
                        except:
                            metric['rate'] = 0
                
                # Update state based on metric type
                if metric_name == 'data_received':
                    state['dataReceived'] = metric['sum']
                elif metric_name == 'data_sent':
                    state['dataSent'] = metric['sum']
                elif metric_name == 'iterations':
                    state['iterationCount'] = metric['count']
                elif metric_name == 'vus':
                    state['vusMax'] = max(state['vusMax'], metric['max'])
                    state['vus'] = metric['max']
                
                metrics[metric_name] = metric
            
            return {
                'state': state,
                'metrics': metrics,
                'root_group': state['rootGroup']
            }
            
        except Exception as e:
            logger.error(f"Failed to convert JSONL to summary: {e}")
            return {
                'state': {'testRunDuration': '0ms', 'vus': 0, 'vusMax': 0},
                'metrics': {},
                'root_group': {'name': '', 'groups': {}, 'checks': {}}
            }
