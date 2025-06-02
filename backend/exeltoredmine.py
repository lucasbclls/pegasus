import pandas as pd
import pyodbc
from datetime import datetime
import re
import requests
import json

# Configurações
EXCEL_PATH = r'C:\Users\Paulo Lucas\OneDrive - Claro SA\USER-DTC_HE_INFRA - ES - Documentos\Acionamento Datacenter_Headend ES1.xlsx'
ABA = 'Sheet1'

# Redmine
REDMINE_URL = "http://187.36.193.239/redmine/issues.json"
REDMINE_API_KEY = "df3745b4f0356e84781e4254d109efd3e31e0eb6"
HEADERS = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": REDMINE_API_KEY
}

# Mapeamento da planilha
MAPEAMENTO_COLUNAS = {
    'id': 'ID',
    'hora de início': 'Hora_inicio',
    'hora de conclusão': 'Hora_conclusao',
    'data do evento': 'Data_Evento',
    'nome do solicitante': 'Nome_solicitante',
    'telefone': 'Telefone',
    'e-mail do solicitante': 'Email_solicitante',
    'empresa': 'Empresa',
    'cidade': 'Cidade',
    'tecnologia': 'Tecnologia',
    'serviço afetado': 'Servico_afetado',
    'base afetada': 'Base_afetada',
    'node(s)/nap(s) afetadas': 'Node_afetadas',
    'contratos afetados': 'Contratos_afetados',
    'tipo de reclamação do cliente': 'Tipo_reclamacao',
    'descreva detalhes do problema (sintomas das reclamações)': 'Detalhes_problema',
    'descreva os testes que foram realizados no cliente': 'Testes_realizados',
    'modelo do equipamento afetado': 'Model_equipamento',
    'status': 'Status'  # importante!
}

def normalizar_coluna(nome):
    return re.sub(r'[:\s]+$', '', nome.strip().lower())

def conectar_banco():
    return pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=localhost;'
        'DATABASE=powerbi;'
        'Trusted_Connection=yes;'
    )

def criar_chamado_redmine(linha):
    payload = {
        "issue": {
            "project_id": 13,
            "tracker_id": 5,
            "status_id": 2,
            "priority_id": 2,
            "assigned_to_id": 10,
            "subject": f"{linha['Servico_afetado']} - {linha['Cidade']}",
            "description": linha['Detalhes_problema'] or "Sem descrição detalhada",
            "start_date": linha['Data_Evento'].strftime('%Y-%m-%d'),
            "due_date": linha['Data_Evento'].strftime('%Y-%m-%d'),
            "done_ratio": 0,
            "custom_fields": [
                {"id": 2, "value": [linha['Cidade']]},
                {"id": 3, "value": "Sem impacto"},
                {"id": 13, "value": linha.get('Base_afetada', "")},
                {"id": 14, "value": ["34"]},
                {"id": 21, "value": "31"},
                {"id": 22, "value": str(linha['ID'])},
                {"id": 24, "value": linha.get('Node_afetadas', "")},
                {"id": 28, "value": linha['Hora_inicio'].strftime('%H:%M') if pd.notna(linha['Hora_inicio']) else "00:00"},
                {"id": 29, "value": linha['Hora_conclusao'].strftime('%H:%M') if pd.notna(linha['Hora_conclusao']) else "00:00"},
            ]
        }
    }

    response = requests.post(REDMINE_URL, headers=HEADERS, json=payload)
    print(f"Redmine → Status: {response.status_code}")
    if response.status_code == 201:
        print("✅ Chamado criado com sucesso.")
    else:
        print(f"❌ Erro ao criar chamado: {response.text}")

def importar_dados():
    conn = conectar_banco()
    cursor = conn.cursor()

    df = pd.read_excel(EXCEL_PATH, sheet_name=ABA)
    df.columns = [normalizar_coluna(col) for col in df.columns]

    colunas_faltando = [col for col in MAPEAMENTO_COLUNAS if col not in df.columns]
    if colunas_faltando:
        print(f"❌ Colunas faltando: {colunas_faltando}")
        return

    df = df[list(MAPEAMENTO_COLUNAS.keys())]
    df.rename(columns=MAPEAMENTO_COLUNAS, inplace=True)

    pendentes = df[df['Status'].str.lower() == 'pendente']

    for i, row in pendentes.iterrows():
        valores = [row[col] if not pd.isna(row[col]) else None for col in df.columns]
        placeholders = ", ".join("?" for _ in df.columns)
        colunas_sql = ", ".join(f"[{col}]" for col in df.columns)

        try:
            cursor.execute(f"""
                INSERT INTO dbo.[GRC-Chamados] ({colunas_sql})
                VALUES ({placeholders})
            """, *valores)
            print(f"📥 Inserido no banco ID={row['ID']}")
            criar_chamado_redmine(row)
        except Exception as e:
            print(f"❌ Erro ao inserir/mandar chamado ID={row['ID']}: {e}")

    conn.commit()
    conn.close()
    print("✅ Processo concluído.")

importar_dados()



