FROM grafana/k6:latest

# Set working directory
WORKDIR /app

# Copy the k6 test script
COPY tests/load_test.js /app/load_test.js

# Create output directory
RUN mkdir -p /output

# Set environment variables for k6
ENV K6_OUT=json=/output/summary.json
ENV K6_NO_USAGE_REPORT=true

# Health check to ensure k6 is working
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD k6 version || exit 1

# Default k6 command with enhanced options
ENTRYPOINT ["k6", "run", "--out", "json=/output/summary.json", "--out", "console", "/app/load_test.js"]
