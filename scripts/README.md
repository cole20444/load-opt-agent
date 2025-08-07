# 📁 Scripts Directory

This directory contains utility scripts for testing, analysis, and development of the Load Testing & Optimization Agent.

## 🔧 **Core Analysis Scripts**

### `page_resource_analyzer.py`
**Purpose**: Analyzes page resources for performance issues
**Usage**: `python scripts/page_resource_analyzer.py <target_url>`
**Output**: `output/page_resource_analysis.json`
**Features**:
- Discovers images, scripts, CSS, fonts, APIs
- Identifies large files, missing compression, slow loads
- Technology-specific optimization recommendations

### `enhanced_performance_analyzer.py`
**Purpose**: Analyzes k6 metrics for detailed performance insights
**Usage**: `python scripts/enhanced_performance_analyzer.py`
**Output**: `output/enhanced_analysis_report.json`
**Features**:
- HTTP timing breakdown analysis
- Data transfer analysis
- Load distribution analysis
- Error pattern analysis

### `analyze_k6_metrics.py`
**Purpose**: Shows all k6 metrics and what we're collecting vs. using
**Usage**: `python scripts/analyze_k6_metrics.py`
**Features**:
- Lists all 21 k6 metrics
- Shows data points collected
- Identifies enhancement opportunities
- Categorizes metrics by type

## 🧪 **Testing Scripts**

### `test_system.py`
**Purpose**: Verifies core system components
**Usage**: `python scripts/test_system.py`
**Tests**:
- YAML parsing
- Docker availability
- File structure
- Python dependencies

### `test_ai_analysis.py`
**Purpose**: Tests the AI analysis functionality
**Usage**: `python scripts/test_ai_analysis.py`
**Tests**:
- Technology template loading
- Performance analysis
- Recommendation generation

### `test_openai_integration.py`
**Purpose**: Tests OpenAI API integration
**Usage**: `python scripts/test_openai_integration.py`
**Tests**:
- OpenAI API availability
- Enhanced analysis agent
- Prompt generation

## 📊 **Utility Scripts**

### `parse_results.py`
**Purpose**: Simple k6 results parser
**Usage**: `python scripts/parse_results.py`
**Features**:
- Parses raw k6 JSON output
- Displays key metrics in human-readable format
- Calculates basic statistics

### `show_ai_prompts.py`
**Purpose**: Shows the actual prompts sent to OpenAI
**Usage**: `python scripts/show_ai_prompts.py`
**Features**:
- Displays full AI prompts
- Shows prompt statistics
- Demonstrates data comprehensiveness

### `show_template_usage.py`
**Purpose**: Demonstrates technology template usage
**Usage**: `python scripts/show_template_usage.py`
**Features**:
- Shows template selection
- Displays optimization patterns
- Demonstrates prompt enhancement

### `list_test_results.py`
**Purpose**: Navigate and find test results in organized output structure
**Usage**: 
- `python scripts/list_test_results.py list` - List all test results
- `python scripts/list_test_results.py latest` - Show latest results for all sites
- `python scripts/list_test_results.py latest <site>` - Show latest results for specific site
**Features**:
- Browse organized test results by site and timestamp
- View detailed test summaries
- Navigate latest results with symlinks
- List available files and their sizes

## 🚀 **Quick Start**

To run a complete analysis:

```bash
# 1. Run the main load test
python run_test.py configs/pop_website_test.yaml

# 2. Or run individual analysis scripts
python scripts/page_resource_analyzer.py https://example.com
python scripts/enhanced_performance_analyzer.py
python scripts/analyze_k6_metrics.py
```

## 📁 **Output Files**

All scripts generate output files in the `output/` directory:
- `page_resource_analysis.json` - Page resource analysis results
- `enhanced_analysis_report.json` - Enhanced performance analysis
- `ai_analysis_report.json` - AI-generated recommendations

## 🔧 **Development**

These scripts are used for:
- **Testing**: Verifying system components work correctly
- **Analysis**: Deep-dive performance investigation
- **Development**: Understanding system behavior
- **Debugging**: Identifying issues in the analysis pipeline 