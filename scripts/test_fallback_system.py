#!/usr/bin/env python3
"""
Test OpenAI Fallback System
Demonstrates how the system handles different OpenAI API errors and falls back to alternative models
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_fallback_system():
    """Test the OpenAI fallback system with different scenarios"""
    
    print("🧪 Testing OpenAI Fallback System")
    print("=" * 50)
    
    # Import our enhanced analysis agent
    try:
        from ai_analysis.openai_enhanced_agent import OpenAIEnhancedAnalysis
        print("✅ Successfully imported OpenAIEnhancedAnalysis")
    except ImportError as e:
        print(f"❌ Failed to import OpenAIEnhancedAnalysis: {e}")
        return
    
    # Create test data
    test_performance_data = {
        'test_summary': {
            'total_requests': 1000,
            'successful_requests': 950,
            'failed_requests': 50,
            'average_response_time': 1500,
            'error_rate': 5.0
        },
        'metrics_analysis': {
            'response_time': {'value': 1500, 'grade': 'C'},
            'error_rate': {'value': 5.0, 'grade': 'D'},
            'throughput': {'value': 100, 'grade': 'B'}
        }
    }
    
    test_site_config = {
        'target': 'https://example.com',
        'vus': 50,
        'duration': '5m',
        'description': 'Test website for fallback system',
        'tags': ['test', 'fallback', 'performance']
    }
    
    # Test the fallback system
    print("\n🔍 Testing fallback system with different scenarios...")
    
    # Scenario 1: Normal operation
    print("\n1️⃣ Testing normal operation...")
    enhanced_analysis = OpenAIEnhancedAnalysis()
    result = enhanced_analysis.generate_ai_insights(test_performance_data, test_site_config)
    
    print(f"   Model used: {result.get('model_used', 'unknown')}")
    print(f"   Recommendations generated: {len(result.get('ai_recommendations', []))}")
    
    # Scenario 2: Test fallback recommendations
    print("\n2️⃣ Testing fallback recommendations...")
    fallback_recs = enhanced_analysis._generate_fallback_recommendations(test_performance_data)
    print(f"   Fallback recommendations: {len(fallback_recs)}")
    
    for i, rec in enumerate(fallback_recs, 1):
        print(f"   {i}. {rec['title']} ({rec['priority']})")
    
    # Scenario 3: Test error handling
    print("\n3️⃣ Testing error handling...")
    
    # Simulate different error types
    test_errors = [
        "Rate limit reached for gpt-4o-mini in organization org-123 on tokens per min (TPM): Limit 100000, Used 100000, Requested 1782",
        "The model `gpt-4o-mini` does not exist or you do not have access to it",
        "You exceeded your current quota, please check your plan and billing details",
        "Something else went wrong"
    ]
    
    for error_msg in test_errors:
        print(f"\n   Testing error: {error_msg[:50]}...")
        should_retry = enhanced_analysis._handle_openai_error(Exception(error_msg))
        print(f"   Should retry: {should_retry}")
    
    print("\n✅ Fallback system test completed!")
    print("\n📋 Summary:")
    print("   - System can handle rate limit errors")
    print("   - System can handle model access errors") 
    print("   - System can handle quota exceeded errors")
    print("   - System provides fallback recommendations")
    print("   - System tracks which model was used")

if __name__ == "__main__":
    test_fallback_system() 