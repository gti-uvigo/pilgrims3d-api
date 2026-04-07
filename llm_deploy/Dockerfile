FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

RUN apt-get update && apt-get install -y python3.10 python3.10-distutils python3-pip git build-essential
# RUN apt-get update && apt-get install -y python3 python3-pip git build-essential
# Establecemos directorio de trabajo
WORKDIR /app

# Copiamos requirements y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Descargamos el modelo desde Hugging Face
RUN huggingface-cli login --token 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

RUN mkdir -p /models/Qwen3-8B
RUN huggingface-cli download Qwen/Qwen3-8B --local-dir /models/Qwen3-8B --local-dir-use-symlinks False
RUN mkdir -p /models/stable-diffusion-3.5-m
RUN huggingface-cli download stabilityai/stable-diffusion-3.5-medium --local-dir /models/stable-diffusion-3.5-m --local-dir-use-symlinks False
RUN mkdir -p /models/shieldgemma-2-4b-it
RUN huggingface-cli download google/shieldgemma-2-4b-it --local-dir /models/shieldgemma-2-4b-it --local-dir-use-symlinks False
RUN mkdir -p /models/shieldgemma-9b
RUN huggingface-cli download google/shieldgemma-9b --local-dir /models/shieldgemma-9b --local-dir-use-symlinks False
RUN pip install flash-attn --no-build-isolation --no-cache-dir -f https://flash-attn.pages.dev/whl/torch280cu128.html
RUN pip install git+https://github.com/huggingface/diffusers.git

# Copiamos la app
COPY . .



# Exponemos el puerto que usará Flask
EXPOSE 5050

# Comando para ejecutar la app
CMD ["python3", "main.py"]
