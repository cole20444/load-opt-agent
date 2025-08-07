#!/usr/bin/env python3
"""
List Test Results
Helps users navigate and find their test results in the organized output structure
"""

import os
import json
from datetime import datetime
from pathlib import Path

def list_test_results():
    """List all test results organized by site and timestamp"""
    output_dir = Path("output")
    
    if not output_dir.exists():
        print("❌ No test results found. Run a test first using: python run_test.py")
        return
    
    print("📊 Test Results Directory Structure")
    print("=" * 50)
    
    # List all sites
    sites = [d for d in output_dir.iterdir() if d.is_dir()]
    
    if not sites:
        print("❌ No test results found. Run a test first using: python run_test.py")
        return
    
    for site_dir in sorted(sites):
        site_name = site_dir.name
        print(f"\n🌐 Site: {site_name}")
        print("-" * 30)
        
        # Check for latest symlink
        latest_link = site_dir / "latest"
        if latest_link.exists():
            latest_target = os.readlink(latest_link)
            print(f"🔗 Latest: {latest_target}")
        
        # List all test runs
        test_runs = [d for d in site_dir.iterdir() if d.is_dir() and d.name != "latest"]
        
        if not test_runs:
            print("  No test runs found")
            continue
        
        for test_run in sorted(test_runs, reverse=True):  # Most recent first
            timestamp = test_run.name
            test_run_path = test_run
            
            # Try to parse timestamp
            try:
                dt = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                formatted_time = timestamp
            
            print(f"  📅 {formatted_time}")
            
            # Check what files are available
            files = list(test_run_path.glob("*.json"))
            if files:
                print(f"    📄 Files: {', '.join([f.name for f in files])}")
            
            # Try to read test report for summary
            test_report = test_run_path / "test_report.json"
            if test_report.exists():
                try:
                    with open(test_report, 'r') as f:
                        report_data = json.load(f)
                    
                    summary = report_data.get('test_summary', {})
                    metadata = report_data.get('test_metadata', {})
                    
                    print(f"    📊 Requests: {summary.get('total_requests', 'N/A')}")
                    print(f"    ⏱️  Avg Response: {summary.get('average_response_time', 0):.0f}ms")
                    print(f"    ❌ Error Rate: {summary.get('error_rate', 0):.2f}%")
                    print(f"    👥 VUs: {metadata.get('virtual_users', 'N/A')}")
                    print(f"    ⏰ Duration: {metadata.get('test_duration', 'N/A')}")
                    
                except Exception as e:
                    print(f"    ⚠️  Could not read test report: {e}")
            
            print()

def show_latest_results(site_name=None):
    """Show the latest test results for a specific site or all sites"""
    output_dir = Path("output")
    
    if not output_dir.exists():
        print("❌ No test results found. Run a test first using: python run_test.py")
        return
    
    if site_name:
        # Show latest for specific site
        site_dir = output_dir / site_name
        if not site_dir.exists():
            print(f"❌ No test results found for site: {site_name}")
            return
        
        latest_link = site_dir / "latest"
        if not latest_link.exists():
            print(f"❌ No latest results found for site: {site_name}")
            return
        
        show_test_run_details(latest_link)
    else:
        # Show latest for all sites
        sites = [d for d in output_dir.iterdir() if d.is_dir()]
        
        for site_dir in sorted(sites):
            site_name = site_dir.name
            latest_link = site_dir / "latest"
            
            if latest_link.exists():
                print(f"\n🌐 Latest Results for: {site_name}")
                print("=" * 40)
                show_test_run_details(latest_link)

def show_test_run_details(test_run_path):
    """Show detailed information about a specific test run"""
    if not test_run_path.exists():
        print(f"❌ Test run not found: {test_run_path}")
        return
    
    # Show test report
    test_report = test_run_path / "test_report.json"
    if test_report.exists():
        try:
            with open(test_report, 'r') as f:
                report_data = json.load(f)
            
            metadata = report_data.get('test_metadata', {})
            summary = report_data.get('test_summary', {})
            metrics = report_data.get('performance_metrics', {})
            
            print(f"📅 Test Date: {metadata.get('test_timestamp', 'N/A')}")
            print(f"🌐 Target: {metadata.get('site_name', 'N/A')}")
            print(f"👥 Virtual Users: {metadata.get('virtual_users', 'N/A')}")
            print(f"⏰ Duration: {metadata.get('test_duration', 'N/A')}")
            print(f"📝 Description: {metadata.get('description', 'N/A')}")
            print(f"🏷️  Tags: {', '.join(metadata.get('tags', []))}")
            
            print(f"\n📊 Performance Summary:")
            print(f"  📈 Total Requests: {summary.get('total_requests', 'N/A')}")
            print(f"  ✅ Successful: {summary.get('successful_requests', 'N/A')}")
            print(f"  ❌ Failed: {summary.get('failed_requests', 'N/A')}")
            print(f"  ⏱️  Avg Response Time: {summary.get('average_response_time', 0):.0f}ms")
            print(f"  📊 Error Rate: {summary.get('error_rate', 0):.2f}%")
            
            # Show detailed metrics if available
            if metrics:
                duration = metrics.get('http_req_duration', {})
                if duration:
                    print(f"\n⏱️  Response Time Details:")
                    print(f"  📊 Average: {duration.get('avg', 0):.0f}ms")
                    print(f"  📉 Minimum: {duration.get('min', 0):.0f}ms")
                    print(f"  📈 Maximum: {duration.get('max', 0):.0f}ms")
            
        except Exception as e:
            print(f"⚠️  Could not read test report: {e}")
    
    # List all files in the test run
    files = list(test_run_path.glob("*.json"))
    if files:
        print(f"\n📄 Available Files:")
        for file in files:
            size = file.stat().st_size
            size_str = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
            print(f"  📄 {file.name} ({size_str})")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "latest":
            site_name = sys.argv[2] if len(sys.argv) > 2 else None
            show_latest_results(site_name)
        elif command == "list":
            list_test_results()
        elif command == "help":
            print("""
📊 Test Results Navigator

Usage:
  python scripts/list_test_results.py list          # List all test results
  python scripts/list_test_results.py latest        # Show latest results for all sites
  python scripts/list_test_results.py latest <site> # Show latest results for specific site
  python scripts/list_test_results.py help          # Show this help

Examples:
  python scripts/list_test_results.py list
  python scripts/list_test_results.py latest
  python scripts/list_test_results.py latest pop-website-2024-dev_azurewebsites_net
            """)
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'help' to see available commands")
    else:
        # Default: show latest results
        show_latest_results()

if __name__ == "__main__":
    main() 