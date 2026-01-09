import requests

for path in ['/api/models','/models','/api','/api/generate','/generate','/v1/models']:
    url='http://127.0.0.1:11434'+path
    try:
        r=requests.get(url, timeout=5)
        print(url, r.status_code)
        body = r.text
        print(body[:400])
    except Exception as e:
        print(url,'ERR',e)
