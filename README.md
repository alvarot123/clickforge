# ClickForge

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/gui-PyQt6-41CD52)
![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-6366F1)
![License](https://img.shields.io/badge/license-MIT-22C55E)
![Version](https://img.shields.io/badge/version-0.1.0-06B6D4)

ClickForge is a modern, lightweight desktop auto clicker built with Python and PyQt6.

It is designed to feel like a polished system utility rather than a throwaway script, with global hotkeys, live metrics, persistent settings, and native packaging support for Windows, macOS, and Linux.

## Highlights

- Native desktop UI built with PyQt6
- Real system mouse clicks powered by `pynput`
- Configurable global hotkey
- `toggle` and `hold` click modes
- Adjustable click rate from `0.1` to `50` CPS
- Optional click target limit with automatic stop
- Cursor-based or fixed-coordinate click positioning
- Session click counter and live CPS display
- Dark and light themes
- Local JSON settings persistence
- Cross-platform packaging with PyInstaller
- Emergency stop by holding `ESC` for 2 seconds

## Screenshot

Add your app screenshot here before publishing to GitHub.

## Project structure

```text
clickforge/
|- main.py
|- build.py
|- requirements.txt
|- README.md
|- LICENSE
|- CHANGELOG.md
|- CODE_OF_CONDUCT.md
|- CONTRIBUTING.md
|- SECURITY.md
|- RELEASING.md
|- assets/
|- core/
`- ui/
```

## Requirements

- Python 3.11 or newer

## Installation

```bash
pip install -r requirements.txt
```

## Running locally

```bash
python main.py
```

On Windows, you can also double-click:

- `Run_ClickForge.bat` to launch the app
- `Build_ClickForge.bat` to generate the packaged build

## Building distributables

```bash
python build.py
```

The build script detects the current operating system and generates:

- Windows: `ClickForge.exe`
- macOS: `ClickForge.app`
- Linux: `clickforge`

After building on Windows, you can launch the packaged app by double-clicking:

- `dist/ClickForge.exe`

## Platform notes

- Windows usually works with the fewest extra permissions.
- macOS may require Accessibility permissions for global input control.
- Linux behavior can depend on the desktop environment, display server, and input permissions.

## Known limitations

- Global hotkey and mouse automation behavior can vary across operating systems.
- Some environments may block simulated input without elevated accessibility permissions.
- Packaging results should be tested on each target platform before release.

## CI

The repository includes a GitHub Actions workflow that:

- installs dependencies
- compiles the project
- smoke-imports the main modules

It runs on Windows, macOS, and Linux with Python 3.11.

## Roadmap

- Better packaging validation per platform
- Optional preset profiles
- Improved diagnostics for permission and hotkey issues
- Optional portable release assets

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Code of conduct

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating in the project.

## Release process

See [RELEASING.md](RELEASING.md) for the suggested release workflow.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
