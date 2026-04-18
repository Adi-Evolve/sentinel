import time
import requests
import argparse
from pathlib import Path

# Configurable parameters
API_URL = "http://localhost:5000/api/scan"  # Adjust if backend runs elsewhere
BATCH_SIZE = 50  # Number of lines per simulated batch
delay = 2  # Seconds between batches

def simulate_live_monitoring(log_path, batch_size=BATCH_SIZE, delay_sec=delay):
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    total = len(lines)
    print(f"Simulating live monitoring for {log_path} ({total} lines)...")
    
    for i in range(0, total, batch_size):
        batch_lines = lines[i:i+batch_size]
        temp_file = f"/tmp/live_batch_{i}.log"
        with open(temp_file, "w", encoding="utf-8") as tf:
            tf.writelines(batch_lines)
        files = {'file': open(temp_file, 'rb')}
        print(f"Uploading batch {i//batch_size+1} ({len(batch_lines)} lines)...")
        try:
            response = requests.post(API_URL, files=files)
            print(f"Response: {response.status_code}")
        except Exception as e:
            print(f"Error uploading batch: {e}")
        time.sleep(delay_sec)
    print("Live monitoring simulation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate live log monitoring.")
    parser.add_argument("logfile", help="Path to log file to simulate")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE, help="Lines per batch")
    parser.add_argument("--delay", type=int, default=delay, help="Delay between batches (sec)")
    args = parser.parse_args()
    simulate_live_monitoring(args.logfile, args.batch, args.delay)
