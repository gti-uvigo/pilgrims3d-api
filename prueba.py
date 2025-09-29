from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import datetime

app = Flask(__name__)

# Configuración básica
app.config["JWT_SECRET_KEY"] = "super-secret-key"
jwt = JWTManager(app)

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)

# ===== RUTA PARA CREAR TOKENS PERSONALIZADOS =====
@app.route("/generate-token", methods=["POST"])
def generate_token():
    """
    Espera un JSON como:
    {
        "expires_minutes": 30,
        "rate_limit": "5 per minute"
    }
    """
    data = request.get_json()
    expires_minutes = data.get("expires_minutes", 15)
    rate_limit = data.get("rate_limit", "10 per minute")

    # Genera un token con claims personalizados
    additional_claims = {
        "rate_limit": rate_limit
    }

    access_token = create_access_token(
        identity="custom_user",
        additional_claims=additional_claims,
        expires_delta=datetime.timedelta(minutes=expires_minutes)
    )

    return jsonify(access_token=access_token)


# ===== RUTA PROTEGIDA CON RATE LIMIT DINÁMICO =====
@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    claims = get_jwt()
    rate_limit = claims.get("rate_limit", "5 per minute")

    # Aplica rate limit dinámico
    @limiter.limit(rate_limit)
    def inner():
        return jsonify(msg=f"Acceso concedido con límite {rate_limit}")

    return inner()


if __name__ == "__main__":
    app.run(debug=True)
