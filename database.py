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
TOP_K = 4
SIMILARITY_THRESHOLD = 0.75



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

        return { 'data' : result, 'status' : 200}
    
    except Exception as e:
        return {'data' : 'Not able to get the data plese try again', 'status' : 400}
    finally:
        conn.close()


def generate_embedding(text):

    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": EMBEDDING_MODEL,
            "input": text
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["embeddings"][0]


def vector_search(query):

    query_embedding = generate_embedding(
        query
    )

    conn = psycopg2.connect(
        **DB_CONFIG
    )

    try:

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
                    1 - (embedding <=> %s::vector)
                        AS similarity

                FROM incident.incidents

                WHERE embedding IS NOT NULL

                ORDER BY embedding <=> %s::vector

                LIMIT %s;
            """, (
                query_embedding,
                query_embedding,
                TOP_K
            ))

            rows = cur.fetchall()

    finally:

        conn.close()


    # --------------------------------------------------------
    # Apply similarity threshold
    # --------------------------------------------------------

    results = []

    for row in rows:

        similarity = float(
            row[12]
        )

        if similarity >= SIMILARITY_THRESHOLD:

            results.append({
                "incident_id": row[0],
                "short_description": row[1],
                "description": row[2],
                "category": row[3],
                "subcategory": row[4],
                "assignment_group": row[5],
                "criticality": row[6],
                "criticality_description": row[7],
                "state": row[8],
                "resolution": row[9],
                "root_cause_analysis": row[10],
                "service": row[11],
                "similarity": similarity
            })

    return results