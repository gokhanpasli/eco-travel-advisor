"""Load API keys from Colab Secrets and start the Rasa services.

Starts the custom action server on port 5055 and the Rasa REST server on
port 5005, using the newest trained model in models/. Requires
scripts/colab_setup.py and a completed training run first.
"""

import glob
import os
import socket
import subprocess
import time

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RASA_BIN = "/content/rasa_venv/bin/rasa"

SECRET_NAMES = [
    "CLIMATIQ_API_KEY",
    "OPENCAGE_API_KEY",
    "OPENROUTER_API_KEY",
    "NEON_DATABASE_URL",
    "AUTH_COOKIE_SECRET",
]


def load_secret_to_env(secret_name):
    try:
        from google.colab import userdata

        secret_value = userdata.get(secret_name)

        if secret_value:
            os.environ[secret_name] = secret_value.strip()
            print(f"{secret_name} loaded from Colab Secrets.")
        else:
            print(f"{secret_name} was not found in Colab Secrets.")

    except Exception as error:
        print(f"Could not load {secret_name} from Colab Secrets:", error)


def log_tail(path, line_count=100):
    if not os.path.exists(path):
        return "Log file was not created."

    with open(path, "r", encoding="utf-8", errors="replace") as log_file:
        lines = log_file.readlines()

    return "".join(lines[-line_count:])


def wait_for_server(port, process, timeout):
    started_at = time.time()

    while time.time() - started_at < timeout:
        if process.poll() is not None:
            return False

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except OSError:
            time.sleep(2)

    return False


def main():
    for secret_name in SECRET_NAMES:
        load_secret_to_env(secret_name)

    models = glob.glob(os.path.join(REPO_DIR, "models", "*.tar.gz"))

    if not models:
        raise RuntimeError(
            "No trained Rasa model was found. Run the training cell first."
        )

    latest_model = max(models, key=os.path.getmtime)
    print("Using model:", latest_model)

    subprocess.run(["pkill", "-f", "rasa run actions"], check=False)
    subprocess.run(["pkill", "-f", "rasa run --enable-api"], check=False)
    time.sleep(2)

    actions_log_path = os.path.join(REPO_DIR, "actions.log")
    actions_log = open(actions_log_path, "w", encoding="utf-8")

    action_process = subprocess.Popen(
        [RASA_BIN, "run", "actions", "--port", "5055"],
        cwd=REPO_DIR,
        stdout=actions_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    if not wait_for_server(5055, action_process, timeout=120):
        actions_log.flush()
        print("ACTION SERVER FAILED\n")
        print(log_tail(actions_log_path))
        raise RuntimeError("Action server could not start.")

    print("Action server ready on port 5055.")

    rasa_log_path = os.path.join(REPO_DIR, "rasa.log")
    rasa_log = open(rasa_log_path, "w", encoding="utf-8")

    rasa_process = subprocess.Popen(
        [
            RASA_BIN,
            "run",
            "--enable-api",
            "--cors",
            "*",
            "--endpoints",
            "endpoints.yml",
            "--model",
            latest_model,
            "--port",
            "5005",
        ],
        cwd=REPO_DIR,
        stdout=rasa_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    if not wait_for_server(5005, rasa_process, timeout=300):
        rasa_log.flush()
        print("RASA REST SERVER FAILED\n")
        print(log_tail(rasa_log_path, 150))
        raise RuntimeError("Rasa REST server could not start.")

    print("Rasa REST server ready on port 5005.")
    print("Both servers started successfully.")

    print("\nLoaded API keys:")
    for secret_name in SECRET_NAMES:
        print(f"- {secret_name}:", "yes" if os.getenv(secret_name) else "no")


if __name__ == "__main__":
    main()
