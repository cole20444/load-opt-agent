# Scripts Directory

This directory contains utility scripts for the Load Testing & Optimization Agent.

## Available Scripts

### `list_test_results.py`
Lists and navigates test results in the organized output structure.

**Usage:**
```bash
python scripts/list_test_results.py
python scripts/list_test_results.py --latest
python scripts/list_test_results.py --site <site_name>
```

### `generate_readable_report.py`
Converts JSON analysis data into human-readable formats (HTML, Markdown, Console).

**Usage:**
```bash
python scripts/generate_readable_report.py <ai_analysis_report.json>
```

**Output:**
- `{filename}_report.html` - Beautiful HTML report with styling and interactive elements
- `{filename}_report.md` - Markdown report for easy reading
- Console summary with key metrics and top recommendations

**Features:**
- Responsive HTML design with modern styling
- Color-coded priority badges and performance grades
- Interactive elements and clean typography
- Comprehensive data visualization
- Technology-specific insights section

### Analysis Scripts

#### `analyze_k6_metrics.py`
Analyzes k6 metrics and generates performance insights.

#### `enhanced_performance_analyzer.py`
Performs enhanced performance analysis with detailed metrics.

#### `page_resource_analyzer.py`
Analyzes page resources and identifies optimization opportunities.

### Testing Scripts

#### `test_system.py`
Tests the entire system end-to-end.

#### `test_ai_analysis.py`
Tests the AI analysis functionality.

#### `test_openai_integration.py`
Tests OpenAI API integration.

### Utility Scripts

#### `parse_results.py`
Parses and formats test results.

#### `show_ai_prompts.py`
Shows the actual prompts sent to OpenAI for review.

#### `show_template_usage.py`
Shows how technology templates are used in analysis. 