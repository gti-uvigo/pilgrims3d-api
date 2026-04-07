import base64
from io import BytesIO
from time import sleep
import requests
import torch
from deploy_models import moderate_text, load_model, unload_model, generate_text, generate_image_SD35, get_vram_free_mb

url = "https://rurallure-api.duckdns.org/"
url_dev = "https://rurallure-api-dev.duckdns.org/"



def create_poi(body):
    sleep_thread = True
    while sleep_thread:
        if get_vram_free_mb() < 20000.00:
            print("Esperando a que haya memoria GPU disponible...")
            sleep(30)
        else:
            sleep_thread = False

    print("Creando POI con los datos:", body)

    image = body.get('image', None)
    title = body.get('title', None)
    description = body.get('description', None)
    latitude = body.get('latitude', None)
    longitude = body.get('longitude', None)
    user_email = body.get('user_email', None)
    types = body.get('types', [])
    languages = body.get('languages', [])
    dev = body.get('dev_mode', True)


    if title or description:
        if title:
            moderation_result = moderate_text(title)
            if moderation_result.get("reject"):
                requests.post(url + "upload_poi_to_mongo", json={"status": "error", "message": "Title rejected by moderation","user_email":user_email},headers={"Content-Type":"application/json"})
                return False
        if description:
            moderation_result = moderate_text(description)
            if moderation_result.get("reject"):
                requests.post(url + "upload_poi_to_mongo", json={"status": "error", "message": "Description rejected by moderation","user_email":user_email},headers={"Content-Type":"application/json"})
                return False

    print("Cargando modelo para generación de texto e imagen...")

    load_model()

    if not title:
        prompt = f"Genera un título para un punto de interés con la descripción: {description}. El título debe ser breve y atractivo."
        title = generate_text(prompt)
        print("Título generado:", title)

    # Generar descripción si no existe
    if not description:
        prompt = f"Genera una descripción corta para un punto de interés con el título: {title}. La descripción debe ser breve y atractiva."
        description = generate_text(prompt)
        print("Descripción generada:", description)

    # Generar tipos si no existen
    if not types or len(types) == 0:
        prompt = f"Dime un tipo posible para un punto de interés con el título: {title} y la descripción: {description}. El tipo debe ser uno de los siguientes: restaurante, museo, parque, monumento, iglesia, playa, montaña, río, lago, bosque, ciudad, pueblo.Responde solo con el tipo, sin más texto."
        type_text = generate_text(prompt)
        types = [t.strip() for t in type_text.split(",")]  # convertir en lista
        print("Tipos generados:", types)

    titles = []
    descriptions_list = []

    for lang in languages:
        lang_id = lang['id']
        lang_name = lang['name']

        # Título
        prompt = f"Traduce el siguiente texto al {lang_name}: {title}"
        translated_title = generate_text(prompt)
        titles.append({"language_id": lang_id, "text": translated_title})
        print(f"Título traducido al {lang_name}:", translated_title)

        # Descripción
        prompt = f"Traduce el siguiente texto al {lang_name}: {description}"
        translated_description = generate_text(prompt)
        descriptions_list.append({"language_id": lang_id, "text": translated_description})
        print(f"Descripción traducida al {lang_name}:", translated_description)

    # descargamos el modelo
    unload_model()

    if not image:
        prompt = f"Genera una imagen para un punto de interés con el título: {title} y la descripción: {description}. La imagen debe ser atractiva y relevante."
        image = generate_image_SD35(prompt)
    
    # Check if image is already a base64 string or needs conversion
    if isinstance(image, str):
        img_base64 = image
    else:
        img_io = BytesIO()
        image.save(img_io, format='PNG')
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.read()).decode('utf-8')

    # Enviar datos al endpoint de subida
    poi_data = {
        "status": "success",
        "title": title,
        "description": description,
        "latitude": latitude,
        "longitude": longitude,
        "image": img_base64,
        "types": types,
        "titles": titles,
        "descriptions": descriptions_list,
        "user_email": user_email
    }

    if dev:
        response = requests.post(url_dev + "upload_poi_to_mongo", json=poi_data, headers={"Content-Type": "application/json"})
    else:
        response = requests.post(url + "upload_poi_to_mongo", json=poi_data, headers={"Content-Type": "application/json"})

    if response.status_code == 200:
        print("✅ POI subido correctamente.")
        return True
    else:
        print("❌ Error al subir el POI.")
        return False