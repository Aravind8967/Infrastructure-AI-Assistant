import json
import os
import psycopg2
import logging
import requests
from psycopg2.extras import execute_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("incident_backend.load_data")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "incident_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "postgres123"),
}

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(SCRIPT_DIR, "incident_management_500.json")
if not os.path.exists(JSON_FILE):
    JSON_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "incident_management_500.json")


def build_document_text(incident):
    return f"""
Incident ID: {incident["incident_id"]}

Problem:
{incident["short_description"]}

Description:
{incident["description"]}

Category:
{incident["category"]}

Subcategory:
{incident["subcategory"]}

Assignment Group:
{incident["assignment_group"]}

Service:
{incident["service"]}

Criticality:
{incident["criticality_description"]}

State:
{incident["state"]}

Root Cause:
{incident["root_cause_analysis"] or "Not available"}

Resolution:
{incident["resolution"] or "Not available"}
""".strip()


def load_json():
    logger.info(f"Reading incident JSON data from: {JSON_FILE}")
    with open(JSON_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "incidents" not in data:
        raise ValueError("JSON does not contain an 'incidents' field")

    incidents = data["incidents"]
    if not isinstance(incidents, list):
        raise ValueError("'incidents' must be a list")

    return data, incidents


def validate_incident(incident):
    required_fields = [
        "incident_id", "short_description", "description", "category",
        "subcategory", "assignment_group", "assigned_to", "criticality",
        "criticality_description", "state", "opened_at", "closed_at",
        "opened_by", "closed_by", "resolution", "root_cause_analysis", "service",
    ]
    for field in required_fields:
        if field not in incident:
            raise ValueError(f"Incident {incident.get('incident_id')} missing field: {field}")


def prepare_incident(incident):
    validate_incident(incident)
    document_text = build_document_text(incident)
    return (
        incident["incident_id"], incident["short_description"], incident["description"],
        incident["category"], incident["subcategory"], incident["assignment_group"],
        incident["assigned_to"], incident["criticality"], incident["criticality_description"],
        incident["state"], incident["opened_at"], incident["closed_at"],
        incident["opened_by"], incident["closed_by"], incident["resolution"],
        incident["root_cause_analysis"], incident["service"], document_text,
    )


def insert_incidents(incidents):
    logger.info(f"Connecting to database at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    connection = psycopg2.connect(**DB_CONFIG)

    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO incident.incidents (
                incident_id, short_description, description, category, subcategory,
                assignment_group, assigned_to, criticality, criticality_description,
                state, opened_at, closed_at, opened_by, closed_by, resolution,
                root_cause_analysis, service, document_text
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (incident_id) DO NOTHING;
        """

        rows = [prepare_incident(inc) for inc in incidents]
        execute_batch(cursor, query, rows, page_size=100)
        connection.commit()
        logger.info(f"Successfully processed {len(rows)} incidents into database.")
    except Exception as e:
        connection.rollback()
        logger.error(f"Failed to insert incidents: {e}")
        raise
    finally:
        cursor.close()
        connection.close()


def generate_and_store_embeddings():
    logger.info(f"Checking for incidents requiring embeddings via Ollama ({OLLAMA_URL})...")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("SELECT incident_id, document_text FROM incident.incidents WHERE embedding IS NULL;")
        rows = cur.fetchall()
        logger.info(f"Found {len(rows)} incidents needing vector embeddings.")

        if not rows:
            logger.info("All incidents already have embeddings.")
            return

        success_count = 0
        for incident_id, doc_text in rows:
            try:
                res = requests.post(
                    f"{OLLAMA_URL}/api/embed",
                    json={"model": EMBEDDING_MODEL, "input": doc_text},
                    timeout=120
                )
                res.raise_for_status()
                embedding = res.json()["embeddings"][0]

                cur.execute(
                    "UPDATE incident.incidents SET embedding = %s WHERE incident_id = %s;",
                    (embedding, incident_id)
                )
                conn.commit()
                success_count += 1
                if success_count % 50 == 0 or success_count == len(rows):
                    logger.info(f"Generated and saved embeddings: {success_count}/{len(rows)}")
            except Exception as e:
                logger.warning(f"Could not generate embedding for {incident_id}: {e}")

        logger.info(f"Completed embedding generation for {success_count} incidents.")
    finally:
        conn.close()


def main():
    print("==================================================")
    print("      INCIDENT MANAGER DATA LOADING UTILITY      ")
    print("==================================================")
    dataset, incidents = load_json()
    logger.info(f"Dataset Name: {dataset['dataset_name']}")
    logger.info(f"Expected Records: {dataset['record_count']}")

    insert_incidents(incidents)

    # Ask or attempt embedding generation
    try:
        generate_and_store_embeddings()
    except Exception as e:
        logger.warning(f"Embedding generation step skipped/failed: {e}")
        logger.info("You can generate embeddings later when Ollama is running.")

    print("\n✅ Incident data loading completed successfully!")


if __name__ == "__main__":
    main()
