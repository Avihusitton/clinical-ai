import urllib.request, json
req = urllib.request.Request('https://openrouter.ai/api/v1/models', headers={'Accept': 'application/json'})
data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
print("=== CHEAP MODELS ===")
cheap = []
for m in data['data']:
    p = m.get('pricing', {})
    pmt = float(p.get('prompt', 0))*1000000
    comp = float(p.get('completion', 0))*1000000
    if pmt <= 0.15 and pmt > 0.0001:
        cheap.append((pmt, m['id'], comp))
cheap.sort()
for pmt, mid, comp in cheap[:10]:
    print(f"{mid} - In: ${pmt:.3f} / Out: ${comp:.3f}")

print("=== DEEPSEEK & GPT ===")
for m in data['data']:
    if m['id'] in ['openai/gpt-5.6-luna-pro', 'deepseek/deepseek-v4-pro', 'deepseek/deepseek-chat', 'deepseek/deepseek-r1']:
        p = m.get('pricing', {})
        pmt = float(p.get('prompt', 0))*1000000
        comp = float(p.get('completion', 0))*1000000
        print(f"{m['id']} - In: ${pmt:.3f} / Out: ${comp:.3f}")
