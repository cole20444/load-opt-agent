# Scripts Directory

This directory contains the core analysis and report generation scripts for the Load Testing & Optimization Agent.

## Core Analysis Scripts

### `enhanced_performance_analyzer.py`
Performs comprehensive protocol-level performance analysis with detailed metrics including:
- HTTP request duration percentiles (P50, P75, P90, P95, P99)
- Connection breakdown analysis (DNS, TCP, TLS, waiting, receiving)
- Data transfer metrics (bytes sent/received)
- Status code distribution
- Virtual user and iteration analysis

**Usage:**
```bash
python scripts/enhanced_performance_analyzer.py <protocol_summary.json>
```

### `browser_metrics_analyzer.py`
Analyzes browser-level performance metrics including:
- Core Web Vitals (FCP, LCP, FID, CLS, TTI, TBT)
- Page load performance analysis
- Resource loading optimization
- Performance issue detection and scoring

**Usage:**
```bash
python scripts/browser_metrics_analyzer.py <browser_summary.json>
```

### `page_resource_analyzer.py`
Analyzes page resources and identifies optimization opportunities:
- Resource type analysis (CSS, JS, images, fonts)
- Compression and caching analysis
- Performance bottleneck identification
- Optimization recommendations

**Usage:**
```bash
python scripts/page_resource_analyzer.py <target_url>
```

## Report Generation Scripts

### `generate_k6_html_report.py`
Generates comprehensive HTML reports with interactive Plotly visualizations:
- Protocol and browser test results
- Interactive charts and graphs
- Performance metrics and insights
- Modern, responsive UI design

**Usage:**
```bash
python scripts/generate_k6_html_report.py <output_directory>
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

### `generate_manual_report.py`
Fallback HTML report generator that works directly from analysis JSON files:
- Loads enhanced_analysis_report.json and browser_summary_analysis.json
- Generates comprehensive HTML report with all metrics
- Useful if primary HTML report generation fails

**Usage:**
```bash
python scripts/generate_manual_report.py <output_directory>
```

## Integration

All these scripts are automatically called by the main `main.py` application in the correct sequence:
1. Enhanced performance analysis runs after protocol tests
2. Browser metrics analysis runs after browser tests
3. HTML report generation runs after all analysis is complete
4. Fallback reports are generated if primary reports fail 