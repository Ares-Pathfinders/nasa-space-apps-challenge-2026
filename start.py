#!/usr/bin/env python3
"""
ARES-Nav // Compila el frontend y arranca el servidor local en un solo paso.

Funciona en Linux, macOS y Windows (en Windows también: doble clic en start_server.bat).

Uso:
    python start.py                 # instala lo que falte, compila y arranca en :8000
    python start.py --port 8080     # otro puerto
    python start.py --no-build      # arranca sin recompilar el frontend
    python start.py --no-browser    # no abre el navegador

Pasos:
  1. Comprueba las dependencias de Python del backend (las instala con pip si faltan).
  2. Instala las dependencias de npm si no existe frontend/node_modules.
  3. Compila el frontend (npm run build -> frontend/dist).
  4. Arranca backend/server.py; si el puerto está ocupado usa el siguiente libre.
  5. Espera a que la API responda y abre el navegador.
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

# Módulos que necesita backend/server.py (nombre de import, no de paquete pip).
PYTHON_MODULES = ["numpy", "scipy", "networkx", "requests", "httpx", "tifffile", "pydantic", "pydantic_settings", "dotenv"]


# La consola de Windows puede usar cp1252: que acentos y flechas no rompan la salida.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
if USE_COLOR and os.name == "nt":
    os.system("")  # activa las secuencias ANSI (colores) en la consola de Windows


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
        fail(f"El comando falló (código {result.returncode}): {' '.join(command)}")


def ensure_python_dependencies() -> None:
    step(f"Comprobando dependencias de Python ({sys.executable})...")
    missing = [name for name in PYTHON_MODULES if importlib.util.find_spec(name) is None]
    if not missing:
        print("  Todo instalado.")
        return
    print(f"  Faltan: {', '.join(missing)}. Instalando backend/requirements.txt...")
    run([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS], cwd=ROOT)


def npm_command() -> str:
    # En Windows npm es npm.cmd; shutil.which lo resuelve con PATHEXT.
    npm = shutil.which("npm.cmd") if os.name == "nt" else None
    npm = npm or shutil.which("npm")
    if not npm:
        fail("No se encuentra npm. Instala Node.js (https://nodejs.org) y vuelve a intentarlo.")
    return npm


def build_frontend() -> None:
    npm = npm_command()
    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        step("Instalando dependencias del frontend (npm install)...")
        run([npm, "install"], cwd=FRONTEND)
    step("Compilando el frontend (npm run build)...")
    run([npm, "run", "build"], cwd=FRONTEND)


def port_is_free(port: int) -> bool:
    # Si algo acepta conexiones en el puerto, está ocupado (igual en Windows y Linux).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            return False
    # Y además tiene que poder abrirse (p. ej. no reservado por el sistema).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if os.name != "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # ignora TIME_WAIT, como server.py
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
                f"  {color(f'El puerto {preferred} ya está en uso', '93')} (¿un server.py antiguo abierto en otra terminal?).\n"
                f"  Uso el puerto {port}. Si quieres el {preferred}, cierra el otro servidor y vuelve a lanzar este script."
            )
            return port
    fail(f"No hay ningún puerto libre entre {preferred} y {preferred + 49}.")
    return preferred  # inalcanzable


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
    parser = argparse.ArgumentParser(description="Compila el frontend y arranca el servidor local de ARES-Nav.")
    parser.add_argument("--port", type=int, default=8000, help="Puerto preferido (por defecto 8000).")
    parser.add_argument("--no-build", action="store_true", help="No recompila el frontend.")
    parser.add_argument("--no-browser", action="store_true", help="No abre el navegador.")
    args = parser.parse_args()

    ensure_python_dependencies()
    if args.no_build:
        if not os.path.isfile(os.path.join(FRONTEND, "dist", "index.html")):
            fail("No existe frontend/dist. Lánzalo sin --no-build para compilarlo.")
    else:
        build_frontend()

    port = choose_port(args.port)
    step(f"Arrancando el servidor en el puerto {port}...")
    server = subprocess.Popen([sys.executable, os.path.join(BACKEND, "server.py"), str(port)], cwd=ROOT)

    try:
        if not wait_for_api(port, server):
            if server.poll() is None:
                server.terminate()
            fail("El servidor no ha arrancado. Revisa los mensajes de arriba.")

        url = f"http://localhost:{port}"
        step(f"Listo -> {url}   (mapa táctico: {url}/tactical)")
        print("  Pulsa Ctrl+C para parar el servidor.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        server.wait()
    except KeyboardInterrupt:
        step("Parando el servidor...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
