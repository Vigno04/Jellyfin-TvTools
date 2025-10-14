# Release Guide for Jellyfin TV Tools

This guide explains how to create releases for Jellyfin TV Tools with pre-built executables.

## 🎯 Quick Release (Automated via GitHub Actions)

### Method 1: Create a Git Tag

The easiest way to trigger a release:

```bash
# Make sure you're on the main branch and up to date
git checkout main
git pull

# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

This will automatically:
1. Build executables for Windows and Linux
2. Create a GitHub release
3. Upload the executables as release assets

### Method 2: Manual Trigger

Go to GitHub → Actions → "Build and Release" workflow → Click "Run workflow"

## 🔧 Local Build (Manual)

If you want to build executables locally:

### Prerequisites

```bash
pip install pyinstaller
```

### Build for Your Platform

```bash
python build_release.py
```

This will:
1. Install PyInstaller if needed
2. Build the executable using `build.spec`
3. Create a release package in `release/`
4. Create a ZIP file ready for distribution

The output will be in:
- `release/JellyfinTvTools-Windows.zip` (on Windows)
- `release/JellyfinTvTools-Linux.zip` (on Linux)

## 📝 Version Numbering

Use semantic versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

Examples:
- `v1.0.0` - First stable release
- `v1.1.0` - Added new features
- `v1.1.1` - Bug fixes

## 🔄 Release Process

### 1. Prepare the Release

```bash
# Update version in your code if needed
# Update CHANGELOG.md with new changes
# Commit all changes
git add .
git commit -m "Prepare release v1.0.0"
git push
```

### 2. Create and Push Tag

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### 3. Monitor GitHub Actions

1. Go to GitHub → Actions
2. Watch the build process
3. Once complete, check Releases

### 4. Edit Release Notes (Optional)

1. Go to GitHub → Releases
2. Click on the new release
3. Edit the description to add more details

## 🛠️ Customization

### Change Executable Icon

1. Create or obtain an `.ico` file (Windows) or `.icns` (macOS)
2. Edit `build.spec`:
   ```python
   icon='path/to/your/icon.ico'
   ```

### Adjust Build Settings

Edit `build.spec` to:
- Add/remove hidden imports
- Include additional data files
- Change executable name
- Modify console/windowed mode

### Modify Release Workflow

Edit `.github/workflows/release.yml` to:
- Change Python version
- Add additional build steps
- Modify release notes format
- Add more platforms (macOS, etc.)

## 📦 What's Included in Release Packages

Each release package contains:
- The executable (`JellyfinTvTools.exe` or `JellyfinTvTools`)
- README.md and LICENSE
- RELEASE_README.txt (quick start guide)
- `data/` directory (for user data)
- Run script (`run.bat` or `run.sh`)

## 🐛 Troubleshooting

### Build Fails on GitHub Actions

- Check the Actions log for errors
- Ensure all dependencies are in `requirements.txt`
- Test the build locally first

### Executable Doesn't Start

- Check that all hidden imports are in `build.spec`
- Test on a clean machine without Python installed
- Check antivirus isn't blocking the executable

### Missing Dependencies

Add them to `hiddenimports` in `build.spec`:
```python
hiddenimports = [
    'flet',
    'requests',
    'your_missing_module',
]
```

## 📚 Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)

## 🎉 First Release Checklist

- [ ] Test application locally
- [ ] Update README.md
- [ ] Add LICENSE file
- [ ] Test local build: `python build_release.py`
- [ ] Push all changes to GitHub
- [ ] Create and push version tag
- [ ] Verify GitHub Actions build succeeds
- [ ] Test downloaded executables on clean systems
- [ ] Announce the release!

---

Happy releasing! 🚀
