import requests
import psycopg2


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text:latest"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "incident_db",
    "user": "postgres",
    "password": "postgres123",
}


# ============================================================
# STEP 1: GET ONE INCIDENT FROM POSTGRESQL
# ============================================================

def get_incident():

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    incident_id,
                    document_text
                FROM incident.incidents
                WHERE embedding IS NULL
                ORDER BY incident_id
                LIMIT 1;
            """)

            row = cur.fetchone()

            if row is None:
                return None

            return {
                "incident_id": row[0],
                "document_text": row[1]
            }

    finally:
        conn.close()


# ============================================================
# STEP 2: SEND TEXT TO OLLAMA
# ============================================================

def generate_embedding(text):

    url = f"{OLLAMA_URL}/api/embed"

    payload = {
        "model": EMBEDDING_MODEL,
        "input": text
    }

    response = requests.post(
        url,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["embeddings"][0]


# ============================================================
# STEP 3: STORE EMBEDDING IN POSTGRESQL
# ============================================================

def store_embedding(incident_id, embedding):

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:

            cur.execute("""
                UPDATE incident.incidents
                SET embedding = %s
                WHERE incident_id = %s;
            """, (
                embedding,
                incident_id
            ))

        conn.commit()

    finally:
        conn.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print("Getting one incident from database...")

    incident = get_incident()

    if incident is None:
        print("No incident found without an embedding.")
        return

    print(f"----------------- Incident ID: {incident['incident_id']} ---------------------")

    print("\nGenerating embedding using Ollama...")

    embedding = generate_embedding(
        incident["document_text"]
    )

    print(f"Embedding generated.")
    print(f"Vector dimensions: {len(embedding)}")

    print("\nFirst 5 values:")
    print(embedding[:5])

    print("\nLast 5 values:")
    print(embedding[-5:])

    print("\nStoring embedding in PostgreSQL...")

    store_embedding(
        incident["incident_id"],
        embedding
    )

    print(
        f"Embedding successfully stored for "
        f"{incident['incident_id']}"
    )

    print('------------------------------------------------------------------------------')


if __name__ == "__main__":
    
    for i in range(483):
        main()