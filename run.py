#!/usr/bin/env python3
"""
Jellyfin TV Tools - Main Entry Point
Modern GUI application for managing IPTV M3U playlists
"""

import os
import sys

def install_requirements():
    """Install required packages if needed"""
    required_packages = ['flet', 'requests']
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing {package}...")
            os.system(f'pip install {package}')

def main():
    """Main application entry point"""
    print("Starting Jellyfin TV Tools...")
    
    # Install requirements if needed
    install_requirements()
    
    # Add src directory to path
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    sys.path.insert(0, src_path)
    
    try:
        # Import and run the app
        from ui.main_app import main as run_app
        import flet as ft
        
        ft.app(target=run_app, view=ft.AppView.FLET_APP)
        
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Please make sure all dependencies are installed.")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
