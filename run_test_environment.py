#!/usr/bin/env python3
import subprocess
import time
import sys
import signal
import os

def run_command(command, env=None):
    """Run a command and return the process."""
    return subprocess.Popen(
        command,
        env=env,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

def main():
    # Start the temperature simulator
    print("Starting Temperature Simulator...")
    simulator = run_command("python temperature_simulator.py")
    time.sleep(2)  # Wait for simulator to start
    
    # Start the main application
    print("Starting Home Temperature Control System...")
    controller = run_command("python home_topology_api.py")
    
    try:
        while True:
            # Check if either process has terminated
            if simulator.poll() is not None:
                print("Temperature Simulator has stopped unexpectedly!")
                break
            if controller.poll() is not None:
                print("Home Temperature Control System has stopped unexpectedly!")
                break
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nShutting down test environment...")
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
        print("Test environment shutdown complete.")

if __name__ == "__main__":
    main()
