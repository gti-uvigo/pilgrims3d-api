import requests
import json
import base64
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth


def haversine_distance(start_points, end_points):
    """
    Calcula la distancia Haversine entre dos puntos geográficos.
    
    :param start_points: Coordenadas del punto de inicio (latitud, longitud).
    :param end_points: Coordenadas del punto final (latitud, longitud).
    :return: Distancia en kilómetros entre los dos puntos.
    """
    from math import radians, sin, cos, sqrt, atan2

    R = 6371.0  # Radio de la Tierra en kilómetros

    lat1 = radians(float(start_points[0]))
    lon1 = radians(float(start_points[1]))
    lat2 = radians(float(end_points[0]))
    lon2 = radians(float(end_points[1]))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance


def get_route(start_points,end_points,profile = "foot"):
    """
    Obtiene una ruta entre dos puntos dados.
    
    :param start_points: Punto de inicio de la ruta.
    :param end_points: Punto final de la ruta.
    :param profile: Modo de transporte (por defecto es "foot").
    :return: Ruta entre los puntos especificados.
    """
  
    lat_origin = float(start_points[0])
    lon_origin = float(start_points[1])
    lat_destination = float(end_points[0])
    lon_destination = float(end_points[1])


    # comprobamos si la distancia es mayor a 2km , si es devolvemos vacio
    if haversine_distance(start_points, end_points) > 2:
        return []

    url = 'http://193.146.210.248:8989/route'


    data = {
        "points": [
            [lon_origin, lat_origin],
            [lon_destination, lat_destination]
        ],
        "profile": profile,
        "ch.disable": True,
        "points_encoded": False,
        "custom_model": {
            "speed": [
                {
                    "if": "true",
                    "limit_to": "100"
                }
            ],
            "priority": [
                {
                    "if": "road_class == MOTORWAY",
                    "multiply_by": "0"
                }
            ],
            "distance_influence": 100
        }
    }

    response = requests.post(url, json=data)
    if response.status_code != 200 or "paths" not in response.text:
        print("hintsss", response.json()["hints"])
        if "PointDistanceExceededException" in response.json()["hints"]:
            data["profile"] = "car"
            response = requests.post(url, json=data)
            print("hintsss", response.json()["hints"])
        print("Error: 'paths' not found in response or bad status code")
        print("Ruta fuera de españa")
        return None
    points = response.json()["paths"][0]["points"]

    return points["coordinates"] if "coordinates" in points else points

def get_route_with_distance(start_points,end_points,profile = "foot"):
    """
    Obtiene una ruta entre dos puntos dados.
    
    :param start_points: Punto de inicio de la ruta.
    :param end_points: Punto final de la ruta.
    :param profile: Modo de transporte (por defecto es "foot").
    :return: Ruta entre los puntos especificados.
    """
  
    lat_origin = float(start_points[0])
    lon_origin = float(start_points[1])
    lat_destination = float(end_points[0])
    lon_destination = float(end_points[1])

    url = 'http://193.146.210.248:8989/route'


    data = {
        "points": [
            [lon_origin, lat_origin],
            [lon_destination, lat_destination]
        ],
        "profile": profile,
        "ch.disable": True,
        "points_encoded": False,
        "custom_model": {
            "speed": [
                {
                    "if": "true",
                    "limit_to": "100"
                }
            ],
            "priority": [
                {
                    "if": "road_class == MOTORWAY",
                    "multiply_by": "0"
                }
            ],
            "distance_influence": 100
        }
    }

    response = requests.post(url, json=data)
    if response.status_code != 200 or "paths" not in response.text:
        print("hintsss", response.json()["hints"])
        if "PointDistanceExceededException" in response.json()["hints"]:
            data["profile"] = "car"
            response = requests.post(url, json=data)
            print("hintsss", response.json()["hints"])
        print("Error: 'paths' not found in response or bad status code")
        print("Ruta fuera de españa")
        return None
    points = response.json()["paths"][0]["points"]

    return points["coordinates"] if "coordinates" in points else points, round(response.json()["paths"][0]["distance"]/1000, 2)



def base64StringToJpg(base64_string):
    """
    Convierte una cadena Base64 a un archivo JPG.
    
    :param base64_string: Cadena Base64 de la imagen.
    """
    return base64.b64decode(base64_string)




def delete_user_from_firebase(email):
    try:
        usuario = auth.get_user_by_email(email)
        print(f"Usuario encontrado: {usuario.uid} - {usuario.email}")
        uid = usuario.uid
        auth.delete_user(uid)
        print(f"El usuario con email '{email}' (UID: {uid}) ha sido eliminado exitosamente.")
        
    except auth.UserNotFoundError:
        print(f"Error: No se encontró ningún usuario con el email '{email}'.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")

