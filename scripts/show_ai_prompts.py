#!/usr/bin/env python3
"""
Script to show the actual AI prompts being generated and sent to OpenAI
"""

import yaml
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_analysis.openai_enhanced_agent import OpenAIEnhancedAnalysis

def show_generated_prompts():
    """Show the actual prompts being generated for AI analysis"""
    
    print("=== Actual AI Prompts Generated for OpenAI ===\n")
    
    # Create the same data that would be used in a real analysis
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
        "description": "Frontend is built with Svelte and the Backend is built with Strapi. The frontend application gets its data from the strapi api. This app is an App Service that lives on azure.",
        "tags": ["svelte", "strapi", "azure", "app-service", "headless-cms", "javascript", "api-driven"]
    }
    
    # Load the technology template
    with open("ai_analysis/technology_templates.yaml", 'r') as f:
        templates = yaml.safe_load(f)
    
    template = templates['templates']['svelte_strapi_azure']
    
    # Create the OpenAI analysis instance
    openai_analysis = OpenAIEnhancedAnalysis()
    
    # Generate the prompt (this is what gets sent to OpenAI)
    prompt = openai_analysis._build_ai_prompt(performance_data, site_config, template)
    
    print("🤖 PROMPT SENT TO OPENAI GPT-4o-mini:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    
    print(f"\n📊 PROMPT STATISTICS:")
    print(f"   Total Characters: {len(prompt)}")
    print(f"   Total Words: {len(prompt.split())}")
    print(f"   Template Patterns Included: {len(template.get('performance_patterns', {}))}")
    
    # Count recommendations in template
    total_recommendations = 0
    for category, patterns in template.get('performance_patterns', {}).items():
        for pattern in patterns:
            total_recommendations += len(pattern.get('recommendations', []))
    
    print(f"   Template Recommendations Available: {total_recommendations}")
    
    print(f"\n🔍 PROMPT BREAKDOWN:")
    print(f"   Site Information: ~{len(site_config.get('description', ''))} chars")
    print(f"   Performance Metrics: ~{len(str(performance_data))} chars")
    print(f"   Technology Template: ~{len(str(template))} chars")
    print(f"   Analysis Instructions: ~{len('Analysis Request section')} chars")
    
    print(f"\n💡 KEY FEATURES OF THIS PROMPT:")
    print("1. Complete site context (URL, description, tech stack)")
    print("2. Detailed performance metrics with grades")
    print("3. Technology-specific optimization patterns")
    print("4. Specific recommendations from templates")
    print("5. Clear instructions for AI analysis")
    print("6. Structured JSON output format")

def show_system_prompt():
    """Show the system prompt used to define the AI's role"""
    
    print("\n" + "=" * 80)
    print("🔧 SYSTEM PROMPT (AI ROLE DEFINITION):")
    print("=" * 80)
    
    system_prompt = """You are an expert web performance optimization consultant with deep knowledge of modern web technologies, cloud platforms, and performance best practices. 

Your role is to analyze performance test results and provide:
1. Detailed insights about what the metrics mean
2. Specific, actionable optimization recommendations
3. Technology-specific advice based on the stack being used
4. Prioritized action items with impact and effort estimates

Be specific, technical, and actionable. Focus on practical improvements that can be implemented."""
    
    print(system_prompt)
    print("=" * 80)

def show_prompt_analysis():
    """Show analysis of the prompt structure"""
    
    print("\n" + "=" * 80)
    print("📋 PROMPT STRUCTURE ANALYSIS:")
    print("=" * 80)
    
    print("""
The prompt is structured in several key sections:

1. 📋 WEBSITE PERFORMANCE ANALYSIS REQUEST
   - Clear title and purpose

2. 🏠 SITE INFORMATION
   - URL, description, technology stack
   - Test duration and virtual users

3. 📊 PERFORMANCE METRICS
   - Response time with grade
   - Error rate with grade  
   - Throughput with grade
   - Total requests

4. 🔧 TECHNOLOGY CONTEXT
   - Template name and description
   - Number of relevant patterns

5. 🎯 TECHNOLOGY-SPECIFIC OPTIMIZATION PATTERNS
   - Frontend optimizations (Svelte-specific)
   - Backend optimizations (Strapi-specific)
   - Infrastructure optimizations (Azure-specific)
   - Each with specific recommendations

6. 📝 ANALYSIS REQUEST
   - Clear instructions for AI
   - Specific tasks to complete
   - JSON output format specification

This structure ensures the AI has:
✅ Complete context about the site
✅ Detailed performance data
✅ Technology-specific optimization patterns
✅ Clear instructions for analysis
✅ Structured output format
""")

if __name__ == "__main__":
    show_generated_prompts()
    show_system_prompt()
    show_prompt_analysis() 