# Releasing ClickForge

This document describes the recommended process for publishing a new ClickForge release.

## Release checklist

1. Update the version in `__init__.py`.
2. Update `CHANGELOG.md`.
3. Verify local execution:

```bash
python main.py
```

4. Verify the project compiles:

```bash
python -m compileall .
```

5. Verify packaging on your current platform:

```bash
python build.py
```

6. Commit the release changes.
7. Create a Git tag such as `v0.1.0`.
8. Publish the release on GitHub with release notes.

## Suggested first release title

`ClickForge v0.1.0`

## Suggested first release notes

- Initial public release
- Native PyQt6 desktop UI
- Global hotkey support
- Toggle and hold modes
- Fixed-position and cursor-position clicking
- Persistent settings
- Cross-platform packaging support
