#!/usr/bin/env python3
"""
Test script for OpenAI integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_analysis.openai_enhanced_agent import OpenAIEnhancedAnalysis, EnhancedAIAnalysisAgent
import yaml
import json

def test_openai_availability():
    """Test if OpenAI is available"""
    print("Testing OpenAI Availability...")
    
    # Check if OpenAI package is installed
    try:
        from openai import OpenAI
        print("✅ OpenAI package is installed")
    except ImportError:
        print("❌ OpenAI package not installed")
        print("   Install with: pip install openai")
        return False
    
    # Check if API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ OPENAI_API_KEY is set")
        return True
    else:
        print("⚠️  OPENAI_API_KEY not set")
        print("   Set it with: export OPENAI_API_KEY='your-api-key'")
        return False

def test_openai_enhanced_analysis():
    """Test OpenAI enhanced analysis"""
    print("\nTesting OpenAI Enhanced Analysis...")
    
    # Create sample data
    performance_data = {
        "metrics_analysis": {
            "response_time": {"value": 553.39, "grade": "C"},
            "error_rate": {"value": 0.0, "grade": "A"},
            "throughput": {"value": 15.9, "grade": "C"}
        },
        "test_summary": {
            "duration": "2m",
            "virtual_users": 25,
            "total_requests": 1934
        }
    }
    
    site_config = {
        "target": "https://pop-website-2024-dev.azurewebsites.net",
        "description": "Frontend is built with Svelte and the Backend is built with Strapi.",
        "tags": ["svelte", "strapi", "azure", "app-service", "headless-cms", "javascript", "api-driven"]
    }
    
    # Test OpenAI analysis
    openai_analysis = OpenAIEnhancedAnalysis()
    insights = openai_analysis.generate_ai_insights(performance_data, site_config)
    
    if insights.get("ai_insights") and "OpenAI not available" not in insights.get("ai_insights", ""):
        print("✅ OpenAI analysis completed successfully!")
        print(f"   AI Insights: {len(insights.get('ai_insights', ''))} characters")
        print(f"   AI Recommendations: {len(insights.get('ai_recommendations', []))}")
        return True
    else:
        print(f"❌ OpenAI analysis failed: {insights.get('ai_insights', 'Unknown error')}")
        return False

def test_enhanced_agent():
    """Test the full enhanced agent"""
    print("\nTesting Enhanced AI Agent...")
    
    # Create sample test results
    sample_results = {
        "http_req_duration": {"avg": 553.39, "min": 426.74, "max": 2185.61},
        "http_req_failed": {"rate": 0.0},
        "http_reqs": {"rate": 15.9, "count": 1934},
        "response_size": {"avg": 76051}
    }
    
    # Save sample results
    with open("output/test_report.json", "w") as f:
        json.dump(sample_results, f)
    
    # Load config
    config = {
        "target": "https://pop-website-2024-dev.azurewebsites.net",
        "description": "Frontend is built with Svelte and the Backend is built with Strapi.",
        "tags": ["svelte", "strapi", "azure", "app-service", "headless-cms", "javascript", "api-driven"]
    }
    
    # Run enhanced analysis
    agent = EnhancedAIAnalysisAgent()
    report = agent.analyze_test_results("output/test_report.json", config)
    
    if report and "error" not in report:
        print("✅ Enhanced AI Agent completed successfully!")
        print(f"   Analysis Method: {report.get('analysis_method', 'Unknown')}")
        print(f"   Total Recommendations: {len(report.get('recommendations', []))}")
        
        # Count AI recommendations
        ai_recommendations = [r for r in report.get('recommendations', []) if r.get('source') == 'AI Analysis']
        print(f"   AI Recommendations: {len(ai_recommendations)}")
        
        return True
    else:
        print(f"❌ Enhanced AI Agent failed: {report.get('error', 'Unknown error')}")
        return False

def main():
    """Run all tests"""
    print("=== OpenAI Integration Test Suite ===\n")
    
    tests = [
        ("OpenAI Availability", test_openai_availability),
        ("OpenAI Enhanced Analysis", test_openai_enhanced_analysis),
        ("Enhanced AI Agent", test_enhanced_agent)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All OpenAI integration tests passed!")
        print("\nNext steps:")
        print("1. Run a load test with enhanced AI analysis")
        print("2. Check output/enhanced_ai_analysis_report.json for AI insights")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTo enable OpenAI analysis:")
        print("1. Install OpenAI: pip install openai")
        print("2. Set API key: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

if __name__ == "__main__":
    main() 