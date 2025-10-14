#!/usr/bin/env python3
"""
Build script for creating Jellyfin TV Tools releases
Creates standalone executables for Windows and Linux
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def print_step(message):
    """Print a formatted step message"""
    print(f"\n{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}\n")

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {description} failed!")
        print(f"Exit code: {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False

def install_pyinstaller():
    """Install PyInstaller if not present"""
    print_step("Checking PyInstaller installation")
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} is already installed")
        return True
    except ImportError:
        print("PyInstaller not found, installing...")
        return run_command(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            "PyInstaller installation"
        )

def clean_build_dirs():
    """Clean previous build directories"""
    print_step("Cleaning previous build directories")
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/")
            shutil.rmtree(dir_name)

def build_executable():
    """Build the executable using PyInstaller"""
    print_step("Building executable with PyInstaller")
    
    # Run PyInstaller with the spec file
    if not run_command(
        [sys.executable, "-m", "PyInstaller", "build.spec", "--clean"],
        "PyInstaller build"
    ):
        return False
    
    return True

def create_release_package():
    """Create a release package with the executable and necessary files"""
    print_step("Creating release package")
    
    # Determine platform
    system = platform.system()
    if system == "Windows":
        exe_name = "JellyfinTvTools.exe"
        package_name = "JellyfinTvTools-Windows"
    elif system == "Linux":
        exe_name = "JellyfinTvTools"
        package_name = "JellyfinTvTools-Linux"
    else:
        exe_name = "JellyfinTvTools"
        package_name = f"JellyfinTvTools-{system}"
    
    # Create release directory
    release_dir = Path("release") / package_name
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy executable
    exe_path = Path("dist") / exe_name
    if not exe_path.exists():
        print(f"Error: Executable not found at {exe_path}")
        return False
    
    print(f"Copying {exe_name} to release package...")
    shutil.copy2(exe_path, release_dir / exe_name)
    
    # Make executable on Linux
    if system == "Linux":
        os.chmod(release_dir / exe_name, 0o755)
    
    # Copy additional files
    additional_files = ['README.md', 'LICENSE']
    for file in additional_files:
        if os.path.exists(file):
            print(f"Copying {file}...")
            shutil.copy2(file, release_dir / file)
    
    # Create data directory structure
    data_dir = release_dir / "data"
    data_dir.mkdir(exist_ok=True)
    print("Created data/ directory for user data")
    
    # Create a simple README for the release
    with open(release_dir / "README.txt", "w") as f:
        f.write("Jellyfin TV Tools - Release Package\n")
        f.write("="*50 + "\n\n")
        f.write("How to run:\n")
        if system == "Windows":
            f.write("  - Double-click JellyfinTvTools.exe\n")
        else:
            f.write("  - Run ./JellyfinTvTools\n")
        f.write("\n")
        f.write("Notes:\n")
        f.write("  - First run may take a few seconds to start\n")
        f.write("  - Configuration will be saved in the data/ directory\n")
        f.write("  - All your playlists and settings are stored locally\n")
        f.write("  - See README.md for full documentation\n")
        f.write("\n")
        f.write("Support:\n")
        f.write("  - GitHub: https://github.com/Vigno04/Jellyfin-TvTools\n")
    
    print(f"\nRelease package created at: {release_dir}")
    
    # Create ZIP archive
    print("\nCreating ZIP archive...")
    archive_name = f"{package_name}"
    shutil.make_archive(
        str(Path("release") / archive_name),
        'zip',
        str(release_dir.parent),
        package_name
    )
    
    print(f"ZIP archive created: release/{archive_name}.zip")
    return True

def main():
    """Main build process"""
    print_step("Jellyfin TV Tools - Release Builder")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version}")
    
    # Step 1: Install PyInstaller
    if not install_pyinstaller():
        print("\n[X] Build failed: Could not install PyInstaller")
        return 1
    
    # Step 2: Clean previous builds
    clean_build_dirs()
    
    # Step 3: Build executable
    if not build_executable():
        print("\n[X] Build failed: PyInstaller build error")
        return 1
    
    # Step 4: Create release package
    if not create_release_package():
        print("\n[X] Build failed: Could not create release package")
        return 1
    
    print_step("Build completed successfully!")
    print("\nYour release package is ready in the 'release/' directory")
    print("You can now distribute the ZIP file to users")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
