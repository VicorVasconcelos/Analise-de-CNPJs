import csv
import os
import requests

payload = {
    "uf": "DF",
    "cnae": "9602501",
    "situacao_cadastral": "02",
}

resp = requests.post("http://localhost:5000/export", json=payload, timeout=220)
print("status", resp.status_code)
data = resp.json()
print("response_keys", sorted(data.keys()))
print("error", data.get("error"))
print("message", data.get("message"))
print("filename", data.get("filename"))

if resp.status_code == 200 and data.get("filename") and os.path.exists(data["filename"]):
    with open(data["filename"], "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader, [])
        row = next(reader, [])
    idx_nome = header.index("NOME_SOCIO") if "NOME_SOCIO" in header else -1
    idx_qual = header.index("QUALIFICACAO_SOCIO") if "QUALIFICACAO_SOCIO" in header else -1
    idx_cpf = header.index("CPF_SOCIO") if "CPF_SOCIO" in header else -1
    print("socios_header_ok", idx_nome >= 0 and idx_qual >= 0 and idx_cpf >= 0)
    if row:
        print("sample_nome_socio", row[idx_nome] if idx_nome >= 0 else None)
        print("sample_qualificacao_socio", row[idx_qual] if idx_qual >= 0 else None)
        print("sample_cpf_socio", row[idx_cpf] if idx_cpf >= 0 else None)
