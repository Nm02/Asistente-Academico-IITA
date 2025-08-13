#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

def mostrar_help():
    texto = f"""
Uso:
  python3 deploy.py activar --nombre NOMBRE --archivo ARCHIVO [--obj OBJ] [--puerto PUERTO]
  python3 deploy.py desactivar --pid PID
  python3 deploy.py listar
  python3 deploy.py reiniciar --nombre NOMBRE --archivo ARCHIVO [--obj OBJ] [--puerto PUERTO]
  python3 deploy.py help

Notas:
- La ruta base es siempre: {BASE_DIR}
- El entorno virtual debe estar en: {BASE_DIR}/env
- --archivo es el .py relativo a esta carpeta (ej. main.py o api/main.py).
- --obj es el nombre del objeto ASGI dentro del archivo (default: app).

Ejemplo:
  python3 deploy.py activar --nombre app --archivo main.py --puerto 8765
"""
    print(texto)

def _to_import_path(archivo: str) -> str:
    """Convierte 'api/main.py' -> 'api.main' relativo a BASE_DIR."""
    file_path = (BASE_DIR / archivo).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
    if file_path.suffix != ".py":
        raise ValueError("--archivo debe ser un .py")
    rel = file_path.relative_to(BASE_DIR).with_suffix("")
    return ".".join(rel.parts)

def levantar_uvicorn_bg(nombre: str, puerto: int, archivo: str, obj: str):
    venv_path = BASE_DIR / "env"
    if not (venv_path / "bin" / "uvicorn").exists():
        raise FileNotFoundError(f"No se encontró uvicorn en el venv: {venv_path}")

    import_path = _to_import_path(archivo)
    target = f"{import_path}:{obj}"

    print(f"Levantando {nombre} -> {target} en {puerto} usando venv {venv_path}...")

    comando = [
        str(venv_path / "bin" / "python"), "-u", "-m", "uvicorn",
        target,
        "--host", "0.0.0.0",
        "--port", str(puerto),
        "--workers", "4",
    ]

    log_file = BASE_DIR / f"{nombre}.log"
    pid_file = BASE_DIR / f"{nombre}.pid"

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    with open(log_file, "a") as log:
        proceso = subprocess.Popen(
            comando,
            cwd=BASE_DIR,
            stdout=log,
            stderr=log,
            env=env
        )

    pid_file.write_text(str(proceso.pid))
    print(f"Servicio '{nombre}' en background | PID: {proceso.pid} | Logs: {log_file} | PID file: {pid_file}")

def detener_por_pid(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Señal SIGTERM enviada al PID {pid}.")
    except ProcessLookupError:
        print(f"No existe proceso con PID {pid}.")
    except PermissionError:
        print(f"Permiso denegado para terminar el PID {pid}.")

def listar_servicios():
    pid_files = list(BASE_DIR.glob("*.pid"))
    if not pid_files:
        print("No hay servicios levantados registrados.")
        return
    print(f"{'Servicio':<20} {'PID':<10} {'Estado':<10}")
    print("-" * 45)
    for pid_file in pid_files:
        nombre = pid_file.stem
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            estado = "Activo"
        except (ValueError, ProcessLookupError):
            estado = "Muerto"
            pid = "N/A"
        print(f"{nombre:<20} {pid:<10} {estado:<10}")

def reiniciar_servicio(nombre: str, puerto: int, archivo: str, obj: str):
    pid_file = BASE_DIR / f"{nombre}.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            detener_por_pid(pid)
        except ValueError:
            print(f"PID inválido en {pid_file}")
    else:
        print(f"No se encontró PID file para '{nombre}'")
    levantar_uvicorn_bg(nombre, puerto, archivo, obj)

def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("operacion", choices=["activar", "desactivar", "listar", "reiniciar", "help"], help="Acción a realizar.")
    parser.add_argument("--nombre", help="Nombre del servicio (ej. app)")
    parser.add_argument("--puerto", type=int, default=8000, help="Puerto de ejecución (default: 8000)")
    parser.add_argument("--pid", type=int, help="PID a detener (para desactivar)")
    parser.add_argument("--archivo", help="Archivo Python relativo a la carpeta base (ej. main.py o api/main.py)")
    parser.add_argument("--obj", default="app", help="Nombre del objeto ASGI dentro del archivo (default: app)")

    args = parser.parse_args()

    if args.operacion == "activar":
        if not args.nombre or not args.archivo:
            parser.error("Para 'activar' se requiere --nombre y --archivo")
    elif args.operacion == "desactivar":
        if args.pid is None:
            parser.error("Para 'desactivar' se requiere --pid")
    elif args.operacion == "reiniciar":
        if not args.nombre or not args.archivo:
            parser.error("Para 'reiniciar' se requiere --nombre y --archivo")

    return args

def main():
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == "help"):
        mostrar_help()
        return

    args = parse_args()

    if args.operacion == "activar":
        levantar_uvicorn_bg(args.nombre, args.puerto, args.archivo, args.obj)
    elif args.operacion == "desactivar":
        detener_por_pid(args.pid)
    elif args.operacion == "listar":
        listar_servicios()
    elif args.operacion == "reiniciar":
        reiniciar_servicio(args.nombre, args.puerto, args.archivo, args.obj)

if __name__ == "__main__":
    main()

