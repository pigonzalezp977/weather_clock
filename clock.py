import os
import sys
import time
import json
import requests
import threading
import pygame
from datetime import datetime

# Directorios de recursos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(SCRIPT_DIR, "icons")
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# Carga de configuración centralizada desde JSON
config = {}
if os.path.isfile(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Advertencia: No se pudo leer {CONFIG_FILE}: {e}")

loc_cfg = config.get("location", {})
CITY_NAME = loc_cfg.get("city", "Santiago")
COUNTRY_TAG = f" {loc_cfg.get('country_code', 'CL')} "
LAT = loc_cfg.get("latitude", -33.45)
LON = loc_cfg.get("longitude", -70.66)

disp_cfg = config.get("display", {})
WIDTH = disp_cfg.get("width", 480)
HEIGHT = disp_cfg.get("height", 320)
FULLSCREEN = disp_cfg.get("fullscreen", True)
HIDE_MOUSE = disp_cfg.get("hide_mouse", True)
FPS = disp_cfg.get("fps", 5)
WEATHER_INTERVAL = disp_cfg.get("weather_update_interval_sec", 900)

# Inicialización de Pygame
pygame.init()
if FULLSCREEN:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

if HIDE_MOUSE:
    pygame.mouse.set_visible(False)

# Paleta de Colores
BLACK = (10, 10, 10)
WHITE = (255, 255, 255)
YELLOW = (255, 204, 0)
GREEN = (50, 205, 50)
CYAN = (0, 200, 255)
NIGHT_BG = (65, 45, 120)

# Fuentes (Usa Roboto si existe, con fallback a monospace)
font_file = os.path.join(FONTS_DIR, "RobotoCondensed-Bold.ttf")
if os.path.isfile(font_file):
    font_clock = pygame.font.Font(font_file, 74)
    font_sec = pygame.font.Font(font_file, 34)
    font_text = pygame.font.Font(font_file, 22)
    font_desc = pygame.font.Font(font_file, 20)
else:
    font_clock = pygame.font.SysFont("monospace", 68, bold=True)
    font_sec = pygame.font.SysFont("monospace", 32, bold=True)
    font_text = pygame.font.SysFont("monospace", 22, bold=True)
    font_desc = pygame.font.SysFont("monospace", 18, bold=True)

# Carga de iconos del clima (Día y Noche)
ICON_SIZE = (96, 96)
weather_icons = {}
icon_names = [
    "sun.png",
    "partly-cloudy.png",
    "cloudy-day.png",
    "rainy-day.png",
    "moon.png",
    "cloudy-night.png",
]

for name in icon_names:
    path = os.path.join(ICONS_DIR, name)
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path)
            # Para iconos nocturnos con fondo negro, aplicar colorkey para transparencia
            if name in ("moon.png", "cloudy-night.png"):
                img = img.convert()
                img.set_colorkey((0, 0, 0))
            else:
                img = img.convert_alpha()
            weather_icons[name] = pygame.transform.smoothscale(img, ICON_SIZE)
        except Exception:
            pass

# Estado del clima
temp_actual = "--"
humedad_actual = "--"
clima_desc = ""
clima_icono_nom = "sun.png"
is_day = 1
last_weather_check = 0


def get_weather_info(code, is_day_val):
    """Determina el icono y la descripción según el código meteorológico y si es día o noche."""
    es_noche = (is_day_val == 0)

    if code == 0:
        if es_noche:
            return "moon.png", "Despejado"
        return "sun.png", "Despejado"

    elif code in (1, 2):
        if es_noche:
            return "cloudy-night.png", "Parcial"
        return "partly-cloudy.png", "Parcial"

    elif code in (3, 45, 48):
        return "cloudy-day.png", "Nublado"

    elif code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rainy-day.png", "Lluvia"

    elif code in (71, 73, 75, 77, 85, 86):
        return "rainy-day.png", "Nieve"

    elif code in (95, 96, 99):
        return "rainy-day.png", "Tormenta"

    else:
        if es_noche:
            return "moon.png", "Despejado"
        return "sun.png", "Despejado"


def update_weather():
    global temp_actual, humedad_actual, clima_desc, clima_icono_nom, is_day
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,weather_code,is_day"
        )
        res = requests.get(url, timeout=6).json()
        current = res.get("current", {})
        temp_actual = f"{round(current.get('temperature_2m', 0))}°C"
        humedad_actual = f"{current.get('relative_humidity_2m', 0)}%"
        code = current.get("weather_code", 0)
        is_day = current.get("is_day", 1)
        clima_icono_nom, clima_desc = get_weather_info(code, is_day)
    except Exception:
        pass


def update_weather_async():
    """Ejecuta la consulta en un hilo secundario para no frenar los FPS del reloj."""
    thread = threading.Thread(target=update_weather, daemon=True)
    thread.start()


running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # Actualizar clima periódicamente de forma asíncrona
    if time.time() - last_weather_check > WEATHER_INTERVAL:
        last_weather_check = time.time()
        update_weather_async()

    # Obtener fecha y hora
    now = datetime.now()
    hora_str = now.strftime("%H:%M")
    sec_str = now.strftime("%S")
    fecha_str = now.strftime("%d/%m/%Y %a")

    # Dibujar UI
    screen.fill(BLACK)

    # 1. Ubicación y encabezado dinámico con indicador Día / Noche
    surf_city = font_text.render(CITY_NAME, True, YELLOW)
    surf_tag = font_text.render(COUNTRY_TAG, True, BLACK, GREEN)
    screen.blit(surf_city, (25, 20))
    tag_x = 25 + surf_city.get_width() + 12
    screen.blit(surf_tag, (tag_x, 20))

    # Etiqueta de Día o Noche
    if is_day == 1:
        surf_dn = font_text.render(" DÍA ", True, BLACK, YELLOW)
    else:
        surf_dn = font_text.render(" NOCHE ", True, WHITE, NIGHT_BG)
    dn_x = tag_x + surf_tag.get_width() + 10
    screen.blit(surf_dn, (dn_x, 20))

    # 2. Reloj Digital
    surf_hora = font_clock.render(hora_str, True, WHITE)
    surf_sec = font_sec.render(sec_str, True, YELLOW)
    screen.blit(surf_hora, (25, 65))
    screen.blit(surf_sec, (260, 75))

    # 3. Fecha
    surf_fecha = font_text.render(fecha_str, True, GREEN)
    screen.blit(surf_fecha, (25, 165))

    # 4. Datos de Clima (Columna Izquierda)
    surf_temp = font_text.render(f"Temp: {temp_actual}", True, CYAN)
    surf_hum = font_text.render(f"Hum:  {humedad_actual}", True, CYAN)
    screen.blit(surf_temp, (25, 215))
    screen.blit(surf_hum, (25, 255))

    # 5. Icono de Clima y Estado (Columna Derecha)
    if clima_icono_nom in weather_icons:
        icon_surf = weather_icons[clima_icono_nom]
        screen.blit(icon_surf, (335, 165))

    if clima_desc:
        surf_desc = font_desc.render(clima_desc, True, WHITE)
        desc_rect = surf_desc.get_rect(center=(383, 275))
        screen.blit(surf_desc, desc_rect)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
