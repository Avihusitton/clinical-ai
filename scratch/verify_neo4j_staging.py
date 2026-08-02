"""
Neo4j staging connectivity test — read-only, no writes.
Checks connection and verifies staging/development target.
Never prints credentials, URI with passwords, or any secrets.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import neo4j

STAGING_DB_MARKERS = {"staging", "stage", "development", "dev", "test", "sandbox"}
STAGING_URI_MARKERS = {"staging", "stage", "dev", "test", "sandbox", "localhost", "127.0.0.1"}

def verify_staging():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")  # default

    # Staging check — never print URI
    uri_lower = uri.lower()
    db_lower = database.lower()
    uri_is_staging = any(m in uri_lower for m in STAGING_URI_MARKERS)
    db_is_staging = any(m in db_lower for m in STAGING_DB_MARKERS)
    db_name = database  # safe to report (no credentials)

    print("=== NEO4J STAGING CONNECTIVITY TEST ===")
    print(f"  NEO4J_URI configured: True (hidden)")
    print(f"  NEO4J_USER configured: {bool(user)}")
    print(f"  NEO4J_PASSWORD configured: {bool(password)}")
    print(f"  NEO4J_DATABASE configured: {bool(os.environ.get('NEO4J_DATABASE'))}")
    print(f"  NEO4J_DATABASE effective value: {db_name}")
    print(f"  URI contains staging/local marker: {uri_is_staging}")
    print(f"  DATABASE name contains staging marker: {db_is_staging}")

    # Default neo4j database is not "staging" by name — but localhost URI is staging
    is_staging_target = uri_is_staging or db_is_staging

    print(f"  staging_target_verified: {is_staging_target}")

    if not is_staging_target:
        print("\nFINAL_ENV_STATUS: BLOCKED_PRODUCTION_DATABASE_TARGET")
        return None

    # Test connectivity (read-only)
    driver = None
    try:
        driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("\nCONNECTIVITY: SUCCESS")

        with driver.session(database=database) as session:
            result = session.run("RETURN 1 AS ping")
            val = result.single()["ping"]
            print(f"PING: {val}")

            # Get db info
            try:
                db_info = session.run("CALL db.info()").data()
                db_name_from_db = db_info[0].get("name", db_name) if db_info else db_name
                print(f"DB name from server: {db_name_from_db}")
                db_lower = db_name_from_db.lower()
                db_is_staging = any(m in db_lower for m in STAGING_DB_MARKERS)
                print(f"SERVER DB staging marker: {db_is_staging}")
            except Exception as e:
                print(f"db.info() unavailable: {e}")
                db_name_from_db = database

        print(f"\nFINAL_ENV_STATUS: STAGING_CONFIRMED")
        print(f"STAGING_DATABASE_NAME: {db_name_from_db}")
        return db_name_from_db

    except Exception as e:
        print(f"\nCONNECTIVITY: FAILED — {type(e).__name__}: {e}")
        print("FINAL_ENV_STATUS: BLOCKED_STAGING_CONNECTION_FAILED")
        return None
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    verify_staging()
