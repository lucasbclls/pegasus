import bcrypt
from flask import Flask, request, jsonify
import bcrypt
from database import get_connection  # Importa do arquivo database.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")

    if not email or not senha:
        return jsonify({"message": "Email e senha são obrigatórios."}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Usuario, Email, Senha FROM Register WHERE Email = ?", (email,))
    result = cursor.fetchone()
    conn.close()

    if result and bcrypt.checkpw(senha.encode('utf-8'), result[2].encode('utf-8')):
        nome, email_retornado, _ = result
        return jsonify({
            "usuario": {
                "nome": nome,
                "email": email_retornado,
                "avatar": None  # ou remova esse campo se quiser
            }
        }), 200
    else:
        return jsonify({"message": "Email ou senha incorretos."}), 401


if __name__ == "__main__":
    app.run(debug=True, port=5004)