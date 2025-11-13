# Back-End API Server for Web Service Monitoring

This server receives health check results from the monitoring agent, logs them, manages alert statuses in a MariaDB database, and sends email notifications when services fail or recover.

## Setup and Configuration

### 1. API Key Configuration

The server requires an API key for authenticating requests. This key must be stored in a file named `API_KEY` in your home directory.

```bash
echo "YOUR_SECRET_API_KEY" > ~/API_KEY
```

### 2. Python Environment

It is recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python libraries from `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. Configure Database and Email Settings

Edit the `config.yaml` file to provide your MariaDB connection details and SMTP server settings.

**MariaDB Configuration:**
-   `DB_HOST`, `DB_PORT`: Your MariaDB server address and port.
-   `DB_USER`, `DB_PASSWORD`: Your database login credentials.
-   `DB_NAME`: The name of the database to use.

**SMTP Configuration:**
-   `SMTP_SERVER`, `SMTP_PORT`: Your SMTP server address and port.
-   `SMTP_USERNAME`, `SMTP_PASSWORD`: Your SMTP login credentials.
-   `SENDER_EMAIL`: The email address from which notifications will be sent.
-   `RECIPIENT_EMAIL`: A list of email addresses that will receive notifications.
-   `RETRY_INTERVAL_SECONDS`: The delay in seconds before retrying a failed email notification.

## Running the Server

Once the setup is complete, you can run the server using `uvicorn`.

```bash
uvicorn main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.
