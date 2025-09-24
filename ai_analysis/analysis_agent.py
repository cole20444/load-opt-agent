#!/usr/bin/env python3
"""
AI Analysis Agent for Load Testing & Optimization
Processes test results and generates optimization recommendations
"""

import yaml
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnologyTemplateManager:
    """Manages technology templates for AI analysis"""
    
    def __init__(self, templates_path: str = "ai_analysis/technology_templates.yaml"):
        self.templates_path = templates_path
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load technology templates from YAML file"""
        try:
            with open(self.templates_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Templates file not found: {self.templates_path}")
            return {"templates": {}, "selection_rules": []}
    
    def select_template(self, site_tags: List[str]) -> Optional[Dict[str, Any]]:
        """Select the best matching template based on site tags"""
        if not site_tags:
            return None
        
        best_match = None
        best_score = 0
        
        for template_id, template in self.templates.get("templates", {}).items():
            template_tags = template.get("tags", [])
            score = self._calculate_match_score(site_tags, template_tags)
            
            if score > best_score:
                best_score = score
                best_match = template
                best_match["id"] = template_id
        
        logger.info(f"Selected template: {best_match.get('name', 'Unknown')} (score: {best_score})")
        return best_match if best_score > 0 else None
    
    def _calculate_match_score(self, site_tags: List[str], template_tags: List[str]) -> float:
        """Calculate how well site tags match template tags"""
        if not template_tags:
            return 0
        
        site_tags_set = set(tag.lower() for tag in site_tags)
        template_tags_set = set(tag.lower() for tag in template_tags)
        
        # Calculate intersection
        matches = len(site_tags_set.intersection(template_tags_set))
        
        # Score based on percentage of template tags matched
        return matches / len(template_tags_set)

class PerformanceAnalyzer:
    """Analyzes performance metrics and identifies optimization opportunities"""
    
    def __init__(self):
        # Performance thresholds (can be made configurable)
        self.thresholds = {
            "response_time": {
                "excellent": 200,  # ms
                "good": 500,
                "poor": 1000
            },
            "error_rate": {
                "excellent": 0.01,  # 1%
                "good": 0.05,       # 5%
                "poor": 0.10        # 10%
            },
            "throughput": {
                "excellent": 100,   # req/s
                "good": 50,
                "poor": 10
            }
        }
    
    def analyze_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics and return insights"""
        analysis = {
            "overall_score": 0,
            "performance_grade": "Unknown",
            "key_insights": [],
            "optimization_opportunities": [],
            "metrics_analysis": {}
        }
        
        # Analyze response time
        if "http_req_duration" in metrics:
            avg_response_time = metrics["http_req_duration"].get("avg", 0)
            analysis["metrics_analysis"]["response_time"] = {
                "value": avg_response_time,
                "grade": self._grade_metric(avg_response_time, "response_time"),
                "insight": self._get_response_time_insight(avg_response_time)
            }
        
        # Analyze error rate
        if "http_req_failed" in metrics:
            error_rate = metrics["http_req_failed"].get("rate", 0)
            analysis["metrics_analysis"]["error_rate"] = {
                "value": error_rate,
                "grade": self._grade_metric(error_rate, "error_rate"),
                "insight": self._get_error_rate_insight(error_rate)
            }
        
        # Analyze throughput
        if "http_reqs" in metrics:
            throughput = metrics["http_reqs"].get("rate", 0)
            analysis["metrics_analysis"]["throughput"] = {
                "value": throughput,
                "grade": self._grade_metric(throughput, "throughput"),
                "insight": self._get_throughput_insight(throughput)
            }
        
        # Calculate overall score
        analysis["overall_score"] = self._calculate_overall_score(analysis["metrics_analysis"])
        analysis["performance_grade"] = self._grade_overall_performance(analysis["overall_score"])
        
        return analysis
    
    def _grade_metric(self, value: float, metric_type: str) -> str:
        """Grade a metric based on thresholds"""
        thresholds = self.thresholds.get(metric_type, {})
        
        if metric_type == "response_time":
            if value <= thresholds.get("excellent", 200):
                return "A"
            elif value <= thresholds.get("good", 500):
                return "B"
            elif value <= thresholds.get("poor", 1000):
                return "C"
            else:
                return "D"
        elif metric_type == "error_rate":
            if value <= thresholds.get("excellent", 0.01):
                return "A"
            elif value <= thresholds.get("good", 0.05):
                return "B"
            elif value <= thresholds.get("poor", 0.10):
                return "C"
            else:
                return "D"
        elif metric_type == "throughput":
            if value >= thresholds.get("excellent", 100):
                return "A"
            elif value >= thresholds.get("good", 50):
                return "B"
            elif value >= thresholds.get("poor", 10):
                return "C"
            else:
                return "D"
        
        return "Unknown"
    
    def _get_response_time_insight(self, response_time: float) -> str:
        """Generate insight for response time"""
        if response_time <= 200:
            return "Excellent response time! Your application is performing very well."
        elif response_time <= 500:
            return "Good response time. Consider minor optimizations for better performance."
        elif response_time <= 1000:
            return "Response time needs improvement. Focus on backend optimization and caching."
        else:
            return "Poor response time. Immediate optimization required for better user experience."
    
    def _get_error_rate_insight(self, error_rate: float) -> str:
        """Generate insight for error rate"""
        if error_rate <= 0.01:
            return "Excellent reliability! Very few errors occurring."
        elif error_rate <= 0.05:
            return "Good reliability. Monitor for potential issues."
        elif error_rate <= 0.10:
            return "Error rate is concerning. Investigate and fix issues."
        else:
            return "High error rate. Critical issues need immediate attention."
    
    def _get_throughput_insight(self, throughput: float) -> str:
        """Generate insight for throughput"""
        if throughput >= 100:
            return "Excellent throughput! Your application can handle high load."
        elif throughput >= 50:
            return "Good throughput. Consider scaling for higher loads."
        elif throughput >= 10:
            return "Moderate throughput. Optimization needed for better scalability."
        else:
            return "Low throughput. Significant optimization required."
    
    def _calculate_overall_score(self, metrics_analysis: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        if not metrics_analysis:
            return 0
        
        total_score = 0
        count = 0
        
        for metric, analysis in metrics_analysis.items():
            grade = analysis.get("grade", "Unknown")
            if grade == "A":
                total_score += 100
            elif grade == "B":
                total_score += 75
            elif grade == "C":
                total_score += 50
            elif grade == "D":
                total_score += 25
            count += 1
        
        return total_score / count if count > 0 else 0
    
    def _grade_overall_performance(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

class AIAnalysisAgent:
    """Main AI Analysis Agent that orchestrates the analysis process"""
    
    def __init__(self, use_enhanced_analysis: bool = True):
        self.template_manager = TechnologyTemplateManager()
        self.performance_analyzer = PerformanceAnalyzer()
        self.use_enhanced_analysis = use_enhanced_analysis
        
        # Import enhanced AI agent if available
        if use_enhanced_analysis:
            try:
                from .enhanced_ai_agent import EnhancedAIAnalysisAgent
                self.enhanced_agent = EnhancedAIAnalysisAgent()
            except ImportError:
                logger.warning("Enhanced AI agent not available, falling back to basic analysis")
                self.enhanced_agent = None
        else:
            self.enhanced_agent = None
    
    def analyze_test_results(self, 
                           test_results_path: str,
                           config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results and generate optimization recommendations"""
        
        logger.info("Starting AI analysis of test results...")
        
        # Load test results
        test_results = self._load_test_results(test_results_path)
        if not test_results:
            return {"error": "Failed to load test results"}
        
        # Select appropriate technology template
        site_tags = config.get("tags", [])
        template = self.template_manager.select_template(site_tags)
        
        # Analyze performance metrics
        performance_analysis = self.performance_analyzer.analyze_metrics(test_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            performance_analysis, 
            template, 
            config
        )
        
        # Create comprehensive report
        report = {
            "timestamp": datetime.now().isoformat(),
            "site_info": {
                "target": config.get("target"),
                "description": config.get("description"),
                "tags": config.get("tags", [])
            },
            "test_summary": {
                "total_requests": test_results.get("http_reqs", {}).get("count", 0),
                "duration": config.get("duration"),
                "virtual_users": config.get("vus")
            },
            "performance_analysis": performance_analysis,
            "technology_template": template.get("name") if template else "Generic",
            "recommendations": recommendations,
            "raw_metrics": test_results
        }
        
        logger.info(f"Analysis complete. Performance Grade: {performance_analysis['performance_grade']}")
        return report
    
    def _load_test_results(self, results_path: str) -> Optional[Dict[str, Any]]:
        """Load and parse k6 test results"""
        try:
            # For now, we'll use the summary format from our parse_results.py
            # In a full implementation, we'd parse the full k6 JSON output
            with open(results_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to load test results: {e}")
            return None
    
    def _generate_recommendations(self, 
                                performance_analysis: Dict[str, Any],
                                template: Optional[Dict[str, Any]],
                                config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis and template"""
        
        recommendations = []
        
        # Add general recommendations based on performance analysis
        for metric, analysis in performance_analysis.get("metrics_analysis", {}).items():
            grade = analysis.get("grade", "Unknown")
            insight = analysis.get("insight", "")
            
            if grade in ["C", "D"]:
                recommendations.append({
                    "category": "Performance",
                    "priority": "High" if grade == "D" else "Medium",
                    "title": f"Improve {metric.replace('_', ' ').title()}",
                    "description": insight,
                    "impact": "High" if grade == "D" else "Medium",
                    "effort": "Medium"
                })
        
        # Add technology-specific recommendations if template is available
        if template:
            template_recommendations = self._get_template_recommendations(
                template, performance_analysis
            )
            recommendations.extend(template_recommendations)
        
        # Sort by priority
        priority_order = {"High": 3, "Medium": 2, "Low": 1}
        recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "Low"), 0), reverse=True)
        
        return recommendations
    
    def _get_template_recommendations(self, 
                                    template: Dict[str, Any],
                                    performance_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get technology-specific recommendations from template"""
        
        recommendations = []
        
        for category, patterns in template.get("performance_patterns", {}).items():
            for pattern in patterns:
                # Check if this pattern is relevant based on current metrics
                relevant_metrics = pattern.get("metrics", [])
                is_relevant = self._is_pattern_relevant(relevant_metrics, performance_analysis)
                
                if is_relevant:
                    for rec in pattern.get("recommendations", []):
                        recommendations.append({
                            "category": category.title(),
                            "priority": "Medium",
                            "title": pattern["name"],
                            "description": rec,
                            "impact": "Medium",
                            "effort": "Medium",
                            "technology": template.get("name")
                        })
        
        return recommendations
    
    def _is_pattern_relevant(self, 
                           pattern_metrics: List[str],
                           performance_analysis: Dict[str, Any]) -> bool:
        """Check if a pattern is relevant based on current performance metrics"""
        
        metrics_analysis = performance_analysis.get("metrics_analysis", {})
        
        for metric in pattern_metrics:
            if metric in metrics_analysis:
                grade = metrics_analysis[metric].get("grade", "Unknown")
                if grade in ["C", "D"]:
                    return True
        
        return False
    
    def analyze_with_enhanced_data(self,
                                 enhanced_analysis_path: str,
                                 browser_analysis_path: str,
                                 config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using enhanced performance analysis data"""
        
        logger.info("Starting enhanced AI analysis...")
        
        # Load enhanced analysis data
        try:
            with open(enhanced_analysis_path, 'r') as f:
                enhanced_analysis = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load enhanced analysis: {e}")
            enhanced_analysis = {}
        
        try:
            with open(browser_analysis_path, 'r') as f:
                browser_analysis = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load browser analysis: {e}")
            browser_analysis = {}
        
        # Use enhanced AI agent if available
        if self.enhanced_agent:
            # Load protocol and browser metrics to get performance deductions
            protocol_metrics = None
            browser_metrics = None
            
            # Try to load protocol metrics
            try:
                protocol_file = os.path.join(os.path.dirname(enhanced_analysis_path), "protocol_summary.json")
                if os.path.exists(protocol_file):
                    with open(protocol_file, 'r') as f:
                        protocol_data = json.load(f)
                    # Extract metrics using the same logic as the HTML report generator
                    protocol_metrics = self._extract_metrics_from_data(protocol_data)
            except Exception as e:
                logger.warning(f"Could not load protocol metrics: {e}")
            
            # Try to load browser metrics
            try:
                browser_file = os.path.join(os.path.dirname(enhanced_analysis_path), "browser_summary.json")
                if os.path.exists(browser_file):
                    with open(browser_file, 'r') as f:
                        browser_data = json.load(f)
                    # Extract metrics using the same logic as the HTML report generator
                    browser_metrics = self._extract_metrics_from_data(browser_data)
            except Exception as e:
                logger.warning(f"Could not load browser metrics: {e}")
            
            return self.enhanced_agent.analyze_with_enhanced_recommendations(
                enhanced_analysis, browser_analysis, config, protocol_metrics, browser_metrics
            )
    
    def _extract_metrics_from_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from k6/Playwright summary data"""
        metrics = {}
        
        if 'metrics' in data:
            metrics_data = data['metrics']
            
            # Extract protocol metrics
            if 'http_req_duration' in metrics_data:
                duration_metric = metrics_data['http_req_duration']
                metrics['avg_response_time'] = duration_metric.get('avg', 0)
                metrics['p95_response_time'] = duration_metric.get('p95', 0)
                metrics['p99_response_time'] = duration_metric.get('p99', 0)
            
            if 'http_req_failed' in metrics_data:
                failed_metric = metrics_data['http_req_failed']
                metrics['error_rate'] = failed_metric.get('rate', 0)
            
            if 'http_reqs' in metrics_data:
                reqs_metric = metrics_data['http_reqs']
                metrics['throughput'] = reqs_metric.get('rate', 0)
            
            # Extract Playwright metrics
            if 'playwright_page_load_time' in metrics_data:
                page_load_metric = metrics_data['playwright_page_load_time']
                metrics['playwright_page_load_time'] = {
                    'avg': page_load_metric.get('avg', 0),
                    'p95': page_load_metric.get('p95', 0),
                    'p99': page_load_metric.get('p99', 0)
                }
            
            if 'playwright_iterations' in metrics_data:
                iterations_metric = metrics_data['playwright_iterations']
                metrics['playwright_iterations'] = {
                    'count': iterations_metric.get('count', 0),
                    'rate': iterations_metric.get('rate', 0)
                }
        
        return metrics

def main():
    """Main function for standalone execution"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analysis_agent.py <test_results_path> [config_path]")
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
    
    # Run analysis
    agent = AIAnalysisAgent()
    report = agent.analyze_test_results(test_results_path, config)
    
    # Save report
    output_path = "output/ai_analysis_report.json"
    Path("output").mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"AI Analysis complete! Report saved to: {output_path}")
    print(f"Performance Grade: {report['performance_analysis']['performance_grade']}")
    print(f"Overall Score: {report['performance_analysis']['overall_score']:.1f}/100")

if __name__ == "__main__":
    main() 