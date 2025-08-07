#!/usr/bin/env python3
"""
Script to show how technology templates are used in AI analysis
"""

import yaml
import json
from ai_analysis.openai_enhanced_agent import OpenAIEnhancedAnalysis

def show_template_usage():
    """Show how templates are used in AI analysis"""
    
    print("=== Technology Template Usage in AI Analysis ===\n")
    
    # Load the Svelte + Strapi + Azure template
    with open("ai_analysis/technology_templates.yaml", 'r') as f:
        templates = yaml.safe_load(f)
    
    template = templates['templates']['svelte_strapi_azure']
    
    print(f"📋 Template: {template['name']}")
    print(f"📝 Description: {template['description']}")
    print(f"🏷️  Tags: {', '.join(template['tags'])}")
    
    print(f"\n🔧 Performance Patterns Available:")
    performance_patterns = template.get('performance_patterns', {})
    
    for category, patterns in performance_patterns.items():
        print(f"\n  📂 {category.upper()}:")
        for pattern in patterns:
            print(f"    • {pattern['name']}")
            print(f"      Description: {pattern['description']}")
            recommendations = pattern.get('recommendations', [])
            print(f"      Recommendations: {len(recommendations)} available")
            for i, rec in enumerate(recommendations[:2], 1):
                print(f"        {i}. {rec}")
            if len(recommendations) > 2:
                print(f"        ... and {len(recommendations) - 2} more")
    
    print(f"\n🤖 How This Information is Used in AI Analysis:")
    print("1. Template is automatically selected based on site tags")
    print("2. All optimization patterns are included in the AI prompt")
    print("3. AI builds upon these patterns for specific recommendations")
    print("4. Recommendations are tailored to the exact technology stack")
    
    # Show sample prompt structure
    print(f"\n📤 Sample AI Prompt Structure:")
    print("""
# Website Performance Analysis Request

## Site Information
- URL, Description, Technology Stack, Test Parameters

## Performance Metrics  
- Response Time, Error Rate, Throughput, etc.

## Technology Context
- Template Name and Description
- Relevant Patterns Count

## Technology-Specific Optimization Patterns

### Frontend Optimizations:
- Svelte Bundle Optimization: Optimize Svelte bundle size and loading performance
  - Key recommendations: Implement code splitting with dynamic imports, Use Svelte's built-in tree-shaking, Optimize component lazy loading
- Asset Optimization: Optimize static assets and media loading
  - Key recommendations: Implement image optimization and lazy loading, Use WebP format with fallbacks, Configure proper caching headers

### Backend Optimizations:
- Strapi API Performance: Optimize Strapi API response times and caching
  - Key recommendations: Implement API response caching, Optimize database queries and indexes, Use Strapi's built-in caching mechanisms
- Database Optimization: Optimize database performance for Strapi
  - Key recommendations: Review and optimize database indexes, Implement connection pooling, Consider read replicas for heavy traffic

### Infrastructure Optimizations:
- Azure App Service Optimization: Optimize Azure App Service configuration
  - Key recommendations: Configure auto-scaling rules, Use Azure CDN for static assets, Optimize App Service plan tier
- Network and CDN: Optimize network performance and CDN usage
  - Key recommendations: Configure Azure CDN with proper caching, Optimize TLS configuration, Use HTTP/2 for better performance

## Analysis Request
- AI is instructed to build upon these patterns
- Focus on technology-specific recommendations
- Provide implementation guidance
""")

if __name__ == "__main__":
    show_template_usage() 