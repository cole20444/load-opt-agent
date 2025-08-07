FROM alpine:latest

# Install k6
RUN apk add --no-cache ca-certificates && \
    wget -qO- https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz | tar xz && \
    mv k6-v0.47.0-linux-amd64/k6 /usr/local/bin/ && \
    rm -rf k6-v0.47.0-linux-amd64

# Set working directory
WORKDIR /app

# Copy the k6 test script
COPY tests/load_test.js /app/load_test.js

# Create output directory
RUN mkdir -p /app/output

# Set environment variables for k6
ENV K6_OUT=json=/app/output/summary.json
ENV K6_NO_USAGE_REPORT=true

# Default k6 command with enhanced options
ENTRYPOINT ["k6", "run", "--out", "json=/app/output/summary.json", "/app/load_test.js"]
