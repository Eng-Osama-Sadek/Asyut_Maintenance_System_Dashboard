import requests
from config import Config

key = Config.GEMINI_API_KEY
print('???????:', key[:10] + '...' if key else '??? ?????')

r = requests.get(f'https://generativelanguage.googleapis.com/v1beta/models?key={key}')
print('Status:', r.status_code)

if r.status_code == 200:
    models = r.json().get('models', [])
    for m in models:
        print(m['name'])
else:
    print(r.text[:500])