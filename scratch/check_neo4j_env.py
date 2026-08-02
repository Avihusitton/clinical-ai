"""
Step 3 – Neo4j environment variable verification.
Prints ONLY whether each required var is present / has a value.
Never prints the actual URI, password, or username.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # parse manually
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

REQUIRED_VARS = {
    "NEO4J_URI": ["NEO4J_URI"],
    "NEO4J_USER_or_USERNAME": ["NEO4J_USERNAME", "NEO4J_USER"],
    "NEO4J_PASSWORD": ["NEO4J_PASSWORD"],
    "NEO4J_DATABASE": ["NEO4J_DATABASE"],
}

STAGING_DB_MARKERS = {"staging", "stage", "development", "dev", "test", "sandbox"}
STAGING_URI_MARKERS = {"staging", "stage", "dev", "test", "sandbox", "localhost", "127.0.0.1"}

def check_presence():
    results = {}
    for label, keys in REQUIRED_VARS.items():
        val = None
        found_key = None
        for k in keys:
            v = os.environ.get(k, "").strip()
            if v:
                val = v
                found_key = k
                break
        results[label] = {
            "present": bool(val),
            "key_name": found_key,
        }

    # Staging check — db name
    db_val = (os.environ.get("NEO4J_DATABASE", "") or "").lower()
    db_is_staging = any(m in db_val for m in STAGING_DB_MARKERS) if db_val else False

    # Staging check — URI host/path (no secrets printed)
    uri_val = (os.environ.get("NEO4J_URI", "") or "").lower()
    uri_is_staging = any(m in uri_val for m in STAGING_URI_MARKERS) if uri_val else False

    # Determine if database name can be reported safely (no credential)
    # Report only whether it contains a staging marker
    all_present = all(r["present"] for r in results.values())
    is_staging_target = db_is_staging or uri_is_staging

    print("=== NEO4J ENV CHECK ===")
    for label, info in results.items():
        print(f"  {label}: PRESENT={info['present']}, key={info['key_name']}")
    print(f"  db_value_contains_staging_marker: {db_is_staging}")
    print(f"  uri_value_contains_staging_marker: {uri_is_staging}")
    print(f"  all_credentials_present: {all_present}")
    print(f"  staging_target_verified: {is_staging_target}")

    # Determine final env status
    if not all_present:
        print("\nFINAL_ENV_STATUS: MISSING_CREDENTIALS")
    elif not is_staging_target:
        print("\nFINAL_ENV_STATUS: CANNOT_CONFIRM_STAGING")
    else:
        print("\nFINAL_ENV_STATUS: STAGING_CONFIRMED")

if __name__ == "__main__":
    check_presence()
