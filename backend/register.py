from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from database import get_connection  # Importa do arquivo database.py

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])
bcrypt = Bcrypt(app)

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    usuario = data.get("usuario")
    senha = data.get("senha")

    if not all([email, usuario, senha]):
        return jsonify({"message": "Todos os campos são obrigatórios."}), 400


    senha_hash = bcrypt.generate_password_hash(senha).decode("utf-8")

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Register (Email, Usuario, Senha)
            VALUES (?, ?, ?)
        """, (email, usuario, senha_hash))
        conn.commit()
        return jsonify({"message": "Usuário registrado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"message": f"Erro ao registrar: {str(e)}"}), 400
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, port=5003)
