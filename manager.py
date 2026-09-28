import re
import requests
from default_prompts import MANAGER_PROMPT
from database import SQLInterface, VectorInterface, ConversationInterface


OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "gemma3:4b-it-q4_K_M"
sql_interface = SQLInterface()
vector_interface = VectorInterface()
conversation = ConversationInterface()

class Manager:
    def classify_query(self, user_question, history):
        conversation_context = []
        for message in history:
            conversation_context.append(
                f"{message['role'].upper()}: {message['content']}\n"
            )

        # Deterministic check for standalone Incident ID lookups (e.g., INC20260029) when not a follow-up pronoun
        if re.search(r'\bINC\d+\b', user_question, re.IGNORECASE) and not any(w in user_question.lower() for w in ['its', 'it', 'that', 'this', 'state', 'resolution', 'root cause', 'status']):
            if not any(word in user_question.lower() for word in ['delete', 'update', 'drop', 'truncate', 'insert']):
                return "SQL"

        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": MANAGER_PROMPT
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Previous conversation (last 5 messages):\n"
                                f"{''.join(conversation_context)}\n"
                                f"\nCurrent question:\n"
                                f"{user_question}"
                            )
                        }
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": 50,
                        "temperature": 0.0
                    }
                },
                timeout=120
            )

            response.raise_for_status()
            data = response.json()
            raw_result = data["message"]["content"].strip().upper()

            # Parse route using regex matching to avoid markdown or formatting issues
            match = re.search(r'\b(SQL|VECTOR|GENERAL|FOLLOW_UP|INVALID)\b', raw_result)
            if match:
                return match.group(1)
            return "GENERAL"
        except Exception as e:
            print(f"Error during classification: {e}")
            return "GENERAL"

    def follow_up(self, question, history):
        conversation_context = []
        history_text = ""
        for message in history:
            formatted = f"{message['role'].upper()}: {message['content']}\n"
            conversation_context.append(formatted)
            history_text += formatted

        # Check if an Incident ID is present in history or question
        inc_match = re.search(r'\bINC\d+\b', question + " " + history_text, re.IGNORECASE)
        additional_db_context = ""
        
        if inc_match:
            inc_id = inc_match.group(0).upper()
            # Fetch complete incident details from DB for exact context
            db_res = sql_interface.sql_assistent(f"SELECT incident_id, short_description, description, category, subcategory, assignment_group, assigned_to, criticality_description, state, resolution, root_cause_analysis, service FROM incident.incidents WHERE incident_id ILIKE '{inc_id}'")
            if db_res and isinstance(db_res, list) and len(db_res) > 0:
                additional_db_context = f"\nRelevant Incident Record ({inc_id}):\n{db_res[0]}\n"

        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a precise software engineering and infrastructure assistant. "
                                "Your primary task is to answer the user's follow-up question by prioritizing the "
                                "conversation history context (last 5 messages) and any provided incident record.\n\n"
                                "Instructions:\n"
                                "1. FIRST, inspect the previous conversation history to determine what topic, concept, or incident "
                                "the user is referring to (e.g. 'its', 'it', 'that', 'those', 'the previous one').\n"
                                "2. If the user is asking about a software/technology concept discussed in history (such as Generative AI, Docker, Kubernetes, etc.), "
                                "provide a comprehensive, factual, and well-structured answer explaining that topic/concept as requested.\n"
                                "3. If the user is asking about specific incident metrics or database fields (such as state, root cause, resolution, assignment group), "
                                "answer using the provided incident record or conversation history.\n"
                                "4. Do NOT say 'data not found in context' when answering follow-up questions about general technical concepts or software topics.\n"
                                "5. Keep responses factual, direct, structured, and helpful."
                            )
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Previous conversation (last 5 messages):\n"
                                f"{''.join(conversation_context)}\n"
                                f"{additional_db_context}"
                                f"Follow-up question:\n"
                                f"{question}"
                            )
                        }
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": 300,
                        "temperature": 0.1
                    }
                },
                timeout=120
            )

            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"Error processing follow-up: {e}"

    def general(self, question):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a precise and helpful software assistant. "
                                "Do not hallucinate. Keep answers factual, concise, and straight to the point."
                            )
                        },
                        {
                            "role": "user",
                            "content": question
                        }
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": 300,
                        "temperature": 0.1
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()

            if "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            else:
                return "Facing an issue, please try again."
        except requests.exceptions.RequestException as e:
            return f"Error contacting Ollama: {e}"

    def draft_answer(self, question, raw_result):
        # Anti-hallucination check: If no data returned from SQL or Vector search
        if not raw_result or raw_result == [] or raw_result == "Not able to get the data plese try again":
            return "No relevant incident data found in the database matching your query."

        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a precise infrastructure assistant. "
                                "Take the raw data provided and draft a short, factual, "
                                "and well-organized answer to the user's question. "
                                "Do NOT hallucinate or add unmentioned details. "
                                "If raw data is empty, state clearly that no data was found."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Question: {question}\nRaw result: {raw_result}"
                        }
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": 300,
                        "temperature": 0.1
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"Error drafting answer: {e}"

    def chat(self, user_id, question):
        history = conversation.get_last_messages(user_id, limit=5)
        route = self.classify_query(question, history)
        print(f"Route : {route}")

        if route == "SQL":
            raw_result = sql_interface.sql_assistent(question)
            if not raw_result or raw_result == []:
                answer = "No relevant incident data found in the database matching your query."
            else:
                answer = self.draft_answer(question, raw_result)

        elif route == "VECTOR":
            raw_result = vector_interface.vector_search(question, top_k=5, similarity_threshold=0.6)
            if not raw_result or raw_result == []:
                answer = "No past incidents found matching your query (similarity threshold 0.6)."
            else:
                answer = self.draft_answer(question, raw_result)

        elif route == "GENERAL":
            answer = self.general(question)

        elif route == "FOLLOW_UP":
            answer = self.follow_up(question, history)

        elif route == "INVALID":
            answer = (
                "I can only answer questions related to "
                "Infrastructure, Databases, Software, "
                "Cloud, DevOps, and incidents. Data modification requests (INSERT, UPDATE, DELETE) are not allowed."
            )

        else:
            answer = "Unknown route. Please refine your question."

        # Store user message
        conversation.save_message(user_id, "user", question)

        # Store assistant response
        conversation.save_message(user_id, "assistant", answer)

        return answer


if __name__ == "__main__":
    manager = Manager()
    user_id = 1

    while True:
        ask = input('ask : ')
        if ask == 'stop':
            break
        else:
            result = manager.chat(user_id, ask)
            print(f"Result: {result}")