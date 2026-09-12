#!/usr/bin/env python3
"""
Script de despliegue para clock.py en Raspberry Pi vía SFTP y SSH.

Lee las credenciales y configuración desde config.json, transfiere el código,
los recursos (icons/fonts) y el archivo de configuración a la Raspberry Pi,
detiene el proceso con pkill y lo inicia con DISPLAY=:0 en segundo plano.
"""

import os
import sys
import time
import json
import getpass
import argparse
import paramiko

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# Valores por defecto en caso de no existir config.json
DEFAULT_IP = "192.168.1.95"
DEFAULT_USER = "pi"
DEFAULT_PASSWORD = ""
DEFAULT_PORT = 22
DEFAULT_REMOTE_DIR = "/home/pi/Proyectos/weather_clock"
DEFAULT_LOCAL_FILE = "clock.py"

# Cargar configuración desde config.json si existe
config_data = {}
if os.path.isfile(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"Advertencia: No se pudo leer {CONFIG_FILE}: {e}")

dep_cfg = config_data.get("deployment", {})
RASPBERRY_IP = dep_cfg.get("raspberry_ip", DEFAULT_IP)
RASPBERRY_USER = dep_cfg.get("raspberry_user", DEFAULT_USER)
RASPBERRY_PASSWORD = dep_cfg.get("raspberry_password", DEFAULT_PASSWORD)
RASPBERRY_PORT = dep_cfg.get("raspberry_port", DEFAULT_PORT)
REMOTE_DIR = dep_cfg.get("remote_dir", DEFAULT_REMOTE_DIR)
LOCAL_FILE = dep_cfg.get("local_file", DEFAULT_LOCAL_FILE)


def print_step(emoji: str, title: str):
    print(f"\n{emoji} \033[1;36m{title}\033[0m")


def print_success(msg: str):
    print(f"  \033[1;32m✔\033[0m {msg}")


def print_warn(msg: str):
    print(f"  \033[1;33m⚠\033[0m {msg}")


def print_error(msg: str):
    print(f"  \033[1;31m✖\033[0m {msg}")


def execute_sudo_command(client: paramiko.SSHClient, command: str, password: str):
    """Ejecuta un comando con sudo enviando la contraseña si es solicitada."""
    stdin, stdout, stderr = client.exec_command(f"sudo -S -p '' {command}")
    stdin.write(f"{password}\n")
    stdin.flush()
    status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return status, out, err


def sftp_put_directory(sftp: paramiko.SFTPClient, local_dir: str, remote_dir: str):
    """Copia un directorio local completo al directorio remoto vía SFTP."""
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass

    for item in os.listdir(local_dir):
        if item.startswith("."):
            continue
        lpath = os.path.join(local_dir, item)
        rpath = f"{remote_dir}/{item}"
        if os.path.isdir(lpath):
            sftp_put_directory(sftp, lpath, rpath)
        else:
            sftp.put(lpath, rpath)


def main():
    parser = argparse.ArgumentParser(
        description="Despliega y reinicia clock.py en la Raspberry Pi vía SFTP (usando config.json)."
    )
    parser.add_argument(
        "--ip",
        default=RASPBERRY_IP,
        help=f"Dirección IP (por defecto: {RASPBERRY_IP})"
    )
    parser.add_argument(
        "--user",
        default=RASPBERRY_USER,
        help=f"Usuario SSH (por defecto: {RASPBERRY_USER})"
    )
    parser.add_argument(
        "--password",
        default=RASPBERRY_PASSWORD,
        help="Contraseña de la Raspberry Pi"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=RASPBERRY_PORT,
        help=f"Puerto SSH (por defecto: {RASPBERRY_PORT})"
    )
    parser.add_argument(
        "--no-sync-assets",
        dest="sync_assets",
        action="store_false",
        help="Omite la sincronización de las carpetas 'fonts' e 'icons'"
    )
    parser.set_defaults(sync_assets=True)

    args = parser.parse_args()

    ip = args.ip
    user = args.user
    port = args.port
    password = args.password

    print("\033[1;35m====================================================\033[0m")
    print("\033[1;35m    🚀 Despliegue de Weather Clock hacia Raspberry  \033[0m")
    print("\033[1;35m====================================================\033[0m")
    print(f" Destino:    {user}@{ip}:{port}")
    print(f" Directorio: {REMOTE_DIR}")

    # Si la contraseña está vacía o es placeholder, solicitarla
    if not password or "XXX" in password or password == "YOUR_PASSWORD_HERE":
        print_warn("Contraseña no encontrada o placeholder en config.json.")
        try:
            password = getpass.getpass(f"Ingresa la contraseña para {user}@{ip}: ")
        except (KeyboardInterrupt, EOFError):
            print("\nOperación cancelada.")
            sys.exit(130)

    local_clock_path = os.path.join(SCRIPT_DIR, LOCAL_FILE)
    if not os.path.isfile(local_clock_path):
        print_error(f"No se encontró el archivo local: {local_clock_path}")
        sys.exit(1)

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 1. Conexión SSH con contraseña
        print_step("🔐", f"Conectando a {user}@{ip} vía SSH...")
        ssh_client.connect(
            hostname=ip,
            port=port,
            username=user,
            password=password,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        print_success("Autenticación exitosa.")

        # 2. Asegurar que existe el directorio remoto y corregir permisos si pertenecía a root
        print_step("📁", "Verificando directorio y permisos remotos...")
        execute_sudo_command(ssh_client, f"mkdir -p {REMOTE_DIR}", password)
        execute_sudo_command(ssh_client, f"chown -R {user}:{user} {REMOTE_DIR}", password)
        print_success(f"Directorio remoto listo y con permisos de '{user}': {REMOTE_DIR}")

        # 3. Transferencia vía SFTP
        print_step("📤", "Iniciando transferencia de archivos vía SFTP...")
        sftp = ssh_client.open_sftp()

        # Transferencia de assets (fuentes e iconos)
        if args.sync_assets:
            fonts_dir = os.path.join(SCRIPT_DIR, "fonts")
            icons_dir = os.path.join(SCRIPT_DIR, "icons")
            if os.path.isdir(fonts_dir):
                print_step("🔤", "Transfiriendo carpeta 'fonts'...")
                sftp_put_directory(sftp, fonts_dir, f"{REMOTE_DIR}/fonts")
                print_success("Carpeta 'fonts' sincronizada.")
            if os.path.isdir(icons_dir):
                print_step("🖼️", "Transfiriendo carpeta 'icons'...")
                sftp_put_directory(sftp, icons_dir, f"{REMOTE_DIR}/icons")
                print_success("Carpeta 'icons' sincronizada.")

        # Transferir config.json
        if os.path.isfile(CONFIG_FILE):
            remote_cfg = f"{REMOTE_DIR}/config.json"
            sftp.put(CONFIG_FILE, remote_cfg)
            print_success("config.json transferido con éxito.")

        # Subida de clock.py
        remote_clock_file = f"{REMOTE_DIR}/{LOCAL_FILE}"
        try:
            sftp.put(local_clock_path, remote_clock_file)
            print_success(f"{LOCAL_FILE} transferido exitosamente.")
        except IOError as err:
            print_warn(f"Escritura directa denegada ({err}), aplicando subida segura vía /tmp...")
            tmp_remote_file = f"/tmp/{LOCAL_FILE}"
            sftp.put(local_clock_path, tmp_remote_file)
            execute_sudo_command(ssh_client, f"mv {tmp_remote_file} {remote_clock_file}", password)
            execute_sudo_command(ssh_client, f"chown {user}:{user} {remote_clock_file}", password)
            print_success(f"{LOCAL_FILE} transferido y actualizado con éxito.")

        sftp.close()

        # 4. Detener proceso anterior
        print_step("⏹️", "Deteniendo proceso anterior...")
        stop_cmd = 'pkill -9 -f "python3 clock.py"'
        execute_sudo_command(ssh_client, stop_cmd, password)
        print_success(f"Comando '{stop_cmd}' ejecutado.")

        time.sleep(1)

        # 5. Iniciar clock.py en segundo plano
        print_step("▶️", "Iniciando clock.py en segundo plano...")
        start_cmd = (
            f"cd {REMOTE_DIR} && "
            f"DISPLAY=:0 nohup python3 {LOCAL_FILE} > app.log 2>&1 < /dev/null &"
        )
        ssh_client.exec_command(start_cmd)
        print_success("Proceso lanzado con DISPLAY=:0 en segundo plano.")

        # 6. Comprobar que el proceso esté corriendo
        print_step("🔍", "Comprobando estado del proceso en la Raspberry...")
        time.sleep(1.5)
        stdin, stdout, stderr = ssh_client.exec_command('pgrep -f "python3 clock.py"')
        pids = stdout.read().decode("utf-8").strip().splitlines()

        if pids:
            print_success(f"¡Proceso activo con PID(s): {', '.join(pids)}!")
        else:
            print_warn(
                "No se detectó el proceso activo tras iniciar. Revisa los logs en la Raspberry:\n"
                f"    ssh {user}@{ip} 'cat {REMOTE_DIR}/app.log'"
            )

        print("\n\033[1;32m✨ ¡Despliegue completado con éxito! ✨\033[0m\n")

    except paramiko.AuthenticationException:
        print_error("Error de autenticación: la contraseña o el usuario son incorrectos.")
        sys.exit(1)
    except paramiko.SSHException as e:
        print_error(f"Error SSH: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        sys.exit(1)
    finally:
        ssh_client.close()


if __name__ == "__main__":
    main()
