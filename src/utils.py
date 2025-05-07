import logging
import colorlog
import os
import yaml
from math import radians, cos, sin, pi, sqrt, atan2
import pandas as pd


# ==================================================================
# Logging 
# ==================================================================
def get_logger(name):
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(name)s] -  %(levelname)s: %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'white',   
            'INFO': 'white',       
            'WARNING': 'yellow',   
            'ERROR': 'red',
            'CRITICAL': 'bold_red' 
        }
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(
        format='%(asctime)s - [%(name)s] %(levelname)s: %(message)s',
        level=logging.INFO,  # El nivel puede ser ajustado a ERROR, INFO, etc.
        handlers=[handler]
    )

    return logging.getLogger(name)


# ==================================================================
# Configuration
# ==================================================================
def load_config(config_path:str) -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"El archivo de configuración no existe: {config_path}")
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
        if not config:
            raise ValueError(f"El archivo de configuración está vacío o no es válido: {config_path}")
        
    return config
    
# ==================================================================
# Geolocation
# ==================================================================
def get_bouncing_box(latitude, longitude, radius_meters):
    earth_radius = 6371000  # metros
    delta_lat = radius_meters / earth_radius
    delta_lon = radius_meters / (earth_radius * cos(radians(latitude)))

    min_lat = latitude - (delta_lat * (180 / pi))
    max_lat = latitude + (delta_lat * (180 / pi))
    min_lon = longitude - (delta_lon * (180 / pi))
    max_lon = longitude + (delta_lon * (180 / pi))

    return {
        "min_latitude": min_lat,
        "max_latitude": max_lat,
        "min_longitude": min_lon,
        "max_longitude": max_lon
    }

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 # Radius of Earth in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (sin(dlat / 2) ** 2) + cos(radians(lat1)) * cos(radians(lat2)) * (sin(dlon / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
    