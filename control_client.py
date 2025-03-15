#!/usr/bin/env python3
import argparse
import requests
import time
from security_utils import SecurityUtils

def main():
    parser = argparse.ArgumentParser(description='Control the Home Temperature Control System')
    parser.add_argument('action', choices=['stop', 'restart'], help='Action to perform')
    parser.add_argument('--pin', default='130376', help='Control PIN (default: 130376)')
    parser.add_argument('--host', default='http://localhost:8000', help='API host (default: http://localhost:8000)')
    
    args = parser.parse_args()
    
    # Generate security token
    security = SecurityUtils(args.pin)
    timestamp = str(int(time.time()))
    token = security.generate_token(timestamp)
    
    # Make request
    url = f"{args.host}/control/{args.action}"
    try:
        response = requests.post(url, json={
            'timestamp': timestamp,
            'token': token
        })
        
        if response.status_code == 200:
            print(f"Successfully sent {args.action} signal")
        else:
            print(f"Error: {response.json().get('detail', 'Unknown error')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to server: {e}")

if __name__ == '__main__':
    main()
