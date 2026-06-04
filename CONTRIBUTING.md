# Contributing to ClickForge

Thanks for your interest in contributing to ClickForge.

## Getting started

1. Fork the repository.
2. Create a feature branch.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app locally:

```bash
python main.py
```

## Development guidelines

- Keep user-facing text in English.
- Keep core logic independent from PyQt6 whenever possible.
- Prefer small, focused pull requests.
- Preserve cross-platform behavior for Windows, macOS, and Linux.
- Avoid adding heavy dependencies unless they clearly improve the project.

## Before opening a pull request

- Verify the app starts correctly with `python main.py`.
- Verify the project still compiles:

```bash
python -m compileall .
```

- If you touched packaging, also test:

```bash
python build.py
```

## Reporting bugs

When opening a bug report, include:

- Operating system and version
- Python version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Any relevant console output or screenshots
