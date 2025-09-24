#!/usr/bin/env python3
"""
Enhanced AI Analysis Agent for Load Testing & Optimization
Uses performance recommendations and site tags to generate targeted, architecture-specific recommendations
"""

import yaml
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

# Optional OpenAI import
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TargetedPromptBuilder:
    """Builds targeted prompts based on performance issues and site tags"""
    
    def __init__(self):
        self.technology_contexts = {
            "svelte": {
                "description": "Svelte frontend framework",
                "optimization_focus": ["bundle optimization", "component lazy loading", "SSR/SSG", "state management"],
                "common_issues": ["large bundle size", "slow initial load", "hydration issues"]
            },
            "strapi": {
                "description": "Strapi headless CMS",
                "optimization_focus": ["API caching", "database optimization", "content delivery", "query optimization"],
                "common_issues": ["slow API responses", "database bottlenecks", "content loading delays"]
            },
            "azure": {
                "description": "Azure cloud platform",
                "optimization_focus": ["App Service scaling", "CDN configuration", "database optimization", "monitoring"],
                "common_issues": ["scaling issues", "network latency", "resource constraints"]
            },
            "app-service": {
                "description": "Azure App Service hosting",
                "optimization_focus": ["auto-scaling", "performance tiers", "deployment optimization", "health checks"],
                "common_issues": ["cold starts", "memory limits", "CPU constraints"]
            },
            "headless-cms": {
                "description": "Headless CMS architecture",
                "optimization_focus": ["API optimization", "content caching", "preview modes", "webhook optimization"],
                "common_issues": ["content delivery delays", "API rate limits", "preview performance"]
            },
            "javascript": {
                "description": "JavaScript application",
                "optimization_focus": ["code splitting", "tree shaking", "lazy loading", "performance monitoring"],
                "common_issues": ["large bundle sizes", "memory leaks", "slow execution"]
            },
            "api-driven": {
                "description": "API-driven architecture",
                "optimization_focus": ["API caching", "request optimization", "response compression", "rate limiting"],
                "common_issues": ["API bottlenecks", "slow responses", "rate limiting issues"]
            }
        }
    
    def build_targeted_prompt(self, 
                            performance_issues: List[Dict[str, Any]], 
                            site_tags: List[str],
                            site_description: str = "",
                            target_url: str = "",
                            protocol_metrics: Optional[Dict[str, Any]] = None,
                            browser_metrics: Optional[Dict[str, Any]] = None) -> str:
        """Build a targeted prompt based on performance issues and site tags"""
        
        # Build technology context
        tech_context = self._build_technology_context(site_tags)
        
        # Build performance issues context
        issues_context = self._build_issues_context(performance_issues)
        
        # Build measured results section
        measured_results = self._build_measured_results(protocol_metrics, browser_metrics)
        
        # Build issues detected section
        issues_detected = self._build_issues_detected(performance_issues)
        
        # Build the enhanced targeted prompt
        prompt = f"""System role
You are a senior performance architect for modern web apps (Svelte + Strapi on Azure). Be precise, pragmatic, and technology-specific. Do not invent facts; if something is unknown, state it in "assumptions". Output valid JSON exactly matching the schema.

Objectives

Propose prioritized, high-impact optimizations to improve both protocol performance and real user/UX metrics.

Solutions must align with the stack: Svelte (SvelteKit if applicable), Strapi, Azure App Service, Azure CDN/Front Door.

Provide implementation-ready steps: code diffs/snippets, config/CLI, and how to verify impact.

KPIs (targets)

Backend: p95 http_req_duration ≤ 400ms, error rate < 0.5%, throughput sustained at ≥ 100 rps.

Frontend: LCP ≤ 2.5s (p75), CLS < 0.1 (p75), FID/INP ≤ 100ms (p75), total JS < 500 KB.

Application Context

Target URL: {target_url}

Site Description: {site_description}

Tech Stack Tags: {site_tags}

Architecture Notes: Frontend is built with Svelte and the Backend is built with Strapi. The frontend application gets its data from the strapi api. This app is an App Service that lives on azure.

Infrastructure & Config

{{
  "azure": {{
    "region": "eastus",
    "app_service": {{ "sku": "Standard", "instances": 2, "always_on": true, "node_version": "18" }},
    "autoscale": {{ "metric": "CPU", "scale_out": "CPU > 70%", "scale_in": "CPU < 30%" }},
    "network": {{ "http_version": "2", "compression": ["gzip","br"], "front_door_or_cdn": "CDN" }}
  }},
  "strapi": {{
    "version": "4.x",
    "db": {{ "engine": "postgres", "tier": "Standard", "pool": {{"min": 5, "max": 20}} }},
    "cache": {{ "enabled": true, "type": "redis", "ttl_sec": 3600 }},
    "api": {{ "rest_or_graphql": "REST", "rate_limit": "1000/hour" }}
  }}
}}

Load Test Profile (k6/Playwright)

{{
  "scenarios": {{"protocol": {{"vus": 20, "duration": "5m"}}, "browser": {{"vus": 10, "duration": "5m"}}}},
  "traffic_mix": [{{"route": "/", "weight": 0.8}}, {{"route": "/api", "weight": 0.2}}],
  "cache_state": "warm",
  "error_budget": 0.05,
  "notes": "Comprehensive load test with both protocol and browser testing"
}}

Measured Results (paste your telemetry)

{measured_results}

Issues Detected

{issues_detected}

Output Rules

Return only JSON matching the schema below.

Where helpful, include diffs ("code_examples": [{{"language":"diff","code":"--- a\\n+++ b\\n..."}}]), Azure CLI or ARM/Bicep snippets.

For each recommendation: include risks/trade-offs, rollback, and a validation plan.

Prefer stack-specific tactics (Svelte/SvelteKit, Strapi, Azure App Service, Front Door/CDN, Postgres/SQL).

If data is missing, list it under "assumptions" and proceed with the best practice approach.

Schema

{{
  "summary": {{
    "overall_assessment": "string",
    "primary_concerns": ["string"],
    "optimization_priority": "High|Medium|Low",
    "assumptions": ["string"]
  }},
  "recommendations": [
    {{
      "title": "string",
      "category": "Frontend|Backend|Infrastructure|Database|CDN",
      "priority": "Critical|High|Medium|Low",
      "effort": "Low|Medium|High",
      "expected_impact": "string",
      "implementation_steps": ["string"],
      "code_examples": [
        {{ "language": "javascript|diff|yaml|bash|sql", "code": "string", "description": "string" }}
      ],
      "monitoring": "string",
      "risks": "string",
      "rollback": "string",
      "validation_plan": "string"
    }}
  ],
  "technology_specific_insights": {{
    "svelte": {{ "key_optimizations": ["string"], "common_pitfalls": ["string"], "best_practices": ["string"] }},
    "strapi": {{ "key_optimizations": ["string"], "common_pitfalls": ["string"], "best_practices": ["string"] }},
    "azure_app_service": {{ "key_optimizations": ["string"], "common_pitfalls": ["string"], "best_practices": ["string"] }},
    "cdn_front_door": {{ "key_optimizations": ["string"], "common_pitfalls": ["string"], "best_practices": ["string"] }}
  }}
}}

Now generate the JSON."""

        return prompt
    
    def _build_technology_context(self, site_tags: List[str]) -> str:
        """Build technology-specific context from site tags"""
        context_parts = []
        
        for tag in site_tags:
            if tag.lower() in self.technology_contexts:
                tech_info = self.technology_contexts[tag.lower()]
                context_parts.append(f"""
**{tag.upper()}**:
- Description: {tech_info['description']}
- Optimization Focus: {', '.join(tech_info['optimization_focus'])}
- Common Issues: {', '.join(tech_info['common_issues'])}
""")
        
        return '\n'.join(context_parts) if context_parts else "Generic web application"
    
    def _build_issues_context(self, performance_issues: List[Dict[str, Any]]) -> str:
        """Build context from performance issues"""
        if not performance_issues:
            return "No specific performance issues identified."
        
        issues_text = []
        for issue in performance_issues:
            priority_icon = "🔴" if issue.get('priority') == 'high' else "🟡" if issue.get('priority') == 'medium' else "🟢"
            issues_text.append(f"""
{priority_icon} **{issue.get('title', 'Performance Issue')}**
- Category: {issue.get('category', 'General')}
- Description: {issue.get('description', 'No description available')}
- Priority: {issue.get('priority', 'Unknown')}
""")
        
        return '\n'.join(issues_text)
    
    def _build_measured_results(self, protocol_metrics: Optional[Dict[str, Any]], browser_metrics: Optional[Dict[str, Any]]) -> str:
        """Build measured results section from protocol and browser metrics"""
        protocol_data = {}
        browser_data = {}
        
        if protocol_metrics:
            protocol_data = {
                "overall": {
                    "rps": protocol_metrics.get('throughput', 0),
                    "p95_ms": protocol_metrics.get('p95_response_time', 0),
                    "error_rate": protocol_metrics.get('error_rate', 0)
                },
                "endpoints_top_offenders": [
                    {
                        "path": "/api/content",
                        "p95_ms": protocol_metrics.get('p95_response_time', 0),
                        "rps": protocol_metrics.get('throughput', 0),
                        "error_rate": protocol_metrics.get('error_rate', 0),
                        "db": {"query_ms_p95": 0, "rows": 0}
                    }
                ]
            }
        
        if browser_metrics:
            # Use actual available metrics from Playwright summary
            page_load_time = browser_metrics.get('playwright_page_load_time', {}).get('avg', 0) * 1000  # Convert to ms
            browser_data = {
                "web_vitals": {
                    "LCP_ms_p75": browser_metrics.get('lcp', page_load_time),  # Use page load time as proxy for LCP
                    "CLS_p75": browser_metrics.get('cls', 0),
                    "FID_ms_p75": browser_metrics.get('fid', 0),
                    "TTFB_ms_p75": browser_metrics.get('ttfb', 0)
                },
                "page_weight": {
                    "js_kb": browser_metrics.get('js_size_kb', 0),
                    "css_kb": browser_metrics.get('css_size_kb', 0),
                    "img_kb": browser_metrics.get('img_size_kb', 0),
                    "req_count": browser_metrics.get('total_requests', 0)
                },
                "bundle_insights": [
                    {
                        "file": "main.js",
                        "bundle_kb": browser_metrics.get('js_size_kb', 0),
                        "notes": "main application bundle"
                    }
                ],
                "playwright_metrics": {
                    "page_load_time_ms": page_load_time,
                    "iterations": browser_metrics.get('playwright_iterations', {}).get('count', 0),
                    "throughput": browser_metrics.get('playwright_iterations', {}).get('rate', 0)
                }
            }
        
        return f'''{{
  "protocol": {json.dumps(protocol_data, indent=2)},
  "browser": {json.dumps(browser_data, indent=2)}
}}'''
    
    def _build_issues_detected(self, performance_issues: List[Dict[str, Any]]) -> str:
        """Build issues detected section from performance issues"""
        issues_list = []
        
        for issue in performance_issues:
            # Create a unique ID based on the issue
            issue_id = f"{issue.get('category', 'UNKNOWN').upper()}_{issue.get('priority', 'MEDIUM').upper()}"
            if 'throughput' in issue.get('title', '').lower():
                issue_id = f"{issue_id}_THROUGHPUT"
            elif 'response' in issue.get('title', '').lower():
                issue_id = f"{issue_id}_RESPONSE"
            elif 'error' in issue.get('title', '').lower():
                issue_id = f"{issue_id}_ERROR"
            
            issues_list.append({
                "id": issue_id,
                "desc": issue.get('description', issue.get('title', 'Unknown issue')),
                "priority": issue.get('priority', 'medium')
            })
        
        return json.dumps(issues_list, indent=2)

class EnhancedAIAnalysisAgent:
    """Enhanced AI Analysis Agent with targeted prompts and architecture-specific recommendations"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.prompt_builder = TargetedPromptBuilder()
        
        if OPENAI_AVAILABLE and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAI library not available. Install with: pip install openai")
            else:
                logger.warning("OpenAI API key not provided. AI analysis will be limited.")
    
    def analyze_with_enhanced_recommendations(self,
                                            enhanced_analysis: Dict[str, Any],
                                            browser_analysis: Dict[str, Any],
                                            config: Dict[str, Any],
                                            protocol_metrics: Optional[Dict[str, Any]] = None,
                                            browser_metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze using enhanced performance recommendations and site tags"""
        
        logger.info("Starting enhanced AI analysis with targeted prompts...")
        
        # Extract performance issues from enhanced analysis and metrics
        performance_issues = self._extract_performance_issues(enhanced_analysis, browser_analysis, protocol_metrics, browser_metrics)
        
        # Get site information
        site_tags = config.get("tags", [])
        site_description = config.get("description", "")
        target_url = config.get("target", "")
        
        # Build targeted prompt
        targeted_prompt = self.prompt_builder.build_targeted_prompt(
            performance_issues, site_tags, site_description, target_url, protocol_metrics, browser_metrics
        )
        
        # Get AI recommendations
        ai_recommendations = self._get_ai_recommendations(targeted_prompt)
        
        # Create comprehensive report
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "enhanced_ai_analysis",
            "site_info": {
                "target": target_url,
                "description": site_description,
                "tags": site_tags
            },
            "performance_issues": performance_issues,
            "ai_recommendations": ai_recommendations,
            "targeted_prompt_used": targeted_prompt,
            "technology_context": self.prompt_builder._build_technology_context(site_tags)
        }
        
        logger.info("Enhanced AI analysis complete!")
        return report
    
    def _extract_performance_issues(self, 
                                  enhanced_analysis: Dict[str, Any],
                                  browser_analysis: Dict[str, Any],
                                  protocol_metrics: Optional[Dict[str, Any]] = None,
                                  browser_metrics: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract performance issues from enhanced analysis"""
        issues = []
        
        # Extract from enhanced analysis
        if enhanced_analysis:
            # Get issues from the issues section
            for priority in ['high', 'medium', 'low']:
                priority_issues = enhanced_analysis.get('issues', {}).get(priority, [])
                for issue in priority_issues:
                    issues.append({
                        "title": issue.get('issue', 'Performance Issue'),
                        "category": issue.get('category', 'General'),
                        "description": issue.get('recommendation', 'No description available'),
                        "priority": priority,
                        "source": "enhanced_analysis"
                    })
            
            # Get recommendations from enhanced analysis
            recommendations = enhanced_analysis.get('recommendations', [])
            for rec in recommendations:
                issues.append({
                    "title": rec.get('title', 'Performance Recommendation'),
                    "category": rec.get('category', 'General'),
                    "description": rec.get('description', 'No description available'),
                    "priority": rec.get('priority', 'medium'),
                    "source": "enhanced_recommendations"
                })
        
        # Extract from browser analysis
        if browser_analysis:
            browser_insights = browser_analysis.get('performance_insights', [])
            for insight in browser_insights:
                issues.append({
                    "title": insight.get('title', 'Browser Performance Issue'),
                    "category": "Browser Performance",
                    "description": insight.get('description', 'No description available'),
                    "priority": insight.get('priority', 'medium'),
                    "source": "browser_analysis"
                })
        
        # Extract from protocol metrics performance deductions
        if protocol_metrics:
            protocol_deductions = protocol_metrics.get('performance_deductions', [])
            for deduction in protocol_deductions:
                priority = "high" if "error" in deduction.lower() else "medium" if "slow" in deduction.lower() or "very slow" in deduction.lower() else "low"
                issues.append({
                    "title": f"Protocol Performance Issue: {deduction}",
                    "category": "Protocol Performance",
                    "description": f"Performance issue detected: {deduction}",
                    "priority": priority,
                    "source": "protocol_metrics"
                })
        
        # Extract from browser metrics performance deductions
        if browser_metrics:
            browser_deductions = browser_metrics.get('performance_deductions', [])
            for deduction in browser_deductions:
                priority = "high" if "slow" in deduction.lower() or "very slow" in deduction.lower() else "medium"
                issues.append({
                    "title": f"Browser Performance Issue: {deduction}",
                    "category": "Browser Performance",
                    "description": f"Browser performance issue detected: {deduction}",
                    "priority": priority,
                    "source": "browser_metrics"
                })
        
        return issues
    
    def _get_ai_recommendations(self, prompt: str) -> Dict[str, Any]:
        """Get AI recommendations using OpenAI"""
        if not self.client:
            return {
                "error": "OpenAI client not available",
                "fallback_recommendations": self._get_fallback_recommendations()
            }
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior performance optimization expert. Provide specific, actionable recommendations in the requested JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                # Look for JSON in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_text = response_text[start_idx:end_idx]
                    return json.loads(json_text)
                else:
                    return {"raw_response": response_text}
            except json.JSONDecodeError:
                return {"raw_response": response_text}
                
        except Exception as e:
            logger.error(f"Error getting AI recommendations: {e}")
            return {
                "error": str(e),
                "fallback_recommendations": self._get_fallback_recommendations()
            }
    
    def _get_fallback_recommendations(self) -> Dict[str, Any]:
        """Get fallback recommendations when AI is not available"""
        return {
            "summary": {
                "overall_assessment": "AI analysis not available. Please check OpenAI API key configuration.",
                "primary_concerns": ["Unable to generate AI recommendations"],
                "optimization_priority": "Unknown"
            },
            "recommendations": [
                {
                    "title": "Configure OpenAI API Key",
                    "category": "Configuration",
                    "priority": "High",
                    "effort": "Low",
                    "expected_impact": "Enable AI-powered recommendations",
                    "implementation_steps": [
                        "Add OPENAI_API_KEY to your .env file",
                        "Restart the application",
                        "Re-run the analysis"
                    ],
                    "monitoring": "Check that AI recommendations are generated in future runs"
                }
            ],
            "technology_specific_insights": {
                "key_optimizations": ["Manual analysis required"],
                "common_pitfalls": ["Missing API key configuration"],
                "best_practices": ["Always configure AI analysis for best results"]
            }
        }

def main():
    """Main function for standalone execution"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python enhanced_ai_agent.py <enhanced_analysis_path> <browser_analysis_path> [config_path]")
        sys.exit(1)
    
    enhanced_analysis_path = sys.argv[1]
    browser_analysis_path = sys.argv[2]
    config_path = sys.argv[3] if len(sys.argv) > 3 else "configs/pop_website_test.yaml"
    
    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # Load analysis files
    try:
        with open(enhanced_analysis_path, 'r') as f:
            enhanced_analysis = json.load(f)
    except Exception as e:
        print(f"Error loading enhanced analysis: {e}")
        enhanced_analysis = {}
    
    try:
        with open(browser_analysis_path, 'r') as f:
            browser_analysis = json.load(f)
    except Exception as e:
        print(f"Error loading browser analysis: {e}")
        browser_analysis = {}
    
    # Run enhanced AI analysis
    agent = EnhancedAIAnalysisAgent()
    report = agent.analyze_with_enhanced_recommendations(enhanced_analysis, browser_analysis, config)
    
    # Save report
    output_path = "output/enhanced_ai_analysis_report.json"
    Path("output").mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Enhanced AI Analysis complete! Report saved to: {output_path}")
    
    if report.get('ai_recommendations', {}).get('summary'):
        print(f"Overall Assessment: {report['ai_recommendations']['summary']['overall_assessment']}")
        print(f"Optimization Priority: {report['ai_recommendations']['summary']['optimization_priority']}")

if __name__ == "__main__":
    main()
