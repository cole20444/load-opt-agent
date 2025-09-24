#!/usr/bin/env python3
"""
Load Testing & Optimization Agent - Phase 1
Python runner for k6 load tests with YAML configuration
Enhanced with xk6-browser support for comprehensive front-end performance testing
Extended with Azure distributed testing capabilities
"""

import subprocess
import yaml
import os
import sys
import json
import logging
import asyncio
import argparse
import signal
import sys
from datetime import datetime
from pathlib import Path

# Import Azure integration components
try:
    from azure_integration.azure_client import AzureClient
    from azure_integration.workload_distributor import WorkloadDistributor
    from azure_integration.container_manager import ContainerManager
    from azure_integration.result_aggregator import ResultAggregator
    AZURE_INTEGRATION_AVAILABLE = True
except ImportError as e:
    AZURE_INTEGRATION_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Azure integration not available: {e}")
    logger.warning("Install requirements-azure.txt for distributed testing")

# Import AI Analysis components
try:
    from ai_analysis.analysis_agent import AIAnalysisAgent
    AI_ANALYSIS_AVAILABLE = True
except ImportError:
    AI_ANALYSIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("AI Analysis not available - skipping optimization recommendations")

# Global variable to track containers for cleanup
active_containers = []

def signal_handler(signum, frame):
    """Handle interrupt signals to ensure cleanup"""
    logger.warning(f"Received signal {signum}, cleaning up containers...")
    if active_containers:
        try:
            # Import here to avoid circular imports
            from azure_integration.azure_client import AzureClient
            from azure_integration.container_manager import ContainerManager
            from azure_integration.workload_distributor import WorkloadDistributor
            
            # Initialize cleanup components
            azure_config = {}  # This would need to be passed from the main function
            azure_client = AzureClient(azure_config)
            workload_distributor = WorkloadDistributor({})
            container_manager = ContainerManager(azure_client, workload_distributor)
            
            cleanup_status = container_manager.cleanup_containers(active_containers)
            successful_cleanup = sum(1 for status in cleanup_status.values() if status)
            logger.info(f"Signal cleanup: {successful_cleanup}/{len(cleanup_status)} containers")
        except Exception as e:
            logger.error(f"Signal cleanup failed: {e}")
    
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Reduce Azure SDK logging to reduce noise
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.identity').setLevel(logging.WARNING)
logging.getLogger('azure.mgmt').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load and validate YAML configuration file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check if this is an Azure distributed config
        is_azure_config = 'azure' in config and 'distribution' in config
        
        if is_azure_config:
            # Azure distributed config validation
            required_fields = ['target', 'test_type']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate Azure configuration
            azure_config = config.get('azure', {})
            required_azure_fields = ['subscription_id', 'resource_group', 'storage_account', 'container_registry']
            for field in required_azure_fields:
                if field not in azure_config:
                    raise ValueError(f"Missing required Azure field: {field}")
            
            # Validate distribution configuration
            distribution_config = config.get('distribution', {})
            required_dist_fields = ['total_vus', 'duration', 'vus_per_container']
            for field in required_dist_fields:
                if field not in distribution_config:
                    raise ValueError(f"Missing required distribution field: {field}")
        else:
            # Local config validation
            required_fields = ['target', 'vus', 'duration']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate data types for local config
            if not isinstance(config['target'], str):
                raise ValueError("target must be a string URL")
            if not isinstance(config['vus'], int) or config['vus'] <= 0:
                raise ValueError("vus must be a positive integer")
            if not isinstance(config['duration'], str):
                raise ValueError("duration must be a string (e.g., '30s', '5m')")
        
        # Set default values for optional fields
        if 'description' not in config:
            config['description'] = "No description provided"
        if 'tags' not in config:
            config['tags'] = []
        if 'test_type' not in config:
            config['test_type'] = 'protocol'  # Default to protocol testing
        
        logger.info(f"Configuration loaded successfully: {config}")
        return config
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration validation error: {e}")
        sys.exit(1)

def create_output_directory(config):
    """Create organized output directory structure"""
    from datetime import datetime
    import re
    
    # Extract site name from URL
    target_url = config.get('target', 'unknown')
    site_name = re.sub(r'https?://(www\.)?', '', target_url)
    site_name = re.sub(r'[^a-zA-Z0-9.-]', '_', site_name)
    site_name = site_name.replace('.', '_')
    
    # Create timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create organized directory structure
    output_dir = f"output/{site_name}/{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a symlink to latest results for easy access
    latest_dir = f"output/{site_name}/latest"
    if os.path.exists(latest_dir):
        if os.path.islink(latest_dir):
            os.unlink(latest_dir)
        else:
            os.remove(latest_dir)
    os.symlink(timestamp, latest_dir)
    
    logger.info(f"Created output directory: {output_dir}")
    return output_dir

def run_protocol_test(config, output_dir):
    """Run protocol-level k6 test (original functionality)"""
    logger.info("🌐 Running protocol-level load test...")
    
    # Set environment variables for k6
    env = os.environ.copy()
    env['TARGET_URL'] = config['target']
    env['K6_OUT'] = f'json={output_dir}/protocol_summary.json'
    
    # Build and run k6 container
    try:
        # Build the protocol Docker image
        build_result = subprocess.run([
            'docker', 'build', '-t', 'k6-load-test', '-f', 'docker/Dockerfile', '.'
        ], capture_output=True, text=True, timeout=300)
        
        if build_result.returncode != 0:
            logger.error(f"Failed to build protocol Docker image: {build_result.stderr}")
            return False
        
        # Run the protocol test with resource limits for high-load testing
        run_result = subprocess.run([
            'docker', 'run', '--rm',
            '--memory=4g',  # 4GB memory limit
            '--cpus=2',     # 2 CPU cores
            '--ulimit', 'nofile=65536:65536',  # Increase file descriptor limit
            '-e', f'TARGET_URL={config["target"]}',
            '-e', f'K6_VUS={config["vus"]}',
            '-e', f'K6_DURATION={config["duration"]}',
            '-v', f'{os.path.abspath("tests/load_test.js")}:/app/load_test.js:ro',
            '-v', f'{os.path.abspath(output_dir)}:/app/output',
            'k6-load-test',
            '--out', 'json=/app/output/protocol_summary.json',
            '/app/load_test.js'
        ], capture_output=True, text=True, timeout=2400)  # 40 minutes timeout for 30m test
        
        # Check if the test generated output files (more reliable than return code)
        protocol_summary_file = os.path.join(output_dir, "protocol_summary.json")
        if os.path.exists(protocol_summary_file) and os.path.getsize(protocol_summary_file) > 0:
            logger.info("✅ Protocol-level test completed successfully")
            return True
        else:
            logger.error(f"Protocol test failed: {run_result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Protocol test timed out")
        return False
    except Exception as e:
        logger.error(f"Error running protocol test: {e}")
        return False

def run_browser_test(config, output_dir):
    """Run browser-level xk6-browser test"""
    logger.info("🌐 Running browser-level load test...")
    
    # Set environment variables for k6
    env = os.environ.copy()
    env['TARGET_URL'] = config['target']
    env['K6_OUT'] = f'json={output_dir}/browser_summary.json'
    
    # Build and run xk6-browser container
    try:
        # Build the browser Docker image
        build_result = subprocess.run([
            'docker', 'build', '-t', 'xk6-browser-test', '-f', 'docker/Dockerfile.browser', '.'
        ], capture_output=True, text=True, timeout=600)  # Longer timeout for browser build
        
        if build_result.returncode != 0:
            logger.error(f"Failed to build browser Docker image: {build_result.stderr}")
            # Create a minimal browser summary file to indicate failure
            create_failed_browser_summary(output_dir)
            return False
        
        # Run the browser test with resource limits
        run_result = subprocess.run([
            'docker', 'run', '--rm',
            '--memory=6g',  # 6GB memory limit for browser tests
            '--cpus=2',     # 2 CPU cores
            '--ulimit', 'nofile=65536:65536',  # Increase file descriptor limit
            '--shm-size=2g',  # Shared memory for browser
            '-e', f'TARGET_URL={config["target"]}',
            '-e', f'K6_VUS={config["vus"]}',
            '-e', f'K6_DURATION={config["duration"]}',
            '-v', f'{os.path.abspath("tests/browser_load_test.js")}:/app/browser_load_test.js:ro',
            '-v', f'{os.path.abspath(output_dir)}:/app/output',
            'xk6-browser-test',
            '--out', 'json=/app/output/browser_summary.json',
            '/app/browser_load_test.js'
        ], capture_output=True, text=True, timeout=1800)  # 30 minutes timeout for browser tests
        
        # Check if the test generated output files (more reliable than return code)
        browser_summary_file = os.path.join(output_dir, "browser_summary.json")
        if os.path.exists(browser_summary_file) and os.path.getsize(browser_summary_file) > 0:
            logger.info("✅ Browser-level test completed successfully")
            return True
        else:
            logger.error(f"Browser test failed: {run_result.stderr}")
            # Create a minimal browser summary file to indicate failure
            create_failed_browser_summary(output_dir)
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Browser test timed out")
        # Create a minimal browser summary file to indicate failure
        create_failed_browser_summary(output_dir)
        return False
    except Exception as e:
        logger.error(f"Error running browser test: {e}")
        # Create a minimal browser summary file to indicate failure
        create_failed_browser_summary(output_dir)
        return False

def create_failed_browser_summary(output_dir):
    """Create a minimal browser summary file when browser test fails"""
    try:
        failed_summary = {
            "type": "Point",
            "data": {
                "time": datetime.now().isoformat(),
                "value": 0,
                "tags": {
                    "test_type": "browser",
                    "status": "failed"
                }
            },
            "metric": "browser_test_failed"
        }
        
        browser_summary_path = os.path.join(output_dir, "browser_summary.json")
        with open(browser_summary_path, 'w') as f:
            json.dump([failed_summary], f)
        
        logger.info(f"Created failed browser summary at {browser_summary_path}")
    except Exception as e:
        logger.error(f"Failed to create browser summary file: {e}")

def run_k6_test(config, output_dir=None):
    """Run k6 test based on configuration"""
    if output_dir is None:
        output_dir = create_output_directory(config)
    
    test_type = config.get('test_type', 'protocol')
    
    if test_type == 'browser':
        return run_browser_test(config, output_dir)
    elif test_type == 'both':
        # Run both protocol and browser tests
        protocol_success = run_protocol_test(config, output_dir)
        browser_success = run_browser_test(config, output_dir)
        return protocol_success and browser_success
    else:
        # Default to protocol testing
        return run_protocol_test(config, output_dir)

def build_docker_image():
    """Build Docker image for k6 testing"""
    logger.info("🔨 Building Docker image...")
    
    try:
        result = subprocess.run([
            'docker', 'build', '-t', 'k6-load-test', '-f', 'docker/Dockerfile', '.'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("✅ Docker image built successfully")
            return True
        else:
            logger.error(f"Failed to build Docker image: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Docker build timed out")
        return False
    except Exception as e:
        logger.error(f"Error building Docker image: {e}")
        return False

def generate_test_report(config, output_dir):
    """Generate test report from k6 results"""
    logger.info("📊 Generating test report...")
    
    # Determine which summary file to use
    test_type = config.get('test_type', 'protocol')
    if test_type == 'browser':
        summary_file = os.path.join(output_dir, "browser_summary.json")
    else:
        summary_file = os.path.join(output_dir, "protocol_summary.json")
    
    if not os.path.exists(summary_file):
        logger.error(f"Summary file not found: {summary_file}")
        return None
    
    try:
        # Parse k6 summary data
        metrics_data = []
        with open(summary_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') == 'Point':
                        metrics_data.append(data)
                except json.JSONDecodeError:
                    continue
        
        # Group metrics by name
        metrics_by_name = {}
        for data in metrics_data:
            metric_name = data.get('metric', 'unknown')
            if metric_name not in metrics_by_name:
                metrics_by_name[metric_name] = []
            metrics_by_name[metric_name].append(data)
        
        # Calculate statistics
        def calculate_stats(values):
            if not values:
                return {'avg': 0, 'min': 0, 'max': 0}
            return {
                'avg': sum(values) / len(values),
                'min': min(values),
                'max': max(values)
            }
        
        # Extract key metrics
        performance_metrics = {}
        for metric_name in ['http_req_duration', 'http_req_failed', 'http_reqs']:
            if metric_name in metrics_by_name:
                values = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name[metric_name]]
                performance_metrics[metric_name] = calculate_stats(values)
        
        # Get duration and VUs from config (handle both local and Azure distributed configs)
        duration = config.get('duration', config.get('distribution', {}).get('duration', '1m'))
        vus = config.get('vus', config.get('distribution', {}).get('total_vus', 1))
        
        # Generate test summary
        test_summary = {
            'total_requests': int(performance_metrics.get('http_reqs', {}).get('avg', 0) * int(duration.replace('s', '').replace('m', '000'))),
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': performance_metrics.get('http_req_duration', {}).get('avg', 0),
            'error_rate': performance_metrics.get('http_req_failed', {}).get('avg', 0) * 100
        }
        
        test_summary['successful_requests'] = test_summary['total_requests'] - test_summary['failed_requests']
        test_summary['failed_requests'] = int(test_summary['total_requests'] * test_summary['error_rate'] / 100)
        
        # Create comprehensive report
        report = {
            'test_metadata': {
                'site_name': config['target'],
                'test_timestamp': datetime.now().isoformat(),
                'test_duration': duration,
                'virtual_users': vus,
                'description': config.get('description', ''),
                'tags': config.get('tags', []),
                'test_type': test_type,
                'output_directory': output_dir
            },
            'performance_metrics': performance_metrics,
            'test_summary': test_summary
        }
        
        # Save report
        report_path = os.path.join(output_dir, "test_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Test report saved to: {report_path}")
        return report
        
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        return None

def run_browser_analysis(config, output_dir):
    """Run browser-specific analysis"""
    logger.info("🔍 Running browser performance analysis...")
    
    browser_summary_file = os.path.join(output_dir, "browser_summary.json")
    
    if not os.path.exists(browser_summary_file):
        logger.warning("Browser summary file not found - skipping browser analysis")
        return None
    
    try:
        # Find individual Playwright result files for browser analysis
        playwright_files = []
        for file in os.listdir(output_dir):
            if file.startswith('playwright_results_') and file.endswith('.json'):
                playwright_files.append(os.path.join(output_dir, file))
        
        if not playwright_files:
            logger.warning("No individual Playwright result files found, using aggregated summary")
            playwright_files = [browser_summary_file]
        
        # Use the first Playwright result file for analysis (contains Core Web Vitals)
        analysis_file = playwright_files[0]
        logger.info(f"Using {analysis_file} for browser analysis")
        
        # Run browser metrics analyzer
        result = subprocess.run([
            'python', 'scripts/browser_metrics_analyzer.py', analysis_file
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info("✅ Browser analysis completed successfully")
            
            # Load the analysis report
            analysis_file = browser_summary_file.replace('.json', '_analysis.json')
            if os.path.exists(analysis_file):
                with open(analysis_file, 'r') as f:
                    analysis_report = json.load(f)
                
                # Save to standard location
                browser_report_path = os.path.join(output_dir, "browser_analysis_report.json")
                with open(browser_report_path, 'w') as f:
                    json.dump(analysis_report, f, indent=2)
                
                logger.info(f"✅ Browser analysis report saved to: {browser_report_path}")
                return analysis_report
        else:
            logger.error(f"Browser analysis failed with return code: {result.returncode}")
            logger.error(f"Browser analysis stdout: {result.stdout}")
            logger.error(f"Browser analysis stderr: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Error running browser analysis: {e}")
        return None

def run_ai_analysis(config, output_dir):
    """Run AI analysis on test results with ALL available data"""
    # Check if AI analysis is disabled in config
    analysis_settings = config.get('analysis_settings', {})
    if analysis_settings.get('run_ai_analysis', True) == False:
        logger.info("🤖 AI analysis disabled in configuration - skipping")
        return None
    
    if not AI_ANALYSIS_AVAILABLE:
        logger.warning("AI Analysis not available - skipping")
        return None
    
    logger.info("🤖 Running comprehensive AI analysis...")
    
    try:
        # Import AI analysis agent
        from ai_analysis.openai_enhanced_agent import EnhancedAIAnalysisAgent
        
        # Initialize the enhanced AI agent
        agent = EnhancedAIAnalysisAgent()
        
        # Run page resource analysis first
        logger.info("Running page resource analysis...")
        try:
            result = subprocess.run([
                'python', 'scripts/page_resource_analyzer.py', config['target']
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("✅ Page resource analysis completed")
                # Move the output to our test directory
                if os.path.exists('page_resource_analysis.json'):
                    import shutil
                    shutil.move('page_resource_analysis.json', os.path.join(output_dir, 'page_resource_analysis.json'))
            else:
                logger.warning(f"⚠️ Page resource analysis failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"⚠️ Could not run page resource analysis: {e}")
        
        # Run enhanced performance analysis
        logger.info("Running enhanced performance analysis...")
        try:
            # Use protocol summary for enhanced analysis
            summary_file = os.path.join(output_dir, "protocol_summary.json")
            
            if os.path.exists(summary_file):
                result = subprocess.run([
                    'python', 'scripts/enhanced_performance_analyzer.py', summary_file
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    logger.info("✅ Enhanced performance analysis completed")
                    # Move the output to our test directory
                    if os.path.exists('enhanced_analysis_report.json'):
                        import shutil
                        shutil.move('enhanced_analysis_report.json', os.path.join(output_dir, 'enhanced_analysis_report.json'))
                else:
                    logger.warning(f"⚠️ Enhanced performance analysis failed: {result.stderr}")
            else:
                logger.warning(f"⚠️ Summary file not found for enhanced analysis: {summary_file}")
        except Exception as e:
            logger.warning(f"⚠️ Could not run enhanced performance analysis: {e}")
        
        # Load test report
        test_report_path = os.path.join(output_dir, "test_report.json")
        
        if not os.path.exists(test_report_path):
            logger.error(f"Test report not found: {test_report_path}")
            return None
        
        # Now run the comprehensive AI analysis with ALL data
        logger.info("Running comprehensive AI analysis...")
        analysis_result = agent.analyze_test_results(test_report_path, config)
        
        if analysis_result:
            # Save the comprehensive analysis report
            ai_report_path = os.path.join(output_dir, "enhanced_ai_analysis_report.json")
            with open(ai_report_path, 'w') as f:
                json.dump(analysis_result, f, indent=2)
            
            logger.info(f"✅ AI analysis report saved to: {ai_report_path}")
            return analysis_result
        else:
            logger.error("❌ AI analysis failed")
            return None
            
    except ImportError as e:
        logger.error(f"❌ Could not import AI analysis modules: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error in AI analysis: {e}")
        return None


def combine_test_results(config, output_dir):
    """Combine protocol and browser test results into a comprehensive report"""
    logger.info("🔗 Combining test results...")
    
    combined_report = {
        'test_metadata': {
            'site_name': config['target'],
            'test_timestamp': datetime.now().isoformat(),
            'test_duration': config.get('duration', config.get('distribution', {}).get('duration', '5m')),
            'virtual_users': config.get('vus', config.get('distribution', {}).get('total_vus', 0)),
            'description': config.get('description', ''),
            'tags': config.get('tags', []),
            'test_types': ['protocol', 'browser'],
            'output_directory': output_dir
        },
        'protocol_results': None,
        'browser_results': None,
        'combined_insights': []
    }
    
    # Load protocol results
    protocol_report_path = os.path.join(output_dir, "test_report.json")
    if os.path.exists(protocol_report_path):
        with open(protocol_report_path, 'r') as f:
            combined_report['protocol_results'] = json.load(f)
    
    # Load browser results
    browser_report_path = os.path.join(output_dir, "browser_analysis_report.json")
    if os.path.exists(browser_report_path):
        with open(browser_report_path, 'r') as f:
            combined_report['browser_results'] = json.load(f)
    
    # Generate combined insights
    insights = []
    
    if combined_report['protocol_results']:
        protocol_summary = combined_report['protocol_results']['test_summary']
        if protocol_summary['error_rate'] > 5:
            insights.append({
                'type': 'protocol',
                'severity': 'high',
                'issue': f"High error rate: {protocol_summary['error_rate']:.1f}%",
                'recommendation': "Investigate server-side issues and network connectivity"
            })
        
        if protocol_summary['average_response_time'] > 1000:
            insights.append({
                'type': 'protocol',
                'severity': 'medium',
                'issue': f"Slow response time: {protocol_summary['average_response_time']:.1f}ms",
                'recommendation': "Optimize server performance and database queries"
            })
    
    if combined_report['browser_results']:
        browser_summary = combined_report['browser_results']
        if browser_summary.get('overall_grade') == 'C':
            insights.append({
                'type': 'browser',
                'severity': 'high',
                'issue': "Poor Core Web Vitals performance",
                'recommendation': "Optimize front-end performance, reduce bundle sizes, implement lazy loading"
            })
    
    combined_report['combined_insights'] = insights
    
    # Save combined report
    combined_report_path = os.path.join(output_dir, "combined_test_report.json")
    with open(combined_report_path, 'w') as f:
        json.dump(combined_report, f, indent=2)
    
    logger.info(f"✅ Combined test report saved to: {combined_report_path}")
    return combined_report

def generate_technical_reports(config, output_dir):
    """Generate technical-only reports when AI analysis is disabled"""
    logger.info("📊 Generating technical-only reports...")
    
    # Create a technical summary report
    technical_report = {
        'test_configuration': config,
        'test_type': config.get('test_type', 'protocol'),
        'analysis_type': 'technical_only',
        'generated_at': datetime.now().isoformat(),
        'available_reports': []
    }
    
    # Check what reports are available
    available_files = []
    
    # Protocol data
    protocol_summary = os.path.join(output_dir, "protocol_summary.json")
    if os.path.exists(protocol_summary):
        available_files.append("protocol_summary.json")
    
    # Browser data
    browser_summary = os.path.join(output_dir, "browser_summary.json")
    if os.path.exists(browser_summary):
        available_files.append("browser_summary.json")
    
    browser_analysis = os.path.join(output_dir, "browser_analysis_report.json")
    if os.path.exists(browser_analysis):
        available_files.append("browser_analysis_report.json")
    
    # Page resource analysis
    page_resources = os.path.join(output_dir, "page_resource_analysis.json")
    if os.path.exists(page_resources):
        available_files.append("page_resource_analysis.json")
    
    # Enhanced performance analysis
    enhanced_analysis = os.path.join(output_dir, "enhanced_analysis_report.json")
    if os.path.exists(enhanced_analysis):
        available_files.append("enhanced_analysis_report.json")
    
    # Combined results
    combined_results = os.path.join(output_dir, "combined_test_report.json")
    if os.path.exists(combined_results):
        available_files.append("combined_test_report.json")
    
    technical_report['available_reports'] = available_files
    
    # Save technical summary
    technical_summary_path = os.path.join(output_dir, "technical_summary.json")
    with open(technical_summary_path, 'w') as f:
        json.dump(technical_report, f, indent=2)
    
    logger.info(f"✅ Technical summary saved to: {technical_summary_path}")
    logger.info(f"📋 Available reports: {', '.join(available_files)}")
    
    # Generate a simple HTML report for technical data
    generate_technical_html_report(technical_report, output_dir)
    
    return technical_report

def generate_technical_html_report(technical_report, output_dir):
    """Generate a simple HTML report for technical analysis data"""
    html = []
    
    # HTML Header
    html.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Technical Load Test Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        
        .file-list {
            list-style: none;
            padding: 0;
        }
        
        .file-list li {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">""")
    
    # Header
    html.append(f"""
        <div class="header">
            <h1>🔧 Technical Load Test Report</h1>
            <div>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>""")
    
    # Test Configuration
    config = technical_report.get('test_configuration', {})
    html.append(f"""
        <div class="card">
            <h2>🔧 Test Configuration</h2>
            <p><strong>Target URL:</strong> {config.get('target', 'N/A')}</p>
            <p><strong>Test Type:</strong> {technical_report.get('test_type', 'N/A')}</p>
            <p><strong>Virtual Users:</strong> {config.get('vus', 'N/A')}</p>
            <p><strong>Duration:</strong> {config.get('duration', 'N/A')}</p>
            <p><strong>Description:</strong> {config.get('description', 'N/A')}</p>
        </div>""")
    
    # Available Reports
    available_files = technical_report.get('available_reports', [])
    html.append("""
        <div class="card">
            <h2>📊 Available Technical Reports</h2>
            <p>This technical analysis includes the following data files:</p>
            <ul class="file-list">""")
    
    for file in available_files:
        html.append(f"<li>📄 {file}</li>")
    
    html.append("</ul></div>")
    
    # Analysis Type
    html.append("""
        <div class="card">
            <h2>🔍 Analysis Type</h2>
            <p><strong>Mode:</strong> Technical Analysis Only (No AI Insights)</p>
            <p>This report contains raw technical data and metrics from the load testing tools. 
            For AI-powered insights and recommendations, enable AI analysis in the configuration.</p>
        </div>""")
    
    # Footer
    html.append("""
        <div class="footer">
            <p>Generated by Load Testing & Optimization Agent</p>
            <p>Technical Analysis Mode - No AI insights included</p>
        </div>
    </div>
</body>
</html>""")
    
    # Write the HTML file
    html_path = os.path.join(output_dir, "technical_report.html")
    with open(html_path, 'w') as f:
        f.write(''.join(html))
    
    logger.info(f"✅ Technical HTML report generated: {html_path}")

def run_azure_distributed_test(config, output_dir):
    """
    Run distributed load test in Azure using multiple worker containers
    
    Args:
        config: Test configuration dictionary
        output_dir: Local output directory for results
        
    Returns:
        bool: True if test completed successfully
    """
    if not AZURE_INTEGRATION_AVAILABLE:
        logger.error("Azure integration not available. Install requirements-azure.txt")
        return False
    
    try:
        # Initialize Azure components
        azure_config = config.get('azure', {})
        if not azure_config:
            logger.error("Azure configuration not found in config file")
            return False
        
        azure_client = AzureClient(azure_config)
        workload_distributor = WorkloadDistributor(config)
        container_manager = ContainerManager(azure_client, workload_distributor)
        result_aggregator = ResultAggregator(azure_client)
        
        # Validate configuration
        if not workload_distributor.validate_configuration():
            logger.error("Invalid distribution configuration")
            return False
        
        # Generate run ID
        run_id = workload_distributor.generate_run_id()
        logger.info(f"Starting Azure distributed test with run ID: {run_id}")
        
        # Determine test types to run
        test_type = config.get('test_type', 'protocol')
        test_types = []
        if test_type in ['protocol', 'both']:
            test_types.append('protocol')
        if test_type in ['browser', 'both']:
            test_types.append('browser')
        
        all_container_names = []
        
        # Update global container tracking
        global active_containers
        active_containers = all_container_names
        
        # Run tests for each type
        for current_test_type in test_types:
            logger.info(f"=== Starting {current_test_type} distributed test ===")
            
            # Create worker containers
            container_names = asyncio.run(container_manager.create_workers(current_test_type, run_id))
            if not container_names:
                logger.error(f"Failed to create {current_test_type} worker containers")
                return False
            
            all_container_names.extend(container_names)
            active_containers = all_container_names  # Update global tracking
            logger.info(f"Created {len(container_names)} {current_test_type} worker containers")
            
            # Wait for containers to complete with timeout
            try:
                completion_status = asyncio.run(container_manager.wait_for_completion(container_names))
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for {current_test_type} containers to complete")
                # Clean up containers on timeout
                cleanup_status = container_manager.cleanup_containers(container_names)
                successful_cleanup = sum(1 for status in cleanup_status.values() if status)
                logger.info(f"Timeout cleanup: {successful_cleanup}/{len(cleanup_status)} containers")
                return False
            
            # Check completion status
            successful_containers = sum(1 for status in completion_status.values() if status)
            total_containers = len(completion_status)
            
            if successful_containers == 0:
                logger.error(f"All {current_test_type} containers failed")
                return False
            elif successful_containers < total_containers:
                logger.warning(f"Only {successful_containers}/{total_containers} {current_test_type} containers completed successfully")
            
            logger.info(f"=== {current_test_type} distributed test completed ===")
            
            # Clean up containers for this test type before starting the next one
            logger.info(f"=== Cleaning up {current_test_type} containers ===")
            cleanup_status = container_manager.cleanup_containers(container_names)
            successful_cleanup = sum(1 for status in cleanup_status.values() if status)
            logger.info(f"Cleaned up {successful_cleanup}/{len(cleanup_status)} {current_test_type} containers")
            
            # Wait a moment to ensure containers are fully terminated
            import time
            time.sleep(30)
        
        # Download and aggregate results
        logger.info("=== Downloading and aggregating results ===")
        
        for current_test_type in test_types:
            worker_count = workload_distributor.calculate_worker_count(current_test_type)
            
            # Download worker results
            downloaded_files = result_aggregator.download_worker_results(
                run_id, worker_count, current_test_type, output_dir
            )
            
            if not downloaded_files:
                logger.warning(f"No results downloaded for {current_test_type} test")
                continue
            
            # Aggregate summaries
            if current_test_type == 'browser':
                summary_files = [f for f in downloaded_files if 'playwright_results_' in f and f.endswith('.json')]
            else:
                summary_files = [f for f in downloaded_files if 'summary_' in f and f.endswith('.json')]
            if summary_files:
                aggregated_summary = result_aggregator.aggregate_summaries(summary_files, current_test_type)
                if aggregated_summary:
                    # Save aggregated summary locally
                    summary_path = os.path.join(output_dir, f"{current_test_type}_summary.json")
                    with open(summary_path, 'w') as f:
                        json.dump(aggregated_summary, f, indent=2)
                    
                    # Upload aggregated result back to Azure
                    result_aggregator.upload_aggregated_result(aggregated_summary, run_id, current_test_type)
                    
                    logger.info(f"✅ Aggregated {current_test_type} summary saved to {summary_path}")
                else:
                    logger.error(f"Failed to aggregate {current_test_type} summaries")
            else:
                logger.warning(f"No summary files found for {current_test_type} test")
        
        # Final cleanup (in case any containers are still running)
        logger.info("=== Final cleanup of any remaining Azure containers ===")
        if all_container_names:
            cleanup_status = container_manager.cleanup_containers(all_container_names)
            successful_cleanup = sum(1 for status in cleanup_status.values() if status)
            logger.info(f"Final cleanup: {successful_cleanup}/{len(cleanup_status)} containers")
        else:
            logger.info("No containers remaining for final cleanup")
        
        # Clear global container tracking
        active_containers.clear()
        
        logger.info("✅ Azure distributed test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Azure distributed test failed: {e}")
        # Clean up containers even on failure
        try:
            logger.info("=== Emergency cleanup of Azure containers ===")
            cleanup_status = container_manager.cleanup_containers(all_container_names)
            successful_cleanup = sum(1 for status in cleanup_status.values() if status)
            logger.info(f"Emergency cleanup: {successful_cleanup}/{len(cleanup_status)} containers")
        except Exception as cleanup_error:
            logger.error(f"Emergency cleanup failed: {cleanup_error}")
        return False

def main():
    """Main function to orchestrate the load test"""
    logger.info("=== Load Testing & Optimization Agent - Enhanced with Browser Testing ===")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Load Testing & Optimization Agent')
    parser.add_argument('config', nargs='?', default="configs/pop_website_test.yaml", 
                       help='Path to configuration file')
    parser.add_argument('--mode', choices=['local', 'azure'], default='local',
                       help='Test execution mode (local or azure)')
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = args.config
    config = load_config(config_path)
    test_type = config.get('test_type', 'protocol')
    analysis_settings = config.get('analysis_settings', {})
    
    logger.info(f"Test type: {test_type}")
    
    # Log analysis settings
    logger.info("=== Analysis Settings ===")
    logger.info(f"Page Resource Analysis: {'✅ Enabled' if analysis_settings.get('run_page_resource_analysis', True) else '❌ Disabled'}")
    logger.info(f"Enhanced Performance Analysis: {'✅ Enabled' if analysis_settings.get('run_enhanced_performance_analysis', True) else '❌ Disabled'}")
    logger.info(f"AI Analysis: {'✅ Enabled' if analysis_settings.get('run_ai_analysis', True) else '❌ Disabled'}")
    logger.info(f"Generate Readable Reports: {'✅ Enabled' if analysis_settings.get('generate_readable_reports', True) else '❌ Disabled'}")
    logger.info(f"Combine Results: {'✅ Enabled' if analysis_settings.get('combine_results', True) else '❌ Disabled'}")
    
    # Create output directory first
    output_dir = create_output_directory(config)
    
    # Run the appropriate test(s) based on mode
    if args.mode == 'azure':
        logger.info("🚀 Running in Azure distributed mode")
        success = run_azure_distributed_test(config, output_dir)
    else:
        logger.info("🏠 Running in local mode")
        success = run_k6_test(config, output_dir)
    
    if success:
        # Azure distributed tests already have their results aggregated by the Azure result aggregator
        # No additional aggregation needed here
        
        # Generate test report
        report = generate_test_report(config, output_dir)
        if report:
            logger.info("=== Test Summary ===")
            logger.info(f"Total Requests: {report['test_summary']['total_requests']}")
            logger.info(f"Failed Requests: {report['test_summary']['failed_requests']}")
            logger.info(f"Average Response Time: {report['test_summary']['average_response_time']:.2f}ms")
            logger.info(f"Error Rate: {report['test_summary']['error_rate']:.2f}%")
        
        # Run enhanced performance analysis for protocol tests
        if test_type in ['protocol', 'both']:
            logger.info("🔍 Running enhanced performance analysis...")
            try:
                protocol_summary_file = os.path.join(output_dir, "protocol_summary.json")
                if os.path.exists(protocol_summary_file):
                    result = subprocess.run([
                        'python', 'scripts/enhanced_performance_analyzer.py', protocol_summary_file
                    ], capture_output=True, text=True, timeout=120)
                    
                    if result.returncode == 0:
                        logger.info("✅ Enhanced performance analysis completed")
                        # Move the output to our test directory
                        if os.path.exists('enhanced_analysis_report.json'):
                            import shutil
                            shutil.move('enhanced_analysis_report.json', os.path.join(output_dir, 'enhanced_analysis_report.json'))
                    else:
                        logger.warning(f"⚠️ Enhanced performance analysis failed: {result.stderr}")
                else:
                    logger.warning(f"⚠️ Protocol summary file not found: {protocol_summary_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not run enhanced performance analysis: {e}")
        
        # Run browser analysis if applicable
        if test_type in ['browser', 'both']:
            browser_report = run_browser_analysis(config, output_dir)
            if browser_report:
                logger.info("=== Browser Analysis Complete ===")
                logger.info(f"Overall Grade: {browser_report.get('overall_grade', 'N/A')}")
                logger.info(f"Core Web Vitals Tested: {browser_report.get('summary', {}).get('core_vitals_tested', 0)}")
        
        # Run AI Analysis (if enabled)
        ai_report = run_ai_analysis(config, output_dir)
        if ai_report:
            logger.info("=== AI Analysis Complete ===")
            logger.info(f"Performance Grade: {ai_report['performance_analysis']['performance_grade']}")
            logger.info(f"Overall Score: {ai_report['performance_analysis']['overall_score']:.1f}/100")
            logger.info(f"Recommendations: {len(ai_report['recommendations'])} generated")
        elif analysis_settings.get('run_ai_analysis', True) == False:
            logger.info("=== AI Analysis Skipped ===")
            logger.info("AI analysis was disabled in configuration")
        
        # Combine results if both tests were run
        if test_type == 'both' and analysis_settings.get('combine_results', True):
            combined_report = combine_test_results(config, output_dir)
            if combined_report:
                logger.info("=== Combined Analysis Complete ===")
                logger.info(f"Combined Insights: {len(combined_report['combined_insights'])} generated")
        
        # Generate readable reports (if enabled)
        if analysis_settings.get('generate_readable_reports', True):
            logger.info("📄 Generating readable reports...")
            try:
                # Generate comprehensive HTML report with enhanced metrics and Plotly visualizations
                logger.info("📊 Generating comprehensive HTML report with enhanced metrics...")
                try:
                    result = subprocess.run([
                        "python", "scripts/generate_k6_html_report.py", output_dir
                    ], capture_output=True, text=True, timeout=120)
                    
                    if result.returncode == 0:
                        logger.info("✅ Comprehensive HTML report generated successfully")
                        logger.info("📊 HTML report: load_test_report.html")
                    else:
                        logger.warning("⚠️  Comprehensive HTML report generation failed")
                        if result.stderr:
                            logger.warning(f"Error: {result.stderr}")
                        
                        # Fallback to readable reports if comprehensive report fails
                        logger.info("📄 Falling back to readable reports...")
                        ai_report_path = os.path.join(output_dir, "enhanced_ai_analysis_report.json")
                        if os.path.exists(ai_report_path):
                            result = subprocess.run([
                                "python", "scripts/generate_readable_report.py", ai_report_path
                            ], capture_output=True, text=True, timeout=60)
                            
                            if result.returncode == 0:
                                logger.info("✅ Readable reports generated successfully")
                                logger.info("📊 HTML report: ai_analysis_report.html")
                                logger.info("📝 Markdown report: ai_analysis_report.md")
                            else:
                                logger.warning("⚠️  Readable report generation failed")
                                if result.stderr:
                                    logger.warning(f"Error: {result.stderr}")
                        else:
                            logger.info("📄 No AI analysis report found - generating technical reports only")
                            # Generate technical-only reports
                            generate_technical_reports(config, output_dir)
                except Exception as e:
                    logger.warning(f"⚠️  Error generating comprehensive HTML report: {e}")
                    # Fallback to readable reports
                    logger.info("📄 Falling back to readable reports...")
                    ai_report_path = os.path.join(output_dir, "enhanced_ai_analysis_report.json")
                    if os.path.exists(ai_report_path):
                        result = subprocess.run([
                            "python", "scripts/generate_readable_report.py", ai_report_path
                        ], capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0:
                            logger.info("✅ Readable reports generated successfully")
                            logger.info("📊 HTML report: ai_analysis_report.html")
                            logger.info("📝 Markdown report: ai_analysis_report.md")
                        else:
                            logger.warning("⚠️  Readable report generation failed")
                            if result.stderr:
                                logger.warning(f"Error: {result.stderr}")
                    else:
                        logger.info("📄 No AI analysis report found - generating technical reports only")
                        # Generate technical-only reports
                        generate_technical_reports(config, output_dir)
            except Exception as e:
                logger.warning(f"⚠️  Error generating readable reports: {e}")
        
        logger.info("Load test completed successfully!")
        logger.info(f"📁 Results saved to: {output_dir}")
        logger.info(f"🔗 Latest results: output/{config['target'].replace('https://', '').replace('http://', '').replace('.', '_')}/latest")
    else:
        logger.error("Load test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
