import json

with open("/home/moonpool/Downloads/pengluaran-app-93d0a57b75f0.json") as f:
    data = json.load(f)

with open(".streamlit/secrets.toml", "w") as f:
    f.write("[gcp_service_account]\n")
    for key, value in data.items():
        value_escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        f.write(f'{key} = "{value_escaped}"\n')

print("secrets.toml berhasil dibuat ulang dari JSON")

