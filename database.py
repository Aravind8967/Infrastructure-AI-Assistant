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


def db_query(sql):
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