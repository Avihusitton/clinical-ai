import requests
import json
import sys

tid = requests.get('http://127.0.0.1:8765/api/therapists').json().get('therapists')[0]['id']
pid = requests.get(f'http://127.0.0.1:8765/api/therapists/{tid}/patients').json().get('patients')[0]['id']
c = requests.post(f'http://127.0.0.1:8765/api/therapists/{tid}/patients/{pid}/conversations', json={'title':'שיחת רון 4'}).json()['conversation']
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
ans = ""
for line in resp.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        try:
            d = json.loads(decoded)
            if 'answer_text' in d:
                ans = d['answer_text']
        except:
            pass

with open('scratch/valid_answer.md', 'w', encoding='utf-8') as f:
    f.write(ans)
print("Done!")
