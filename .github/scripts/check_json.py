import json
import os
import requests
from datetime import datetime

def send_notification(title, body):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
        f.write(f"## {title}\n{body}\n")
    print(f"::notice title={title}::{body}")

def check_json_url(url, filename):
    try:
        # Fetch current JSON
        response = requests.get(url)
        response.raise_for_status()
        current_data = response.json()
        
        # Load previous data if exists
        previous_data = None
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                previous_data = json.load(f)
        
        # Save current data
        with open(filename, 'w') as f:
            json.dump(current_data, f, indent=2)
        
        # Return True if changes detected
        if previous_data is None:
            send_notification(
                f"First JSON Check - {filename}",
                f"Initial data captured at {datetime.now().isoformat()}"
            )
            return True
        elif previous_data != current_data:
            send_notification(
                f"JSON Changes Detected - {filename}",
                f"Changes detected at {datetime.now().isoformat()}"
            )
            return True
        return False
        
    except Exception as e:
        send_notification(f"Error checking {filename}", str(e))
        return False

def main():
    urls = {
        'data/nycu_intern.json': os.environ['JSON_URL_1'],
        'data/nycu_fulltime.json': os.environ['JSON_URL_2']
    }
    
    changes_detected = False
    for filename, url in urls.items():
        if check_json_url(url, filename):
            changes_detected = True
    
    # Commit changes if there are any
    if changes_detected:
        os.system('git config --global user.name "GitHub Action"')
        os.system('git config --global user.email "action@github.com"')
        os.system('git add *.json')
        os.system('git commit -m "Update JSON states"')
        os.system('git push')

if __name__ == '__main__':
    main()
