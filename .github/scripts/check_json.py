import json
import os
import requests
from datetime import datetime

def send_notification(changes):
    """
    Send a single consolidated notification for all changes
    changes: dict with 'intern' and 'fulltime' lists of updates
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Updates in NYCU OIA Jobs ({current_time})"
    body = []
    
    if changes.get('intern'):
        body.append("Changes detected in Intern:")
        body.extend(changes['intern'])
        body.append("")  # Empty line for spacing
        
    if changes.get('fulltime'):
        body.append("Changes detected in Full Time:")
        body.extend(changes['fulltime'])
    
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
        f.write(f"## {title}\n{''.join(body)}\n")
    print(f"::notice title={title}::{''.join(body)}")

def compare_json_data(current_data, previous_data):
    """Compare current and previous JSON data and return list of changes"""
    if previous_data is None:
        return [f"{item['subject']} ({item['updateDate']})\n" for item in current_data]

    updates = []
    for current_item in current_data:
        is_new = True
        for prev_item in previous_data:
            if current_item['subject'] == prev_item['subject']:
                is_new = False
                if current_item['updateDate'] != prev_item['updateDate']:
                    updates.append(f"{current_item['subject']} ({current_item['updateDate']})\n")
                break
        if is_new:
            updates.append(f"{current_item['subject']} ({current_item['updateDate']})\n")
    return updates

def main():
    urls = {
        ('data/nycu_intern.json', 'intern'): os.environ['JSON_URL_1'],
        ('data/nycu_fulltime.json', 'fulltime'): os.environ['JSON_URL_2']
    }
    
    all_changes = {}
    changes_detected = False
    
    for (filename, job_type), url in urls.items():
        try:
            response = requests.get(url)
            response.raise_for_status()
            current_data = response.json()
            
            previous_data = None
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    previous_data = json.load(f)
            
            updates = compare_json_data(current_data, previous_data)
            if updates:
                all_changes[job_type] = updates
                changes_detected = True
            
            # Save current data
            with open(filename, 'w') as f:
                json.dump(current_data, f, indent=2)
                
        except Exception as e:
            print(f"Error checking {job_type} jobs: {str(e)}")
    
    if changes_detected:
        send_notification(all_changes)
        # Git commands for committing changes
        os.system('git config --global user.name "GitHub Action"')
        os.system('git config --global user.email "action@github.com"')
        os.system('git add data/*.json')
        os.system('git commit -m "Update JSON states"')
        os.system('git push')
