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

# Nombres de días en español
DIAS_SEMANA = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]

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
CARD_BG = (20, 22, 28)
CARD_BORDER = (42, 46, 58)
TEMP_MAX_COLOR = (255, 140, 60)
TEMP_MIN_COLOR = (90, 200, 255)
GRAY_TEXT = (150, 150, 160)

# Tipografías ajustadas a la resolución 480x320
font_file = os.path.join(FONTS_DIR, "RobotoCondensed-Bold.ttf")
if os.path.isfile(font_file):
    font_clock = pygame.font.Font(font_file, 56)
    font_sec = pygame.font.Font(font_file, 26)
    font_text = pygame.font.Font(font_file, 17)
    font_desc = pygame.font.Font(font_file, 15)
    font_day = pygame.font.Font(font_file, 14)
    font_card_date = pygame.font.Font(font_file, 11)
    font_card_temp = pygame.font.Font(font_file, 12)
    font_small = pygame.font.Font(font_file, 12)
else:
    font_clock = pygame.font.SysFont("monospace", 50, bold=True)
    font_sec = pygame.font.SysFont("monospace", 24, bold=True)
    font_text = pygame.font.SysFont("monospace", 16, bold=True)
    font_desc = pygame.font.SysFont("monospace", 14, bold=True)
    font_day = pygame.font.SysFont("monospace", 13, bold=True)
    font_card_date = pygame.font.SysFont("monospace", 11)
    font_card_temp = pygame.font.SysFont("monospace", 12, bold=True)
    font_small = pygame.font.SysFont("monospace", 11, bold=True)

# Carga de iconos (Normal 72x72 y Mini 32x32)
ICON_SIZE = (72, 72)
MINI_ICON_SIZE = (32, 32)
weather_icons = {}
weather_icons_mini = {}

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
            if name in ("moon.png", "cloudy-night.png", "cloudy-day.png"):
                img = img.convert()
                img.set_colorkey((0, 0, 0))
            else:
                img = img.convert_alpha()
            weather_icons[name] = pygame.transform.smoothscale(img, ICON_SIZE)
            weather_icons_mini[name] = pygame.transform.smoothscale(img, MINI_ICON_SIZE)
        except Exception:
            pass

# Estado del clima actual
temp_actual = "--"
humedad_actual = "--"
clima_desc = ""
clima_icono_nom = "sun.png"
is_day = 1
pronostico_semana = []
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


def parse_day_card(date_str, code, max_temp, min_temp):
    """Convierte los datos diarios de la API en una estructura para las tarjetas de pronóstico."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dia_nom = DIAS_SEMANA[dt.weekday()]
        fecha_corta = dt.strftime("%d/%m")
    except Exception:
        dia_nom = "---"
        fecha_corta = "--/--"

    # Los pronósticos diurnos se representan con iconos de día
    icono_nom, _ = get_weather_info(code, is_day_val=1)

    return {
        "dia": dia_nom,
        "fecha": fecha_corta,
        "icono": icono_nom,
        "max": f"{round(max_temp)}°" if max_temp is not None else "--",
        "min": f"{round(min_temp)}°" if min_temp is not None else "--"
    }


def update_weather():
    global temp_actual, humedad_actual, clima_desc, clima_icono_nom, is_day, pronostico_semana
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={LAT}&longitude={LON}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,is_day"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
            f"&timezone=auto&forecast_days=6"
        )
        res = requests.get(url, timeout=6).json()

        # 1. Clima actual
        current = res.get("current", {})
        temp_actual = f"{round(current.get('temperature_2m', 0))}°C"
        humedad_actual = f"{current.get('relative_humidity_2m', 0)}%"
        code = current.get("weather_code", 0)
        is_day = current.get("is_day", 1)
        clima_icono_nom, clima_desc = get_weather_info(code, is_day)

        # 2. Pronóstico para los próximos 5 días (índices 1 al 5)
        daily = res.get("daily", {})
        times = daily.get("time", [])
        codes = daily.get("weather_code", [])
        t_maxs = daily.get("temperature_2m_max", [])
        t_mins = daily.get("temperature_2m_min", [])

        nuevos_dias = []
        for i in range(1, min(6, len(times))):
            dia_info = parse_day_card(
                times[i],
                codes[i] if i < len(codes) else 0,
                t_maxs[i] if i < len(t_maxs) else None,
                t_mins[i] if i < len(t_mins) else None
            )
            nuevos_dias.append(dia_info)

        pronostico_semana = nuevos_dias

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
    fecha_str = now.strftime("%d/%m/%Y") + f" {DIAS_SEMANA[now.weekday()]}"

    # Dibujar UI
    screen.fill(BLACK)

    # 1. Ubicación y encabezado dinámico con indicador Día / Noche
    surf_city = font_text.render(CITY_NAME, True, YELLOW)
    surf_tag = font_text.render(COUNTRY_TAG, True, BLACK, GREEN)
    screen.blit(surf_city, (20, 10))
    tag_x = 20 + surf_city.get_width() + 10
    screen.blit(surf_tag, (tag_x, 10))

    # Etiqueta de Día o Noche
    if is_day == 1:
        surf_dn = font_text.render(" DÍA ", True, BLACK, YELLOW)
    else:
        surf_dn = font_text.render(" NOCHE ", True, WHITE, NIGHT_BG)
    dn_x = tag_x + surf_tag.get_width() + 10
    screen.blit(surf_dn, (dn_x, 10))

    # 2. Reloj Digital
    surf_hora = font_clock.render(hora_str, True, WHITE)
    surf_sec = font_sec.render(sec_str, True, YELLOW)
    screen.blit(surf_hora, (20, 36))
    screen.blit(surf_sec, (170, 44))

    # 3. Fecha
    surf_fecha = font_text.render(fecha_str, True, GREEN)
    screen.blit(surf_fecha, (20, 96))

    # 4. Datos de Clima Actual
    surf_temp_hum = font_text.render(f"Temp: {temp_actual}   Hum: {humedad_actual}", True, CYAN)
    screen.blit(surf_temp_hum, (20, 120))

    # 5. Icono de Clima Actual y Estado (Columna Derecha)
    if clima_icono_nom in weather_icons:
        icon_surf = weather_icons[clima_icono_nom]
        screen.blit(icon_surf, (345, 32))

    if clima_desc:
        surf_desc = font_desc.render(clima_desc, True, WHITE)
        desc_rect = surf_desc.get_rect(center=(381, 116))
        screen.blit(surf_desc, desc_rect)

    # Línea divisoria elegante
    pygame.draw.line(screen, (38, 42, 54), (15, 145), (465, 145), 1)

    # 6. Sección de Pronóstico 5 Días
    surf_fore_title = font_small.render("PRONÓSTICO 5 DÍAS", True, GRAY_TEXT)
    screen.blit(surf_fore_title, (20, 153))

    card_w = 84
    card_h = 136
    card_gap = 8
    start_x = 15
    card_y = 173

    for i, day in enumerate(pronostico_semana):
        cx = start_x + i * (card_w + card_gap)
        card_rect = pygame.Rect(cx, card_y, card_w, card_h)

        # Fondo y borde de la tarjeta
        pygame.draw.rect(screen, CARD_BG, card_rect, border_radius=8)
        pygame.draw.rect(screen, CARD_BORDER, card_rect, width=1, border_radius=8)

        # Día de la semana (ej: MIÉ)
        surf_d_nom = font_day.render(day["dia"], True, YELLOW)
        screen.blit(surf_d_nom, surf_d_nom.get_rect(center=(cx + card_w // 2, card_y + 14)))

        # Fecha corta (ej: 16/09)
        surf_d_fecha = font_card_date.render(day["fecha"], True, GRAY_TEXT)
        screen.blit(surf_d_fecha, surf_d_fecha.get_rect(center=(cx + card_w // 2, card_y + 30)))

        # Mini icono del clima
        icon_nom = day["icono"]
        if icon_nom in weather_icons_mini:
            m_surf = weather_icons_mini[icon_nom]
            screen.blit(m_surf, (cx + (card_w - 32) // 2, card_y + 46))

        # Temperatura Máxima (Cálido / Naranja)
        surf_max = font_card_temp.render(f"Max {day['max']}", True, TEMP_MAX_COLOR)
        screen.blit(surf_max, surf_max.get_rect(center=(cx + card_w // 2, card_y + 92)))

        # Temperatura Mínima (Frío / Celeste)
        surf_min = font_card_temp.render(f"Min {day['min']}", True, TEMP_MIN_COLOR)
        screen.blit(surf_min, surf_min.get_rect(center=(cx + card_w // 2, card_y + 114)))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
