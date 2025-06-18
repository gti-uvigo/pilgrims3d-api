import requests
import json


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
        print("Error: 'paths' not found in response or bad status code")
        print("Ruta fuera de españa")
        return None
    points = response.json()["paths"][0]["points"]

    return points["coordinates"] if "coordinates" in points else points
