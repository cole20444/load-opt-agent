# Load Testing & Optimization Agent - Enhanced with Browser Testing

A professional-grade load testing system that combines k6 protocol-level testing with xk6-browser front-end performance analysis and AI-powered optimization recommendations. Test any web application and get comprehensive insights from both server and client perspectives.

## 📖 Documentation

**[📖 Full Documentation](https://colespicer.github.io/load-opt-agent)** - Complete guides and reference  
**[🚀 Quick Start Guide](https://colespicer.github.io/load-opt-agent/quick-start)** - Get up and running in minutes  
**[⚙️ Configuration Reference](https://colespicer.github.io/load-opt-agent/configuration)** - YAML configuration options

## 🌟 New Features - Browser Testing Integration

### 🌐 xk6-browser Support
- **Real Browser Testing**: Uses actual Chromium browser for realistic front-end performance testing
- **Core Web Vitals**: Measures FCP, LCP, FID, CLS, and other user-centric metrics
- **User Interaction Simulation**: Clicks, scrolls, and interacts with page elements
- **Resource Loading Analysis**: Browser-level resource timing and optimization insights
- **Layout Shift Detection**: Identifies visual stability issues

### 🔄 Dual Testing Modes
- **Protocol Testing**: Traditional k6 HTTP-level load testing (high concurrency)
- **Browser Testing**: xk6-browser front-end performance testing (lower concurrency, higher realism)
- **Combined Testing**: Run both tests for comprehensive analysis

## Features

### 🐳 Core Load Testing
- **Dockerized k6 Test Runner**: Containerized load testing for consistent environments
- **xk6-browser Integration**: Real browser testing with Chromium
- **YAML Configuration**: Simple, readable configuration files for test parameters
- **Comprehensive Metrics**: 21+ k6 metrics + Core Web Vitals + browser-specific metrics
- **Performance Thresholds**: Built-in performance validation with configurable thresholds
- **Multiple Test Scenarios**: Support for different application types and load patterns

### 🌐 Browser-Level Analysis
- **Core Web Vitals**: First Contentful Paint, Largest Contentful Paint, First Input Delay, Cumulative Layout Shift
- **Navigation Timing**: DOM Content Loaded, Load Complete, Time to Interactive
- **Resource Analysis**: Browser-level resource loading and optimization insights
- **User Interaction Metrics**: Script execution time, interaction responsiveness
- **Visual Stability**: Layout shift detection and analysis

### 🤖 AI-Powered Analysis
- **OpenAI Integration**: GPT-4o-mini powered optimization recommendations
- **Technology Templates**: Technology-specific optimization patterns
- **Page Resource Analysis**: Identifies performance bottlenecks in page assets
- **Enhanced Metrics Analysis**: Deep dive into k6 performance data
- **Browser Performance Insights**: Front-end specific optimization recommendations
- **Actionable Recommendations**: Prioritized optimization suggestions

### 📊 Results Management
- **Organized Output**: Site-based organization with timestamped test runs
- **Latest Results**: Automatic symlinks to most recent test results
- **Navigation Tools**: Easy result browsing with `list_test_results.py`
- **Comprehensive Reports**: Multiple analysis outputs for complete insights
- **Historical Tracking**: Maintain test history for performance trends
- **Combined Analysis**: Protocol + browser results in unified reports

### 🔧 Developer Experience
- **Professional Documentation**: Modern docs with Mintlify and GitHub Pages
- **Utility Scripts**: Comprehensive set of analysis and testing tools
- **Clean Architecture**: Well-organized, maintainable codebase
- **Extensible Design**: Easy to add new features and analysis tools

## Quick Start

### Prerequisites

- Docker
- Python 3.7+
- Required Python packages (install with `pip install -r requirements.txt`)

### Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure environment** (for AI analysis):
```bash
cp env.example .env
# Add your OpenAI API key to .env
```

3. **Run a comprehensive load test**:
```bash
# Run both protocol and browser tests with AI analysis
python run_test.py configs/comprehensive_test.yaml

# Run technical analysis only (no AI, faster, no API costs)
python run_test.py configs/technical_analysis.yaml

# Run only protocol testing (traditional k6)
python run_test.py configs/pop_website_test.yaml

# Run only browser testing (front-end performance)
python run_test.py configs/browser_test.yaml
```

4. **Check results**:
```bash
# List all test results
python scripts/list_test_results.py list

# View latest results
python scripts/list_test_results.py latest

# View results for specific site
python scripts/list_test_results.py latest pop-website-2024-dev.azurewebsites.net
```

## Test Types

### 🔌 Protocol Testing (k6)
- **High concurrency**: 50+ virtual users
- **HTTP-level metrics**: Response times, error rates, throughput
- **Network analysis**: DNS, TLS, server processing times
- **Resource optimization**: Compression, caching analysis

### 🌐 Browser Testing (xk6-browser)
- **Real browser**: Chromium-based testing
- **Core Web Vitals**: User-centric performance metrics
- **Front-end analysis**: JavaScript execution, layout shifts
- **User interactions**: Click, scroll, form interactions

### 🔄 Combined Testing
- **Best of both worlds**: Protocol + browser insights
- **Comprehensive analysis**: Server + client performance
- **Unified recommendations**: End-to-end optimization suggestions

### 🔧 Technical Analysis (No AI)
- **Fast execution**: No OpenAI API calls
- **Cost effective**: No API costs
- **Raw data**: Technical metrics and insights
- **Debugging friendly**: Focus on technical components

## Configuration

### Basic Configuration

Edit `configs/test_config.yaml`:
```yaml
# Target URL to test (any web application)
target: https://example.com/contact

# Number of virtual users (concurrent users)
vus: 50

# Test duration (supports: 30s, 1m, 5m, 1h, etc.)
duration: 30s

# Test type: protocol, browser, or both
test_type: both

# Analysis settings
analysis_settings:
  run_page_resource_analysis: true
  run_enhanced_performance_analysis: true
  run_ai_analysis: true  # Set to false to skip AI analysis
  generate_readable_reports: true
  combine_results: true

# Site description for AI analysis (optional)
description: "Example website for load testing"

# Tags for categorization and AI analysis (optional)
tags:
  - "example"
  - "contact-form"
  - "static-site"
```

### Example Configurations

The project includes several example configurations:

- `configs/test_config.yaml` - Basic example
- `configs/pop_website_test.yaml` - POP website (protocol testing)
- `configs/browser_test.yaml` - Browser-based front-end testing
- `configs/comprehensive_test.yaml` - Both protocol and browser testing with AI
- `configs/technical_analysis.yaml` - Technical analysis only (no AI)
- `configs/wordpress_test.yaml` - WordPress site testing
- `configs/api_test.yaml` - API endpoint testing

### Analysis Settings

You can control which analysis components run:

```yaml
analysis_settings:
  run_page_resource_analysis: true      # Analyze page resources (images, scripts, etc.)
  run_enhanced_performance_analysis: true # Detailed k6/browser metrics analysis
  run_ai_analysis: true                 # AI-powered insights (requires OpenAI API)
  generate_readable_reports: true       # Generate HTML/Markdown reports
  combine_results: true                 # Combine protocol + browser results
```

**Benefits of disabling AI analysis:**
- **Faster execution**: No API calls to OpenAI
- **Cost savings**: No API usage costs
- **Technical focus**: Raw metrics and data
- **Debugging**: Easier to troubleshoot technical issues

## Test Metrics

### Protocol Metrics (k6)
- **Request Metrics**: Total requests, requests per second
- **Response Times**: Average, median, P95, P99 response times
- **Error Rates**: Failed request percentage
- **Payload Sizes**: Request and response sizes
- **Network Timing**: DNS, TLS, server processing, data transfer times

### Browser Metrics (xk6-browser)
- **Core Web Vitals**: FCP, LCP, FID, CLS
- **Navigation Timing**: DOM Content Loaded, Load Complete, Time to Interactive
- **Resource Loading**: Resource counts, sizes, loading times
- **User Interactions**: Script execution time, interaction responsiveness
- **Visual Stability**: Layout shift detection and analysis

### Performance Thresholds

Built-in performance thresholds (configurable):
- **Protocol**: 95% of requests should complete in < 2 seconds, Error rate < 10%
- **Browser**: FCP < 1.8s, LCP < 2.5s, FID < 100ms, CLS < 0.1

## Output Files

After running a test, the following files are generated:

### Protocol Testing
- `protocol_summary.json` - Raw k6 metrics in JSON format
- `test_report.json` - Formatted test summary with key metrics

### Browser Testing
- `browser_summary.json` - Raw xk6-browser metrics
- `browser_analysis_report.json` - Browser performance analysis

### Combined Testing
- `combined_test_report.json` - Unified protocol + browser results
- `ai_analysis_report.json` - AI-generated optimization recommendations
- `page_resource_analysis.json` - Page resource analysis results
- `enhanced_analysis_report.json` - Enhanced performance analysis

### Reports
- `ai_analysis_report.html` - Interactive HTML report
- `ai_analysis_report.md` - Markdown report
- `load_test.log` - Detailed execution logs

## Supported Applications

This system can test any web application:

- **Content Management Systems**: AEM, WordPress, Drupal
- **Single Page Applications**: React, Vue, Angular, Svelte
- **APIs**: REST APIs, GraphQL endpoints
- **Static Sites**: HTML, CSS, JavaScript sites
- **E-commerce**: Shopify, WooCommerce, custom solutions
- **Progressive Web Apps**: PWA performance and functionality

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YAML Config   │───▶│  Python Runner  │───▶│  Docker + k6    │
│                 │    │                 │    │                 │
│ - target URL    │    │ - Config parse  │    │ - Protocol test │
│ - VUs           │    │ - Docker build  │    │ - 21+ metrics   │
│ - duration      │    │ - Test execution│    │ - JSON export   │
│ - test_type     │    │ - Output org    │    │ - Performance   │
│ - description   │    │ - Site structure│    │ - Thresholds    │
│ - tags          │    │ - Dual testing  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Docker + xk6   │
                       │    Browser      │
                       │                 │
                       │ - Browser test  │
                       │ - Core Web Vitals│
                       │ - User interactions│
                       │ - Chromium      │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Analysis Layer │
                       │                 │
                       │ - Page Resources│
                       │ - Enhanced k6   │
                       │ - Browser Metrics│
                       │ - AI Analysis   │
                       │ - OpenAI GPT-4o │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Organized Output│
                       │                 │
                       │ output/         │
                       │ ├── site_name/  │
                       │ │   └── timestamp/│
                       │ │       ├── protocol_summary.json│
                       │ │       ├── browser_summary.json│
                       │ │       ├── test_report.json│
                       │ │       ├── browser_analysis_report.json│
                       │ │       ├── combined_test_report.json│
                       │ │       ├── page_resource_analysis.json│
                       │ │       ├── enhanced_analysis_report.json│
                       │ │       └── ai_analysis_report.json│
                       │ └── latest -> timestamp/│
                       └─────────────────┘
```

## Development

### Project Structure

```
load-opt-agent/
├── 📖 docs/                    # Documentation
├── 📋 configs/                # Load test configurations
│   ├── test_config.yaml       # Basic test configuration
│   ├── browser_test.yaml      # Browser-only test config
│   ├── comprehensive_test.yaml # Both protocol and browser
│   ├── wordpress_test.yaml    # WordPress test config
│   ├── api_test.yaml          # API test config
│   └── pop_website_test.yaml  # POP website test config
├── 🔧 scripts/                # Utility and analysis scripts
│   ├── browser_metrics_analyzer.py    # Browser metrics analysis
│   ├── page_resource_analyzer.py      # Page resource analysis
│   ├── enhanced_performance_analyzer.py # Enhanced k6 analysis
│   ├── analyze_k6_metrics.py          # k6 metrics analysis
│   ├── list_test_results.py           # Test results navigation
│   ├── test_system.py                 # System testing
│   ├── test_ai_analysis.py            # AI analysis testing
│   ├── test_openai_integration.py     # OpenAI integration testing
│   ├── parse_results.py               # Results parsing
│   ├── show_ai_prompts.py             # AI prompt display
│   ├── show_template_usage.py         # Template usage demo
│   └── README.md                      # Scripts documentation
├── 🤖 ai_analysis/            # AI analysis components
│   ├── openai_enhanced_agent.py       # AI-enhanced analysis
│   └── technology_templates.yaml      # Technology-specific patterns
├── 🧪 tests/                  # k6 test scripts
│   ├── load_test.js           # Protocol-level k6 test script
│   └── browser_load_test.js   # Browser-level xk6-browser test script
├── 🐳 docker/                 # Docker configuration
│   ├── Dockerfile             # k6 container definition
│   └── Dockerfile.browser     # xk6-browser container definition
├── 📊 output/                 # Test results (auto-created)
│   └── [site_name]/           # Organized by site
│       └── [timestamp]/       # Organized by test run
│           ├── protocol_summary.json   # Protocol test metrics
│           ├── browser_summary.json    # Browser test metrics
│           ├── test_report.json # Formatted results
│           ├── browser_analysis_report.json # Browser analysis
│           ├── combined_test_report.json # Combined results
│           ├── page_resource_analysis.json # Page analysis
│           ├── enhanced_analysis_report.json # Enhanced analysis
│           └── ai_analysis_report.json # AI recommendations
├── 📄 run_test.py             # Main test runner
├── 📋 requirements.txt        # Python dependencies
├── 🔑 env.example             # Environment variables template
├── 🚫 .gitignore             # Git ignore rules
└── 📖 README.md              # This file
```

### Extending the System

The system is designed for easy extension:

1. **New Test Types**: Add new k6 test scripts in `tests/`
2. **Browser Extensions**: Extend xk6-browser functionality in `tests/browser_load_test.js`
3. **Configuration Options**: Extend YAML schema in `run_test.py`
4. **Metrics**: Add custom k6 metrics in `tests/load_test.js`
5. **Analysis Scripts**: Add new analysis tools in `scripts/`
6. **AI Templates**: Extend technology patterns in `ai_analysis/technology_templates.yaml`
7. **Output Formats**: Extend reporting in `run_test.py`
8. **Documentation**: Add new guides in `docs/`

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker daemon is started
2. **Permission errors**: Run with appropriate Docker permissions
3. **Network issues**: Check target URL accessibility
4. **Browser test failures**: Ensure sufficient system resources for Chromium
5. **Timeout errors**: Increase timeout in `run_test.py`

### Browser Testing Tips

- **Resource requirements**: Browser tests need more RAM and CPU
- **Lower concurrency**: Use fewer VUs for browser tests (3-5 vs 25-50)
- **Longer timeouts**: Browser tests take longer to complete
- **System resources**: Ensure adequate memory for Chromium instances

### Logs

Check `load_test.log` for detailed execution information and error messages.

## Next Steps (Future Phases)

This project includes Phase 1 (Dockerized Load Testing) and Phase 2 (AI-Powered Optimization). Future phases will include:

- **Phase 3**: Advanced test scenarios and workflows
- **Phase 4**: Real-time monitoring and alerting
- **Phase 5**: Integration with CI/CD pipelines
- **Phase 6**: Multi-site dashboard and reporting
- **Phase 7**: Advanced browser automation and visual regression testing

## License

This project is part of the POP Agents initiative for automated performance optimization.
