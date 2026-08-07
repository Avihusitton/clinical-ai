# -*- coding: utf-8 -*-
import json
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# We trust these prefixes for our production models
TRUSTED_PREFIXES = [
    "anthropic/claude-3.5",
    "meta-llama/llama-3",
    "deepseek/deepseek-",
    "mistralai/mistral-large",
    "mistralai/mistral-nemo",
    "google/gemini-pro",
    "google/gemini-flash",
    "moonshotai/kimi-",
    "openai/gpt-",
    "openai/o",
    "x-ai/grok-",
    "qwen/",
    "xiaomi/"
]

# Max price per 1K prompt tokens (USD)
FAST_PRICE_CAP = 0.0005 
PRO_PRICE_CAP = 0.005

class ModelRouter:
    """Dynamically fetches and selects the best Fast and Pro models from OpenRouter."""
    
    def __init__(self, refresh_interval_seconds: int = 86400):
        self.refresh_interval_seconds = refresh_interval_seconds
        self._cache: Dict[str, Any] = {
            "fast": {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3", "price": 0.00014},
            "pro": {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "price": 0.003},
            "last_updated": 0
        }
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start_background_refresh(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        
        # Trigger an initial synchronous update so it's ready immediately
        try:
            self.update_models()
        except Exception as e:
            print(f"Initial model update failed: {e}")
            
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def stop_background_refresh(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _refresh_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._stop_event.wait(self.refresh_interval_seconds):
                break
            try:
                self.update_models()
            except Exception as e:
                print(f"ModelRouter background refresh failed: {e}")

    def get_current_models(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "fast": self._cache["fast"],
                "pro": self._cache["pro"],
            }
            
    def get_model_id(self, category: str) -> str:
        """category is 'fast' or 'pro'. Default to pro if unknown."""
        with self._lock:
            if category == "fast":
                return self._cache["fast"]["id"]
            return self._cache["pro"]["id"]

    def update_models(self) -> None:
        """Fetches the latest models and selects the best ones."""
        req = urllib.request.Request(OPENROUTER_MODELS_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15.0) as response:
            data = json.loads(response.read().decode("utf-8"))
            
        models: List[Dict[str, Any]] = data.get("data", [])
        
        candidates = []
        for m in models:
            m_id = m.get("id", "")
            
            # Check if it's a trusted family
            is_trusted = any(m_id.startswith(p) for p in TRUSTED_PREFIXES)
            if not is_trusted:
                continue
                
            # Filter out experimental/beta/self-moderated models if there's a stable alternative
            if "beta" in m_id.lower() or "experimental" in m_id.lower() or "self-moderated" in m_id.lower():
                continue
                
            ctx = m.get("context_length", 0)
            if ctx < 16000:
                continue
                
            pricing = m.get("pricing", {})
            try:
                prompt_price = float(pricing.get("prompt", "999"))
            except (ValueError, TypeError):
                prompt_price = 999.0
                
            candidates.append({
                "id": m_id,
                "name": m.get("name", m_id),
                "context_length": ctx,
                "price": prompt_price * 1000  # Price per 1K tokens
            })
            
        if not candidates:
            return
            
        fast_candidates = [m for m in candidates if m["price"] <= FAST_PRICE_CAP]
        pro_candidates = [m for m in candidates if m["price"] <= PRO_PRICE_CAP]
        
        if not fast_candidates:
            fast_candidates = candidates
        if not pro_candidates:
            pro_candidates = candidates
            
        # For fast: prioritize lowest price primarily
        best_fast = min(fast_candidates, key=lambda x: x["price"])
        
        # For pro: prioritize top-tier capability, but within top-tier prioritize the CHEAPEST price
        def pro_score(m: Dict[str, Any]) -> float:
            score = 0
            name_lower = m["id"].lower()
            # Huge boost for models known for top-tier reasoning/capability
            if "pro" in name_lower or "opus" in name_lower or "large" in name_lower or "3.5-sonnet" in name_lower or "deepseek-r1" in name_lower or "deepseek-v4-pro" in name_lower or "deepseek-chat" in name_lower:
                score -= 100 
            
            # Secondarily prioritize lowest price (instead of context length)
            score += m["price"]
            return score
            
        best_pro = min(pro_candidates, key=pro_score)
        
        with self._lock:
            self._cache["fast"] = best_fast
            self._cache["pro"] = best_pro
            self._cache["last_updated"] = time.time()
