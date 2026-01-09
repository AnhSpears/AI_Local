import requests

try:
    r = requests.get('http://127.0.0.1:11434/api/models', timeout=5)
    print('STATUS', r.status_code)
    print(r.text[:2000])
except Exception as e:
    print('ERR', e)
