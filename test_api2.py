import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:8765/api/therapists', data=b'{"name":"Dr. Test"}', headers={'Content-Type': 'application/json'}, method='POST')
res = urllib.request.urlopen(req)
thr = json.loads(res.read())
thr_id = thr.get('id', thr.get('therapist', {}).get('id'))

req2 = urllib.request.Request(f'http://127.0.0.1:8765/api/therapists/{thr_id}/patients', data=b'{"name":"Test Patient"}', headers={'Content-Type': 'application/json'}, method='POST')
res2 = urllib.request.urlopen(req2)
pat = json.loads(res2.read())
pat_id = pat.get('id', pat.get('patient', {}).get('id'))

req3 = urllib.request.Request(f'http://127.0.0.1:8765/api/therapists/{thr_id}/patients')
res3 = urllib.request.urlopen(req3)
pats = json.loads(res3.read())
print('Patients GET:', pats)
print('Is in list:', any(p.get('id') == pat_id for p in pats.get('patients', [])))
