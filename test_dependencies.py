#!/usr/bin/env python3
"""
ReolinkANPR Dependency Test Script
Tests all required dependencies before running the application.
"""

import sys
import subprocess

def test_python_version():
    """Check Python version (3.11+ required for TCP push events)."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}: OK")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro}: REQUIRES Python 3.11+")
        print(f"  TCP push events require reolink-aio 0.10+ which needs Python 3.11+")
        return False

def test_dependency(name, import_name=None):
    """Test a single Python dependency."""
    if import_name is None:
        import_name = name.replace('-', '_')

    try:
        __import__(import_name)
        print(f"✓ {name}: OK")
        return True
    except ImportError:
        print(f"✗ {name}: NOT INSTALLED")
        return False

def test_ffmpeg():
    """Test ffmpeg availability."""
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ ffmpeg: OK ({version})")
            return True
        else:
            print("✗ ffmpeg: FOUND BUT ERROR")
            return False
    except FileNotFoundError:
        print("✗ ffmpeg: NOT FOUND")
        print("  Install: brew install ffmpeg (macOS) or apt install ffmpeg (Ubuntu)")
        return False
    except Exception as e:
        print(f"✗ ffmpeg: ERROR ({e})")
        return False

def main():
    """Run all dependency tests."""
    print("=" * 60)
    print("ReolinkANPR Dependency Test")
    print("=" * 60)
    print()

    results = []

    # Python version
    results.append(test_python_version())
    print()

    # Python dependencies
    print("Python Dependencies:")
    results.append(test_dependency('reolink_aio'))
    results.append(test_dependency('fast-alpr', 'fast_alpr'))
    results.append(test_dependency('opencv-python-headless', 'cv2'))
    results.append(test_dependency('numpy'))
    results.append(test_dependency('PyYAML', 'yaml'))
    results.append(test_dependency('aiosqlite'))
    results.append(test_dependency('Flask', 'flask'))
    results.append(test_dependency('nest-asyncio', 'nest_asyncio'))
    results.append(test_dependency('aiohttp'))
    results.append(test_dependency('python-dateutil', 'dateutil'))
    print()

    # System dependencies
    print("System Dependencies:")
    results.append(test_ffmpeg())
    print()

    # Summary
    print("=" * 60)
    if all(results):
        print("✓ All dependencies installed successfully!")
        print("You can now run: python3 run.py")
        return 0
    else:
        print("✗ Some dependencies are missing.")
        print("Install Python packages: pip3 install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
