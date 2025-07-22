# Contributing to DSL to PNG MCP Server

Thank you for your interest in contributing to the DSL to PNG MCP Server! This guide will help you get started with contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Guidelines](#code-guidelines)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)
- [Community Guidelines](#community-guidelines)

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.11+** installed
- **Docker & Docker Compose** for containerized development
- **Git** for version control
- **Node.js 16+** (for MCP client testing)
- **Redis** (or use Docker container)

### Development Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/dslToPngMCP.git
   cd dslToPngMCP
   
   # Add upstream remote
   git remote add upstream https://github.com/ORIGINAL_OWNER/dslToPngMCP.git
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies
   pip install -r requirements/dev.txt
   
   # Install pre-commit hooks
   pre-commit install
   
   # Set up environment variables
   cp .env.example .env
   ```

3. **Start Development Services**
   ```bash
   # Option 1: Docker (Recommended)
   docker compose up -d
   
   # Option 2: Local development
   # Start Redis
   redis-server
   
   # Start FastAPI server
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   
   # Start Celery workers (in another terminal)
   celery -A src.core.queue.tasks worker --loglevel=info
   ```

4. **Verify Setup**
   ```bash
   # Test health endpoint
   curl http://localhost:8000/health
   
   # Run tests
   pytest
   
   # Check code quality
   make lint
   ```

---

## Development Workflow

### Branch Strategy

We use **GitHub Flow** with the following conventions:

- **`main`** - Production-ready code
- **Feature branches** - `feature/description` or `feat/issue-number`
- **Bug fixes** - `fix/description` or `fix/issue-number`
- **Documentation** - `docs/description`
- **Hotfixes** - `hotfix/critical-issue`

### Creating a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/add-new-element-type

# Work on your changes...
git add .
git commit -m "feat: add support for table element type"

# Push to your fork
git push origin feature/add-new-element-type
```

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes
- `perf`: Performance improvements
- `ci`: CI/CD changes

**Examples:**
```bash
git commit -m "feat(dsl): add support for table element with responsive layout"
git commit -m "fix(api): handle malformed DSL content gracefully"
git commit -m "docs: update installation guide for Windows users"
git commit -m "test: add integration tests for async rendering"
```

---

## Code Guidelines

### Python Code Style

We follow **PEP 8** with these additional conventions:

#### Formatting
```python
# Use Black for consistent formatting
black src/ tests/

# Line length: 88 characters (Black default)
# Use double quotes for strings
# Use trailing commas in multi-line structures
```

#### Type Hints
```python
# Always use type hints for function signatures
from typing import Optional, List, Dict, Any

async def parse_dsl(content: str, strict: bool = False) -> ParseResult:
    """Parse DSL content with optional strict validation."""
    pass

# Use Pydantic models for data validation
class DSLElement(BaseModel):
    type: ElementType
    layout: Optional[ElementLayout] = None
    style: Optional[ElementStyle] = None
```

#### Error Handling
```python
# Use specific exception types
class DSLParseError(Exception):
    """Raised when DSL parsing fails."""
    pass

# Provide detailed error messages
try:
    result = parse_dsl(content)
except DSLParseError as e:
    logger.error("DSL parsing failed", content_length=len(content), error=str(e))
    raise HTTPException(
        status_code=400,
        detail=f"DSL parsing failed: {e}. Check syntax and try again."
    )
```

#### Logging
```python
# Use structured logging
from src.config.logging import get_logger

logger = get_logger(__name__)

# Log with context
logger.info(
    "DSL parsing completed",
    content_length=len(content),
    element_count=len(document.elements),
    processing_time=elapsed_time
)
```

### Code Organization

#### Project Structure
```
src/
├── api/                 # FastAPI application
│   ├── main.py         # App factory and configuration
│   ├── routers/        # API route handlers
│   └── dependencies/   # Dependency injection
├── core/               # Business logic
│   ├── dsl/           # DSL parsing and validation
│   ├── rendering/     # HTML/PNG generation
│   ├── queue/         # Task queue management
│   └── storage/       # File storage abstraction
├── mcp_server/        # MCP protocol implementation
├── models/            # Pydantic models and schemas
├── config/            # Configuration management
└── utils/             # Shared utilities
```

#### Module Guidelines
```python
# Each module should have a clear, single responsibility
# Use __init__.py files to define public interfaces

# src/core/dsl/__init__.py
from .parser import parse_dsl, validate_dsl_syntax
from .schemas import DSLDocument, DSLElement

__all__ = ["parse_dsl", "validate_dsl_syntax", "DSLDocument", "DSLElement"]

# Import ordering: stdlib, third-party, local
import asyncio
import json
from typing import Dict, List

import redis
from fastapi import HTTPException
from pydantic import BaseModel

from src.config.settings import get_settings
from src.models.schemas import DSLRenderRequest
```

### Performance Guidelines

#### Async Programming
```python
# Use async/await for I/O operations
async def generate_png(html_content: str, options: RenderOptions) -> PNGResult:
    """Generate PNG from HTML using browser automation."""
    async with browser_pool.acquire() as browser:
        page = await browser.new_page()
        await page.set_content(html_content)
        screenshot = await page.screenshot()
        return PNGResult(png_data=screenshot)

# Avoid blocking operations in async functions
# Use run_in_executor for CPU-bound tasks
```

#### Memory Management
```python
# Use context managers for resource cleanup
async def process_large_dsl(content: str):
    async with temp_file() as temp_path:
        # Process large content with memory limits
        pass

# Limit collection sizes
@lru_cache(maxsize=100)
def expensive_computation(data: str) -> str:
    # Cached computation
    pass
```

---

## Testing Requirements

### Test Categories

1. **Unit Tests** - Test individual functions/classes
2. **Integration Tests** - Test component interactions
3. **End-to-End Tests** - Test complete user workflows
4. **Performance Tests** - Test system performance
5. **Security Tests** - Test security measures

### Writing Tests

#### Unit Test Example
```python
# tests/unit/test_dsl_parser.py
import pytest
from src.core.dsl.parser import parse_dsl, DSLParseError

class TestDSLParser:
    @pytest.mark.asyncio
    async def test_parse_valid_json_dsl(self):
        """Test parsing valid JSON DSL content."""
        dsl_content = '{"width": 400, "height": 300, "elements": []}'
        
        result = await parse_dsl(dsl_content)
        
        assert result.success
        assert result.document.width == 400
        assert result.document.height == 300
        assert len(result.document.elements) == 0
    
    @pytest.mark.asyncio
    async def test_parse_invalid_json_raises_error(self):
        """Test that invalid JSON raises appropriate error."""
        dsl_content = '{"width": 400, "height": 300, "elements": []'  # Missing }
        
        result = await parse_dsl(dsl_content)
        
        assert not result.success
        assert "Invalid JSON syntax" in result.errors[0]
    
    @pytest.mark.parametrize("width,height,expected", [
        (100, 100, True),
        (0, 100, False),
        (100, 0, False),
        (5000, 100, False),
    ])
    @pytest.mark.asyncio
    async def test_canvas_size_validation(self, width, height, expected):
        """Test canvas size validation."""
        dsl_content = f'{{"width": {width}, "height": {height}, "elements": []}}'
        
        result = await parse_dsl(dsl_content)
        
        assert result.success == expected
```

#### Integration Test Example
```python
# tests/integration/test_render_pipeline.py
import pytest
from httpx import AsyncClient
from src.api.main import app

class TestRenderPipeline:
    @pytest.mark.asyncio
    async def test_complete_render_workflow(self):
        """Test complete DSL to PNG workflow."""
        dsl_content = {
            "width": 400,
            "height": 300,
            "elements": [
                {
                    "type": "button",
                    "layout": {"x": 100, "y": 100, "width": 200, "height": 50},
                    "label": "Test Button",
                    "style": {"background": "#007bff", "color": "white"}
                }
            ]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. Validate DSL
            response = await client.post("/validate", json={"dsl_content": str(dsl_content)})
            assert response.status_code == 200
            assert response.json()["valid"]
            
            # 2. Render PNG
            response = await client.post("/render", json={"dsl_content": str(dsl_content)})
            assert response.status_code == 200
            
            result = response.json()
            assert result["success"]
            assert "png_result" in result
            assert result["png_result"]["width"] == 400
            assert result["png_result"]["height"] == 300
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_dsl_parser.py::TestDSLParser::test_parse_valid_json_dsl

# Run tests in parallel
pytest -n auto

# Run tests with specific markers
pytest -m "not slow"
```

### Test Configuration

```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-branch
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    performance: marks tests as performance tests
```

### Test Data and Fixtures

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from src.api.main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_dsl():
    """Sample DSL for testing."""
    return {
        "width": 400,
        "height": 300,
        "elements": [
            {
                "type": "text",
                "text": "Hello World",
                "layout": {"x": 50, "y": 50, "width": 300, "height": 50}
            }
        ]
    }
```

---

## Documentation Standards

### Documentation Types

1. **Code Documentation** - Docstrings and comments
2. **API Documentation** - OpenAPI/Swagger specs
3. **User Documentation** - Guides and tutorials
4. **Architecture Documentation** - Design decisions

### Docstring Standards

```python
def parse_dsl(content: str, parser_type: Optional[str] = None) -> ParseResult:
    """
    Parse DSL content using appropriate parser.
    
    Automatically detects parser type (JSON/YAML) if not specified.
    Validates syntax and structure according to DSL schema.
    
    Args:
        content: Raw DSL content as string
        parser_type: Optional parser type override ("json" or "yaml")
        
    Returns:
        ParseResult containing parsed document or validation errors
        
    Raises:
        DSLParseError: When DSL content is invalid or unsupported
        
    Example:
        >>> result = await parse_dsl('{"width": 400, "height": 300, "elements": []}')
        >>> assert result.success
        >>> assert result.document.width == 400
    """
```

### Markdown Documentation

```markdown
# Use clear headings hierarchy
## Second level
### Third level

# Code blocks with language specification
```python
def example_function():
    pass
```

# Tables for structured information
| Parameter | Type | Description |
|-----------|------|-------------|
| content | string | DSL content |

# Links to related sections
See [API Documentation](./docs/API.md) for details.
```

### Documentation Updates

When making changes:

1. **Update docstrings** for modified functions
2. **Update API docs** if endpoints change
3. **Update user guides** for new features
4. **Add examples** for new functionality
5. **Update changelog** with user-facing changes

---

## Submitting Changes

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following guidelines
   - Add/update tests
   - Update documentation
   - Ensure all tests pass

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature with tests and docs"
   ```

4. **Push to Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Use the PR template
   - Provide clear description
   - Link related issues
   - Add screenshots for UI changes

### Pull Request Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact assessed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Changelog updated (if needed)

## Screenshots/Examples
(If applicable)

## Related Issues
Fixes #(issue_number)
```

### Code Review Guidelines

#### For Authors
- Keep PRs focused and reasonably sized
- Provide clear commit messages
- Add tests for new functionality
- Update documentation
- Respond to feedback promptly

#### For Reviewers
- Review for correctness, performance, and maintainability
- Provide constructive feedback
- Approve when confident in changes
- Test locally for complex changes

### Review Checklist

- [ ] **Correctness**: Does the code do what it's supposed to do?
- [ ] **Performance**: Are there any performance implications?
- [ ] **Security**: Are there any security concerns?
- [ ] **Testing**: Are there adequate tests?
- [ ] **Documentation**: Is documentation updated?
- [ ] **Style**: Does code follow project conventions?
- [ ] **Maintainability**: Is the code readable and maintainable?

---

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality
- **PATCH** version for backwards-compatible bug fixes

Examples:
- `1.0.0` - Initial release
- `1.1.0` - New features added
- `1.1.1` - Bug fixes
- `2.0.0` - Breaking changes

### Release Workflow

1. **Prepare Release**
   ```bash
   # Update version in pyproject.toml
   # Update CHANGELOG.md
   # Ensure all tests pass
   # Create release branch
   git checkout -b release/v1.2.0
   ```

2. **Create Release PR**
   - Update version numbers
   - Update changelog
   - Get approval from maintainers

3. **Tag Release**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

4. **Build and Deploy**
   - CI/CD automatically builds Docker images
   - Docker images tagged with version
   - Release notes generated from changelog

### Changelog Format

```markdown
# Changelog

## [1.2.0] - 2024-01-20

### Added
- New table element type for DSL
- Support for responsive breakpoints
- Performance monitoring dashboard

### Changed
- Improved error messages in DSL validation
- Updated Docker base images

### Fixed
- Fixed memory leak in browser pool
- Resolved CSS rendering issues

### Security
- Updated dependencies with security patches
```

---

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

### Communication Channels

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General questions and discussions
- **Pull Requests** - Code contributions and reviews

### Getting Help

- **Documentation** - Check existing docs first
- **Issues Search** - Look for similar issues
- **Discussions** - Ask questions in GitHub Discussions
- **Support** - Create issue with "question" label

### Reporting Issues

When reporting bugs:

1. **Check existing issues** first
2. **Use issue template** provided
3. **Provide minimal reproduction** case
4. **Include system information**
5. **Add relevant labels**

**Bug Report Template:**
```markdown
## Bug Description
Clear description of the bug.

## Steps to Reproduce
1. Step one
2. Step two
3. See error

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Environment
- OS: [e.g., Ubuntu 20.04]
- Python: [e.g., 3.11.0]
- Docker: [e.g., 20.10.8]
- Browser: [e.g., Chrome 96]

## Additional Context
Screenshots, logs, etc.
```

### Feature Requests

When requesting features:

1. **Search existing requests**
2. **Describe the problem** you're solving
3. **Propose a solution**
4. **Consider implementation** complexity
5. **Discuss in GitHub Discussions** first for large features

### Recognition

Contributors are recognized in:
- **README.md** contributors section
- **Release notes** for significant contributions
- **GitHub contributors** page

---

## Development Tools

### Recommended IDE Setup

**VS Code Extensions:**
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.pylint",
    "ms-python.mypy-type-checker",
    "redhat.vscode-yaml",
    "ms-vscode.vscode-json",
    "ms-azuretools.vscode-docker"
  ]
}
```

**Settings:**
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true
}
```

### Makefile Commands

```makefile
# Development commands
.PHONY: dev test lint format clean

dev:
	docker compose up -d

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html

lint:
	pylint src/
	mypy src/
	black --check src/

format:
	black src/ tests/
	isort src/ tests/

clean:
	docker compose down
	docker system prune -f
```

---

## Questions?

If you have questions about contributing:

1. Check this guide and existing documentation
2. Search GitHub Issues and Discussions
3. Create a new Discussion with the "question" label
4. Reach out to maintainers via GitHub

Thank you for contributing to DSL to PNG MCP Server! 🎨