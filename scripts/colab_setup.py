"""Prepare a pinned Python 3.10 Rasa environment on Google Colab.

Colab ships a newer Python than Rasa 3.6 supports, so this script uses uv
to install a standalone Python 3.10 and build an isolated virtual
environment under /content. Run it once per Colab session.
"""

import os
import shutil
import subprocess
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UV_VERSION = "0.11.28"
UV_PATH = "/content/uv-bin/uv"
VENV_DIR = "/content/rasa_venv"
PYTHON_BIN = f"{VENV_DIR}/bin/python"
RASA_BIN = f"{VENV_DIR}/bin/rasa"

SPACY_MODEL_URL = (
    "https://github.com/explosion/spacy-models/releases/download/"
    "en_core_web_md-3.4.1/"
    "en_core_web_md-3.4.1-py3-none-any.whl"
)


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def main():
    run([sys.executable, "-m", "pip", "install", "-q", "pyngrok"])

    # Remove incomplete installations and old caches.
    for path in [
        VENV_DIR,
        "/content/uv-bin",
        "/content/uv-cache",
        "/content/uv-python",
        "/root/.cache/uv",
    ]:
        shutil.rmtree(path, ignore_errors=True)

    # Install a standalone, pinned uv version under /content.
    run(
        [
            "bash",
            "-lc",
            (
                f"curl -LsSf https://astral.sh/uv/{UV_VERSION}/install.sh "
                "| env UV_INSTALL_DIR=/content/uv-bin "
                "UV_NO_MODIFY_PATH=1 sh"
            ),
        ]
    )

    uv_environment = os.environ.copy()
    uv_environment.update(
        {
            "UV_CACHE_DIR": "/content/uv-cache",
            "UV_PYTHON_INSTALL_DIR": "/content/uv-python",
            "UV_LINK_MODE": "copy",
        }
    )

    run([UV_PATH, "--version"], env=uv_environment)
    run([UV_PATH, "python", "install", "3.10"], env=uv_environment)
    run(
        [UV_PATH, "venv", "--python", "3.10", VENV_DIR],
        env=uv_environment,
    )

    requirements_path = os.path.join(REPO_DIR, "requirements.txt")
    run(
        [
            UV_PATH,
            "pip",
            "install",
            "--python",
            PYTHON_BIN,
            "-r",
            requirements_path,
        ],
        env=uv_environment,
    )
    run(
        [
            UV_PATH,
            "pip",
            "install",
            "--python",
            PYTHON_BIN,
            SPACY_MODEL_URL,
        ],
        env=uv_environment,
    )

    os.environ["PATH"] = f"{VENV_DIR}/bin:" + os.environ["PATH"]

    run([PYTHON_BIN, "--version"])
    run([RASA_BIN, "--version"])
    run(
        [
            PYTHON_BIN,
            "-c",
            (
                "import spacy; "
                "spacy.load('en_core_web_md'); "
                "print('spaCy model loaded successfully.')"
            ),
        ]
    )

    print("Environment setup completed successfully.")


if __name__ == "__main__":
    main()
