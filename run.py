#!/usr/bin/env python3
"""
ReolinkANPR Startup Script
Starts both the ANPR service and web dashboard
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path


def main():
    print("=" * 60)
    print("ReolinkANPR - Starting...")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 11):
        print(f"ERROR: Python 3.11+ required (you have {sys.version_info.major}.{sys.version_info.minor})")
        print("TCP push events require reolink-aio 0.10+ which needs Python 3.11+")
        print("Please upgrade Python or use pyenv/venv with Python 3.11+")
        sys.exit(1)

    print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}: OK")
    print()

    # Get script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    processes = []
    log_files = []

    def signal_handler(signum, frame):
        print("\nShutting down ReolinkANPR...")
        for proc in processes:
            if proc and proc.poll() is None:
                proc.terminate()
        time.sleep(2)
        for proc in processes:
            if proc and proc.poll() is None:
                proc.kill()
        # Close log files
        for log_file in log_files:
            try:
                log_file.close()
            except:
                pass
        print("ReolinkANPR stopped")
        sys.exit(0)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create log files for processes
        web_log = open("logs/web.log", "w")
        anpr_log = open("logs/anpr_startup.log", "w")
        log_files.extend([web_log, anpr_log])

        # Start web dashboard
        print("Starting web dashboard...")
        web_proc = subprocess.Popen(
            [sys.executable, "web/app.py"],
            stdout=web_log,
            stderr=subprocess.STDOUT
        )
        processes.append(web_proc)
        time.sleep(2)

        # Check if web dashboard started successfully
        if web_proc.poll() is not None:
            web_log.close()
            print("ERROR: Web dashboard failed to start!")
            print("Check logs at: logs/web.log")
            sys.exit(1)

        # Start ANPR service
        print("Starting ANPR service...")
        anpr_proc = subprocess.Popen(
            [sys.executable, "-m", "src.anpr_service"],
            stdout=anpr_log,
            stderr=subprocess.STDOUT
        )
        processes.append(anpr_proc)
        time.sleep(2)

        # Check if ANPR service started successfully
        if anpr_proc.poll() is not None:
            anpr_log.close()
            print("ERROR: ANPR service failed to start!")
            print("Check logs at: logs/anpr.log and logs/anpr_startup.log")
            sys.exit(1)

        # Read port from config
        try:
            from src.config import Config
            config = Config()
            port = config.web_port
        except:
            port = 5001  # fallback

        print("=" * 60)
        print("ReolinkANPR is running!")
        print()
        print(f"  Web Dashboard: http://localhost:{port}")
        print()
        print("Press Ctrl+C to stop")
        print("=" * 60)

        # Monitor processes
        while True:
            time.sleep(5)

            if web_proc.poll() is not None:
                print("Web dashboard stopped unexpectedly!")
                break

            if anpr_proc.poll() is not None:
                print("ANPR service stopped unexpectedly!")
                break

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"Error: {e}")
        signal_handler(signal.SIGTERM, None)
        sys.exit(1)


if __name__ == "__main__":
    main()
