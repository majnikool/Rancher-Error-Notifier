import re
import os
import time
from datetime import datetime, timedelta, timezone
from kubernetes import client, config
from slack_sdk import WebClient
from collections import defaultdict



# Constants
SLACK_TOKEN = os.getenv('SLACK_TOKEN')
if not SLACK_TOKEN:
    raise ValueError("SLACK_TOKEN environment variable not set")

CHANNEL_NAME = os.getenv('CHANNEL_NAME', '#rancher-errors')  # Default channel if not provided
NAMESPACE = "cattle-system"
APP_LABEL = "app=rancher"
ALT_ERROR_LOG_REGEX = r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[ERROR\] (.+)"
WE_LOG_REGEX = r"([E|W]\d{4} \d{2}:\d{2}:\d{2}\.\d{6})[ ]+(\d+) (.+)"
X_MINUTES = int(os.getenv('X_MINUTES', 60))  # Default to 60 minutes if not provided
DEBUG_FILE = '/tmp/debug_output.txt'
SEND_TO_SLACK = True
DEBUG = os.getenv('DEBUG', 'False') == 'True'  # Default to False if not provided
LOCAL_TIME_OFFSET_HOURS = int(os.getenv('LOCAL_TIME_OFFSET_HOURS', 2))  # Default to Finland UTC+2
LOCAL_TIME_OFFSET = timedelta(hours=LOCAL_TIME_OFFSET_HOURS)

# Slack Config
slack_client = WebClient(token=SLACK_TOKEN)

# Kubernetes Config
config.load_kube_config()
v1 = client.CoreV1Api()

def debug_print(message):
    if DEBUG:
        print(message)

def fetch_logs():
    print("Fetching logs...")
    pods = v1.list_namespaced_pod(NAMESPACE, label_selector=APP_LABEL)
    logs = []
    for pod in pods.items:
        pod_name = pod.metadata.name
        logs.append(v1.read_namespaced_pod_log(pod_name, NAMESPACE))
    return logs

def find_errors(logs):
    print("Finding error lines...")
    error_lines = []
    error_counts = defaultdict(int)
    current_time = datetime.now(timezone.utc)
    time_limit = current_time - timedelta(minutes=X_MINUTES)

    # Regex to match IP addresses in error messages and normalize them
    ip_error_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+:\d+->\d+\.\d+\.\d+\.\d+:\d+)')

    for log in logs:
        for line in log.splitlines():
            # Normalize the line to remove unique IP addresses
            normalized_line = ip_error_pattern.sub('[IP_REDACTED]', line)

            # Check for the alternative error log format
            alt_error_match = re.match(ALT_ERROR_LOG_REGEX, normalized_line)
            if alt_error_match:
                timestamp_str = alt_error_match.group(1)
                timestamp_format = "%Y/%m/%d %H:%M:%S"
                raw_error_msg = alt_error_match.group(2)
            else:
                # Check for the 'W' or 'E' log format
                we_match = re.match(WE_LOG_REGEX, normalized_line)
                if we_match:
                    year = current_time.year
                    # Adjust the timestamp string to include the year
                    timestamp_str = f"{year}-{we_match.group(1)[1:]}"
                    timestamp_format = "%Y-%m%d %H:%M:%S.%f"
                    raw_error_msg = we_match.group(3)
            
            # Check if either regex matched and process accordingly
            if alt_error_match or we_match:
                timestamp = datetime.strptime(timestamp_str, timestamp_format).replace(tzinfo=timezone.utc)
                if timestamp >= time_limit:
                    error_counts[raw_error_msg] += 1
                    # Only update timestamp and count if we have seen this error before
                    if error_counts[raw_error_msg] > 1:
                        # We already normalized and counted, so continue
                        continue
                    else:
                        error_type = "Error" if "E" in normalized_line else "Warning"
                        local_timestamp = timestamp.astimezone(timezone(LOCAL_TIME_OFFSET))
                        error_msg = f"{error_type}: {local_timestamp.strftime('%Y-%m-%d %H:%M:%S')} --> {raw_error_msg}"
                        error_lines.append((timestamp, error_msg, raw_error_msg))
    
    # Sort error lines based on timestamp
    error_lines.sort(key=lambda x: x[0])
    
    # Create final output, including the count of occurrences
    final_output = []
    for _, message, raw_msg in error_lines:
        count = error_counts[raw_msg]
        if count > 1:
            # Append the count to the message
            message += f" ({count} occurrences)"
        final_output.append(message)
        
    return final_output



def post_to_slack(messages):
    if not SEND_TO_SLACK:
        return

    title = f"Rancher Errors in the Last {X_MINUTES} Minutes"
    full_message = f"{title}\n\n" + "\n\n".join(messages)  # Add extra newline for spacing

    try:
        debug_print(f"Debug: Sending message to Slack: {full_message}")
        slack_client.chat_postMessage(channel=CHANNEL_NAME, text=full_message)
        debug_print("Debug: Message sent successfully.")
    except Exception as e:
        print(f"Failed to send message to Slack: {e}")

def save_to_file(messages):
    print("Saving to local file...")
    with open(DEBUG_FILE, 'w') as f:
        f.write(f"Rancher Errors in the Last {X_MINUTES} Minutes\n\n")  # Add extra newline for spacing
        for message in messages:
            f.write(f"{message}\n\n")  # Add extra newline for spacing
    debug_print(f"Debug: Messages saved to {DEBUG_FILE}")

if __name__ == "__main__":
    logs = fetch_logs()
    error_lines = find_errors(logs)

    if error_lines:
        save_to_file(error_lines)
        post_to_slack(error_lines)
