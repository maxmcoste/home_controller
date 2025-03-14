#!/usr/bin/env python3
"""
Script to launch both the temperature simulator and home temperature control system
"""
import subprocess
import time
import os
import signal
import sys
import argparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('launcher')

def run_process(cmd, name, env=None):
    """Run a process and return the subprocess object"""
    logger.info(f"Starting {name}...")
    process = subprocess.Popen(
        cmd,
        shell=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    logger.info(f"{name} started with PID {process.pid}")
    return process

def log_output(process, name):
    """Log process output in real-time"""
    for line in process.stdout:
        logger.info(f"[{name}] {line.strip()}")
    for line in process.stderr:
        logger.error(f"[{name}] {line.strip()}")

def main():
    parser = argparse.ArgumentParser(description="Run Home Temperature Control System")
    parser.add_argument("--sim-port", type=int, default=8100, help="Port for simulator")
    parser.add_argument("--app-port", type=int, default=8000, help="Port for main application")
    args = parser.parse_args()
    
    processes = []
    
    try:
        # Start temperature simulator
        sim_process = run_process(
            f"python temperature_simulator.py --port {args.sim_port}",
            "Temperature Simulator"
        )
        processes.append(sim_process)
        
        # Give the simulator time to initialize
        time.sleep(2)
        
        # Start the main application
        app_process = run_process(
            f"python home_topology_api.py --port {args.app_port}",
            "Temperature Control API"
        )
        processes.append(app_process)
        
        logger.info("All processes started. Press Ctrl+C to stop.")
        
        # Monitor processes
        while all(p.poll() is None for p in processes):
            time.sleep(1)
            
        # Check if any process has terminated
        for i, process in enumerate(processes):
            if process.poll() is not None:
                name = "Temperature Simulator" if i == 0 else "Temperature Control API"
                logger.error(f"{name} has terminated unexpectedly (exit code: {process.returncode})")
                # Output any remaining stderr
                stderr = process.stderr.read()
                if stderr:
                    logger.error(f"{name} error output: {stderr}")
    
    except KeyboardInterrupt:
        logger.info("Shutdown requested. Terminating processes...")
    
    finally:
        # Terminate all processes
        for i, process in enumerate(processes):
            if process.poll() is None:
                name = "Temperature Simulator" if i == 0 else "Temperature Control API"
                logger.info(f"Terminating {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    logger.info(f"{name} terminated.")
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} did not terminate gracefully. Forcing termination...")
                    process.kill()
                    process.wait()
                    logger.info(f"{name} forcibly terminated.")

if __name__ == "__main__":
    main()
