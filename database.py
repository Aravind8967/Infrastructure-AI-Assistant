import requests
import psycopg2
import re
from default_prompts import SQL_SYSTEM_PROMPT


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "incident_db",
    "user": "incident_ai",
    "password": "ai_password"
}


OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma3:4b-it-q4_K_M"
EMBEDDING_MODEL = "nomic-embed-text:latest"


# ================================= SQl =====================================

def generate_sql(question):
    prompt = SQL_SYSTEM_PROMPT + f"""
        User Question: {question}
        SQL Query:
    """

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0},
    }
    res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
    raw_response = res.json()["response"]

    # Extract SQL from markdown fences
    match = re.search(r"```sql\s*(.*?)\s*```", raw_response, re.DOTALL | re.IGNORECASE)
    sql = match.group(1).strip() if match else raw_response.strip()

    return sql


def sql_assistent(question):
    sql = generate_sql(question)
    print(f"Generated sql : {sql}")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cursor = conn.cursor()

        cursor.execute(sql)

        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]

        result = [
            dict(zip(columns, row))
            for row in rows
        ]

        cursor.close()

        return result
    
    except Exception as e:
        return 'Not able to get the data plese try again'
    finally:
        conn.close()


# ======================== Vector search =======================================

def generate_embedding(text):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return data["embeddings"][0]
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama embedding request failed: {e}")

def vector_search(query, top_k=5, similarity_threshold=0.5):
    query_embedding = generate_embedding(query)

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        incident_id,
                        short_description,
                        description,
                        category,
                        subcategory,
                        assignment_group,
                        criticality,
                        criticality_description,
                        state,
                        resolution,
                        root_cause_analysis,
                        service,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM incident.incidents
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                """, (query_embedding, query_embedding, top_k))

                rows = cur.fetchall()
    except psycopg2.Error as e:
        raise RuntimeError(f"Database query failed: {e}")

    results = []
    for row in rows:
        (
            incident_id, short_description, description, category,
            subcategory, assignment_group, criticality,
            criticality_description, state, resolution,
            root_cause_analysis, service, similarity
        ) = row

        similarity = max(0.0, min(1.0, float(similarity)))

        if similarity >= similarity_threshold:
            results.append({
                "incident_id": incident_id,
                "short_description": short_description,
                "description": description,
                "category": category,
                "subcategory": subcategory,
                "assignment_group": assignment_group,
                "criticality": criticality,
                "criticality_description": criticality_description,
                "state": state,
                "resolution": resolution,
                "root_cause_analysis": root_cause_analysis,
                "service": service,
                "similarity": similarity
            })

    return results
