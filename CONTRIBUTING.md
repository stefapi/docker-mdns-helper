# Contributing to Docker mDNS Helper

Thank you for your interest in contributing to Docker mDNS Helper! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Style and Standards](#code-style-and-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Project Structure](#project-structure)

## Code of Conduct

This project follows a standard code of conduct. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Linux system** (Ubuntu, Debian, CentOS, etc.)
- **Python 3.8+** installed
- **Docker** installed and running
- **Avahi daemon** installed and running
- **Git** for version control
- **Root/sudo access** for testing system integration

### Fork and Clone

1. Fork the repository on GitHub: https://github.com/stefapi/docker-mdns-helper
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/docker-mdns-helper.git
   cd docker-mdns-helper
   ```

## Development Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Or install with optional dev dependencies
pip install -e ".[dev]"
```

### 3. Install Pre-commit Hooks

```bash
pre-commit install
```

### 4. Verify Setup

```bash
# Run tests to ensure everything works
pytest

# Check code style
black --check .
flake8 .
isort --check-only .
mypy .
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write your code following the project's style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_docker_domains.py

# Run security checks
bandit -r .
safety check
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new feature description"
# or
git commit -m "fix: resolve issue with specific component"
```

Use conventional commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/modifications
- `refactor:` for code refactoring
- `style:` for formatting changes
- `chore:` for maintenance tasks

## Code Style and Standards

This project follows strict code quality standards:

### Python Code Style

- **Line length**: 88 characters (Black default)
- **Code formatter**: Black
- **Import sorting**: isort
- **Linting**: flake8
- **Type checking**: mypy

### Formatting Commands

```bash
# Format code
black .

# Sort imports
isort .

# Check linting
flake8 .

# Type checking
mypy .
```

### Code Quality Requirements

- All code must pass flake8 linting
- All code must be formatted with Black
- All imports must be sorted with isort
- Type hints are required for all functions and methods
- All code must pass mypy type checking

## Testing

### Test Structure

- Tests are located in the `tests/` directory
- Test files follow the pattern `test_*.py`
- Use pytest for all testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_avahi_publisher.py

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Run tests matching a pattern
pytest -k "test_docker_domains"
```

### Writing Tests

- Write unit tests for all new functionality
- Use pytest fixtures for common test setup
- Mock external dependencies (Docker API, Avahi, etc.)
- Aim for high test coverage (>90%)
- Include both positive and negative test cases
- Test edge cases and error conditions

### Test Categories

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Robustness tests**: Test error handling and recovery
- **Version compatibility tests**: Test with different Docker/Traefik versions

## Submitting Changes

### Pull Request Process

1. **Update your branch** with the latest main:
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Ensure all checks pass**:
   ```bash
   pytest
   black --check .
   flake8 .
   isort --check-only .
   mypy .
   bandit -r .
   ```

3. **Push your changes**:
   ```bash
   git push origin your-branch
   ```

4. **Create Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues
   - Screenshots or examples if applicable

### Pull Request Requirements

- All tests must pass
- Code coverage should not decrease
- All code quality checks must pass
- Documentation must be updated if needed
- Commit messages should follow conventional format

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

- **Environment details**: OS, Python version, Docker version
- **Steps to reproduce**: Clear, step-by-step instructions
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Logs**: Relevant log output or error messages
- **Configuration**: Docker labels, command-line arguments used

### Feature Requests

For feature requests, please include:

- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches you've thought about
- **Additional context**: Any other relevant information

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed

## Project Structure

```
docker-mdns-helper/
├── start.py                 # Main entry point
├── docker_domains.py        # Docker container monitoring
├── avahi_publisher.py       # Avahi/mDNS publishing
├── daemonize.py            # Daemon functionality
├── config.py               # Configuration handling
├── _avahi/                 # Avahi D-Bus interface
├── tests/                  # Test suite
│   ├── test_avahi_publisher.py
│   ├── test_docker_domains.py
│   ├── test_robustness.py
│   └── test_version_compatibility.py
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Development dependencies
├── pyproject.toml         # Project configuration
├── Dockerfile             # Container build
├── docker-compose.yml     # Docker Compose example
└── README.md              # Project documentation
```

### Key Components

- **start.py**: Main application entry point and orchestration
- **docker_domains.py**: Monitors Docker containers and extracts domain information
- **avahi_publisher.py**: Publishes mDNS records via Avahi D-Bus interface
- **_avahi/**: Low-level Avahi D-Bus communication
- **tests/**: Comprehensive test suite covering all components

## Development Tips

### Local Testing

1. **Test with real Docker containers**:
   ```bash
   # Start a test container with labels
   docker run -d --name test-app \
     --label "traefik.http.routers.test.rule=Host(\`test.local\`)" \
     nginx
   
   # Run the helper
   python start.py --verbose
   ```

2. **Test mDNS resolution**:
   ```bash
   # Check if mDNS record is published
   avahi-resolve -n test.local
   
   # Browse available services
   avahi-browse -a
   ```

### Debugging

- Use `--verbose` flag for detailed logging
- Use `ipdb` for interactive debugging
- Check Avahi logs: `journalctl -u avahi-daemon`
- Monitor Docker events: `docker events`

### Performance Considerations

- The service monitors Docker events in real-time
- mDNS records are only updated when container labels change
- Use appropriate TTL values for mDNS records
- Consider resource usage when adding new features

## Getting Help

- **GitHub Issues**: https://github.com/stefapi/docker-mdns-helper/issues
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check the README.md for usage examples

Thank you for contributing to Docker mDNS Helper! 🚀
