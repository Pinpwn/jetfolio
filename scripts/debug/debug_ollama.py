import requests
import json
import sys

url = "http://127.0.0.1:8888/api/create"
headers = {"Content-Type": "application/json"}

# Minimal modelfile
modelfile = "FROM /root/.ollama/Qwen3-4B-Q4_K_M.gguf"

payload = {
    "name": "qwen3",
    "modelfile": modelfile
}

print(f"Sending request to {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    with requests.post(url, json=payload, stream=True) as resp:
        print(f"Response Status: {resp.status_code}")
        if resp.status_code != 200:
             print(f"Error Content: {resp.text}")
             sys.exit(1)
             
        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                print(f"Progress: {data.get('status')}")
                if 'error' in data:
                    print(f"Ollama Error: {data['error']}")

except Exception as e:
    print(f"Exception: {e}")
