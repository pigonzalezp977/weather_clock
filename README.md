# ⏰ Weather Clock para Raspberry Pi

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.0+-green?style=flat)](https://www.pygame.org/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-OS-C51A4A?style=flat&logo=raspberry-pi&logoColor=white)](https://www.raspberrypi.com/)
[![Open-Meteo](https://img.shields.io/badge/Weather%20API-Open--Meteo-blue?style=flat)](https://open-meteo.com/)

Aplicación de reloj digital y estación meteorológica diseñada para pantallas LCD/TFT de **3.5" (resolución 480x320 px)** en Raspberry Pi, desarrollada con **Pygame**.

Muestra la hora, fecha, condiciones meteorológicas en tiempo real (temperatura, humedad, estado del cielo) con íconos dinámicos y distinción astronómica entre **Día y Noche**, optimizada para un consumo mínimo de CPU.

---

## 📸 Distribución de la Pantalla (480 x 320 px)

```text
+-------------------------------------------------------------------------------+
|  Santiago [ CL ] [ DÍA ]                                                     |
|                                                                               |
|   13:18  42 (amarillo)                     [ Ícono Actual 72x72 ]             |
|   15/09/2026 Mar (verde)                         Despejado                    |
|   Temp: 27°C   Hum: 45% (cian)                                                |
+-------------------------------------------------------------------------------+
|  PRONÓSTICO 5 DÍAS                                                            |
|  +---------+   +---------+   +---------+   +---------+   +---------+          |
|  |   MIÉ   |   |   JUE   |   |   VIE   |   |   SÁB   |   |   DOM   |          |
|  |  16/09  |   |  17/09  |   |  18/09  |   |  19/09  |   |  20/09  |          |
|  | [Icono] |   | [Icono] |   | [Icono] |   | [Icono] |   | [Icono] |          |
|  | Max 26° |   | Max 28° |   | Max 27° |   | Max 27° |   | Max 18° | (naranja)|
|  | Min 14° |   | Min 14° |   | Min 14° |   | Min 14° |   | Min 11° | (celeste)|
|  +---------+   +---------+   +---------+   +---------+   +---------+          |
+-------------------------------------------------------------------------------+
```

---

## ✨ Características Principales

- **Reloj Digital Preciso**: Formato `HH:MM` en gran tamaño con segundero `SS` en amarillo.
- **Pronóstico Meteorológico Semanal (5 Días)**: 5 tarjetas individuales con el día de la semana en español, fecha (`DD/MM`), mini ícono meteorológico y temperaturas Máxima (cálida) y Mínima (fría).
- **Detección Astronómica Día / Noche**: Utiliza la coordenada solar de la API para saber con exactitud si es de día o de noche:
  - ☀️ De día: Muestra ícono de sol y etiqueta `[ DÍA ]`.
  - 🌙 De noche: Muestra luna creciente con estrellas y etiqueta `[ NOCHE ]`.
- **Iconografía Meteorológica Adaptativa**: Soporte para cielo despejado, parcialmente nublado, nublado, lluvia, nieve y tormenta en dos tamaños (72x72 px y 32x32 px).
- **Peticiones Asíncronas (Multihilo)**: La consulta meteorológica se procesa en segundo plano (`threading.Thread`), evitando pausas o saltos en el segundero.
- **Consumo Ultra Bajo**: Limitado a 5 FPS (`clock.tick(5)`), manteniendo la Raspberry Pi fría y con uso de CPU inferior al 3%.
- **Sin Claves de API**: Conexión a la API gratuita de [Open-Meteo](https://open-meteo.com/) sin registrar tarjetas ni tokens.
- **Despliegue Remoto en 1 Clic (`despliega.py`)**: Sube archivos vía SFTP, detiene instancias previas (`pkill`) y relanza la aplicación sobre la pantalla local (`DISPLAY=:0`) automáticamente.
- **Configuración Centralizada en JSON**: Todos los parámetros (ciudad, coordenadas, pantalla y credenciales de red) se configuran en `config.json`.

---

## 📂 Estructura del Proyecto

```text
weather_clock/
├── clock.py               # Script principal del reloj e interfaz Pygame
├── despliega.py           # Script de despliegue remoto hacia Raspberry Pi (SFTP/SSH)
├── config.example.json    # Plantilla de configuración para control de versiones
├── config.json            # Configuración local con credenciales (ignorado por git)
├── .gitignore             # Filtro de archivos sensibles y temporales
├── fonts/
│   └── RobotoCondensed-Bold.ttf   # Tipografía moderna para números y textos
└── icons/
    ├── sun.png            # Sol (Día despejado)
    ├── moon.png           # Luna (Noche despejada)
    ├── partly-cloudy.png  # Parcialmente nublado (Día)
    ├── cloudy-night.png   # Parcialmente nublado (Noche)
    ├── cloudy-day.png     # Nublado completo
    └── rainy-day.png      # Lluvia / Chubascos
```

---

## 🛠️ Requisitos

### En la Raspberry Pi:
- Raspberry Pi (Cualquier modelo: Zero 2W, 3B, 3B+, 4B, 5).
- Pantalla LCD 3.5" (resolución 480x320 o compatible con framebuffer / X11).
- Raspberry Pi OS con entorno gráfico (X11 / Wayland).
- Python 3 y librerías:
  ```bash
  sudo apt update
  sudo apt install -y python3-pygame python3-requests
  ```

### En tu computadora de desarrollo (Mac/Linux/Windows):
- Python 3.9+.
- Librería `paramiko` (para el script de despliegue):
  ```bash
  pip install paramiko
  ```

---

## ⚙️ Configuración

1. Copia la plantilla `config.example.json` a `config.json`:
   ```bash
   cp config.example.json config.json
   ```

2. Edita `config.json` con tus datos:
   ```json
   {
     "location": {
       "city": "Santiago",
       "country_code": "CL",
       "latitude": -33.45,
       "longitude": -70.66
     },
     "display": {
       "width": 480,
       "height": 320,
       "fullscreen": true,
       "hide_mouse": true,
       "fps": 5,
       "weather_update_interval_sec": 900
     },
     "deployment": {
       "raspberry_ip": "192.168.1.95",
       "raspberry_user": "pi",
       "raspberry_password": "TU_PASSWORD_AQUI",
       "raspberry_port": 22,
       "remote_dir": "/home/pi/Proyectos/weather_clock",
       "local_file": "clock.py"
     }
   }
   ```

> [!TIP]
> Puedes buscar la latitud y longitud de tu localidad en [Open-Meteo](https://open-meteo.com/).

---

## 🚀 Despliegue Remoto a la Raspberry Pi

Desde tu terminal de desarrollo ejecuta:

```bash
python3 despliega.py
```

El script se encargará automáticamente de:
1. Conectarse a la Raspberry Pi vía SSH con la contraseña configurada.
2. Crear y asignar permisos a la carpeta de destino (`/home/pi/Proyectos/weather_clock`).
3. Sincronizar por SFTP: `clock.py`, `config.json`, `fonts/` e `icons/`.
4. Detener cualquier instancia anterior con `pkill -9 -f "python3 clock.py"`.
5. Ejecutar la nueva versión en segundo plano apuntando a la pantalla del dispositivo (`DISPLAY=:0 nohup python3 clock.py > app.log 2>&1 &`).
6. Verificar y mostrar el PID del proceso activo.

---

## 🖥️ Ejecución Local en la Raspberry Pi

Si te encuentras directamente en la consola de la Raspberry Pi:

```bash
cd /home/pi/Proyectos/weather_clock
DISPLAY=:0 python3 clock.py
```

Para salir de la aplicación en cualquier momento, presiona la tecla `ESC`.

---

## 🔄 Inicio Automático al Encender la Raspberry Pi

Para que el reloj se inicie automáticamente cada vez que enciendas tu Raspberry Pi, puedes crear un servicio `systemd`:

1. Crea el archivo del servicio:
   ```bash
   sudo nano /etc/systemd/system/weather-clock.service
   ```

2. Agrega el siguiente contenido:
   ```ini
   [Unit]
   Description=Weather Clock Pygame
   After=graphical.target network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=pi
   Environment=DISPLAY=:0
   WorkingDirectory=/home/pi/Proyectos/weather_clock
   ExecStart=/usr/bin/python3 /home/pi/Proyectos/weather_clock/clock.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=graphical.target
   ```

3. Habilita e inicia el servicio:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable weather-clock.service
   sudo systemctl start weather-clock.service
   ```

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Consulta `LICENSE` para más información.
Tipografía **Roboto Condensed** bajo [Apache License 2.0 / SIL OFL](https://fonts.google.com/specimen/Roboto+Condensed).
