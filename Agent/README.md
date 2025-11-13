# Web Service Monitoring Agent

This agent periodically checks the status of web services and sends the results to a backend server.

## Configuration

The agent is configured using the `config.yaml` file.

*   `TARGET_URLS`: A list of URLs to monitor.
*   `SERVER_ADDRESS`: The address of the backend server.
*   `API_KEY`: The API key for authenticating with the backend server.
*   `CHECK_INTERVAL_MINUTES`: The interval in minutes between health checks.

## Installation

1.  Install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Fill in the placeholder values in `config.yaml`.
2.  Run the agent:
    ```bash
    python agent.py
    ```
