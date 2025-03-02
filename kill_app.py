#!/usr/bin/env python3
"""
Simple script to find and kill the home temperature control application process.
"""
import subprocess
import argparse
import sys
import signal
import os

def main():
    parser = argparse.ArgumentParser(description="Kill the home temperature control application")
    parser.add_argument("--port", type=int, default=8000, help="Port the application is running on")
    parser.add_argument("--force", action="store_true", help="Use SIGKILL instead of SIGTERM")
    args = parser.parse_args()
    
    port = args.port
    sig = signal.SIGKILL if args.force else signal.SIGTERM
    sig_name = "SIGKILL" if args.force else "SIGTERM"
    
    print(f"Looking for processes using port {port}...")
    
    try:
        if sys.platform == "darwin":  # macOS
            cmd = f"lsof -i :{port} -sTCP:LISTEN -t"
            pids = subprocess.check_output(cmd, shell=True).decode().strip().split("\n")
        elif sys.platform == "linux":  # Linux
            cmd = f"fuser {port}/tcp 2>/dev/null"
            pids = subprocess.check_output(cmd, shell=True).decode().strip().split()
        elif sys.platform == "win32":  # Windows
            cmd = f"netstat -ano | findstr :{port}"
            output = subprocess.check_output(cmd, shell=True).decode()
            pids = []
            for line in output.strip().split('\n'):
                if 'LISTENING' in line:
                    pids.append(line.strip().split()[-1])
        else:
            print(f"Unsupported platform: {sys.platform}")
            sys.exit(1)
        
        if not pids or (len(pids) == 1 and not pids[0]):
            print(f"No process found using port {port}")
            sys.exit(1)
        
        for pid in pids:
            if pid:
                pid = pid.strip()
                print(f"Sending {sig_name} to process {pid}...")
                try:
                    os.kill(int(pid), sig)
                    print(f"Signal sent to process {pid}")
                except ProcessLookupError:
                    print(f"Process {pid} not found")
                except PermissionError:
                    print(f"Permission denied when trying to kill process {pid}")
        
    except subprocess.CalledProcessError:
        print("No processes found using the specified port")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
