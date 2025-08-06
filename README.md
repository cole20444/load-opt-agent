# Load Testing & Optimization Agent - Phase 1

A Dockerized load testing system using k6 with YAML configuration for repeatable performance testing of web applications (AEM, WordPress, React, APIs, etc.).

## Features

- **Dockerized k6 Test Runner**: Containerized load testing for consistent environments
- **YAML Configuration**: Simple, readable configuration files for test parameters
- **Comprehensive Metrics**: Collects latency, response times, error rates, and payload sizes
- **Performance Thresholds**: Built-in performance validation with configurable thresholds
- **JSON Export**: Detailed test results exported for analysis
- **Robust Error Handling**: Comprehensive logging and error reporting
- **Multiple Test Scenarios**: Support for different application types and load patterns

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

2. **Build Docker image** (automatically done on first run):
```bash
python run_test.py
```

3. **Run a load test**:
```bash
# Use default configuration
python run_test.py

# Use custom configuration
python run_test.py examples/wordpress_test.yaml
```

4. **Check results**:
- View console output for real-time test progress
- Check `output/summary.json` for raw k6 metrics
- Check `output/test_report.json` for formatted results
- Check `load_test.log` for detailed logs

## Configuration

### Basic Configuration

Edit `examples/test_config.yaml`:
```yaml
# Target URL to test (any web application)
target: https://example.com/contact

# Number of virtual users (concurrent users)
vus: 50

# Test duration (supports: 30s, 1m, 5m, 1h, etc.)
duration: 30s
```

### Example Configurations

The project includes several example configurations:

- `examples/test_config.yaml` - Basic example
- `examples/wordpress_test.yaml` - WordPress site testing
- `examples/api_test.yaml` - API endpoint testing

### Configuration Validation

The system validates:
- Required fields (target, vus, duration)
- Data types (string URL, positive integer VUs, string duration)
- URL format validation

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

- `output/summary.json` - Raw k6 metrics in JSON format
- `output/test_report.json` - Formatted test summary with key metrics
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
│ - VUs           │    │ - Docker build  │    │ - Metrics       │
│ - duration      │    │ - Test execution│    │ - JSON export   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Test Results  │
                       │                 │
                       │ - summary.json  │
                       │ - test_report   │
                       │ - logs          │
                       └─────────────────┘
```

## Development

### Project Structure

```
load-opt-agent/
├── docker/
│   └── Dockerfile          # k6 container definition
├── examples/
│   ├── test_config.yaml    # Basic test configuration
│   ├── wordpress_test.yaml # WordPress test config
│   └── api_test.yaml       # API test config
├── tests/
│   └── load_test.js        # k6 test script
├── output/                 # Test results (auto-created)
├── run_test.py            # Python test runner
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Extending the System

The system is designed for easy extension:

1. **New Test Types**: Add new k6 test scripts in `tests/`
2. **Configuration Options**: Extend YAML schema in `run_test.py`
3. **Metrics**: Add custom k6 metrics in `load_test.js`
4. **Output Formats**: Extend reporting in `generate_test_report()`

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker daemon is started
2. **Permission errors**: Run with appropriate Docker permissions
3. **Network issues**: Check target URL accessibility
4. **Timeout errors**: Increase timeout in `run_test.py`

### Logs

Check `load_test.log` for detailed execution information and error messages.

## Next Steps (Future Phases)

This is Phase 1 of the Load Testing & Optimization Agent. Future phases will include:

- **Phase 2**: AI-powered optimization recommendations
- **Phase 3**: Advanced test scenarios and workflows
- **Phase 4**: Real-time monitoring and alerting
- **Phase 5**: Integration with CI/CD pipelines

## License

This project is part of the POP Agents initiative for automated performance optimization.
