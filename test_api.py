import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:8765/api/therapists', data=b'{"name":"Dr. Test"}', headers={'Content-Type': 'application/json'}, method='POST')
res = urllib.request.urlopen(req)
thr = json.loads(res.read())
print('Therapist:', thr)

thr_id = thr.get('id', thr.get('therapist', {}).get('id'))
print('Thr ID:', thr_id)

req2 = urllib.request.Request(f'http://127.0.0.1:8765/api/therapists/{thr_id}/patients', data=b'{"name":"Test Patient"}', headers={'Content-Type': 'application/json'}, method='POST')
res2 = urllib.request.urlopen(req2)
pat = json.loads(res2.read())
print('Patient:', pat)
