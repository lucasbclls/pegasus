import requests

# Parâmetros
api_key = "df3745b4f0356e84781e4254d109efd3e31e0eb6"
issue_id = 37462  # ID do chamado que você quer editar
url = f"http://187.36.193.239/redmine/issues/{issue_id}.json"

# Headers com autenticação
headers = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": api_key
}

# Dados que serão atualizados
payload = {
    "issue": {
        "subject": "Chamado atualizado via Python",
        "description": "Descrição editada automaticamente com sucesso.",
        "priority_id": 3  # Exemplo: Alta prioridade (confirme os IDs no seu Redmine)
    }
}

# Envia requisição PUT
response = requests.put(url, headers=headers, json=payload)

# Mostra resultado
print(f"Status: {response.status_code}")
print("Resposta:", response.text)
