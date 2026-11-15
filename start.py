#!/usr/bin/env python3
"""
ARES-Nav // Build the frontend and start the local server in one step.

Works on Linux, macOS and Windows (on Windows you can also double-click start_server.bat).

Usage:
    python start.py                 # install what is missing, build and serve on :8000
    python start.py --port 8080     # another port
    python start.py --no-build      # start without rebuilding the frontend
    python start.py --no-browser    # do not open the browser

Steps:
  1. Checks the backend Python dependencies (installs them with pip if missing).
  2. Installs npm dependencies if frontend/node_modules does not exist.
  3. Builds the frontend (npm run build -> frontend/dist).
  4. Starts backend/server.py; if the port is busy, uses the next free one.
  5. Waits for the API to respond and opens the browser.
"""

import argparse
import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND = os.path.join(ROOT, "backend")
REQUIREMENTS = os.path.join(BACKEND, "requirements.txt")

# Modules required by backend/server.py (import names, not pip package names).
PYTHON_MODULES = ["numpy", "scipy", "networkx", "requests", "httpx", "tifffile", "pydantic", "pydantic_settings", "dotenv"]


# The Windows console may use cp1252: keep non-ASCII characters from breaking output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
if USE_COLOR and os.name == "nt":
    os.system("")  # enable ANSI escape sequences (colours) in the Windows console


def color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def step(message: str) -> None:
    print(f"\n{color('[ARES-Nav]', '96')} {message}", flush=True)


def fail(message: str) -> None:
    print(f"\n{color('[ARES-Nav] ERROR:', '91')} {message}", file=sys.stderr, flush=True)
    sys.exit(1)


def run(command: list, cwd: str) -> None:
    print("  $ " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        fail(f"Command failed (exit code {result.returncode}): {' '.join(command)}")


def ensure_python_dependencies() -> None:
    step(f"Checking Python dependencies ({sys.executable})...")
    missing = [name for name in PYTHON_MODULES if importlib.util.find_spec(name) is None]
    if not missing:
        print("  Everything is installed.")
        return
    print(f"  Missing: {', '.join(missing)}. Installing backend/requirements.txt...")
    run([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS], cwd=ROOT)


def npm_command() -> str:
    # On Windows npm is npm.cmd; shutil.which resolves it through PATHEXT.
    npm = shutil.which("npm.cmd") if os.name == "nt" else None
    npm = npm or shutil.which("npm")
    if not npm:
        fail("npm not found. Install Node.js (https://nodejs.org) and try again.")
    return npm


def build_frontend() -> None:
    npm = npm_command()
    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        step("Installing frontend dependencies (npm install)...")
        run([npm, "install"], cwd=FRONTEND)
    step("Building the frontend (npm run build)...")
    run([npm, "run", "build"], cwd=FRONTEND)


def port_is_free(port: int) -> bool:
    # If something accepts connections on the port, it is busy (same on Windows and Linux).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            return False
    # It must also be bindable (e.g. not reserved by the system).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if os.name != "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # ignore TIME_WAIT, like server.py
        try:
            sock.bind(("", port))
        except OSError:
            return False
    return True


def choose_port(preferred: int) -> int:
    if port_is_free(preferred):
        return preferred
    for port in range(preferred + 1, preferred + 50):
        if port_is_free(port):
            print(
                f"  {color(f'Port {preferred} is already in use', '93')} (an old server.py open in another terminal?).\n"
                f"  Using port {port}. To use {preferred}, stop the other server and run this script again."
            )
            return port
    fail(f"No free port between {preferred} and {preferred + 49}.")
    return preferred  # unreachable


def wait_for_api(port: int, process: subprocess.Popen, timeout_s: float = 120.0) -> bool:
    url = f"http://localhost:{port}/api/health"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the frontend and start the ARES-Nav local server.")
    parser.add_argument("--port", type=int, default=8000, help="Preferred port (default 8000).")
    parser.add_argument("--no-build", action="store_true", help="Do not rebuild the frontend.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser.")
    args = parser.parse_args()

    ensure_python_dependencies()
    if args.no_build:
        if not os.path.isfile(os.path.join(FRONTEND, "dist", "index.html")):
            fail("frontend/dist does not exist. Run without --no-build to build it.")
    else:
        build_frontend()

    port = choose_port(args.port)
    step(f"Starting the server on port {port}...")
    server = subprocess.Popen([sys.executable, os.path.join(BACKEND, "server.py"), str(port)], cwd=ROOT)

    try:
        if not wait_for_api(port, server):
            if server.poll() is None:
                server.terminate()
            fail("The server did not start. Check the messages above.")

        url = f"http://localhost:{port}"
        step(f"Ready -> {url}   (tactical map: {url}/tactical)")
        print("  Press Ctrl+C to stop the server.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        server.wait()
    except KeyboardInterrupt:
        step("Stopping the server...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
