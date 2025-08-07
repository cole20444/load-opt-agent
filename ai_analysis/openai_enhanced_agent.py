#!/usr/bin/env python3
"""
OpenAI-Enhanced AI Analysis Agent
Integrates GPT-4 for intelligent performance analysis and recommendations
"""

import os
import yaml
import json
import logging
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
    """Enhanced analysis using OpenAI GPT-4"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key and OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            logger.warning("OpenAI not available - using rule-based analysis only")
    
    def generate_ai_insights(self, 
                           performance_data: Dict[str, Any],
                           site_config: Dict[str, Any],
                           technology_template: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate AI-powered insights using GPT-4"""
        
        if not self.client:
            return {"ai_insights": "OpenAI not available", "ai_recommendations": []}
        
        try:
            # Build comprehensive prompt
            prompt = self._build_ai_prompt(performance_data, site_config, technology_template)
            
            # Generate AI response
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
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
            
            # Parse AI response into structured format
            structured_insights = self._parse_ai_response(ai_response)
            
            return {
                "ai_insights": ai_response,
                "ai_recommendations": structured_insights.get("recommendations", []),
                "ai_analysis": structured_insights.get("analysis", {}),
                "ai_priorities": structured_insights.get("priorities", [])
            }
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return {
                "ai_insights": f"AI analysis failed: {str(e)}",
                "ai_recommendations": [],
                "ai_analysis": {},
                "ai_priorities": []
            }
    
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

        # Include load distribution analysis
        if 'load_distribution' in performance_data:
            load = performance_data['load_distribution']
            prompt += f"""
## Load Distribution Analysis
- **Average VUs**: {load.get('average_vus', 'Unknown')}
- **Max VUs**: {load.get('max_vus', 'Unknown')}
- **Load Distribution**: {load.get('distribution_quality', 'Unknown')}
"""

        # Include error pattern analysis
        if 'error_analysis' in performance_data:
            errors = performance_data['error_analysis']
            prompt += f"""
## Error Pattern Analysis
- **Error Rate**: {errors.get('error_rate', 'Unknown')}%
- **Error Types**: {', '.join(errors.get('error_types', []))}
- **Failure Patterns**: {errors.get('failure_patterns', 'None detected')}
"""

        prompt += f"""
## Technology Context
"""
        
        if technology_template:
            prompt += f"""
- **Template**: {technology_template.get('name', 'Unknown')}
- **Template Description**: {technology_template.get('description', 'No description')}
- **Relevant Patterns**: {len(technology_template.get('performance_patterns', {}))} categories

## Technology-Specific Optimization Patterns
"""
            
            # Include detailed optimization patterns from the template
            performance_patterns = technology_template.get('performance_patterns', {})
            for category, patterns in performance_patterns.items():
                prompt += f"\n### {category.title()} Optimizations:\n"
                for pattern in patterns:
                    prompt += f"- **{pattern.get('name', 'Unknown')}**: {pattern.get('description', 'No description')}\n"
                    recommendations = pattern.get('recommendations', [])
                    if recommendations:
                        prompt += f"  - Key recommendations: {', '.join(recommendations[:3])}\n"
                        if len(recommendations) > 3:
                            prompt += f"  - Additional: {len(recommendations) - 3} more recommendations available\n"
        
        prompt += f"""
## Comprehensive Analysis Request

You now have access to ALL available performance data including:
1. **Basic k6 metrics** (response time, error rate, throughput)
2. **Detailed HTTP timing breakdown** (DNS, TCP, TLS, server processing, data transfer)
3. **Page resource analysis** (images, scripts, CSS, fonts, APIs with specific issues)
4. **Enhanced performance analysis** (detailed issue categorization)
5. **Load distribution patterns** (VU scaling and distribution)
6. **Error pattern analysis** (failure types and patterns)
7. **Technology-specific optimization patterns** (Svelte, Strapi, Azure specific)

Please provide a comprehensive performance analysis including:

1. **Performance Assessment**: What do ALL these metrics tell us about the site's performance?
2. **Root Cause Analysis**: Based on the detailed timing breakdown and resource analysis, what are the specific bottlenecks?
3. **Technology-Specific Recommendations**: 
   - Build upon the optimization patterns provided above
   - Prioritize recommendations that align with the specific technology stack
   - Consider ALL the performance data when selecting which patterns to focus on
   - Address specific resource issues identified (large images, missing compression, etc.)
4. **Priority Actions**: List 5-7 high-impact, actionable recommendations in order of priority
5. **Implementation Guidance**: For each recommendation, provide specific implementation steps
6. **Expected Impact**: Estimate the performance improvement for each recommendation

**Important**: Use ALL the data provided above. The detailed HTTP timing, resource analysis, and technology patterns should guide your analysis. Be specific about which metrics indicate which issues.

Format your response as JSON with the following structure:
{{
    "analysis": {{
        "performance_assessment": "Overall assessment based on ALL metrics",
        "root_causes": ["Specific bottlenecks identified from timing and resource analysis"],
        "strengths": ["What's working well based on the data"],
        "weaknesses": ["What needs improvement based on specific metrics"],
        "key_insights": ["Important findings from the detailed analysis"]
    }},
    "recommendations": [
        {{
            "title": "Recommendation title",
            "description": "Detailed description",
            "priority": "High/Medium/Low",
            "impact": "High/Medium/Low",
            "effort": "High/Medium/Low",
            "implementation": ["Step 1", "Step 2", "Step 3"],
            "technology_focus": "Frontend/Backend/Infrastructure",
            "expected_improvement": "Estimated performance gain",
            "data_support": "Which specific metrics support this recommendation"
        }}
    ],
    "priorities": ["Priority 1", "Priority 2", "Priority 3"],
    "summary": {{
        "overall_score": "Current performance score",
        "target_score": "Expected score after optimizations",
        "biggest_impact": "Which optimization will have the biggest impact",
        "quick_wins": ["Low effort, high impact improvements"]
    }}
}}

Be specific, technical, and actionable. Reference specific metrics and data points in your analysis. Focus on practical improvements that can be implemented based on the detailed data provided.
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
                'total_requests': test_results.get('http_reqs', {}).get('count', 'Unknown')
            },
            'metrics_analysis': {
                'response_time': {
                    'value': test_results.get('http_req_duration', {}).get('avg', 'Unknown'),
                    'grade': self._grade_response_time(test_results.get('http_req_duration', {}).get('avg', 0))
                },
                'error_rate': {
                    'value': test_results.get('http_req_failed', {}).get('rate', 0) * 100,
                    'grade': self._grade_error_rate(test_results.get('http_req_failed', {}).get('rate', 0))
                },
                'throughput': {
                    'value': test_results.get('http_reqs', {}).get('rate', 'Unknown'),
                    'grade': self._grade_throughput(test_results.get('http_reqs', {}).get('rate', 0))
                }
            }
        }
        
        # Collect enhanced k6 metrics from summary.json if available
        summary_path = test_results_path.replace('test_report.json', 'summary.json')
        if os.path.exists(summary_path):
            try:
                enhanced_metrics = self._collect_enhanced_k6_metrics(summary_path)
                performance_data.update(enhanced_metrics)
            except Exception as e:
                logger.warning(f"Could not collect enhanced k6 metrics: {e}")
        
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
        
        # Combine all analysis results
        analysis_result = {
            'test_configuration': config,
            'test_results': test_results,
            'performance_analysis': {
                'overall_score': self._calculate_overall_score(performance_data),
                'performance_grade': self._calculate_performance_grade(performance_data),
                'key_metrics': performance_data.get('metrics_analysis', {}),
                'detailed_analysis': performance_data
            },
            'ai_analysis': ai_insights,
            'technology_template': technology_template,
            'recommendations': self._combine_recommendations(performance_data, ai_insights),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return analysis_result
    
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