# Publishing ardenpy to PyPI

## Prerequisites

```bash
pip install build twine
```

You'll need API tokens for [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org).
Generate them under Account Settings → API tokens on each site.

---

## Release checklist

1. Update `version` in `pyproject.toml` and `__version__` in `ardenpy/__init__.py`
2. Run tests: `.venv/bin/pytest tests/ -v -m "not integration"`
3. Verify all examples parse cleanly (see `examples/README.md`)
4. Build, check, and publish (steps below)

---

## Build

```bash
rm -rf dist/ build/ ardenpy.egg-info/
python -m build
twine check dist/*
```

This produces:
- `dist/ardenpy-<version>-py3-none-any.whl`
- `dist/ardenpy-<version>.tar.gz`

---

## Test on TestPyPI first

```bash
twine upload --repository testpypi dist/*

# Verify installation
pip install --index-url https://test.pypi.org/simple/ "ardenpy[all]"
python -c "import ardenpy; print(ardenpy.__version__)"
```

---

## Publish to PyPI

```bash
twine upload dist/*

# Verify
pip install ardenpy
python -c "import ardenpy; print(ardenpy.__version__)"
```

---

## Optional: automate with GitHub Actions

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
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install build twine
      - run: python -m build
      - env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

---

## Versioning

Follow [SemVer](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR** — breaking API changes
- **MINOR** — new features, backward-compatible
- **PATCH** — bug fixes

Current version: `0.4.0`
