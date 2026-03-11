# Publishing Arden to PyPI

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **Install Build Tools**:
```bash
pip install build twine
```

3. **API Tokens**: Generate API tokens for uploading:
   - PyPI: Account Settings → API tokens → Add API token
   - TestPyPI: Same process on test.pypi.org

## Pre-Publishing Checklist

### 1. Version Management
Update version in `pyproject.toml`:
```toml
[project]
name = "ardenpy"
version = "0.1.0"  # Update this for each release
```

### 2. Verify Package Structure
```
agentgate-sdk/
├── ardenpy/
│   ├── __init__.py
│   ├── guard.py
│   ├── client.py
│   ├── config.py
│   └── types.py
├── examples/
├── pyproject.toml
├── README.md
├── LICENSE
└── MANIFEST.in
```

### 3. Test Package Locally
```bash
# Build the package
python -m build

# Check the built package
twine check dist/*

# Test installation locally
pip install dist/agentgate-*.whl
```

### 4. Update Documentation
- Ensure `README.md` is complete and accurate
- Update `CHANGELOG.md` with new features
- Verify all examples work

## Publishing Process

### Step 1: Clean Previous Builds
```bash
rm -rf dist/ build/ *.egg-info/
```

### Step 2: Build Package
```bash
python -m build
```

This creates:
- `dist/ardenpy-0.1.0.tar.gz` (source distribution)
- `dist/ardenpy-0.1.0-py3-none-any.whl` (wheel)

### Step 3: Test on TestPyPI First
```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ ardenpy

# Test that it works
python -c "from ardenpy import configure, guard_tool; print('✅ Import successful')"
```

### Step 4: Upload to Production PyPI
```bash
# Upload to PyPI
twine upload dist/*
```

### Step 5: Verify Installation
```bash
# Install from PyPI
pip install ardenpy

# Test installation
python -c "from ardenpy import configure, guard_tool; print('✅ Arden installed successfully')"
```

## Configuration Files

### `.pypirc` (Optional)
Create `~/.pypirc` for easier uploads:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-testpypi-token-here
```

### GitHub Actions (Optional)
Automate publishing with GitHub Actions:

`.github/workflows/publish.yml`:
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.8'
    
    - name: Install dependencies
      run: |
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## Version Management Strategy

### Semantic Versioning
Follow [SemVer](https://semver.org/):
- `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Pre-release Versions
For testing:
- `0.1.0a1` (alpha)
- `0.1.0b1` (beta)
- `0.1.0rc1` (release candidate)

### Development Workflow
1. **Development**: `0.1.0.dev0`
2. **Alpha**: `0.1.0a1`
3. **Beta**: `0.1.0b1`
4. **Release Candidate**: `0.1.0rc1`
5. **Release**: `0.1.0`

## Package Metadata

Ensure `pyproject.toml` has complete metadata:

```toml
[project]
name = "ardenpy"
version = "0.1.0"
description = "AI agent tool call gate with policy enforcement and human approval workflow"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Arden Team", email = "team@arden.dev"}
]
maintainers = [
    {name = "Arden Team", email = "team@arden.dev"}
]
keywords = ["ai", "agent", "security", "policy", "approval", "gate"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Security",
]
requires-python = ">=3.8"
dependencies = [
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "typing-extensions>=4.0.0",
]

[project.urls]
Homepage = "https://github.com/agentgate/agentgate"
Documentation = "https://agentgate.readthedocs.io"
Repository = "https://github.com/agentgate/agentgate"
Issues = "https://github.com/agentgate/agentgate/issues"
Changelog = "https://github.com/agentgate/agentgate/blob/main/CHANGELOG.md"
```

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md`
- [ ] Test all examples locally
- [ ] Run tests (if any)
- [ ] Build package: `python -m build`
- [ ] Check package: `twine check dist/*`
- [ ] Upload to TestPyPI: `twine upload --repository testpypi dist/*`
- [ ] Test installation from TestPyPI
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Test installation from PyPI
- [ ] Create GitHub release
- [ ] Update documentation
- [ ] Announce release

## Troubleshooting

### Common Issues

1. **File not found errors**:
   - Check `MANIFEST.in` includes all necessary files
   - Verify file paths are correct

2. **Import errors after installation**:
   - Check `__init__.py` exports
   - Verify package structure

3. **Upload failures**:
   - Check API token permissions
   - Verify package name isn't taken
   - Ensure version number is new

4. **Dependency conflicts**:
   - Test in clean virtual environment
   - Check version constraints

### Testing in Clean Environment
```bash
# Create clean test environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install and test
pip install ardenpy
python -c "from ardenpy import configure; print('Success!')"

# Cleanup
deactivate
rm -rf test_env
```

## Post-Release

1. **Monitor Downloads**: Check PyPI statistics
2. **User Feedback**: Monitor GitHub issues
3. **Documentation**: Update any external docs
4. **Community**: Announce on relevant forums/social media

## Security Considerations

- **Never commit API tokens** to version control
- **Use environment variables** or GitHub secrets
- **Regularly rotate tokens**
- **Monitor package for unauthorized changes**

Once published, users can install with:
```bash
pip install ardenpy
```

And use immediately:
```python
from ardenpy import configure, guard_tool
configure(api_key="your-key")
protected_func = guard_tool("tool.name", your_function)
```
