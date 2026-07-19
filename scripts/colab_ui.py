"""Start the Streamlit UI on Colab and expose it through an ngrok tunnel.

Requires the Rasa services from scripts/colab_services.py to be running.
Add NGROK_AUTH_TOKEN to Colab Secrets for a stable tunnel.
"""

import os
import subprocess
import time

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMLIT_BIN = "/content/rasa_venv/bin/streamlit"
APP_PATH = os.path.join(REPO_DIR, "ui", "app.py")


def main():
    subprocess.run(["pkill", "-f", "streamlit run"], check=False)
    time.sleep(2)

    streamlit_log_path = os.path.join(REPO_DIR, "streamlit.log")
    streamlit_log = open(streamlit_log_path, "w", encoding="utf-8")

    subprocess.Popen(
        [
            STREAMLIT_BIN,
            "run",
            APP_PATH,
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
            "--server.enableCORS",
            "false",
            "--server.enableXsrfProtection",
            "false",
        ],
        cwd=REPO_DIR,
        stdout=streamlit_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    time.sleep(8)
    print("Streamlit started.")

    from pyngrok import ngrok

    try:
        ngrok.kill()
    except Exception:
        pass

    ngrok_token = None
    try:
        from google.colab import userdata

        ngrok_token = userdata.get("NGROK_AUTH_TOKEN")
    except Exception:
        ngrok_token = None

    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)
        print("NGROK_AUTH_TOKEN loaded.")
    else:
        print(
            "NGROK_AUTH_TOKEN not found. "
            "Add it in Colab Secrets if needed."
        )

    public_url = ngrok.connect(addr=8501, proto="http")

    print("Eco-Travel Advisor is ready:")
    print(public_url.public_url)


if __name__ == "__main__":
    main()
