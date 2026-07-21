from config import Config
from llm_client import LLMClient

cfg = Config()
llm = LLMClient(cfg.openrouter_api_key, cfg.llm_model)

raw = (
    "דוגמה פיקטיבית בלבד: דנה כהן התקשרה מ-050-1234567. "
    "מספר הזהות לדוגמה הוא 123456789. "
    "בזמן הפעלה עולים רגשות בסיס והגנות."
)

clean = llm.deidentify(raw)
verdict = llm.verify_candidate(
    clean,
    "הפעלה",
    "מצב של עוררות רגשית שבו הגנות ותגובות אוטומטיות מקשות על קשר וראיית המהות."
)
modality = llm.classify_modality(clean)

print("ניקוי:")
print(clean)
print("אימות 'הפעלה':", verdict)
print("הקשר טיפולי:", modality)
