import datetime
from datetime import timezone
import time
import yaml
import requests
import schedule
import logging
import os

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    """Loads configuration from config.yaml."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("config.yaml not found. Please create it.")
        exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config.yaml: {e}")
        exit(1)

def health_check(urls):
    """Performs a health check on the given URLs."""
    results = []
    for url in urls:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            response_time_ms = (time.time() - start_time) * 1000
            status = response.status_code
        except requests.exceptions.RequestException as e:
            response_time_ms = (time.time() - start_time) * 1000
            status = -1  # Using -1 to indicate a request exception
            logging.warning(f"Could not connect to {url}: {e}")

        results.append({
            "url": url,
            "status": status,
            "response_time_ms": round(response_time_ms, 2),
            "timestamp": timestamp
        })
    return results

def send_results(results, server_address, api_key):
    """Sends the health check results to the backend server."""
    if not results:
        logging.info("No results to send.")
        return

    api_url = f"http://{server_address}/events"
    headers = {"X-API-Key": api_key}
    payload = {"results": results}

    start_time = time.time()
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        duration = round(time.time() - start_time, 2)
        if response.ok:
            logging.info(f"[Success] Sent results to {api_url}. Response Status: {response.status_code}. Duration: {duration}s")
        else:
            logging.error(f"[Failure] Failed to send results to {api_url}. Response Status: {response.status_code}. Reason: {response.text}")
    except requests.exceptions.RequestException as e:
        duration = round(time.time() - start_time, 2)
        logging.error(f"[Failure] Failed to send results to {api_url}. Reason: {e}")

def run_check():
    """Loads config, runs health checks, and sends results."""
    logging.info("Running health check...")
    config = load_config()
    target_urls = config.get('TARGET_URLS', [])
    server_address = config.get('SERVER_ADDRESS')
    api_key = config.get('API_KEY')

    if not all([target_urls, server_address, api_key]):
        logging.error("Configuration is missing required fields (TARGET_URLS, SERVER_ADDRESS, API_KEY).")
        return

    check_results = health_check(target_urls)
    send_results(check_results, server_address, api_key)
    logging.info("Health check finished.")

def main():
    """Main function to schedule and run the agent."""
    config = load_config()
    interval = config.get('CHECK_INTERVAL_MINUTES', 5)

    logging.info(f"Agent started. Scheduling checks every {interval} minutes.")

    # Run the check once immediately
    run_check()

    schedule.every(interval).minutes.do(run_check)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
