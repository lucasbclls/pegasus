from flask import Flask, jsonify
from flask_cors import CORS
import pyodbc
from datetime import datetime

app = Flask(__name__)
CORS(app)

def conectar_banco():
    return pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=localhost;'
        'DATABASE=powerbi;'
        'Trusted_Connection=yes;'
    )

def converter_data(data):
    if isinstance(data, datetime):
        return data.isoformat()
    return data

@app.route('/')
def index():
    return jsonify({"mensagem": "API de Chamados está no ar! Use /api/chamados para acessar os dados."})

@app.route('/api/chamados', methods=['GET'])
def listar_chamados():
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM dbo.[GRC-Chamados]")
    colunas = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    chamados = []
    for row in rows:
        d = dict(zip(colunas, row))

        chamado = {
            "id": d.get("ID"),
            "horaInicio": converter_data(d.get("Hora_inicio")),
            "horaConclusao": converter_data(d.get("Hora_conclusao")),
            "dataEvento": converter_data(d.get("Data_Evento")),
            "nomeSolicitante": d.get("Nome_solicitante"),
            "telefone": d.get("Telefone"),
            "emailSolicitante": d.get("Email_solicitante"),
            "empresa": d.get("Empresa"),
            "cidade": d.get("Cidade"),
            "tecnologia": d.get("Tecnologia"),
            "servicoAfetado": d.get("Servico_afetado"),
            "baseAfetada": d.get("Base_afetada"),
            "nodeAfetadas": d.get("Node_afetadas"),
            "contratosAfetados": d.get("Contratos_afetados"),
            "tipoReclamacao": d.get("Tipo_reclamacao"),
            "detalhesProblema": d.get("Detalhes_problema"),
            "testesRealizados": d.get("Testes_realizados"),
            "modelEquipamento": d.get("Model_equipamento"),
        }
        chamados.append(chamado)

    conn.close()
    return jsonify(chamados)

if __name__ == '__main__':
    app.run(port=5001)
