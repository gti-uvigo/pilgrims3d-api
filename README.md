# rurallure-api

API para la gestión de rutas, puntos de interés e imágenes usando Flask y MongoDB.

## Requisitos

- Python 3.12
- MongoDB
- pip

## Instalación

1. **Clona el repositorio:**
   ```sh
   git clone <URL-del-repositorio>
   cd rurallure-api
   ```

2. **Crea un entorno virtual:**
   ```sh
   python3 -m venv env
   source env/bin/activate
   ```

3. **Instala las dependencias:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Crea el archivo `.env` en la raíz del proyecto con el siguiente contenido:**
   ```
   MONGO_URI=<tu_mongo_uri>
   MONGO_USERNAME=<tu_usuario>
   MONGO_PASSWORD=<tu_contraseña>
   MONGO_AUTH_SOURCE=admin
   DB_NAME=<nombre_de_tu_db>
   ```

## Uso

1. **Inicia la aplicación:**
   ```sh
   flask run
   ```
   O bien:
   ```sh
   python app.py
   ```

## Notas

- Asegúrate de tener el archivo `.env` correctamente configurado antes de iniciar la aplicación.
- El entorno virtual (`env/`) y el archivo `.env` están en `.gitignore` y no deben subirse al repositorio.