#!/usr/bin/env python3
"""
OpenAI-Enhanced AI Analysis Agent
Integrates GPT-4 for intelligent performance analysis and recommendations
"""

import os
import yaml
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# OpenAI integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available - falling back to rule-based analysis")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIEnhancedAnalysis:
    """Enhanced analysis using OpenAI GPT-4 with fallback models"""
    
    # Available models in order of preference (best to fallback)
    AVAILABLE_MODELS = [
        "gpt-4o-mini",      # Best performance, lower cost ← DEFAULT
        "gpt-4o",           # Best performance, highest cost
        "gpt-4-turbo",      # Good performance, high cost
        "gpt-4-turbo-preview", # Latest GPT-4 variant
        "gpt-3.5-turbo",    # Good performance, lower cost
        "gpt-3.5-turbo-16k" # Good performance, higher context
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.current_model_index = 0  # Start with the first model
        
        if self.api_key and OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            logger.warning("OpenAI not available - using rule-based analysis only")
    
    def _get_current_model(self) -> str:
        """Get the current model to use"""
        if self.current_model_index < len(self.AVAILABLE_MODELS):
            return self.AVAILABLE_MODELS[self.current_model_index]
        else:
            # If we've tried all models, go back to the first one
            self.current_model_index = 0
            return self.AVAILABLE_MODELS[0]
    
    def _try_next_model(self) -> Optional[str]:
        """Try the next available model"""
        self.current_model_index += 1
        if self.current_model_index < len(self.AVAILABLE_MODELS):
            next_model = self.AVAILABLE_MODELS[self.current_model_index]
            logger.info(f"🔄 Switching to fallback model: {next_model}")
            return next_model
        else:
            logger.error("❌ All available models have been tried")
            return None
    
    def _handle_openai_error(self, error: Exception) -> bool:
        """Handle OpenAI API errors and determine if we should retry with a different model"""
        error_str = str(error).lower()
        
        # Rate limit errors - try next model
        if "rate limit" in error_str or "tpm" in error_str or "rpm" in error_str:
            logger.warning(f"⚠️ Rate limit hit on {self._get_current_model()}: {error}")
            return self._try_next_model() is not None
        
        # Quota exceeded - this affects all models, don't retry
        elif "quota" in error_str or "billing" in error_str or "insufficient_quota" in error_str:
            logger.error(f"❌ Quota exceeded on {self._get_current_model()}: {error}")
            logger.error("💡 Solution: Add payment method at https://platform.openai.com/account/billing")
            return False
        
        # Model not found or access denied - try next model
        elif "does not exist" in error_str or "not have access" in error_str:
            logger.warning(f"⚠️ Model access issue on {self._get_current_model()}: {error}")
            return self._try_next_model() is not None
        
        # Other errors - don't retry
        else:
            logger.error(f"❌ OpenAI API error: {error}")
            return False
    
    def generate_ai_insights(self, 
                           performance_data: Dict[str, Any],
                           site_config: Dict[str, Any],
                           technology_template: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate AI-powered insights using OpenAI with fallback models"""
        
        if not self.client:
            return {"ai_insights": "OpenAI not available", "ai_recommendations": []}
        
        # Build comprehensive prompt
        prompt = self._build_ai_prompt(performance_data, site_config, technology_template)
        
        # Try each model until one works
        max_retries = len(self.AVAILABLE_MODELS)
        retry_count = 0
        
        while retry_count < max_retries:
            current_model = self._get_current_model()
            logger.info(f"🤖 Attempting AI analysis with model: {current_model}")
            
            try:
                # Generate AI response
                response = self.client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert web performance optimization consultant with deep knowledge of modern web technologies, cloud platforms, and performance best practices. 

Your role is to analyze performance test results and provide:
1. Detailed insights about what the metrics mean
2. Specific, actionable optimization recommendations
3. Technology-specific advice based on the stack being used
4. Prioritized action items with impact and effort estimates

Be specific, technical, and actionable. Focus on practical improvements that can be implemented."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more consistent, technical responses
                    max_tokens=1500
                )
                
                ai_response = response.choices[0].message.content
                logger.info(f"✅ AI analysis completed successfully with {current_model}")
                
                # Parse AI response into structured format
                structured_insights = self._parse_ai_response(ai_response)
                
                return {
                    "ai_insights": ai_response,
                    "ai_recommendations": structured_insights.get("recommendations", []),
                    "ai_analysis": structured_insights.get("analysis", {}),
                    "ai_priorities": structured_insights.get("priorities", []),
                    "model_used": current_model
                }
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"⚠️ Attempt {retry_count} failed with {current_model}: {e}")
                
                # Check if we should try the next model
                if not self._handle_openai_error(e):
                    logger.error("❌ All retry attempts failed")
                    break
                
                # Small delay before retrying
                time.sleep(1)
        
        # If all models failed, return fallback response
        logger.error("❌ All OpenAI models failed - using fallback analysis")
        return {
            "ai_insights": "OpenAI analysis unavailable due to API issues. Using rule-based analysis.",
            "ai_recommendations": self._generate_fallback_recommendations(performance_data),
            "ai_analysis": {},
            "ai_priorities": [],
            "model_used": "fallback"
        }
    
    def _generate_fallback_recommendations(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate basic recommendations when AI is unavailable"""
        recommendations = []
        
        # Basic performance recommendations based on metrics
        if 'test_summary' in performance_data:
            summary = performance_data['test_summary']
            
            avg_response_time = summary.get('average_response_time', 0)
            error_rate = summary.get('error_rate', 0)
            
            if avg_response_time > 1000:
                recommendations.append({
                    "title": "Optimize Server Response Time",
                    "priority": "high",
                    "impact": "High",
                    "effort": "Medium",
                    "description": f"Average response time of {avg_response_time:.0f}ms is above recommended threshold. Consider server-side optimizations.",
                    "implementation": [
                        "Review database queries and add indexes",
                        "Implement caching strategies",
                        "Optimize server-side code",
                        "Consider CDN for static assets"
                    ],
                    "expected_improvement": "Reduce response time by 30-50%",
                    "data_support": f"Current average response time: {avg_response_time:.0f}ms"
                })
            
            if error_rate > 5:
                recommendations.append({
                    "title": "Reduce Error Rate",
                    "priority": "high",
                    "impact": "High",
                    "effort": "Medium",
                    "description": f"Error rate of {error_rate:.2f}% is above acceptable threshold. Investigate and fix errors.",
                    "implementation": [
                        "Review server logs for error patterns",
                        "Implement proper error handling",
                        "Add monitoring and alerting",
                        "Test error scenarios"
                    ],
                    "expected_improvement": "Reduce error rate to below 1%",
                    "data_support": f"Current error rate: {error_rate:.2f}%"
                })
        
        return recommendations
    
    def _build_ai_prompt(self, 
                        performance_data: Dict[str, Any],
                        site_config: Dict[str, Any],
                        technology_template: Optional[Dict[str, Any]] = None) -> str:
        """Build a comprehensive prompt for AI analysis with ALL available data"""
        
        # Extract key metrics
        metrics = performance_data.get("metrics_analysis", {})
        
        prompt = f"""
# Comprehensive Website Performance Analysis Request

## Site Information
- **URL**: {site_config.get('target', 'Unknown')}
- **Description**: {site_config.get('description', 'No description provided')}
- **Technology Stack**: {', '.join(site_config.get('tags', []))}
- **Test Duration**: {performance_data.get('test_summary', {}).get('duration', 'Unknown')}
- **Virtual Users**: {performance_data.get('test_summary', {}).get('virtual_users', 'Unknown')}

## Basic Performance Metrics
- **Response Time**: {metrics.get('response_time', {}).get('value', 'Unknown')}ms (Grade: {metrics.get('response_time', {}).get('grade', 'Unknown')})
- **Error Rate**: {metrics.get('error_rate', {}).get('value', 'Unknown')}% (Grade: {metrics.get('error_rate', {}).get('grade', 'Unknown')})
- **Throughput**: {metrics.get('throughput', {}).get('value', 'Unknown')} req/s (Grade: {metrics.get('throughput', {}).get('grade', 'Unknown')})
- **Total Requests**: {performance_data.get('test_summary', {}).get('total_requests', 'Unknown')}

## Detailed HTTP Timing Breakdown (k6 Enhanced Metrics)
"""
        
        # Include detailed HTTP timing metrics if available
        if 'http_timing_analysis' in performance_data:
            timing = performance_data['http_timing_analysis']
            prompt += f"""
### Network Performance Analysis:
- **DNS/Connection Pool**: {timing.get('dns_connection_pool', {}).get('average', 'Unknown')}ms
- **TCP Connection**: {timing.get('tcp_connection', {}).get('average', 'Unknown')}ms  
- **TLS Handshake**: {timing.get('tls_handshake', {}).get('average', 'Unknown')}ms
- **Request Sending**: {timing.get('request_sending', {}).get('average', 'Unknown')}ms
- **Server Processing**: {timing.get('server_processing', {}).get('average', 'Unknown')}ms
- **Response Receiving**: {timing.get('response_receiving', {}).get('average', 'Unknown')}ms

### Data Transfer Analysis:
- **Data Sent**: {timing.get('data_sent', {}).get('average', 'Unknown')} bytes
- **Data Received**: {timing.get('data_received', {}).get('average', 'Unknown')} bytes ({timing.get('data_received', {}).get('average_kb', 'Unknown')}KB)
- **Compression Ratio**: {timing.get('compression_ratio', {}).get('average', 'Unknown')}%
"""
        
        # Include page resource analysis if available
        if 'page_resource_analysis' in performance_data:
            resource_analysis = performance_data['page_resource_analysis']
            prompt += f"""
## Page Resource Analysis Results
- **Total Resources**: {resource_analysis.get('total_resources', 'Unknown')}
- **Total Size**: {resource_analysis.get('total_size_mb', 'Unknown')}MB
- **Total Load Time**: {resource_analysis.get('total_load_time', 'Unknown')}ms
- **Performance Score**: {resource_analysis.get('performance_score', 'Unknown')}/100

### Resource Issues Found:
"""
            
            issues = resource_analysis.get('issues', {})
            if issues.get('high'):
                prompt += "\n**High Priority Issues:**\n"
                for issue in issues['high']:
                    prompt += f"- {issue.get('description', 'Unknown issue')}\n"
            
            if issues.get('medium'):
                prompt += "\n**Medium Priority Issues:**\n"
                for issue in issues['medium']:
                    prompt += f"- {issue.get('description', 'Unknown issue')}\n"
            
            if issues.get('low'):
                prompt += "\n**Low Priority Issues:**\n"
                for issue in issues['low'][:5]:  # Limit to top 5
                    prompt += f"- {issue.get('description', 'Unknown issue')}\n"
            
            # Include specific resource details
            resources = resource_analysis.get('resources', [])
            if resources:
                prompt += "\n### Resource Details:\n"
                for resource in resources[:10]:  # Limit to top 10 resources
                    prompt += f"- **{resource.get('type', 'Unknown')}**: {resource.get('url', 'Unknown')[:60]}...\n"
                    prompt += f"  Size: {resource.get('size', 0)/1024:.1f}KB, Load Time: {resource.get('load_time', 0):.0f}ms\n"
                    if resource.get('issues'):
                        for issue in resource['issues']:
                            prompt += f"  Issue: {issue.get('description', 'Unknown')}\n"

        # Include enhanced performance analysis if available
        if 'enhanced_analysis' in performance_data:
            enhanced = performance_data['enhanced_analysis']
            prompt += f"""
## Enhanced Performance Analysis
- **Performance Score**: {enhanced.get('performance_score', 'Unknown')}/100
- **Total Issues**: {enhanced.get('total_issues', 'Unknown')}
- **High Priority**: {enhanced.get('high_priority', 'Unknown')}
- **Medium Priority**: {enhanced.get('medium_priority', 'Unknown')}
- **Low Priority**: {enhanced.get('low_priority', 'Unknown')}

### Detailed Issues:
"""
            
            issues = enhanced.get('issues', {})
            if issues.get('high'):
                prompt += "\n**High Priority Issues:**\n"
                for issue in issues['high']:
                    prompt += f"- {issue.get('issue', 'Unknown')}\n"
                    prompt += f"  Recommendation: {issue.get('recommendation', 'None')}\n"
            
            if issues.get('medium'):
                prompt += "\n**Medium Priority Issues:**\n"
                for issue in issues['medium']:
                    prompt += f"- {issue.get('issue', 'Unknown')}\n"
                    prompt += f"  Recommendation: {issue.get('recommendation', 'None')}\n"

        # Include browser analysis if available
        if 'browser_analysis' in performance_data:
            browser = performance_data['browser_analysis']
            prompt += f"""
## Browser Performance Analysis (Core Web Vitals)
- **Overall Score**: {browser.get('overall_score', 'Unknown')}/100
- **Overall Grade**: {browser.get('overall_grade', 'Unknown')}

### Core Web Vitals:
"""
            
            core_vitals = browser.get('core_web_vitals', {})
            for metric, data in core_vitals.items():
                prompt += f"- **{data.get('name', metric)}**: {data.get('average', 'Unknown')}ms (Grade: {data.get('grade', 'Unknown')})\n"
            
            # Navigation timing
            navigation = browser.get('navigation_timing', {})
            if navigation:
                prompt += "\n### Navigation Timing:\n"
                for metric, data in navigation.items():
                    prompt += f"- **{data.get('name', metric)}**: {data.get('average', 'Unknown')}ms (Grade: {data.get('grade', 'Unknown')})\n"
            
            # Resource loading
            resources = browser.get('resource_loading', {})
            if resources:
                prompt += f"\n### Resource Loading:\n"
                prompt += f"- **Total Size**: {resources.get('resource_sizes', {}).get('total', 0)/1024/1024:.1f}MB\n"
                prompt += f"- **Average Size**: {resources.get('resource_sizes', {}).get('average', 0)/1024:.1f}KB\n"
                
                resource_counts = resources.get('resource_counts', {})
                if resource_counts:
                    prompt += "- **Resource Counts**:\n"
                    for resource_type, count in resource_counts.items():
                        prompt += f"  - {resource_type}: {count}\n"
            
            # User interactions
            interactions = browser.get('user_interactions', {})
            if interactions:
                prompt += "\n### User Interactions:\n"
                if 'script_execution' in interactions:
                    script_data = interactions['script_execution']
                    prompt += f"- **Script Execution**: {script_data.get('average', 'Unknown')}ms average\n"
                if 'layout_shifts' in interactions:
                    prompt += f"- **Layout Shifts**: {interactions['layout_shifts']} detected\n"
            
            # Browser performance insights
            insights = browser.get('performance_insights', [])
            if insights:
                prompt += "\n### Browser Performance Issues:\n"
                for insight in insights[:5]:  # Limit to top 5
                    prompt += f"- **{insight.get('severity', 'Unknown').upper()}**: {insight.get('issue', 'Unknown issue')}\n"

        # Include technology template if available
        if technology_template:
            prompt += f"""
## Technology-Specific Context
- **Technology**: {technology_template.get('name', 'Unknown')}
- **Description**: {technology_template.get('description', 'No description')}
- **Performance Patterns**: {', '.join(technology_template.get('performance_patterns', []))}
- **Optimization Strategies**: {', '.join(technology_template.get('optimization_strategies', []))}
"""

        prompt += f"""
## Analysis Request

Please provide a comprehensive performance analysis in the following JSON format:

{{
  "analysis": {{
    "performance_assessment": "Overall assessment of the site's performance with grade and reasoning",
    "key_issues": ["List of critical performance problems"],
    "business_impact": "Explanation of how performance affects user experience and business metrics"
  }},
  "recommendations": [
    {{
      "title": "Recommendation title",
      "category": "Frontend|Backend|Infrastructure|Database|CDN",
      "priority": "Critical|High|Medium|Low",
      "effort": "Low|Medium|High",
      "expected_impact": "Description of expected performance improvement",
      "implementation_steps": ["Step 1", "Step 2", "Step 3"],
      "code_examples": [
        {{
          "language": "javascript|html|css|yaml|bash",
          "code": "Code example here",
          "description": "What this code does"
        }}
      ],
      "monitoring": "How to measure the impact of this recommendation"
    }}
  ],
  "priorities": [
    {{
      "action": "Specific action to take",
      "impact": "High|Medium|Low",
      "effort": "Low|Medium|High",
      "category": "Frontend|Backend|Infrastructure"
    }}
  ]
}}

Please provide a comprehensive performance analysis including:

1. **Overall Performance Assessment**: Grade the site's performance (A-F) with detailed reasoning
2. **Key Performance Issues**: Identify the most critical performance problems
3. **Technology-Specific Recommendations**: Provide targeted optimization suggestions based on the technology stack
4. **Priority Actions**: List the top 5-10 actionable improvements in order of impact
5. **Performance Insights**: Explain what the metrics mean and their business impact
6. **Front-end vs Back-end Analysis**: Separate server-side and client-side optimization opportunities
7. **Resource Optimization**: Specific recommendations for images, scripts, CSS, and other resources
8. **Core Web Vitals Optimization**: If browser data is available, provide specific CWV improvements

**IMPORTANT**: Return ONLY valid JSON in the exact format specified above. Do not include any additional text or explanations outside the JSON structure.
"""
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured format"""
        try:
            # Try to extract JSON from the response
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # If no JSON found, create a structured response
                return {
                    "analysis": {
                        "performance_assessment": "AI analysis completed",
                        "raw_response": ai_response
                    },
                    "recommendations": [],
                    "priorities": []
                }
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {
                "analysis": {
                    "performance_assessment": "Error parsing AI response",
                    "raw_response": ai_response
                },
                "recommendations": [],
                "priorities": []
            }

class EnhancedAIAnalysisAgent:
    """Enhanced AI Analysis Agent with OpenAI integration"""
    
    def __init__(self):
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ai_analysis.analysis_agent import AIAnalysisAgent
        self.base_agent = AIAnalysisAgent()
        self.openai_enhanced = OpenAIEnhancedAnalysis()
    
    def analyze_test_results(self, 
                           test_results_path: str,
                           config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results with enhanced data collection and AI insights"""
        
        # Load test results
        try:
            with open(test_results_path, 'r') as f:
                test_results = json.load(f)
        except Exception as e:
            logger.error(f"Error loading test results: {e}")
            return {}
        
        # Get technology template
        technology_template = self._get_technology_template(config.get('tags', []))
        
        # Enhanced data collection - gather ALL available performance data
        performance_data = {
            'test_summary': {
                'duration': config.get('duration', 'Unknown'),
                'virtual_users': config.get('vus', 'Unknown'),
                'target_url': config.get('target', 'Unknown'),
                'total_requests': test_results.get('test_summary', {}).get('total_requests', 'Unknown')
            },
            'metrics_analysis': {
                'response_time': {
                    'value': test_results.get('performance_metrics', {}).get('http_req_duration', {}).get('avg', 'Unknown'),
                    'grade': self._grade_response_time(test_results.get('performance_metrics', {}).get('http_req_duration', {}).get('avg', 0))
                },
                'error_rate': {
                    'value': test_results.get('performance_metrics', {}).get('http_req_failed', {}).get('rate', 0) * 100,
                    'grade': self._grade_error_rate(test_results.get('performance_metrics', {}).get('http_req_failed', {}).get('rate', 0))
                },
                'throughput': {
                    'value': test_results.get('performance_metrics', {}).get('http_reqs', {}).get('rate', 'Unknown'),
                    'grade': self._grade_throughput(test_results.get('performance_metrics', {}).get('http_reqs', {}).get('rate', 0))
                }
            }
        }
        
        # Collect enhanced k6 metrics from protocol_summary.json if available
        test_type = config.get('test_type', 'protocol') if config else 'protocol'
        if test_type in ['protocol', 'both']:
            protocol_summary_path = test_results_path.replace('test_report.json', 'protocol_summary.json')
            if os.path.exists(protocol_summary_path):
                try:
                    enhanced_metrics = self._collect_enhanced_k6_metrics(protocol_summary_path)
                    performance_data.update(enhanced_metrics)
                except Exception as e:
                    logger.warning(f"Could not collect enhanced k6 metrics: {e}")
        
        # Collect browser analysis data if available
        if test_type in ['browser', 'both']:
            browser_analysis_path = test_results_path.replace('test_report.json', 'browser_analysis_report.json')
            if os.path.exists(browser_analysis_path):
                try:
                    with open(browser_analysis_path, 'r') as f:
                        browser_analysis = json.load(f)
                        performance_data['browser_analysis'] = {
                            'overall_score': browser_analysis.get('overall_score', 'Unknown'),
                            'overall_grade': browser_analysis.get('overall_grade', 'Unknown'),
                            'core_web_vitals': browser_analysis.get('core_web_vitals', {}),
                            'navigation_timing': browser_analysis.get('navigation_timing', {}),
                            'resource_loading': browser_analysis.get('resource_loading', {}),
                            'user_interactions': browser_analysis.get('user_interactions', {}),
                            'performance_insights': browser_analysis.get('performance_insights', [])
                        }
                except Exception as e:
                    logger.warning(f"Could not load browser analysis: {e}")
        
        # Collect page resource analysis if available
        resource_analysis_path = test_results_path.replace('test_report.json', 'page_resource_analysis.json')
        if os.path.exists(resource_analysis_path):
            try:
                with open(resource_analysis_path, 'r') as f:
                    resource_analysis = json.load(f)
                    performance_data['page_resource_analysis'] = {
                        'total_resources': resource_analysis.get('summary', {}).get('total_resources', 'Unknown'),
                        'total_size_mb': resource_analysis.get('summary', {}).get('total_size', 0) / 1024 / 1024,
                        'total_load_time': resource_analysis.get('summary', {}).get('total_load_time', 'Unknown'),
                        'performance_score': resource_analysis.get('summary', {}).get('performance_score', 'Unknown'),
                        'issues': resource_analysis.get('issues', {}),
                        'resources': resource_analysis.get('resources', [])
                    }
            except Exception as e:
                logger.warning(f"Could not load page resource analysis: {e}")
        
        # Collect enhanced performance analysis if available
        enhanced_analysis_path = test_results_path.replace('test_report.json', 'enhanced_analysis_report.json')
        if os.path.exists(enhanced_analysis_path):
            try:
                with open(enhanced_analysis_path, 'r') as f:
                    enhanced_analysis = json.load(f)
                    performance_data['enhanced_analysis'] = {
                        'performance_score': enhanced_analysis.get('summary', {}).get('performance_score', 'Unknown'),
                        'total_issues': enhanced_analysis.get('summary', {}).get('total_issues', 'Unknown'),
                        'high_priority': enhanced_analysis.get('summary', {}).get('high_priority', 'Unknown'),
                        'medium_priority': enhanced_analysis.get('summary', {}).get('medium_priority', 'Unknown'),
                        'low_priority': enhanced_analysis.get('summary', {}).get('low_priority', 'Unknown'),
                        'issues': enhanced_analysis.get('issues', {}),
                        'recommendations': enhanced_analysis.get('recommendations', [])
                    }
            except Exception as e:
                logger.warning(f"Could not load enhanced analysis: {e}")
        
        # Generate AI insights with ALL available data
        ai_insights = self.openai_enhanced.generate_ai_insights(
            performance_data, config, technology_template
        )
        
        # Combine all analysis results in the structured format
        analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'enhanced_ai_analysis',
            'site_info': {
                'target': config.get('target'),
                'description': config.get('description'),
                'tags': config.get('tags', [])
            },
            'performance_issues': self._extract_performance_issues(performance_data),
            'ai_recommendations': {
                'summary': {
                    'overall_assessment': self._extract_overall_assessment(ai_insights),
                    'primary_concerns': self._extract_primary_concerns(performance_data),
                    'optimization_priority': self._determine_optimization_priority(performance_data),
                    'assumptions': self._extract_assumptions(ai_insights)
                },
                'recommendations': ai_insights.get('ai_recommendations', []),
                'technology_specific_insights': self._extract_technology_insights(technology_template)
            },
            'performance_analysis': {
                'overall_score': self._calculate_overall_score(performance_data),
                'performance_grade': self._calculate_performance_grade(performance_data),
                'key_metrics': performance_data.get('metrics_analysis', {}),
                'detailed_analysis': performance_data
            },
            'technology_template': technology_template,
            'recommendations': self._combine_recommendations(performance_data, ai_insights),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return analysis_result
    
    def _extract_performance_issues(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract performance issues from the data"""
        issues = []
        
        # Check for browser performance issues
        if 'browser_analysis' in performance_data:
            browser_data = performance_data['browser_analysis']
            if browser_data.get('performance_score', 100) < 80:
                issues.append({
                    "title": "Suboptimal Browser Performance",
                    "category": "Browser Performance",
                    "description": f"Browser performance score is {browser_data.get('performance_score', 'unknown')} (should be above 80)",
                    "priority": "medium",
                    "source": "browser_analysis"
                })
        
        return issues
    
    def _extract_overall_assessment(self, ai_insights: Dict[str, Any]) -> str:
        """Extract overall assessment from AI insights"""
        insights = ai_insights.get('ai_insights', '')
        if 'underperforming' in insights.lower():
            return "The application is underperforming in both backend and frontend metrics, particularly in LCP and TBT. Immediate optimizations are required to meet KPIs."
        elif 'excellent' in insights.lower():
            return "The application is performing well with good metrics across all areas."
        else:
            return "The application shows mixed performance with some areas requiring optimization."
    
    def _extract_primary_concerns(self, performance_data: Dict[str, Any]) -> List[str]:
        """Extract primary performance concerns"""
        concerns = []
        
        # Check response time
        metrics = performance_data.get('metrics_analysis', {})
        response_time = metrics.get('response_time', {})
        if response_time.get('grade') in ['D', 'F']:
            concerns.append("Response time is above acceptable thresholds.")
        
        # Check error rate
        error_rate = metrics.get('error_rate', {})
        if error_rate.get('grade') in ['D', 'F']:
            concerns.append("Error rate is above acceptable levels.")
        
        # Check throughput
        throughput = metrics.get('throughput', {})
        if throughput.get('grade') in ['D', 'F']:
            concerns.append("Throughput is below desired levels.")
        
        # Check browser performance
        if 'browser_analysis' in performance_data:
            browser_data = performance_data['browser_analysis']
            if browser_data.get('performance_score', 100) < 80:
                concerns.append("Browser performance metrics indicate optimization opportunities.")
        
        return concerns if concerns else ["No major performance concerns identified."]
    
    def _determine_optimization_priority(self, performance_data: Dict[str, Any]) -> str:
        """Determine optimization priority based on performance data"""
        metrics = performance_data.get('metrics_analysis', {})
        grades = [metrics.get('response_time', {}).get('grade', 'A'),
                 metrics.get('error_rate', {}).get('grade', 'A'),
                 metrics.get('throughput', {}).get('grade', 'A')]
        
        if any(grade in ['D', 'F'] for grade in grades):
            return "High"
        elif any(grade == 'C' for grade in grades):
            return "Medium"
        else:
            return "Low"
    
    def _extract_assumptions(self, ai_insights: Dict[str, Any]) -> List[str]:
        """Extract assumptions from AI insights"""
        return [
            "The telemetry data provided is accurate and reflects the current performance state.",
            "The application is properly configured for the expected load patterns."
        ]
    
    def _extract_technology_insights(self, technology_template: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract technology-specific insights"""
        if not technology_template:
            return {}
        
        return {
            "svelte": {
                "key_optimizations": [
                    "Implement component lazy loading",
                    "Optimize bundle size with tree shaking",
                    "Use SvelteKit for SSR/SSG when applicable"
                ],
                "common_pitfalls": [
                    "Large bundle sizes due to poor code splitting",
                    "Slow initial load times",
                    "Hydration issues with SSR"
                ],
                "best_practices": [
                    "Use Svelte's built-in reactivity efficiently",
                    "Implement proper error boundaries",
                    "Optimize component lifecycle methods"
                ]
            },
            "strapi": {
                "key_optimizations": [
                    "Implement API response caching",
                    "Optimize database queries",
                    "Use content delivery optimization"
                ],
                "common_pitfalls": [
                    "Slow API responses due to inefficient queries",
                    "Database bottlenecks",
                    "Content loading delays"
                ],
                "best_practices": [
                    "Use proper indexing on database fields",
                    "Implement rate limiting",
                    "Cache frequently accessed content"
                ]
            },
            "azure_app_service": {
                "key_optimizations": [
                    "Configure auto-scaling rules",
                    "Use appropriate performance tiers",
                    "Optimize deployment strategies"
                ],
                "common_pitfalls": [
                    "Cold start issues",
                    "Memory and CPU constraints",
                    "Inefficient scaling policies"
                ],
                "best_practices": [
                    "Use always-on for production",
                    "Implement health checks",
                    "Monitor resource usage"
                ]
            },
            "cdn_front_door": {
                "key_optimizations": [
                    "Configure proper caching rules",
                    "Use edge optimization",
                    "Implement compression"
                ],
                "common_pitfalls": [
                    "Incorrect cache expiration policies",
                    "Over-caching dynamic content"
                ],
                "best_practices": [
                    "Use versioning for static assets",
                    "Regularly review CDN performance"
                ]
            }
        }
    
    def _combine_recommendations(self, performance_data: Dict[str, Any], ai_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combine recommendations from different sources"""
        recommendations = ai_insights.get('ai_recommendations', [])
        
        # Add any additional recommendations based on performance data
        if 'enhanced_analysis' in performance_data:
            enhanced_recs = performance_data['enhanced_analysis'].get('recommendations', [])
            recommendations.extend(enhanced_recs)
        
        return recommendations
    
    def _collect_enhanced_k6_metrics(self, summary_path: str) -> Dict[str, Any]:
        """Collect detailed k6 metrics from summary.json"""
        enhanced_data = {}
        
        try:
            with open(summary_path, 'r') as f:
                metrics_data = []
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get('type') == 'Point':
                            metrics_data.append(data)
                    except json.JSONDecodeError:
                        continue
            
            # Group metrics by type
            metrics_by_name = {}
            for data in metrics_data:
                metric_name = data.get('metric', 'unknown')
                if metric_name not in metrics_by_name:
                    metrics_by_name[metric_name] = []
                metrics_by_name[metric_name].append(data)
            
            # Extract HTTP timing metrics
            timing_metrics = {
                'http_req_blocked': 'dns_connection_pool',
                'http_req_connecting': 'tcp_connection',
                'http_req_tls_handshaking': 'tls_handshake',
                'http_req_sending': 'request_sending',
                'http_req_waiting': 'server_processing',
                'http_req_receiving': 'response_receiving'
            }
            
            http_timing = {}
            for metric, key in timing_metrics.items():
                if metric in metrics_by_name:
                    values = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name[metric]]
                    if values:
                        http_timing[key] = {
                            'average': sum(values) / len(values),
                            'max': max(values),
                            'p95': sorted(values)[int(len(values) * 0.95)]
                        }
            
            if http_timing:
                enhanced_data['http_timing_analysis'] = http_timing
            
            # Extract data transfer metrics
            if 'data_sent' in metrics_by_name and 'data_received' in metrics_by_name:
                sent_values = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['data_sent']]
                received_values = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['data_received']]
                
                if sent_values and received_values:
                    enhanced_data['data_transfer_analysis'] = {
                        'data_sent': {
                            'average': sum(sent_values) / len(sent_values),
                            'total': sum(sent_values)
                        },
                        'data_received': {
                            'average': sum(received_values) / len(received_values),
                            'average_kb': (sum(received_values) / len(received_values)) / 1024,
                            'total': sum(received_values)
                        }
                    }
            
            # Extract load distribution metrics
            if 'vus' in metrics_by_name:
                vus_values = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['vus']]
                if vus_values:
                    enhanced_data['load_distribution'] = {
                        'average_vus': sum(vus_values) / len(vus_values),
                        'max_vus': max(vus_values),
                        'distribution_quality': 'Good' if max(vus_values) > 0 and (sum(vus_values) / len(vus_values)) / max(vus_values) > 0.5 else 'Uneven'
                    }
            
            # Extract error analysis
            if 'http_req_failed' in metrics_by_name:
                failed_values = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['http_req_failed']]
                if failed_values:
                    error_rate = sum(failed_values) / len(failed_values)
                    enhanced_data['error_analysis'] = {
                        'error_rate': error_rate * 100,
                        'error_types': ['HTTP failures'] if error_rate > 0 else [],
                        'failure_patterns': 'Consistent failures' if error_rate > 0.05 else 'No significant failures'
                    }
            
        except Exception as e:
            logger.warning(f"Error collecting enhanced k6 metrics: {e}")
        
        return enhanced_data
    
    def _grade_response_time(self, value: float) -> str:
        """Grade response time (ms)"""
        if value < 100:
            return "A"
        elif value < 200:
            return "B"
        elif value < 500:
            return "C"
        elif value < 1000:
            return "D"
        else:
            return "F"
    
    def _grade_error_rate(self, value: float) -> str:
        """Grade error rate (%)"""
        if value < 1:
            return "A"
        elif value < 5:
            return "B"
        elif value < 10:
            return "C"
        elif value < 20:
            return "D"
        else:
            return "F"
    
    def _grade_throughput(self, value: float) -> str:
        """Grade throughput (req/s)"""
        if value > 1000:
            return "A"
        elif value > 500:
            return "B"
        elif value > 100:
            return "C"
        elif value > 50:
            return "D"
        else:
            return "F"
    
    def _calculate_overall_score(self, performance_data: Dict[str, Any]) -> float:
        """Calculate overall performance score based on key metrics"""
        response_time_score = self._grade_to_score(performance_data['metrics_analysis']['response_time']['grade'])
        error_rate_score = self._grade_to_score(performance_data['metrics_analysis']['error_rate']['grade'])
        throughput_score = self._grade_to_score(performance_data['metrics_analysis']['throughput']['grade'])
        
        # Simple weighted average for now, adjust weights as needed
        return (response_time_score * 0.4 + error_rate_score * 0.3 + throughput_score * 0.3)
    
    def _calculate_performance_grade(self, performance_data: Dict[str, Any]) -> str:
        """Calculate overall performance grade based on key metrics"""
        response_time_grade = performance_data['metrics_analysis']['response_time']['grade']
        error_rate_grade = performance_data['metrics_analysis']['error_rate']['grade']
        throughput_grade = performance_data['metrics_analysis']['throughput']['grade']
        
        # Simple weighted average for now, adjust weights as needed
        return self._grade_to_grade(response_time_grade, error_rate_grade, throughput_grade)
    
    def _grade_to_score(self, grade: str) -> float:
        """Convert grade (A, B, C, D, F) to a score (0-100)"""
        if grade == "A":
            return 100
        elif grade == "B":
            return 80
        elif grade == "C":
            return 60
        elif grade == "D":
            return 40
        else: # F
            return 20
    
    def _grade_to_grade(self, response_time_grade: str, error_rate_grade: str, throughput_grade: str) -> str:
        """Combine grades into a single overall grade"""
        # Simple weighted average for now, adjust weights as needed
        return self._grade_to_grade_weighted(response_time_grade, error_rate_grade, throughput_grade)
    
    def _grade_to_grade_weighted(self, response_time_grade: str, error_rate_grade: str, throughput_grade: str) -> str:
        """Combine grades into a single overall grade (weighted)"""
        # Example: response_time_grade (40%), error_rate_grade (30%), throughput_grade (30%)
        # This is a placeholder and needs actual weighting logic
        # For now, let's assume a simple average or a more complex weighted sum
        # Let's use a weighted sum for simplicity, where A is 100, B is 80, etc.
        response_time_weight = 40
        error_rate_weight = 30
        throughput_weight = 30
        
        response_time_score = self._grade_to_score(response_time_grade)
        error_rate_score = self._grade_to_score(error_rate_grade)
        throughput_score = self._grade_to_score(throughput_grade)
        
        overall_score = (response_time_score * response_time_weight + error_rate_score * error_rate_weight + throughput_score * throughput_weight) / (response_time_weight + error_rate_weight + throughput_weight)
        
        if overall_score >= 90:
            return "A"
        elif overall_score >= 80:
            return "B"
        elif overall_score >= 70:
            return "C"
        elif overall_score >= 60:
            return "D"
        else:
            return "F"
    
    def _combine_recommendations(self, performance_data: Dict[str, Any], ai_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combine base recommendations with AI recommendations, prioritizing AI ones"""
        # Get AI recommendations
        ai_recommendations = ai_insights.get("ai_recommendations", [])
        
        # Add AI recommendations with source marking
        for rec in ai_recommendations:
            rec["source"] = "AI Analysis"
        
        # For now, just return AI recommendations
        # In the future, we could combine with rule-based recommendations
        return ai_recommendations
    
    def _get_technology_template(self, site_tags: List[str]) -> Optional[Dict[str, Any]]:
        """Get technology template for AI context"""
        return self.base_agent.template_manager.select_template(site_tags)

def main():
    """Main function for standalone execution"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python openai_enhanced_agent.py <test_results_path> [config_path]")
        print("\nNote: Set OPENAI_API_KEY environment variable for AI analysis")
        sys.exit(1)
    
    test_results_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else "examples/pop_website_test.yaml"
    
    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # Run enhanced analysis
    agent = EnhancedAIAnalysisAgent()
    report = agent.analyze_test_results(test_results_path, config)
    
    # Save report
    output_path = "output/enhanced_ai_analysis_report.json"
    Path("output").mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Enhanced AI Analysis complete! Report saved to: {output_path}")
    print(f"Performance Grade: {report['performance_analysis']['performance_grade']}")
    print(f"Overall Score: {report['performance_analysis']['overall_score']:.1f}/100")
    print(f"AI Recommendations: {len(report.get('ai_analysis', {}).get('ai_recommendations', []))}")
    
    if not OPENAI_AVAILABLE:
        print("\n⚠️  OpenAI not available - install with: pip install openai")
    elif not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY not set - AI analysis will be limited")

if __name__ == "__main__":
    main() 