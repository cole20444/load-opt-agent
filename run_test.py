#!/usr/bin/env python3
"""
Load Testing & Optimization Agent - Phase 1
Python runner for k6 load tests with YAML configuration
"""

import subprocess
import yaml
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Import AI Analysis components
try:
    from ai_analysis.analysis_agent import AIAnalysisAgent
    AI_ANALYSIS_AVAILABLE = True
except ImportError:
    AI_ANALYSIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("AI Analysis not available - skipping optimization recommendations")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load and validate YAML configuration file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        required_fields = ['target', 'vus', 'duration']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate data types
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
        os.remove(latest_dir)
    os.symlink(timestamp, latest_dir)
    
    logger.info(f"📁 Created output directory: {output_dir}")
    logger.info(f"🔗 Latest results available at: {latest_dir}")
    
    return output_dir

def run_k6_test(config):
    """Run k6 load test with the provided configuration"""
    try:
        # Ensure output directory exists
        output_dir = create_output_directory(config)
        
        # Prepare environment variables
        env_vars = {
            "TARGET_URL": config["target"],
            "VUS": str(config["vus"]),
            "DURATION": config["duration"]
        }
        
        # Build Docker command
        command = [
            "docker", "run", "--rm",
            "-e", f"TARGET_URL={env_vars['TARGET_URL']}",
            "-e", f"VUS={env_vars['VUS']}",
            "-e", f"DURATION={env_vars['DURATION']}",
            "-v", f"{os.getcwd()}/{output_dir}:/app/output",
            "load-tester"
        ]
        
        logger.info(f"Starting k6 load test with command: {' '.join(command)}")
        logger.info(f"Target: {config['target']}")
        logger.info(f"Virtual Users: {config['vus']}")
        logger.info(f"Duration: {config['duration']}")
        
        # Run the Docker container
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logger.info("Load test completed successfully")
            if result.stdout:
                logger.info(f"Test output: {result.stdout}")
        else:
            logger.error(f"Load test failed with return code: {result.returncode}")
            if result.stderr:
                logger.error(f"Error output: {result.stderr}")
            if result.stdout:
                logger.info(f"Standard output: {result.stdout}")
            return False
            
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Load test timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Unexpected error running load test: {e}")
        return False

def build_docker_image():
    """Build the Docker image if it doesn't exist"""
    try:
        # Check if image exists
        result = subprocess.run(
            ["docker", "images", "-q", "load-tester"],
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            logger.info("Building Docker image...")
            build_result = subprocess.run(
                ["docker", "build", "-t", "load-tester", "-f", "docker/Dockerfile", "."],
                capture_output=True,
                text=True
            )
            
            if build_result.returncode != 0:
                logger.error(f"Failed to build Docker image: {build_result.stderr}")
                return False
            else:
                logger.info("Docker image built successfully")
        else:
            logger.info("Docker image already exists")
            
        return True
        
    except Exception as e:
        logger.error(f"Error building Docker image: {e}")
        return False

def generate_test_report(config, output_dir):
    """Generate a comprehensive test report with metadata"""
    import json
    from datetime import datetime
    
    # Load test results
    summary_path = os.path.join(output_dir, "summary.json")
    if not os.path.exists(summary_path):
        logger.error(f"Summary file not found: {summary_path}")
        return None
    
    try:
        # Parse k6 summary data
        metrics_data = []
        with open(summary_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') == 'Point':
                        metrics_data.append(data)
                except json.JSONDecodeError:
                    continue
        
        # Calculate key metrics
        http_req_duration = []
        http_req_failed = []
        http_reqs = []
        response_size = []
        
        for data in metrics_data:
            metric = data.get('metric', '')
            value = data.get('data', {}).get('value', 0)
            
            if metric == 'http_req_duration':
                http_req_duration.append(value)
            elif metric == 'http_req_failed':
                http_req_failed.append(value)
            elif metric == 'http_reqs':
                http_reqs.append(value)
            elif metric == 'response_size':
                response_size.append(value)
        
        # Calculate statistics
        def calculate_stats(values):
            if not values:
                return {"avg": 0, "min": 0, "max": 0}
            return {
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
        
        # Create test report
        test_report = {
            "test_metadata": {
                "site_name": config.get('target', 'Unknown'),
                "test_timestamp": datetime.now().isoformat(),
                "test_duration": config.get('duration', 'Unknown'),
                "virtual_users": config.get('vus', 'Unknown'),
                "description": config.get('description', 'No description'),
                "tags": config.get('tags', []),
                "output_directory": output_dir
            },
            "performance_metrics": {
                "http_req_duration": calculate_stats(http_req_duration),
                "http_req_failed": {"rate": sum(http_req_failed) / len(http_req_failed) if http_req_failed else 0},
                "http_reqs": {
                    "rate": sum(http_reqs) / len(http_reqs) if http_reqs else 0,
                    "count": len(http_req_duration) if http_req_duration else 0
                },
                "response_size": calculate_stats(response_size)
            },
            "test_summary": {
                "total_requests": len(http_req_duration) if http_req_duration else 0,
                "successful_requests": len([x for x in http_req_failed if x == 0]) if http_req_failed else 0,
                "failed_requests": len([x for x in http_req_failed if x > 0]) if http_req_failed else 0,
                "average_response_time": calculate_stats(http_req_duration)["avg"],
                "error_rate": (sum(http_req_failed) / len(http_req_failed) * 100) if http_req_failed else 0
            }
        }
        
        # Save test report
        report_path = os.path.join(output_dir, "test_report.json")
        with open(report_path, 'w') as f:
            json.dump(test_report, f, indent=2)
        
        logger.info(f"📊 Test report generated: {report_path}")
        return test_report
        
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        return None

def run_ai_analysis(config, output_dir):
    """Run AI analysis with ALL available data"""
    logger.info("=== Running Enhanced AI Analysis ===")
    
    try:
        # Import the enhanced AI analysis agent
        from ai_analysis.openai_enhanced_agent import EnhancedAIAnalysisAgent
        
        # Initialize the enhanced agent
        agent = EnhancedAIAnalysisAgent()
        
        # Run page resource analysis first
        logger.info("Running page resource analysis...")
        try:
            import subprocess
            result = subprocess.run([
                'python', 'scripts/page_resource_analyzer.py', config['target']
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✅ Page resource analysis completed")
            else:
                logger.warning(f"⚠️ Page resource analysis failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"⚠️ Could not run page resource analysis: {e}")
        
        # Run enhanced performance analysis
        logger.info("Running enhanced performance analysis...")
        try:
            result = subprocess.run([
                'python', 'scripts/enhanced_performance_analyzer.py'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✅ Enhanced performance analysis completed")
            else:
                logger.warning(f"⚠️ Enhanced performance analysis failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"⚠️ Could not run enhanced performance analysis: {e}")
        
        # Now run the comprehensive AI analysis with ALL data
        logger.info("Running comprehensive AI analysis...")
        test_report_path = os.path.join(output_dir, "test_report.json")
        
        if not os.path.exists(test_report_path):
            logger.error(f"Test report not found: {test_report_path}")
            return None
        
        # Run the enhanced analysis that includes ALL available data
        analysis_result = agent.analyze_test_results(test_report_path, config)
        
        if analysis_result:
            # Save the comprehensive analysis report
            ai_report_path = os.path.join(output_dir, "ai_analysis_report.json")
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

def main():
    """Main function to orchestrate the load test"""
    logger.info("=== Load Testing & Optimization Agent - Phase 1 ===")
    
    # Load configuration
    config_path = "configs/test_config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    config = load_config(config_path)
    
    # Build Docker image
    if not build_docker_image():
        logger.error("Failed to build Docker image. Exiting.")
        sys.exit(1)
    
    # Run the load test
    success = run_k6_test(config)
    
    if success:
        # Generate test report
        output_dir = create_output_directory(config)
        report = generate_test_report(config, output_dir)
        if report:
            logger.info("=== Test Summary ===")
            logger.info(f"Total Requests: {report['test_summary']['total_requests']}")
            logger.info(f"Failed Requests: {report['test_summary']['failed_requests']}")
            logger.info(f"Average Response Time: {report['test_summary']['average_response_time']:.2f}ms")
            logger.info(f"Error Rate: {report['test_summary']['error_rate']:.2f}%")
        
        # Run AI Analysis
        ai_report = run_ai_analysis(config, output_dir)
        if ai_report:
            logger.info("=== AI Analysis Complete ===")
            logger.info(f"Performance Grade: {ai_report['performance_analysis']['performance_grade']}")
            logger.info(f"Overall Score: {ai_report['performance_analysis']['overall_score']:.1f}/100")
            logger.info(f"Recommendations: {len(ai_report['recommendations'])} generated")
        
        logger.info("Load test completed successfully!")
        logger.info(f"📁 Results saved to: {output_dir}")
        logger.info(f"🔗 Latest results: output/{config['target'].replace('https://', '').replace('http://', '').replace('.', '_')}/latest")
    else:
        logger.error("Load test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
