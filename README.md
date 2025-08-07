# Load Testing & Optimization Agent - Phase 1

A professional-grade load testing system that combines k6 performance testing with AI-powered optimization recommendations. Test any web application and get intelligent insights for performance improvements.

## 📖 Documentation

**[📖 Full Documentation](https://colespicer.github.io/load-opt-agent)** - Complete guides and reference  
**[🚀 Quick Start Guide](https://colespicer.github.io/load-opt-agent/quick-start)** - Get up and running in minutes  
**[⚙️ Configuration Reference](https://colespicer.github.io/load-opt-agent/configuration)** - YAML configuration options

## Features

### 🐳 Core Load Testing
- **Dockerized k6 Test Runner**: Containerized load testing for consistent environments
- **YAML Configuration**: Simple, readable configuration files for test parameters
- **Comprehensive Metrics**: 21 k6 metrics with 38K+ data points per test
- **Performance Thresholds**: Built-in performance validation with configurable thresholds
- **Multiple Test Scenarios**: Support for different application types and load patterns

### 🤖 AI-Powered Analysis
- **OpenAI Integration**: GPT-4o-mini powered optimization recommendations
- **Technology Templates**: Technology-specific optimization patterns
- **Page Resource Analysis**: Identifies performance bottlenecks in page assets
- **Enhanced Metrics Analysis**: Deep dive into k6 performance data
- **Actionable Recommendations**: Prioritized optimization suggestions

### 📊 Results Management
- **Organized Output**: Site-based organization with timestamped test runs
- **Latest Results**: Automatic symlinks to most recent test results
- **Navigation Tools**: Easy result browsing with `list_test_results.py`
- **Comprehensive Reports**: Multiple analysis outputs for complete insights
- **Historical Tracking**: Maintain test history for performance trends

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

3. **Build Docker image** (automatically done on first run):
```bash
python run_test.py
```

4. **Run a complete load test with analysis**:
```bash
# Use POP website configuration (includes AI analysis)
python run_test.py configs/pop_website_test.yaml

# Use custom configuration
python run_test.py configs/wordpress_test.yaml
```

5. **Check results**:
```bash
# List all test results
python scripts/list_test_results.py list

# View latest results
python scripts/list_test_results.py latest

# View results for specific site
python scripts/list_test_results.py latest pop-website-2024-dev.azurewebsites.net
```

Results are organized by site and timestamp:
- **Console output** - Real-time test progress
- **`output/site_name/timestamp/`** - Organized test results
  - `summary.json` - Raw k6 metrics (21 metrics, 38K+ data points)
  - `test_report.json` - Formatted results with metadata
  - `page_resource_analysis.json` - Page resource analysis
  - `enhanced_analysis_report.json` - Enhanced performance analysis
  - `ai_analysis_report.json` - AI optimization recommendations
- **`output/site_name/latest/`** - Symlink to most recent results
- **`load_test.log`** - Detailed execution logs

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
- `configs/pop_website_test.yaml` - POP website (Svelte + Strapi)
- `configs/wordpress_test.yaml` - WordPress site testing
- `configs/api_test.yaml` - API endpoint testing

### Configuration Validation

The system validates:
- Required fields (target, vus, duration)
- Data types (string URL, positive integer VUs, string duration)
- URL format validation
- Optional fields (description, tags) with default values

## Test Metrics

The load test collects comprehensive performance metrics:

- **Request Metrics**: Total requests, requests per second
- **Response Times**: Average, median, P95, P99 response times
- **Error Rates**: Failed request percentage
- **Payload Sizes**: Request and response sizes
- **Custom Metrics**: Success/failure counters, custom error rates

### Performance Thresholds

Built-in performance thresholds (configurable):
- 95% of requests should complete in < 2 seconds
- Error rate should be < 10%
- Custom error rate monitoring

## Output Files

After running a test, the following files are generated:

- `output/summary.json` - Raw k6 metrics in JSON format (21 metrics, 38K+ data points)
- `output/test_report.json` - Formatted test summary with key metrics
- `output/page_resource_analysis.json` - Page resource analysis results
- `output/enhanced_analysis_report.json` - Enhanced performance analysis
- `output/ai_analysis_report.json` - AI-generated optimization recommendations
- `load_test.log` - Detailed execution logs

## Supported Applications

This system can test any web application:

- **Content Management Systems**: AEM, WordPress, Drupal
- **Single Page Applications**: React, Vue, Angular
- **APIs**: REST APIs, GraphQL endpoints
- **Static Sites**: HTML, CSS, JavaScript sites
- **E-commerce**: Shopify, WooCommerce, custom solutions

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YAML Config   │───▶│  Python Runner  │───▶│  Docker + k6    │
│                 │    │                 │    │                 │
│ - target URL    │    │ - Config parse  │    │ - Load test     │
│ - VUs           │    │ - Docker build  │    │ - 21 metrics    │
│ - duration      │    │ - Test execution│    │ - 38K+ data pts │
│ - description   │    │ - Output org    │    │ - JSON export   │
│ - tags          │    │ - Site structure│    │ - Performance   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Analysis Layer │
                       │                 │
                       │ - Page Resources│
                       │ - Enhanced k6   │
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
                       │ │       ├── summary.json│
                       │ │       ├── test_report.json│
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
│   ├── mint.json              # Mintlify configuration
│   ├── index.mdx              # Landing page
│   ├── quick-start.mdx        # Quick start guide
│   ├── configuration.mdx      # Configuration reference
│   ├── _config.yml            # GitHub Pages configuration
│   └── [legacy .md files]     # Performance analysis docs
├── 📋 configs/                # Load test configurations
│   ├── test_config.yaml       # Basic test configuration
│   ├── wordpress_test.yaml    # WordPress test config
│   ├── api_test.yaml          # API test config
│   └── pop_website_test.yaml  # POP website test config
├── 🔧 scripts/                # Utility and analysis scripts
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
│   └── load_test.js           # Main k6 test script
├── 🐳 docker/                 # Docker configuration
│   └── Dockerfile             # k6 container definition
├── 📊 output/                 # Test results (auto-created)
│   └── [site_name]/           # Organized by site
│       └── [timestamp]/       # Organized by test run
│           ├── summary.json   # Raw k6 metrics
│           ├── test_report.json # Formatted results
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
2. **Configuration Options**: Extend YAML schema in `run_test.py`
3. **Metrics**: Add custom k6 metrics in `tests/load_test.js`
4. **Analysis Scripts**: Add new analysis tools in `scripts/`
5. **AI Templates**: Extend technology patterns in `ai_analysis/technology_templates.yaml`
6. **Output Formats**: Extend reporting in `run_test.py`
7. **Documentation**: Add new guides in `docs/`

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker daemon is started
2. **Permission errors**: Run with appropriate Docker permissions
3. **Network issues**: Check target URL accessibility
4. **Timeout errors**: Increase timeout in `run_test.py`

### Logs

Check `load_test.log` for detailed execution information and error messages.

## Next Steps (Future Phases)

This project includes Phase 1 (Dockerized Load Testing) and Phase 2 (AI-Powered Optimization). Future phases will include:

- **Phase 3**: Advanced test scenarios and workflows
- **Phase 4**: Real-time monitoring and alerting
- **Phase 5**: Integration with CI/CD pipelines
- **Phase 6**: Multi-site dashboard and reporting

## License

This project is part of the POP Agents initiative for automated performance optimization.
