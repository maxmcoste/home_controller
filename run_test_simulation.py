#!/usr/bin/env python3
import subprocess
import time
import sys
import signal
import os
import logging

# Configure logging
logger = logging.getLogger('test_simulation')
logger.setLevel(logging.DEBUG)

# Create file handler
fh = logging.FileHandler('logs/test_simulation.log')
fh.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
fh.setFormatter(formatter)

# Add handler to logger
logger.addHandler(fh)

# Prevent logging to console
logger.propagate = False

def run_command(command, env=None):
    """Run a command and return the process."""
    # Open log files for stdout and stderr
    stdout_log = open('logs/subprocess_stdout.log', 'a')
    stderr_log = open('logs/subprocess_stderr.log', 'a')
    
    # Write a separator to the logs
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    header = f"\n=== {timestamp} - Running: {command} ===\n"
    stdout_log.write(header)
    stderr_log.write(header)
    
    return subprocess.Popen(
        command,
        env=env,
        shell=True,
        stdout=stdout_log,
        stderr=stderr_log,
        universal_newlines=True
    )

def wait_for_api(max_attempts=10):
    """Wait for the API to be ready."""
    import requests
    from requests.exceptions import RequestException
    
    for i in range(max_attempts):
        try:
            response = requests.get('http://localhost:8000/topology')
            if response.status_code == 200:
                logger.info("API is ready!")
                return True
        except RequestException:
            pass
        logger.info(f"Waiting for API to start (attempt {i+1}/{max_attempts})...")
        time.sleep(1)
    return False

def main():
    # Start the main application
    logger.info("Starting Home Temperature Control System...")
    controller = run_command("python home_topology_api.py")
    
    # Wait for the API to be ready
    if not wait_for_api():
        logger.error("API failed to start")
        controller.terminate()
        return
    
    # Start the temperature test simulator
    logger.info("Starting Temperature Test Simulator...")
    simulator = run_command("python temperature_test_simulator.py")
    
    try:
        while True:
            # Check if either process has terminated
            if simulator.poll() is not None:
                logger.error("Temperature Test Simulator has stopped unexpectedly!")
                break
            if controller.poll() is not None:
                logger.error("Home Temperature Control System has stopped unexpectedly!")
                break
            
            # Log a status message every minute
            logger.info("Test environment running. Press Ctrl+C to stop.")
            time.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("Shutting down test environment...")
    finally:
        # Terminate both processes
        for process in [simulator, controller]:
            if process.poll() is None:  # If process is still running
                if sys.platform == "win32":
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        
        # Wait for processes to terminate
        simulator.wait()
        controller.wait()
        logger.info("Test environment shutdown complete.")

if __name__ == "__main__":
    main()
