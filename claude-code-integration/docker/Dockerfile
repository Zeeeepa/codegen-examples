# Multi-stage Dockerfile for Claude Code Validation Engine
# Optimized for security, performance, and minimal attack surface

# Stage 1: Base security-hardened image
FROM ubuntu:22.04 AS base

# Install security updates and essential packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        apt-transport-https && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r validation && \
    useradd -r -g validation -d /home/validation -s /bin/bash validation && \
    mkdir -p /home/validation && \
    chown -R validation:validation /home/validation

# Stage 2: Development tools and language runtimes
FROM base AS tools

# Install Node.js 18 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# Install Python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
        python3.11 \
        python3.11-dev \
        python3.11-venv \
        python3-pip \
        python3-setuptools

# Install Go 1.21
RUN curl -fsSL https://golang.org/dl/go1.21.0.linux-amd64.tar.gz | tar -C /usr/local -xzf -
ENV PATH="/usr/local/go/bin:${PATH}"

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Ruby 3.2
RUN apt-get update && \
    apt-get install -y \
        ruby3.2 \
        ruby3.2-dev \
        rubygems

# Install Java 17 (OpenJDK)
RUN apt-get install -y openjdk-17-jdk
ENV JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"

# Install additional development tools
RUN apt-get install -y \
        git \
        build-essential \
        pkg-config \
        libssl-dev \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        tcl8.6-dev \
        tk8.6-dev \
        python3-tk \
        libharfbuzz-dev \
        libfribidi-dev \
        libxcb1-dev

# Stage 3: Security and analysis tools
FROM tools AS security-tools

# Install security scanning tools
RUN pip3 install --no-cache-dir \
        bandit \
        safety \
        semgrep \
        pip-audit

# Install Node.js security tools
RUN npm install -g \
        eslint \
        @typescript-eslint/parser \
        @typescript-eslint/eslint-plugin \
        eslint-plugin-security \
        audit-ci \
        retire

# Install Ruby security tools
RUN gem install \
        brakeman \
        bundler-audit \
        ruby_audit

# Install Go security tools
RUN go install github.com/securecodewarrior/gosec/v2/cmd/gosec@latest && \
    go install github.com/sonatypecommunity/nancy@latest

# Install Rust security tools
RUN cargo install cargo-audit cargo-deny

# Install additional security tools
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin && \
    curl -sSfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Stage 4: Testing frameworks
FROM security-tools AS testing-tools

# Install Python testing tools
RUN pip3 install --no-cache-dir \
        pytest \
        pytest-cov \
        pytest-xdist \
        pytest-mock \
        coverage \
        nose2 \
        unittest-xml-reporting \
        memory-profiler \
        py-spy

# Install Node.js testing tools
RUN npm install -g \
        jest \
        mocha \
        chai \
        cypress \
        @playwright/test \
        nyc \
        c8

# Install Ruby testing tools
RUN gem install \
        rspec \
        minitest \
        simplecov \
        factory_bot

# Install Go testing tools
RUN go install github.com/onsi/ginkgo/v2/ginkgo@latest && \
    go install github.com/onsi/gomega/...@latest

# Stage 5: Code quality and linting tools
FROM testing-tools AS quality-tools

# Install Python code quality tools
RUN pip3 install --no-cache-dir \
        pylint \
        flake8 \
        black \
        isort \
        mypy \
        pydocstyle \
        pycodestyle \
        autopep8 \
        vulture \
        radon \
        mccabe

# Install additional Node.js quality tools
RUN npm install -g \
        prettier \
        jshint \
        standard \
        xo \
        complexity-report

# Install Ruby code quality tools
RUN gem install \
        rubocop \
        reek \
        flog \
        flay \
        rails_best_practices

# Install Go code quality tools
RUN go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest && \
    go install honnef.co/go/tools/cmd/staticcheck@latest

# Install Rust code quality tools
RUN rustup component add clippy rustfmt

# Stage 6: Performance profiling tools
FROM quality-tools AS performance-tools

# Install system monitoring tools
RUN apt-get update && \
    apt-get install -y \
        htop \
        iotop \
        nethogs \
        iftop \
        sysstat \
        strace \
        ltrace \
        valgrind \
        perf-tools-unstable

# Install language-specific profiling tools
RUN pip3 install --no-cache-dir \
        line_profiler \
        memory_profiler \
        py-spy \
        scalene \
        pympler

RUN npm install -g \
        clinic \
        0x \
        autocannon

# Stage 7: Final application image
FROM performance-tools AS final

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY requirements.txt ./
COPY package.json package-lock.json ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Node.js dependencies
RUN npm ci --only=production

# Create necessary directories
RUN mkdir -p \
        /app/logs \
        /app/tmp \
        /app/cache \
        /app/ml-models \
        /workspace \
        /var/log/validation

# Set proper permissions
RUN chown -R validation:validation /app /workspace /var/log/validation && \
    chmod -R 755 /app && \
    chmod -R 777 /app/tmp /app/cache /app/logs /workspace /var/log/validation

# Install custom seccomp profile
COPY docker/seccomp-profile.json /etc/docker/seccomp-profile.json

# Create health check script
COPY docker/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Security hardening
RUN apt-get update && \
    apt-get remove -y \
        curl \
        wget \
        netcat \
        telnet && \
    apt-get autoremove -y && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Remove unnecessary setuid/setgid binaries
RUN find / -perm /6000 -type f -exec chmod a-s {} \; 2>/dev/null || true

# Switch to non-root user
USER validation

# Set environment variables
ENV PYTHONPATH="/app/src"
ENV NODE_PATH="/app/node_modules"
ENV PATH="/app/scripts:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose ports (will be overridden by container runtime)
EXPOSE 8000 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Default command
CMD ["python3", "-m", "src.validation_engine"]

