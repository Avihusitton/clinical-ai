# -*- coding: utf-8 -*-
"""
עטיפה אחידה לכל הקריאות למודל שפה (LLM) דרך OpenRouter.
ארבע המשימות (de-id, אימות מושג, סיווג הקשר טיפולי, סיווג קשר בין מושגים)
עוברות דרך אותה פונקציית תשתית _call() - מקום אחד לטפל בשגיאות ו-retries.

⚠️ מצב מוק (mock=True): כל התשובות מזויפות וקבועות, לבדיקת מבנה הקוד בלבד.
   אסור להשתמש בו על קבצים אמיתיים של מטופלים - הוא לא באמת מנקה פרטים
   מזהים. תמיד מדפיס אזהרה בלוג כדי שאי אפשר יהיה לפספס בטעות.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from pathlib import Path

import requests

log = logging.getLogger("llm_client")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    """כל כשל בקריאה למודל - רשת, מפתח חסר, תשובה לא תקינה."""


class LLMClient:
    def __init__(self, api_key: str, model: str, mock: bool = False,
                 timeout: int = 60, max_retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.mock = mock
        self.timeout = timeout
        self.max_retries = max_retries
        if self.mock:
            log.warning("LLMClient במצב MOCK - כל התשובות מזויפות. "
                        "אסור להריץ כך על קבצים אמיתיים של מטופלים.")

    def _increment_api_counter(self):
        status_file = Path("out/pipeline_status.json")
        if status_file.exists():
            try:
                import json
                with open(status_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["current_run_api_calls"] = data.get("current_run_api_calls", 0) + 1
                data["total_api_calls"] = data.get("total_api_calls", 0) + 1
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
            except Exception as e:
                log.warning(f"Failed to update API counter: {e}")

    def _call(self, system_prompt: str, user_prompt: str, mock_response: str) -> str:
        if self.mock:
            return mock_response
        if not self.api_key:
            raise LLMError(
                "אין מפתח OPENROUTER_API_KEY. הוסיפו אותו לקובץ .env, "
                "או הריצו עם --mock-llm על דאטה מזויפת בלבד לבדיקות."
            )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "reasoning": {"enabled": False},  # משימות סגורות - לא צריך חשיבה ארוכה, חוסך עלות
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = requests.post(OPENROUTER_URL, headers=headers,
                                      json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"].get("content")
                if content is None:
                    raise ValueError("API returned null content")
                self._increment_api_counter()
                return content.strip()
            except Exception as exc:  # noqa: BLE001 - תופסים הכל, מנסים שוב
                last_exc = exc
                log.warning("קריאת LLM נכשלה (ניסיון %d/%d): %s",
                            attempt, self.max_retries + 1, exc)
                if attempt <= self.max_retries:
                    time.sleep(1.5 * attempt)
        raise LLMError(f"קריאת LLM נכשלה אחרי {self.max_retries + 1} ניסיונות: {last_exc}")

    # ------------------------------------------------------------------
    # 1) De-identification - שער קשיח. אין ברירת מחדל בטוחה חוץ מלהיכשל.
    # ------------------------------------------------------------------
    def deidentify(self, text: str) -> str:
        system = (
            "אתה כלי אנונימיזציה לטקסטים קליניים בעברית. מחק/החלף כל פרט "
            "מזהה (שמות פרטיים, שמות משפחה, מקומות עבודה, שמות ישובים "
            "קטנים, מספרי טלפון, תעודות זהות) בתווית כללית כמו [שם], "
            "[מקום], [טלפון]. השאר את שאר הטקסט הקליני (התוכן התיאורטי, "
            "תיאור הסימפטומים, הדוגמה הקלינית עצמה) ללא שינוי. החזר אך ורק "
            "את הטקסט המנוקה, בלי הקדמות ובלי הערות."
        )
        return self._call(system, text, mock_response=text)

    # ------------------------------------------------------------------
    # 2) אימות בינארי של מועמד Entity Linking (שער ב')
    # ------------------------------------------------------------------
    def verify_candidate(self, chunk_text: str, canonical_name: str, definition: str) -> str:
        """מחזיר 'yes' / 'no' / 'unclear'."""
        system = (
            "אתה שופט מדויק לקישור מושגים בשיטת טיפול. תקבל קטע טקסט, שם "
            "מושג קנוני, והגדרתו. ענה אך ורק במילה אחת: yes אם הקטע באמת "
            "מתייחס למושג הזה כפי שהוגדר, no אם הוא לא מתייחס אליו, "
            "unclear אם אי אפשר לקבוע בביטחון. בלי הסברים."
        )
        user = (f"מושג קנוני: {canonical_name}\nהגדרה: {definition}\n\n"
                f"קטע הטקסט:\n{chunk_text}\n\nהאם הקטע מתייחס למושג הזה? "
                "ענה yes/no/unclear בלבד.")
        answer = self._call(system, user, mock_response="unclear").strip().lower()
        if answer not in ("yes", "no", "unclear"):
            log.warning("תשובת אימות לא צפויה: %r - מתייחסים כ-unclear", answer)
            return "unclear"
        return answer

    # ------------------------------------------------------------------
    # 3) סיווג הקשר טיפולי (פרטני / זוגי / משפחתי / כללי)
    # ------------------------------------------------------------------
    def classify_modality(self, chunk_text: str, doc_name: str = "") -> str:
        system = (
            "קרא את קטע הטקסט וקבע מהו ההקשר הטיפולי המדובר. ענה במילה "
            "אחת באנגלית בלבד: individual (טיפול פרטני), couples (טיפול "
            "זוגי), family (טיפול משפחתי), general (כללי / לא ניתן לקבוע)."
        )
        context_str = f"שם מסמך המקור: '{doc_name}'.\n\n" if doc_name else ""
        answer = self._call(system, context_str + chunk_text, mock_response="general").strip().lower()
        if answer not in ("individual", "couples", "family", "general"):
            log.warning("תשובת סיווג הקשר לא צפויה: %r - מתייחסים כ-general", answer)
            return "general"
        return answer

    # ------------------------------------------------------------------
    # 4) סיווג קשר תיאורטי בין שני מושגים (להשלמת הגרף התיאורטי)
    # ------------------------------------------------------------------
    def classify_relationship(self, concept_a: str, concept_b: str, chunk_text: str,
                               allowed_types: list[str]) -> Optional[str]:
        """
        מחזיר אחד מ-allowed_types, או None אם אין קשר קנוני ברור.
        הערה: זו הרחבה שהושלמה כדי לבנות בפועל את הקשרים התיאורטיים בין
        מושגים (is_symptom_of וכו') - פייבל וג'מיני קבעו את העיקרון (סט
        סגור + ברירת מחדל לשתיקה) אבל לא כתבו לזה קוד. כדאי לעבור על
        התוצאות הראשונות בעין ביקורתית.
        """
        options = ", ".join(allowed_types + ["none"])
        system = (
            "אתה שופט קפדני לקשרים תיאורטיים בשיטת טיפול. תקבל שני מושגים "
            "וקטע טקסט. קבע אם הטקסט קובע במפורש קשר קנוני בין המושגים "
            f"מתוך הרשימה הסגורה: {options}. אם הטקסט הוא רק דוגמה/מקרה "
            "ולא קביעה תיאורטית כללית, או שאין קשר ברור - ענה none. "
            "ענה במילה אחת בלבד."
        )
        user = f"מושג א': {concept_a}\nמושג ב': {concept_b}\n\nטקסט:\n{chunk_text}"
        answer = self._call(system, user, mock_response="none").strip().lower()
        if answer == "none":
            return None
        if answer not in [t.lower() for t in allowed_types]:
            log.warning("סוג קשר לא צפוי: %r - מתייחסים כאין-קשר", answer)
            return None
        return answer
