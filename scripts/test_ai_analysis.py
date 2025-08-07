#!/usr/bin/env python3
"""
Test script for AI Analysis functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_analysis.analysis_agent import AIAnalysisAgent, TechnologyTemplateManager, PerformanceAnalyzer
import yaml
import json

def test_template_manager():
    """Test technology template manager"""
    print("Testing Technology Template Manager...")
    
    manager = TechnologyTemplateManager()
    
    # Test with POP website tags
    pop_tags = ["svelte", "strapi", "azure", "app-service", "headless-cms", "javascript", "api-driven"]
    template = manager.select_template(pop_tags)
    
    if template:
        print(f"✅ Selected template: {template['name']}")
        print(f"   Tags: {template['tags']}")
        return True
    else:
        print("❌ No template selected")
        return False

def test_performance_analyzer():
    """Test performance analyzer"""
    print("\nTesting Performance Analyzer...")
    
    analyzer = PerformanceAnalyzer()
    
    # Test with sample metrics
    sample_metrics = {
        "http_req_duration": {"avg": 553.39},
        "http_req_failed": {"rate": 0.0},
        "http_reqs": {"rate": 15.9}
    }
    
    analysis = analyzer.analyze_metrics(sample_metrics)
    
    print(f"✅ Performance Grade: {analysis['performance_grade']}")
    print(f"   Overall Score: {analysis['overall_score']:.1f}/100")
    
    for metric, data in analysis['metrics_analysis'].items():
        print(f"   {metric}: {data['grade']} - {data['insight']}")
    
    return True

def test_ai_agent():
    """Test full AI analysis agent"""
    print("\nTesting AI Analysis Agent...")
    
    # Load sample config
    config = {
        "target": "https://pop-website-2024-dev.azurewebsites.net",
        "description": "Frontend is built with Svelte and the Backend is built with Strapi.",
        "tags": ["svelte", "strapi", "azure", "app-service", "headless-cms", "javascript", "api-driven"]
    }
    
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
    
    # Run analysis
    agent = AIAnalysisAgent()
    report = agent.analyze_test_results("output/test_report.json", config)
    
    if report and "error" not in report:
        print("✅ AI Analysis completed successfully!")
        print(f"   Technology Template: {report['technology_template']}")
        print(f"   Performance Grade: {report['performance_analysis']['performance_grade']}")
        print(f"   Recommendations: {len(report['recommendations'])}")
        
        # Show top recommendations
        for i, rec in enumerate(report['recommendations'][:3]):
            print(f"   {i+1}. {rec['title']} ({rec['priority']} priority)")
        
        return True
    else:
        print(f"❌ AI Analysis failed: {report.get('error', 'Unknown error')}")
        return False

def main():
    """Run all tests"""
    print("=== AI Analysis Test Suite ===\n")
    
    tests = [
        ("Template Manager", test_template_manager),
        ("Performance Analyzer", test_performance_analyzer),
        ("AI Agent", test_ai_agent)
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
        print("✅ All AI Analysis tests passed!")
        print("\nNext steps:")
        print("1. Run a load test to see AI analysis in action")
        print("2. Check output/ai_analysis_report.json for detailed recommendations")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 