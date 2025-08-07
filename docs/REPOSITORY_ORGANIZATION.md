---
title: Repository Organization
description: Clean repository structure and organization for the Load Testing & Optimization Agent
---

# 🗂️ Repository Organization

## 📁 **Clean Directory Structure**

The repository is now organized with a clean, logical structure where only essential files are in the root directory.

### **Root Directory (Essential Files Only)**
```
load-opt-agent/
├── run_test.py              # 🚀 Main test runner
├── requirements.txt         # 📦 Python dependencies
├── env.example             # 🔧 Environment variables template
├── .gitignore             # 🚫 Git ignore rules
├── README.md              # 📖 Main documentation
├── AI_ANALYSIS_DATA_SUMMARY.md    # 📊 AI analysis documentation
├── PERFORMANCE_ANALYSIS_SUMMARY.md # 📈 Performance analysis docs
└── load_test.log          # 📝 Latest test logs
```

### **Core Directories**
```
load-opt-agent/
├── docker/                 # 🐳 Docker configuration
│   └── Dockerfile         # k6 container definition
├── tests/                  # 🧪 Test scripts
│   └── load_test.js       # k6 load test script
├── ai_analysis/           # 🤖 AI analysis components
│   ├── analysis_agent.py  # Rule-based analysis
│   ├── openai_enhanced_agent.py # AI-enhanced analysis
│   └── technology_templates.yaml # Technology patterns
├── scripts/               # 🔧 Utility and test scripts
│   ├── README.md          # Scripts documentation
│   ├── page_resource_analyzer.py      # Page resource analysis
│   ├── enhanced_performance_analyzer.py # Enhanced k6 analysis
│   ├── analyze_k6_metrics.py          # k6 metrics analysis
│   ├── test_system.py                 # System testing
│   ├── test_ai_analysis.py            # AI analysis testing
│   ├── test_openai_integration.py     # OpenAI integration testing
│   ├── parse_results.py               # Results parsing
│   ├── show_ai_prompts.py             # AI prompt display
│   └── show_template_usage.py         # Template usage demo
├── configs/               # 📋 Load test configurations
│   ├── test_config.yaml   # Basic example
│   ├── pop_website_test.yaml # POP website (Svelte + Strapi)
│   ├── wordpress_test.yaml # WordPress example
│   └── api_test.yaml      # API example
├── output/                # 📊 Test results and reports
│   ├── summary.json       # Raw k6 metrics
│   ├── test_report.json   # Formatted test results
│   ├── page_resource_analysis.json # Page resource analysis
│   ├── enhanced_analysis_report.json # Enhanced analysis
│   └── ai_analysis_report.json # AI recommendations
└── .venv/                 # 🐍 Python virtual environment
```

## 🎯 **Organization Benefits**

### **1. Clean Root Directory**
- **Only essential files** in root
- **Easy to find** main entry points
- **Professional appearance**
- **Clear separation** of concerns

### **2. Logical Grouping**
- **`docker/`** - Container configuration
- **`tests/`** - Core test scripts
- **`ai_analysis/`** - AI analysis components
- **`scripts/`** - Utility and testing scripts
- **`configs/`** - Load test configurations
- **`output/`** - Generated results

### **3. Easy Navigation**
- **Main runner**: `run_test.py` (root)
- **Documentation**: `README.md` (root)
- **Scripts**: `scripts/` directory
- **Configurations**: `configs/` directory
- **Results**: `output/` directory

## 🔧 **Scripts Organization**

### **Core Analysis Scripts**
- `page_resource_analyzer.py` - Page resource analysis
- `enhanced_performance_analyzer.py` - Enhanced k6 analysis
- `analyze_k6_metrics.py` - k6 metrics analysis

### **Testing Scripts**
- `test_system.py` - System verification
- `test_ai_analysis.py` - AI analysis testing
- `test_openai_integration.py` - OpenAI integration testing

### **Utility Scripts**
- `parse_results.py` - Results parsing
- `show_ai_prompts.py` - AI prompt display
- `show_template_usage.py` - Template usage demo

## 📋 **Usage Examples**

### **Main Operations**
```bash
# Run complete test with analysis
python run_test.py configs/pop_website_test.yaml

# Run individual analysis
python scripts/page_resource_analyzer.py https://example.com
python scripts/enhanced_performance_analyzer.py
python scripts/analyze_k6_metrics.py

# Test system components
python scripts/test_system.py
python scripts/test_ai_analysis.py
```

### **Development Workflow**
```bash
# 1. Test system components
python scripts/test_system.py

# 2. Run load test
python run_test.py configs/pop_website_test.yaml

# 3. Analyze results
python scripts/analyze_k6_metrics.py
python scripts/enhanced_performance_analyzer.py

# 4. Check AI analysis
python scripts/show_ai_prompts.py
```

## 🚀 **Benefits for Development**

### **1. Clear Separation**
- **Core functionality** in root
- **Utilities** in `scripts/`
- **Configurations** in `configs/`
- **Results** in `output/`

### **2. Easy Maintenance**
- **Organized by purpose**
- **Clear file locations**
- **Documented structure**
- **Consistent naming**

### **3. Scalable Structure**
- **Easy to add new scripts**
- **Clear organization patterns**
- **Documented conventions**
- **Professional appearance**

## ✅ **Verification**

All scripts work correctly from their new locations:
- ✅ `python scripts/test_system.py` - System verification
- ✅ `python scripts/analyze_k6_metrics.py` - Metrics analysis
- ✅ `python run_test.py` - Main runner (updated paths)

The repository is now **clean, organized, and professional** with a logical structure that makes it easy to find and use all components. 