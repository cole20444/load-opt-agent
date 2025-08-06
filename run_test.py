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

def ensure_output_directory():
    """Ensure output directory exists"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    return output_dir

def run_k6_test(config):
    """Run k6 load test with the provided configuration"""
    try:
        # Ensure output directory exists
        output_dir = ensure_output_directory()
        
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
            "-v", f"{os.getcwd()}/output:/output",
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

def generate_test_report():
    """Generate a summary report from the test results"""
    try:
        summary_file = Path("output/summary.json")
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            # Create a human-readable report
            report = {
                "timestamp": datetime.now().isoformat(),
                "test_summary": {
                    "total_requests": summary.get("metrics", {}).get("http_reqs", {}).get("count", 0),
                    "failed_requests": summary.get("metrics", {}).get("http_req_failed", {}).get("rate", 0),
                    "average_response_time": summary.get("metrics", {}).get("http_req_duration", {}).get("avg", 0),
                    "p95_response_time": summary.get("metrics", {}).get("http_req_duration", {}).get("p(95)", 0),
                    "requests_per_second": summary.get("metrics", {}).get("http_reqs", {}).get("rate", 0),
                },
                "thresholds": summary.get("thresholds", {}),
                "raw_summary": summary
            }
            
            # Save the report
            report_file = Path("output/test_report.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Test report generated: {report_file}")
            return report
            
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        return None

def main():
    """Main function to orchestrate the load test"""
    logger.info("=== Load Testing & Optimization Agent - Phase 1 ===")
    
    # Load configuration
    config_path = "examples/test_config.yaml"
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
        report = generate_test_report()
        if report:
            logger.info("=== Test Summary ===")
            logger.info(f"Total Requests: {report['test_summary']['total_requests']}")
            logger.info(f"Failed Requests Rate: {report['test_summary']['failed_requests']:.2%}")
            logger.info(f"Average Response Time: {report['test_summary']['average_response_time']:.2f}ms")
            logger.info(f"P95 Response Time: {report['test_summary']['p95_response_time']:.2f}ms")
            logger.info(f"Requests/Second: {report['test_summary']['requests_per_second']:.2f}")
        
        logger.info("Load test completed successfully!")
    else:
        logger.error("Load test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
