FROM grafana/k6:latest

# Set working directory
WORKDIR /app

# Set environment variables for k6
ENV K6_NO_USAGE_REPORT=true

# Memory and performance optimizations for high-load testing
ENV K6_DISABLE_COMPRESSION=true
ENV K6_DISABLE_HTTP2=true

# Default k6 command - will be overridden with volume mounts
ENTRYPOINT ["k6", "run"]
