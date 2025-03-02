#!/usr/bin/env python3
"""
Script to safely stop the home temperature control application
by sending a stop command through the secure control API.
"""
import requests
import argparse
import sys
import hashlib
import time
import json

def main():
    parser = argparse.ArgumentParser(description="Stop the home temperature control application")
    parser.add_argument("--host", default="localhost", help="API host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="API port (default: 8000)")
    parser.add_argument("--pin", help="Control PIN (overrides config file)")
    parser.add_argument("--debug", action="store_true", help="Show detailed debug information")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    debug = args.debug
    
    try:
        # Try to get the control PIN, either from argument or config file
        control_pin = args.pin
        
        if not control_pin:
            print("Attempting to load control PIN from config file...")
            try:
                import yaml
                from pathlib import Path
                
                config_path = Path(__file__).parent / 'config.yaml'
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    control_pin = config.get('api', {}).get('control_pin')
                    
                if control_pin:
                    print("Successfully loaded control PIN from config file.")
                else:
                    print("No control PIN found in config file.")
            except Exception as e:
                if debug:
                    print(f"Error loading config file: {str(e)}")
                print("Could not load control PIN from config file.")
        
        if not control_pin:
            print("Error: No control PIN provided. Use --pin option or ensure it's in config.yaml")
            sys.exit(1)
        
        # Generate security token manually
        timestamp = str(int(time.time()))
        token = hashlib.sha256(f"{timestamp}{control_pin}".encode()).hexdigest()
        
        if debug:
            print(f"Generated timestamp: {timestamp}")
            print(f"Using control PIN: {control_pin}")
            print(f"Generated token: {token}")
        
        # Test connectivity first
        try:
            print(f"Testing connection to {base_url}...")
            health_response = requests.get(f"{base_url}/", timeout=5)
            print(f"Connection successful. Status: {health_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not connect to base URL: {str(e)}")
            print("Proceeding with stop command anyway...")
        
        # Send stop command
        print(f"Sending stop command to {base_url}/control/stop...")
        payload = {"token": token, "timestamp": timestamp}
        
        if debug:
            print(f"Sending payload: {json.dumps(payload)}")
            
        response = requests.post(
            f"{base_url}/control/stop",
            json=payload,
            timeout=10
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            print("Stop command sent successfully. The application should be stopping now.")
        else:
            print(f"Error: Failed to stop application (status code {response.status_code})")
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {base_url}. The application may not be running.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
