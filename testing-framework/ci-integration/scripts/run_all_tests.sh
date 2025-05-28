#!/bin/bash

# Comprehensive Testing & Quality Assurance Framework
# Main test execution script

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
COVERAGE_THRESHOLD=90
PERFORMANCE_THRESHOLD_MS=500

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to print section headers
print_section() {
    echo
    echo "=================================="
    echo "$1"
    echo "=================================="
    echo
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to setup environment
setup_environment() {
    print_section "Setting up test environment"
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"/{coverage,test-results,performance,security,quality}
    
    # Check Python version
    if ! command_exists python; then
        log_error "Python is not installed"
        exit 1
    fi
    
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    log_info "Python version: $python_version"
    
    # Install dependencies if requirements file exists
    if [ -f "$PROJECT_ROOT/testing-framework/requirements.txt" ]; then
        log_info "Installing test dependencies..."
        pip install -r "$PROJECT_ROOT/testing-framework/requirements.txt"
    fi
    
    # Check for Docker if integration tests are enabled
    if [ "$RUN_INTEGRATION_TESTS" = "true" ] && command_exists docker; then
        log_info "Docker is available for integration tests"
    elif [ "$RUN_INTEGRATION_TESTS" = "true" ]; then
        log_warning "Docker not found, integration tests may fail"
    fi
}

# Function to run code quality checks
run_code_quality() {
    print_section "Running code quality checks"
    
    local quality_passed=true
    
    # Linting with flake8
    if command_exists flake8; then
        log_info "Running flake8 linting..."
        if flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics; then
            log_success "Flake8 critical checks passed"
        else
            log_error "Flake8 critical checks failed"
            quality_passed=false
        fi
        
        # Generate flake8 report
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 \
            --statistics --tee --output-file="$REPORTS_DIR/quality/flake8-report.txt"
    else
        log_warning "flake8 not found, skipping linting"
    fi
    
    # Type checking with mypy
    if command_exists mypy; then
        log_info "Running mypy type checking..."
        if mypy . --ignore-missing-imports --no-strict-optional \
            --html-report "$REPORTS_DIR/quality/mypy-report" 2>/dev/null; then
            log_success "MyPy type checking passed"
        else
            log_warning "MyPy type checking found issues"
        fi
    else
        log_warning "mypy not found, skipping type checking"
    fi
    
    # Security analysis with bandit
    if command_exists bandit; then
        log_info "Running bandit security analysis..."
        bandit -r . -f json -o "$REPORTS_DIR/security/bandit-report.json" 2>/dev/null || true
        bandit -r . -f txt -o "$REPORTS_DIR/security/bandit-report.txt" 2>/dev/null || true
        log_success "Bandit security analysis completed"
    else
        log_warning "bandit not found, skipping security analysis"
    fi
    
    # Dependency vulnerability check
    if command_exists safety; then
        log_info "Checking dependencies for vulnerabilities..."
        safety check --json --output "$REPORTS_DIR/security/safety-report.json" 2>/dev/null || true
        safety check --output "$REPORTS_DIR/security/safety-report.txt" 2>/dev/null || true
        log_success "Dependency vulnerability check completed"
    else
        log_warning "safety not found, skipping dependency check"
    fi
    
    if [ "$quality_passed" = true ]; then
        log_success "Code quality checks completed"
        return 0
    else
        log_error "Code quality checks failed"
        return 1
    fi
}

# Function to run unit tests
run_unit_tests() {
    print_section "Running unit tests"
    
    cd "$PROJECT_ROOT/testing-framework"
    
    log_info "Executing unit tests with coverage..."
    
    if python -m pytest unit-tests/ \
        --cov=. \
        --cov-report=html:"$REPORTS_DIR/coverage/html" \
        --cov-report=xml:"$REPORTS_DIR/coverage/coverage.xml" \
        --cov-report=json:"$REPORTS_DIR/coverage/coverage.json" \
        --cov-report=term-missing \
        --html="$REPORTS_DIR/test-results/unit-tests.html" \
        --self-contained-html \
        --json-report \
        --json-report-file="$REPORTS_DIR/test-results/unit-tests.json" \
        --maxfail=10 \
        -v; then
        
        log_success "Unit tests passed"
        
        # Check coverage threshold
        if [ -f "$REPORTS_DIR/coverage/coverage.json" ]; then
            coverage=$(python -c "
import json
with open('$REPORTS_DIR/coverage/coverage.json') as f:
    data = json.load(f)
print(data['totals']['percent_covered'])
")
            
            log_info "Coverage: ${coverage}%"
            
            if (( $(echo "$coverage >= $COVERAGE_THRESHOLD" | bc -l) )); then
                log_success "Coverage threshold met (${coverage}% >= ${COVERAGE_THRESHOLD}%)"
            else
                log_error "Coverage threshold not met (${coverage}% < ${COVERAGE_THRESHOLD}%)"
                return 1
            fi
        fi
        
        return 0
    else
        log_error "Unit tests failed"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    print_section "Running integration tests"
    
    if [ "$RUN_INTEGRATION_TESTS" != "true" ]; then
        log_info "Integration tests disabled, skipping..."
        return 0
    fi
    
    cd "$PROJECT_ROOT/testing-framework"
    
    # Start test environment if docker-compose exists
    if [ -f "integration-tests/environments/docker-compose.test.yml" ]; then
        log_info "Starting test environment..."
        cd integration-tests/environments
        docker-compose -f docker-compose.test.yml up -d
        sleep 30  # Wait for services to be ready
        cd ../..
    fi
    
    log_info "Executing integration tests..."
    
    if python -m pytest integration-tests/ \
        --html="$REPORTS_DIR/test-results/integration-tests.html" \
        --self-contained-html \
        --json-report \
        --json-report-file="$REPORTS_DIR/test-results/integration-tests.json" \
        -v \
        -m "integration"; then
        
        log_success "Integration tests passed"
        integration_result=0
    else
        log_error "Integration tests failed"
        integration_result=1
    fi
    
    # Stop test environment
    if [ -f "integration-tests/environments/docker-compose.test.yml" ]; then
        log_info "Stopping test environment..."
        cd integration-tests/environments
        docker-compose -f docker-compose.test.yml down
        cd ../..
    fi
    
    return $integration_result
}

# Function to run performance tests
run_performance_tests() {
    print_section "Running performance tests"
    
    if [ "$RUN_PERFORMANCE_TESTS" != "true" ]; then
        log_info "Performance tests disabled, skipping..."
        return 0
    fi
    
    cd "$PROJECT_ROOT/testing-framework"
    
    # Run benchmark tests
    log_info "Running performance benchmarks..."
    if python -m pytest performance-tests/benchmark_tests/ \
        --benchmark-only \
        --benchmark-json="$REPORTS_DIR/performance/benchmark-results.json" \
        --benchmark-html="$REPORTS_DIR/performance/benchmark-results.html"; then
        
        log_success "Performance benchmarks completed"
        
        # Check performance thresholds
        if [ -f "$REPORTS_DIR/performance/benchmark-results.json" ]; then
            python -c "
import json
import sys

with open('$REPORTS_DIR/performance/benchmark-results.json') as f:
    data = json.load(f)

threshold_ms = $PERFORMANCE_THRESHOLD_MS
failed_tests = []

for benchmark in data['benchmarks']:
    mean_time_ms = benchmark['stats']['mean'] * 1000
    if mean_time_ms > threshold_ms:
        failed_tests.append(f\"{benchmark['name']}: {mean_time_ms:.2f}ms\")

if failed_tests:
    print('Performance tests failed:')
    for test in failed_tests:
        print(f'  - {test}')
    sys.exit(1)
else:
    print('All performance tests passed')
"
            if [ $? -eq 0 ]; then
                log_success "Performance thresholds met"
            else
                log_error "Performance thresholds not met"
                return 1
            fi
        fi
        
        return 0
    else
        log_error "Performance tests failed"
        return 1
    fi
}

# Function to run security tests
run_security_tests() {
    print_section "Running security tests"
    
    if [ "$RUN_SECURITY_TESTS" != "true" ]; then
        log_info "Security tests disabled, skipping..."
        return 0
    fi
    
    cd "$PROJECT_ROOT/testing-framework"
    
    log_info "Executing security tests..."
    
    if python -m pytest security-tests/ \
        --html="$REPORTS_DIR/security/security-tests.html" \
        --self-contained-html \
        -v \
        -m "security"; then
        
        log_success "Security tests passed"
        return 0
    else
        log_error "Security tests failed"
        return 1
    fi
}

# Function to generate reports
generate_reports() {
    print_section "Generating comprehensive reports"
    
    cd "$PROJECT_ROOT/testing-framework"
    
    log_info "Generating quality dashboard..."
    
    if python quality-metrics/dashboard_generator.py \
        --input-dir "$REPORTS_DIR" \
        --output-dir "$REPORTS_DIR/dashboard"; then
        
        log_success "Quality dashboard generated"
        log_info "Dashboard available at: $REPORTS_DIR/dashboard/index.html"
    else
        log_warning "Failed to generate quality dashboard"
    fi
    
    # Generate coverage badge
    if [ -f "$REPORTS_DIR/coverage/coverage.json" ]; then
        log_info "Generating coverage badge..."
        python -c "
import json
from quality_metrics.coverage_reporter import CoverageReporter

with open('$REPORTS_DIR/coverage/coverage.json') as f:
    data = json.load(f)

coverage = data['totals']['percent_covered']
reporter = CoverageReporter()
badge = reporter.generate_coverage_badge(coverage)

with open('$REPORTS_DIR/coverage/badge.svg', 'w') as f:
    f.write(badge)

print(f'Coverage badge generated: {coverage:.1f}%')
"
    fi
}

# Function to display summary
display_summary() {
    print_section "Test Execution Summary"
    
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    # Count test results
    if [ -f "$REPORTS_DIR/test-results/unit-tests.json" ]; then
        unit_passed=$(python -c "
import json
with open('$REPORTS_DIR/test-results/unit-tests.json') as f:
    data = json.load(f)
print(data['summary']['passed'])
")
        unit_failed=$(python -c "
import json
with open('$REPORTS_DIR/test-results/unit-tests.json') as f:
    data = json.load(f)
print(data['summary']['failed'])
")
        total_tests=$((total_tests + unit_passed + unit_failed))
        passed_tests=$((passed_tests + unit_passed))
        failed_tests=$((failed_tests + unit_failed))
        
        log_info "Unit Tests: $unit_passed passed, $unit_failed failed"
    fi
    
    if [ -f "$REPORTS_DIR/test-results/integration-tests.json" ]; then
        int_passed=$(python -c "
import json
with open('$REPORTS_DIR/test-results/integration-tests.json') as f:
    data = json.load(f)
print(data['summary']['passed'])
")
        int_failed=$(python -c "
import json
with open('$REPORTS_DIR/test-results/integration-tests.json') as f:
    data = json.load(f)
print(data['summary']['failed'])
")
        total_tests=$((total_tests + int_passed + int_failed))
        passed_tests=$((passed_tests + int_passed))
        failed_tests=$((failed_tests + int_failed))
        
        log_info "Integration Tests: $int_passed passed, $int_failed failed"
    fi
    
    # Display coverage
    if [ -f "$REPORTS_DIR/coverage/coverage.json" ]; then
        coverage=$(python -c "
import json
with open('$REPORTS_DIR/coverage/coverage.json') as f:
    data = json.load(f)
print(f\"{data['totals']['percent_covered']:.2f}\")
")
        log_info "Code Coverage: ${coverage}%"
    fi
    
    echo
    if [ $failed_tests -eq 0 ]; then
        log_success "All tests passed! ($passed_tests/$total_tests)"
        log_info "Reports available in: $REPORTS_DIR"
        return 0
    else
        log_error "Some tests failed ($failed_tests/$total_tests failed)"
        log_info "Check reports in: $REPORTS_DIR"
        return 1
    fi
}

# Main execution function
main() {
    local start_time=$(date +%s)
    
    echo "🧪 Comprehensive Testing & Quality Assurance Framework"
    echo "======================================================"
    echo
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit-only)
                RUN_INTEGRATION_TESTS=false
                RUN_PERFORMANCE_TESTS=false
                RUN_SECURITY_TESTS=false
                shift
                ;;
            --no-integration)
                RUN_INTEGRATION_TESTS=false
                shift
                ;;
            --no-performance)
                RUN_PERFORMANCE_TESTS=false
                shift
                ;;
            --no-security)
                RUN_SECURITY_TESTS=false
                shift
                ;;
            --coverage-threshold)
                COVERAGE_THRESHOLD="$2"
                shift 2
                ;;
            --performance-threshold)
                PERFORMANCE_THRESHOLD_MS="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --unit-only              Run only unit tests"
                echo "  --no-integration         Skip integration tests"
                echo "  --no-performance         Skip performance tests"
                echo "  --no-security           Skip security tests"
                echo "  --coverage-threshold N   Set coverage threshold (default: 90)"
                echo "  --performance-threshold N Set performance threshold in ms (default: 500)"
                echo "  --help                   Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Set defaults
    RUN_INTEGRATION_TESTS=${RUN_INTEGRATION_TESTS:-true}
    RUN_PERFORMANCE_TESTS=${RUN_PERFORMANCE_TESTS:-true}
    RUN_SECURITY_TESTS=${RUN_SECURITY_TESTS:-true}
    
    # Execute test phases
    local exit_code=0
    
    setup_environment || exit_code=1
    
    if [ $exit_code -eq 0 ]; then
        run_code_quality || exit_code=1
    fi
    
    if [ $exit_code -eq 0 ]; then
        run_unit_tests || exit_code=1
    fi
    
    if [ $exit_code -eq 0 ] && [ "$RUN_INTEGRATION_TESTS" = "true" ]; then
        run_integration_tests || exit_code=1
    fi
    
    if [ $exit_code -eq 0 ] && [ "$RUN_PERFORMANCE_TESTS" = "true" ]; then
        run_performance_tests || exit_code=1
    fi
    
    if [ $exit_code -eq 0 ] && [ "$RUN_SECURITY_TESTS" = "true" ]; then
        run_security_tests || exit_code=1
    fi
    
    # Always generate reports
    generate_reports
    
    # Display summary
    display_summary
    local summary_exit=$?
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo
    log_info "Total execution time: ${duration} seconds"
    
    # Return the worst exit code
    if [ $exit_code -ne 0 ]; then
        exit $exit_code
    else
        exit $summary_exit
    fi
}

# Run main function with all arguments
main "$@"

