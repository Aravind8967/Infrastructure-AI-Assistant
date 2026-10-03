import os
import requests
import psycopg2
import re
import logging
from default_prompts import SQL_SYSTEM_PROMPT

logger = logging.getLogger("incident_backend.database")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = "gemma3:4b-it-q4_K_M"
EMBEDDING_MODEL = "nomic-embed-text:latest"


# ================================= SQL =====================================
class SQLInterface:
    def __init__(self):
        self.DB_CONFIG = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "incident_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASS", "postgres123")
        }

    def generate_sql(self, question):
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

    def sql_assistent(self, question):
        sql = self.generate_sql(question)
        logger.info(f"Generated SQL: {sql}")
        print(f"Generated sql : {sql}")

        conn = psycopg2.connect(**self.DB_CONFIG)
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            result = []
            for row in rows[:10]:  # Limit to max 10 records for concise LLM processing
                row_dict = dict(zip(columns, row))
                # Explicitly strip out large vector embedding column if present
                row_dict.pop("embedding", None)
                result.append(row_dict)

            cursor.close()
            return result
        except Exception as e:
            logger.error(f"Database error executing SQL: {e}")
            print(f"Database error executing SQL: {e}")
            return []
        finally:
            conn.close()


# ======================== Vector search =======================================

class VectorInterface:
    def __init__(self):
        self.DB_CONFIG = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "incident_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASS", "postgres123")
        }

    def generate_embedding(self, text):
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
            logger.error(f"Ollama embedding request failed: {e}")
            raise RuntimeError(f"Ollama embedding request failed: {e}")

    def vector_search(self, query, top_k=5, similarity_threshold=0.6):
        query_embedding = self.generate_embedding(query)

        try:
            with psycopg2.connect(**self.DB_CONFIG) as conn:
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
            logger.error(f"Database query failed during vector search: {e}")
            print(f"Database query failed during vector search: {e}")
            return []

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
                    "similarity": round(similarity, 4)
                })

        return results


# ========================== Conversation ===================================

class ConversationInterface:
    def __init__(self):
        self.DB_CONFIG = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "incident_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASS", "postgres123")
        }

    def save_message(self, user_id, role, content):
        conn = psycopg2.connect(**self.DB_CONFIG)

        try:
            cursor = conn.cursor()

            # Check if user exists, otherwise create a default entry for smooth execution
            cursor.execute("SELECT user_id FROM identity.users WHERE user_id = %s;", (user_id,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO identity.users (user_id, user_name, user_role) VALUES (%s, %s, %s);",
                    (user_id, f"User_{user_id}", "User")
                )

            query = """
                INSERT INTO conversation.messages
                    (user_id, role, content)
                VALUES
                    (%s, %s, %s)
            """

            cursor.execute(
                query,
                (user_id, role, content)
            )

            conn.commit()
            logger.info(f"{role} message saved to database for user_id={user_id}")
            print(f"{role} message saved to database")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving conversation message: {e}")
            print(f"Error saving conversation message: {e}")
        finally:
            cursor.close()
            conn.close()

    def get_last_messages(self, user_id, limit=5):
        conn = psycopg2.connect(**self.DB_CONFIG)

        try:
            cursor = conn.cursor()

            query = """
                SELECT
                    role,
                    content,
                    created_at
                FROM conversation.messages
                WHERE user_id = %s
                ORDER BY created_at DESC, message_id DESC
                LIMIT %s
            """

            cursor.execute(
                query,
                (user_id, limit)
            )

            rows = cursor.fetchall()

            cursor.close()

            # Database returns newest first.
            # Reverse so LLM sees conversation chronologically.
            rows.reverse()

            return [
                {
                    "role": row[0],
                    "content": row[1],
                    "created_at": str(row[2])
                }
                for row in rows
            ]

        finally:
            conn.close()

    def clear_history(self, user_id):
        conn = psycopg2.connect(**self.DB_CONFIG)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation.messages WHERE user_id = %s;", (user_id,))
            conn.commit()
            logger.info(f"Cleared conversation history for user_id={user_id}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error clearing conversation history: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()


class UserInterface:
    def __init__(self):
        self.DB_CONFIG = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "incident_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASS", "postgres123")
        }

    def insert_user(self, user_name, user_role, password):
        conn = psycopg2.connect(**self.DB_CONFIG)

        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO identity.users (user_name, user_role, password)
                VALUES (%s, %s, %s)
                RETURNING user_id, user_name, user_role, created_at;
            """

            cursor.execute(query, (user_name, user_role, password))
            created_user = cursor.fetchone()
            conn.commit()

            logger.info(f"New User created username: {user_name}")
            print(f"New User created username : {user_name}")
            return {
                'user_id': created_user[0],
                'user_name': created_user[1],
                'user_role': created_user[2],
                'created_at': str(created_user[3])
            }
        finally:
            cursor.close()
            conn.close()

    def get_user(self, user_name):
        conn = psycopg2.connect(**self.DB_CONFIG)

        try:
            cursor = conn.cursor()
            query = """
                SELECT * from identity.users 
                WHERE user_name LIKE %s
            """
            cursor.execute(query, (user_name,))
            user = cursor.fetchone()

            if user:
                return {
                    'user_id': user[0],
                    'user_name': user[1],
                    'user_role': user[2],
                    'created_at': str(user[3]),
                    'password' : user[4]
                }
            else:
                return None

        finally:
            conn.close()

    def authenticate_user(self, user_name, password):
        conn = psycopg2.connect(**self.DB_CONFIG)
        try:
            cursor = conn.cursor()
            query = """
                SELECT user_id, user_name, user_role, created_at, password
                FROM identity.users 
                WHERE LOWER(user_name) = LOWER(%s)
            """
            cursor.execute(query, (user_name,))
            user = cursor.fetchone()

            if user and (len(user) <= 4 or user[4] == password or not user[4]):
                return {
                    'user_id': user[0],
                    'user_name': user[1],
                    'user_role': user[2],
                    'created_at': str(user[3])
                }
            return None
        finally:
            cursor.close()
            conn.close()


class IncidentInterface:
    def __init__(self):
        self.DB_CONFIG = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "incident_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASS", "postgres123")
        }

    def get_stats(self):
        conn = psycopg2.connect(**self.DB_CONFIG)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE LOWER(state) = 'open') as open_count,
                    COUNT(*) FILTER (WHERE LOWER(state) = 'in progress') as in_progress_count,
                    COUNT(*) FILTER (WHERE LOWER(state) = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE LOWER(state) = 'closed') as closed_count
                FROM incident.incidents;
            """)
            row = cursor.fetchone()
            return {
                "total": row[0] or 0,
                "open": row[1] or 0,
                "in_progress": row[2] or 0,
                "pending": row[3] or 0,
                "closed": row[4] or 0
            }
        finally:
            conn.close()

    def get_incidents_by_state(self, state=None):
        conn = psycopg2.connect(**self.DB_CONFIG)
        try:
            cursor = conn.cursor()
            if state and state.lower() != 'all':
                cursor.execute("""
                    SELECT incident_id, short_description, category, subcategory, 
                           assignment_group, assigned_to, criticality, state, opened_at
                    FROM incident.incidents
                    WHERE LOWER(state) = LOWER(%s)
                    ORDER BY opened_at DESC;
                """, (state,))
            else:
                cursor.execute("""
                    SELECT incident_id, short_description, category, subcategory, 
                           assignment_group, assigned_to, criticality, state, opened_at
                    FROM incident.incidents
                    ORDER BY opened_at DESC;
                """)
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = []
            for row in rows:
                item = dict(zip(columns, row))
                if item.get("opened_at"):
                    item["opened_at"] = str(item["opened_at"])
                result.append(item)
            return result
        finally:
            conn.close()

    def get_incident_by_id(self, incident_id):
        conn = psycopg2.connect(**self.DB_CONFIG)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT incident_id, short_description, description, category, subcategory,
                       assignment_group, assigned_to, criticality, criticality_description,
                       state, opened_at, closed_at, opened_by, closed_by, resolution,
                       root_cause_analysis, service
                FROM incident.incidents
                WHERE LOWER(incident_id) = LOWER(%s);
            """, (incident_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            item = dict(zip(columns, row))
            if item.get("opened_at"):
                item["opened_at"] = str(item["opened_at"])
            if item.get("closed_at"):
                item["closed_at"] = str(item["closed_at"])
            return item
        finally:
            conn.close()


if __name__ == '__main__':
    user = ConversationInterface()
    print(user.get_last_messages(2))
