"""
run.py - start KrishiAI with one command.

    python run.py

Starts the Streamlit web app on http://localhost:8501 and the Weather
Advisory REST API on http://127.0.0.1:8000 (Swagger docs at /docs).
Press Ctrl+C once to stop both.

Options:  python run.py --app-port 8501 --api-port 8000
"""

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KrishiAI web app and REST API together.")
    parser.add_argument("--app-port", default="8501")
    parser.add_argument("--api-port", default="8000")
    args = parser.parse_args()

    env = dict(os.environ, KRISHI_API_URL=f"http://127.0.0.1:{args.api_port}")

    # Streamlit must start from the project root: that is where .streamlit/config.toml
    # (theme + bundled-font serving) lives.
    procs = [
        subprocess.Popen([sys.executable, "-m", "uvicorn", "api:app", "--port", args.api_port],
                         cwd=os.path.join(ROOT, "src"), env=env),
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", os.path.join("src", "app.py"),
                          "--server.port", args.app_port], cwd=ROOT, env=env),
    ]
    print(f"\n  KrishiAI app : http://localhost:{args.app_port}"
          f"\n  REST API     : http://127.0.0.1:{args.api_port}   (docs: /docs)\n  Ctrl+C to stop.\n")
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
