import requests

# Dados de autenticação e configuração
api_key = "df3745b4f0356e84781e4254d109efd3e31e0eb6"
issue_id = 37462  # ID do chamado a ser concluído
url = f"http://187.36.193.239/redmine/issues/{issue_id}.json"

# Cabeçalhos da requisição
headers = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": api_key
}

# Corpo da requisição para concluir o chamado
payload = {
    "issue": {
        "status_id": 5,       # ID do status "Concluído"
        "done_ratio": 100     # Percentual de conclusão
    }
}

# Requisição PUT para atualizar o chamado
response = requests.put(url, headers=headers, json=payload)

# Exibe o resultado
print(f"Status: {response.status_code}")
print("Resposta:", response.text)
