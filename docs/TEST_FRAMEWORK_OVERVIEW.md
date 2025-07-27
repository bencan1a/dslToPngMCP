# Testing Framework Overview

This document provides a comprehensive overview of the testing framework for the DSL to PNG MCP project. It covers the architecture, organization, execution workflows, and best practices for testing.

## Testing Framework Architecture

The testing framework is divided into two main tiers:

1. **Containerized Testing (Unit & Integration)**
   - **Description**: Runs unit and integration tests within Docker containers
   - **Configuration**: Managed through `docker-compose.test.yml`
   - **Services**:
     - PostgreSQL database
     - Redis for caching and message queuing
     - Test runner using pytest
   - **Execution**:
     - Primary command: `docker compose -f docker/docker-compose.test.yml up`
     - Specific test categories can be run using:
       ```bash
       docker compose -f docker/docker-compose.test.yml run test pytest -m "category"
       ```
     - Example categories: `smoke`, `unit`, `integration`, `performance`, `security`

2. **Host-Based End-to-End (E2E) Testing**
   - **Description**: Runs E2E tests directly on the host environment
   - **Configuration**:
     - Uses activated virtual environment
     - Test discovery and fixtures in `tests/conftest.py`
   - **Execution**:
     - Command: `. venv/bin/activate && pytest tests/e2e/`
     - Manages development environment through `docker-compose.yaml`

## VS Code Integration

The project includes comprehensive VS Code integration for seamless testing within the IDE:

### Smart Test Runner

A custom test runner (`scripts/vscode_test_runner.py`) automatically routes tests according to the two-tier architecture:

- **Integration/Unit tests**: Automatically run via Docker Compose
- **E2E tests**: Run locally with virtual environment activation
- **Mixed test runs**: Intelligently handles both types in sequence

### VS Code Configuration

The `.vscode/` directory contains:

- **`settings.json`**: Configures Python testing, interpreter, and workspace settings
- **`tasks.json`**: Provides tasks for running different test types
- **`launch.json`**: Debug configurations for test debugging

### Available VS Code Tasks

Access via `Ctrl+Shift+P` → "Tasks: Run Task":

1. **Run All Tests (Smart)**: Uses the smart test runner for automatic routing
2. **Run Docker Tests Only**: Forces Docker Compose execution
3. **Run E2E Tests Only**: Forces local execution with venv
4. **Test Discovery**: Discovers tests without running them
5. **Setup Test Environment**: Runs test setup scripts
6. **Clean Test Artifacts**: Removes cache and temporary files

### Debug Configurations

Access via `F5` or Debug panel:

1. **Debug Current Test File**: Debug the currently open test file
2. **Debug Specific Test**: Debug tests matching a pattern
3. **Debug E2E Tests**: Debug E2E tests specifically
4. **Debug Test Runner**: Debug the smart test runner itself

### Test Discovery and Execution

- **Automatic Discovery**: Tests are discovered automatically on save
- **Individual Test Running**: Click the play button next to any test
- **Test Filtering**: Use VS Code's test filter to run specific test categories
- **Real-time Results**: See test results directly in the VS Code interface

### Benefits

- **Seamless Integration**: No need to remember Docker commands
- **Automatic Routing**: Tests run in the correct environment automatically
- **IDE Features**: Full debugging, breakpoints, and test exploration
- **Consistent Experience**: Works the same way regardless of test type

## Test Organization

Tests are organized in the following structure:

```
tests/
├── unit/                 # Unit tests
├── integration/          # Integration tests
├── performance/          # Performance tests
├── security/             # Security tests
├── e2e/                  # End-to-end tests
└── fixtures/             # Test fixtures and helpers
```

## Execution Workflows

### Containerized Testing
1. **Run all tests**:
   ```bash
   docker compose -f docker/docker-compose.test.yml up
   ```
2. **Run specific test categories**:
   ```bash
   docker compose -f docker/docker-compose.test.yml run test-runner pytest tests/<category>/ -m <marker>
   ```
   - Example: `docker compose -f docker/docker-compose.test.yml run test-runner pytest tests/unit/`

### Host-Based E2E Testing
1. **Activate virtual environment**:
   ```bash
   . venv/bin/activate
   ```
2. **Run E2E tests**:
   ```bash
   pytest tests/e2e/
   ```

### VS Code Integration Workflow
1. **Open VS Code**: The workspace is automatically configured for testing
2. **Test Discovery**: Tests are discovered automatically on workspace load
3. **Run Individual Tests**: 
   - Click the play button next to any test in the Test Explorer
   - Use `Ctrl+Shift+P` → "Python: Run Test" commands
4. **Run Test Suites**:
   - Use VS Code tasks (`Ctrl+Shift+P` → "Tasks: Run Task")
   - Tests are automatically routed to the correct environment
5. **Debug Tests**:
   - Set breakpoints and use `F5` to debug
   - Choose appropriate debug configuration for test type

## Configuration

- **Primary Configuration**: `pyproject.toml`
- **Pytest Configuration**: `pytest.ini`
- **Environment Variables**: Managed through Docker Compose files
- **Test Fixtures**: Located in `tests/fixtures/`

## Best Practices

1. **Test Categories**:
   - Use markers (`-m` flag) to categorize and filter tests
   - Common markers: `smoke`, `unit`, `integration`, `performance`, `security`

2. **Development Workflow**:
   - Use containerized environment for unit/integration tests
   - Use host environment for E2E tests
   - Leverage test fixtures for consistent test setup

3. **Test Writing**:
   - Follow pytest best practices
   - Use fixtures for test setup/teardown
   - Maintain clear separation between test categories

4. **Logging and Debugging**:
   - Use `docker compose logs` for containerized test output
   - Enable verbose output with `-v` flag for pytest
   - Use VS Code debugging features for interactive debugging

5. **VS Code Integration**:
   - Tests automatically route to the correct environment
   - Use the Test Explorer for visual test management
   - Leverage built-in debugging capabilities
   - Use tasks for common testing workflows