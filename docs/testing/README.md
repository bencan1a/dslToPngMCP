# DSL to PNG Testing Framework

## Overview

This document provides comprehensive guidance for the DSL to PNG conversion system testing framework. The framework includes multiple test types, automation tools, and quality assurance measures to ensure system reliability and performance.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Types](#test-types)
- [Setup and Installation](#setup-and-installation)
- [Running Tests](#running-tests)
- [Test Data and Scenarios](#test-data-and-scenarios)
- [CI/CD Integration](#cicd-integration)
- [Coverage and Reporting](#coverage-and-reporting)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Redis (for integration tests)
- Chromium/Chrome browser

### Basic Test Execution

```bash
# Install dependencies
pip install -r requirements/dev.txt

# Run all tests
pytest

# Run specific test types
pytest -m "smoke"           # Smoke tests only
pytest -m "unit"            # Unit tests only
pytest -m "integration"     # Integration tests only
pytest -m "performance"     # Performance tests only
pytest -m "security"        # Security tests only
```

## Test Types

### 1. Smoke Tests 🚀
**Purpose**: Quick validation of core functionality  
**Duration**: < 2 minutes  
**Coverage**: Critical paths only

```bash
pytest -m "smoke"
```

### 2. Unit Tests 🔧
**Purpose**: Individual component testing  
**Duration**: 5-10 minutes  
**Coverage**: All core modules

```bash
pytest tests/unit/
```

**Components tested**:
- DSL Parser (`tests/unit/test_dsl_parser.py`)
- HTML Generator (`tests/unit/test_html_generator.py`)
- PNG Generator (`tests/unit/test_png_generator.py`)
- Storage Manager (`tests/unit/test_storage_manager.py`)

### 3. Integration Tests 🔗
**Purpose**: Component interaction testing  
**Duration**: 15-30 minutes  
**Coverage**: End-to-end workflows

```bash
pytest tests/integration/
```

**Areas covered**:
- End-to-end pipeline (`tests/integration/test_end_to_end_pipeline.py`)
- API contracts (`tests/integration/test_api_contracts.py`)
- MCP protocol (`tests/integration/test_mcp_protocol.py`)

### 4. Performance Tests ⚡
**Purpose**: Performance and scalability validation  
**Duration**: 30-60 minutes  
**Coverage**: Load and stress testing

```bash
pytest tests/performance/
```

### 5. Security Tests 🔒
**Purpose**: Security vulnerability detection  
**Duration**: 10-20 minutes  
**Coverage**: Input validation, authentication, authorization

```bash
pytest tests/security/
```

### 6. Docker Container Tests 🐳
**Purpose**: Containerized deployment validation  
**Duration**: 20-40 minutes  
**Coverage**: Multi-container orchestration

```bash
docker compose -f docker/docker compose.test.yml up --abort-on-container-exit
```

## Setup and Installation

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dslToPngMCP
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/dev.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

5. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Docker Setup

1. **Build test container**
   ```bash
   docker build -f docker/Dockerfile.test -t dsl-png-test .
   ```

2. **Run containerized tests**
   ```bash
   docker compose -f docker/docker compose.test.yml up
   ```

### CI/CD Setup

The project includes GitHub Actions workflows for automated testing:

- **Main workflow**: `.github/workflows/test-suite.yml`
- **Triggers**: Push to main/develop, PR creation, daily schedule
- **Environments**: Ubuntu, Windows, macOS
- **Python versions**: 3.9, 3.10, 3.11, 3.12

## Running Tests

### Command Line Options

#### Basic Execution
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_dsl_parser.py

# Run specific test class
pytest tests/unit/test_dsl_parser.py::TestDSLParser

# Run specific test method
pytest tests/unit/test_dsl_parser.py::TestDSLParser::test_parse_valid_json
```

#### Test Selection by Markers
```bash
# Critical tests only
pytest -m "critical"

# Exclude slow tests
pytest -m "not slow"

# Multiple markers
pytest -m "unit and not requires_browser"

# Performance tests with benchmarking
pytest -m "performance" --benchmark-sort=mean
```

#### Output and Reporting
```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# Generate JUnit XML
pytest --junitxml=test-results.xml

# Show test durations
pytest --durations=10

# Stop on first failure
pytest -x

# Show local variables on failure
pytest --showlocals
```

### Docker Test Execution

#### Full Test Suite
```bash
docker compose -f docker/docker compose.test.yml up test
```

#### Specific Test Types
```bash
# Unit tests only
docker compose -f docker/docker compose.test.yml up unit-test

# Integration tests
docker compose -f docker/docker compose.test.yml up integration-test

# Performance tests
docker compose -f docker/docker compose.test.yml up performance-test

# Security tests
docker compose -f docker/docker compose.test.yml up security-test
```

## Test Data and Scenarios

### Sample DSL Documents

The framework includes comprehensive test data in `tests/data/`:

- **Simple documents**: Basic text and layout examples
- **Complex documents**: Dashboards, responsive designs
- **Performance documents**: Large-scale stress testing
- **Edge cases**: Empty, minimal, maximum size documents
- **Invalid documents**: Error condition testing

```python
from tests.data import (
    SIMPLE_TEXT_DOCUMENT,
    COMPLEX_DASHBOARD_DOCUMENT,
    RESPONSIVE_DESIGN_DOCUMENT
)
```

### Render Options

Predefined render configurations for various scenarios:

```python
from tests.data import (
    BASIC_RENDER_OPTIONS,
    HIGH_DPI_RENDER_OPTIONS,
    MOBILE_PORTRAIT_OPTIONS
)
```

### Test Scenarios

Structured test scenarios combining documents and options:

```python
from tests.data import (
    SMOKE_TEST_SCENARIOS,
    PERFORMANCE_TEST_SCENARIOS,
    get_scenario_by_name
)
```

## CI/CD Integration

### GitHub Actions Workflow

The main workflow (`.github/workflows/test-suite.yml`) includes:

1. **Smoke Tests**: Fast feedback (< 10 minutes)
2. **Unit Tests**: Matrix across OS and Python versions
3. **Integration Tests**: With service dependencies
4. **Performance Tests**: With regression detection
5. **Security Tests**: Vulnerability scanning
6. **Docker Tests**: Container validation
7. **Test Reporting**: Combined results and coverage

### Workflow Triggers

- **Push**: To main/develop branches
- **Pull Request**: To main/develop branches
- **Schedule**: Daily at 2 AM UTC
- **Manual**: Via workflow_dispatch

### Quality Gates

Tests must pass these criteria:

- **Coverage**: Minimum 80%
- **Success Rate**: Minimum 95%
- **Performance**: No >10% regression
- **Security**: No critical vulnerabilities

## Coverage and Reporting

### Coverage Configuration

Coverage is configured in `pytest.ini`:

```ini
addopts = 
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-branch
    --cov-fail-under=80
```

### Report Generation

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### CI Report Integration

- **Codecov**: Automatic upload of coverage data
- **GitHub PR**: Automated comments with test results
- **Artifacts**: Test results preserved for 30 days

## Performance Testing

### Benchmark Framework

Performance tests use pytest-benchmark:

```python
def test_dsl_parsing_performance(benchmark):
    parser = DSLParser()
    document = benchmark(parser.parse_dict, sample_dsl)
    assert document is not None
```

### Performance Metrics

- **Processing Time**: Individual operation duration
- **Throughput**: Requests per second
- **Memory Usage**: Peak memory consumption
- **Concurrent Performance**: Multi-request handling

### Regression Detection

Automated performance regression checking:

```bash
python scripts/check_performance_regression.py \
    --current performance-benchmark.json \
    --baseline performance-baseline.json \
    --threshold 0.1
```

## Security Testing

### Test Categories

1. **Input Validation**: XSS, injection attacks
2. **Authentication**: JWT token validation
3. **Authorization**: Permission checking
4. **File System**: Path traversal prevention
5. **Data Sanitization**: Output encoding

### Security Tools Integration

- **Bandit**: Static security analysis
- **Safety**: Dependency vulnerability scanning
- **Custom Tests**: Application-specific security validation

### Security Reports

```bash
# Run security scan
bandit -r src/ -f json -o security-report.json

# Check dependencies
safety check --json --output safety-report.json
```

## Troubleshooting

### Common Issues

#### Browser Installation
```bash
# If Playwright browsers are missing
playwright install chromium
playwright install-deps
```

#### Permission Errors
```bash
# Fix script permissions
chmod +x scripts/*.py
```

#### Memory Issues
```bash
# Increase Docker memory limit
docker system prune -a
```

#### Port Conflicts
```bash
# Check for conflicting services
lsof -i :6379  # Redis
lsof -i :5432  # PostgreSQL
```

### Debug Mode

Enable debug logging:

```bash
# Environment variable
export TESTING_DEBUG=true

# pytest option
pytest --log-cli-level=DEBUG
```

### Test Isolation

Ensure test isolation:

```bash
# Clean pytest cache
pytest --cache-clear

# Remove test artifacts
rm -rf .pytest_cache htmlcov test-results.xml
```

## Contributing

### Writing New Tests

1. **Follow naming conventions**:
   - Files: `test_*.py`
   - Classes: `Test*`
   - Methods: `test_*`

2. **Use appropriate markers**:
   ```python
   @pytest.mark.unit
   @pytest.mark.requires_browser
   def test_example():
       pass
   ```

3. **Add documentation**:
   ```python
   def test_dsl_parsing():
       """Test DSL parsing with valid input.
       
       This test validates that the DSL parser correctly
       processes valid JSON/YAML input and returns a
       properly structured document object.
       """
       pass
   ```

### Test Guidelines

1. **Test Independence**: Each test should be independent
2. **Clear Assertions**: Use descriptive assertion messages
3. **Fixtures**: Use fixtures for common setup
4. **Mocking**: Mock external dependencies appropriately
5. **Performance**: Consider test execution time

### Code Coverage

- Aim for >90% line coverage
- Include branch coverage
- Test error conditions
- Validate edge cases

### Pull Request Requirements

1. All tests must pass
2. Coverage must not decrease
3. New code must include tests
4. Security tests must pass
5. Performance tests must not regress

## Best Practices

### Test Structure

```python
# Good test structure
def test_feature_with_valid_input():
    # Arrange
    input_data = create_test_data()
    processor = FeatureProcessor()
    
    # Act
    result = processor.process(input_data)
    
    # Assert
    assert result.is_valid
    assert result.output_count == expected_count
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    async with AsyncProcessor() as processor:
        result = await processor.process_async(data)
        assert result is not None
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input_data,expected", [
    ("valid_input", True),
    ("invalid_input", False),
])
def test_validation(input_data, expected):
    result = validate(input_data)
    assert result == expected
```

### Error Testing

```python
def test_error_handling():
    processor = DataProcessor()
    
    with pytest.raises(ValidationError) as exc_info:
        processor.process(invalid_data)
    
    assert "validation failed" in str(exc_info.value)
```

For more detailed information, see the specific documentation files:

- [Unit Testing Guide](unit-testing.md)
- [Integration Testing Guide](integration-testing.md)
- [Performance Testing Guide](performance-testing.md)
- [Security Testing Guide](security-testing.md)
- [CI/CD Guide](cicd-guide.md)