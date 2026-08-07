import urllib.request, json
req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"Accept": "application/json"})
data = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
for m in data["data"]:
    if m["id"] in ["openai/gpt-5.6-luna-pro", "deepseek/deepseek-v4-pro", "deepseek/deepseek-chat"]:
        print(m["id"], float(m.get("pricing", {}).get("prompt", 0)) * 1000000)
