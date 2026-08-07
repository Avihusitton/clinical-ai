import requests, json

headers = {'Content-Type': 'application/json'}
t = requests.get('http://127.0.0.1:8765/api/therapists').json().get('therapists', [])
if not t:
    t = [requests.post('http://127.0.0.1:8765/api/therapists', json={'name':'Test'}).json()['therapist']]
tid = t[0]['id']

p = requests.get(f'http://127.0.0.1:8765/api/therapists/{tid}/patients').json().get('patients', [])
if not p:
    p = [requests.post(f'http://127.0.0.1:8765/api/therapists/{tid}/patients', json={'name':'Ron'}).json()['patient']]
pid = p[0]['id']

c = requests.post(f'http://127.0.0.1:8765/api/therapists/{tid}/patients/{pid}/conversations', json={'title':'שיחת רון'}).json()['conversation']
cid = c['id']

q = '''החוויה הפנימית של רון
עבור רון, העולם החברתי הוא שדה מוקשים פוטנציאלי.
הוא חי בפחד מתמיד משיפוט שלילי.
כל אינטראקציה, אפילו הפשוטה ביותר, מלווה בזרם בלתי פוסק של מחשבות ביקורתיות כלפי עצמו: "בטח אמרתי משהו טיפשי", "הם חושבים שאני מוזר", "אני משעמם אותם", "למה אני לא יכול להיות נורמלי כמו כולם?".
הוא צופה מראש תרחישים של מבוכה והשפלה ומפרש כל רמז ניטרלי או עמום כאישור לחששות.
המודעות העצמית שלו מוגברת באופן קיצוני; [והקשב מוטה פנימה]
במקום להשתלב זרימה החוצה.
הוא מרגיש שזרקור מסנוור מכוון אליו כל הזמן, בוחן'''

payload = {
    'therapist_id': tid,
    'patient_id': pid,
    'conversation_id': cid,
    'question': q,
    'use_ai': True,
    'auto_route': True,
    'confirmed_no_patient_data': True
}

resp = requests.post('http://127.0.0.1:8765/api/ask', json=payload, stream=True)
for line in resp.iter_lines():
    if line:
        data = json.loads(line.decode('utf-8'))
        if 'content' in data:
            print(data['content'], end='', flush=True)
