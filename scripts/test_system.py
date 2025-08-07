#!/usr/bin/env python3
"""
System test script to verify all components are working correctly
"""

import os
import sys
import yaml
import subprocess
from pathlib import Path

def test_yaml_parsing():
    """Test YAML configuration parsing"""
    print("Testing YAML configuration parsing...")
    
    try:
        with open("examples/test_config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        required_fields = ['target', 'vus', 'duration']
        for field in required_fields:
            if field not in config:
                print(f"❌ Missing required field: {field}")
                return False
        
        print(f"✅ YAML parsing successful: {config}")
        return True
        
    except Exception as e:
        print(f"❌ YAML parsing failed: {e}")
        return False

def test_docker_availability():
    """Test if Docker is available"""
    print("Testing Docker availability...")
    
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Docker available: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Docker not available: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Docker not found in PATH")
        return False

def test_file_structure():
    """Test if all required files exist"""
    print("Testing file structure...")
    
    required_files = [
        "docker/Dockerfile",
        "tests/load_test.js",
        "run_test.py",
        "requirements.txt",
        "examples/test_config.yaml"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_exist = False
    
    return all_exist

def test_python_dependencies():
    """Test if Python dependencies can be imported"""
    print("Testing Python dependencies...")
    
    try:
        import yaml
        print("✅ PyYAML imported successfully")
        return True
    except ImportError as e:
        print(f"❌ PyYAML import failed: {e}")
        return False

def main():
    """Run all system tests"""
    print("=== Load Testing System Verification ===\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Dependencies", test_python_dependencies),
        ("YAML Parsing", test_yaml_parsing),
        ("Docker Availability", test_docker_availability),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        print()
    
    print("=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Run: python run_test.py")
        print("2. Check output/ directory for results")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 