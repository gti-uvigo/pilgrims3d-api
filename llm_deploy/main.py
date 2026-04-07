from flask import Flask, request, jsonify, abort
from deploy_models import generate_text, load_model, unload_model, ensure_model, generate_image_SD35, moderate_text
from io import BytesIO
import base64
from redis import Redis
from rq import Queue
from tasks import create_poi # Importamos nuestra tarea

app = Flask(__name__)
ALLOWED_IPS = {"193.146.210.248"}  

# Conexión a Redis (localhost, puerto 6379)
redis_conn = Redis(host='redisRurallure', port=6379)
# Creamos una cola 'llms'
q = Queue('llms', connection=redis_conn)

@app.before_request
def limit_remote_addr():
    print(request.remote_addr)
    if request.remote_addr not in ALLOWED_IPS:
        abort(403)

@app.route("/generate_poi",methods=["POST"])
def generate_poi_route():
    body = request.get_json() 
    job = q.enqueue(create_poi, body)

    if job:
        return jsonify({"job_id": job.get_id()}), 200
    else:
        return jsonify({"error": "Failed to enqueue job"}), 500

@app.route('/generate_text', methods=['POST'])
def generate_text_route():
    print("Generating text...")
    body = request.json
    prompt = body.get("prompt", "testtt")
    result = generate_text(prompt)
    return jsonify({"text": result})

@app.route('/load_model', methods=['GET'])
def load_model_route():
    response = load_model()
    if not response:
        return jsonify({"error": "Failed to load model"}), 500
    return jsonify({"status": "Model loaded successfully"})

@app.route('/unload_model', methods=['GET'])
def unload_model_route():
    unload_model()
    return jsonify({"status": "Model unloaded successfully"})

@app.route('/generate_image', methods=['POST'])
def generate_image_route():
    data = request.json
    prompt = data.get("prompt", "")
    image = generate_image_SD35(prompt)
    if image is None:
        return jsonify({"error": "No prompt provided"}), 400
    img_io = BytesIO()
    image.save(img_io, format='PNG')
    img_io.seek(0)
    img_base64 = base64.b64encode(img_io.read()).decode('utf-8')

    return jsonify({"image_base64": img_base64})

@app.route("/moderate_text", methods=["POST"])
def moderate_text_route():
    text = request.json.get("text")
    print("Moderating text...")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    result = moderate_text(text)
    if result["reject"]:
        return jsonify({"error": "Text not allowed", "scores": result["scores"]}), 403

    return jsonify({"ok": True, "scores": result["scores"]})

if __name__ == '__main__':
    ensure_model()
    app.run(host='0.0.0.0', port=5050)