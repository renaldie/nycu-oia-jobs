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

def make_request_with_retry(url, max_retries=3, delay=5):
    """Make HTTP request with retry logic"""
    import time
    
    for attempt in range(max_retries):
        try:
            # Add headers to make request more like a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:  # Last attempt
                raise  # Re-raise the last exception
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            time.sleep(delay)  # Wait before retrying

def ensure_data_directory():
    """Ensure the data directory exists"""
    data_dir = 'data'
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            print(f"Created directory: {data_dir}")
        except Exception as e:
            print(f"Error creating directory: {str(e)}")
            raise

def save_json_safely(data, filename):
    """Safely save JSON data to file with error handling"""
    try:
        # First write to a temporary file
        temp_filename = filename + '.tmp'
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Then rename it to the target file (atomic operation)
        os.replace(temp_filename, filename)
        print(f"Successfully saved: {filename}")
    except Exception as e:
        print(f"Error saving file {filename}: {str(e)}")
        # Try one more time with force write
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved with force write: {filename}")
        except Exception as e:
            print(f"Critical error saving file {filename}: {str(e)}")
            raise

def main():
    ensure_data_directory()
    
    urls = {
        ('data/nycu_intern.json', 'intern'): os.environ['JSON_URL_1'],
        ('data/nycu_fulltime.json', 'fulltime'): os.environ['JSON_URL_2']
    }
    
    all_changes = {}
    
    for (filename, job_type), url in urls.items():
        try:
            response = make_request_with_retry(url)
            current_data = response.json()
            
            previous_data = None
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        previous_data = json.load(f)
                except Exception as e:
                    print(f"Error reading previous data from {filename}: {str(e)}")
            
            updates = compare_json_data(current_data, previous_data)
            if updates:
                all_changes[job_type] = updates
            
            # Always save current data
            save_json_safely(current_data, filename)
                
        except Exception as e:
            print(f"Error checking {job_type} jobs: {str(e)}")
    
    # Send notification only if there are changes
    if all_changes:
        send_notification(all_changes)
