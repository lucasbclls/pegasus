import requests
import json

url = "http://187.36.193.239/redmine/issues.json"
api_key = "df3745b4f0356e84781e4254d109efd3e31e0eb6"

headers = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": api_key
}

payload = {
    "issue": {
        "project_id": 13,
        "tracker_id": 5,
        "status_id": 2,
        "priority_id": 2,
        "assigned_to_id": 10,
        "subject": "Teste local via Python",
        "description": "Chamado gerado automaticamente em teste local.",
        "start_date": "2025-05-23",
        "due_date": "2025-05-23",
        "done_ratio": 0,
        "custom_fields": [
            {"id": 2, "value": ["VTA"]},
            {"id": 3, "value": "Sem impacto"},
            {"id": 13, "value": ""},
            {"id": 14, "value": ["34"]},
            {"id": 21, "value": "31"},
            {"id": 22, "value": "99999999"},
            {"id": 24, "value": ""},
            {"id": 28, "value": "10:00"},
            {"id": 29, "value": "10:30"}
        ]
    }
}

response = requests.post(url, headers=headers, json=payload)
print("Status:", response.status_code)
print("Resposta:", response.text)
