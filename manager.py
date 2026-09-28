import re
import requests
from default_prompts import MANAGER_PROMPT, SQL_SYSTEM_PROMPT
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

        print('--------------- Previous Conversaion context ----------------------------')
        print(''.join(conversation_context))
        print('-------------------------------------------------------------------------')
        
        # Deterministic check for standalone Incident ID lookups (e.g., INC20260465) when not a pronoun reference
        if re.search(r'\bINC\d+\b', user_question, re.IGNORECASE) and not any(w in user_question.lower() for w in ['its', 'it', 'that', 'this', 'when', 'who', 'state', 'status']):
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

            match = re.search(r'\b(SQL|VECTOR|GENERAL|FOLLOW_UP|INVALID)\b', raw_result)
            if match:
                return match.group(1)
            return "GENERAL"
        except Exception as e:
            print(f"Error during classification: {e}")
            return "GENERAL"

    def rewrite_follow_up(self, question, history):
        """
        Rewrite a follow-up question into a standalone question using the last 5 messages context.
        """
        conversation_context = []
        for message in history:
            conversation_context.append(
                f"{message['role'].upper()}: {message['content']}\n"
            )

        print('=================== rewrite follow up function called ==============================')
        print('------- inside that convestion context ------------------')
        print(''.join(conversation_context))
        print('---------------------------------------------------------')
        print('====================================================================================')
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert query contextualizer.\n"
                                "Your ONLY task is to rewrite the user's follow-up question into a self-contained, "
                                "standalone question by replacing ambiguous pronouns or references (such as 'its', 'it', 'this incident', "
                                "'these incidents', 'from those', 'how many of them', 'who opened it', 'when was it opened') with the exact Incident ID (e.g. INC20260465) or topic from the previous conversation.\n"
                                "Rules:\n"
                                "1. Do NOT add extra assumed filters or change the meaning of the question.\n"
                                "2. Simply substitute 'this incident' or 'it' with the specific Incident ID (e.g., INC20260465).\n"
                                "3. Do NOT answer the question or output code blocks.\n"
                                "Return ONLY the rewritten standalone question."
                            )
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Previous conversation:\n"
                                f"{''.join(conversation_context)}\n"
                                f"Follow-up question: {question}\n"
                                f"Standalone question:"
                            )
                        }
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": 80,
                        "temperature": 0.0
                    }
                },
                timeout=120
            )

            response.raise_for_status()
            data = response.json()
            rewritten = data.get("message", {}).get("content", "").strip()
            rewritten = re.sub(r'```.*?\n', '', rewritten).replace('```', '').strip()
            return rewritten if rewritten else question
        except Exception as e:
            print(f"Error rewriting follow-up: {e}")
            return question

    def follow_up(self, question, history):
        # Step 1: Rewrite follow-up into a standalone question using conversation history
        standalone_q = self.rewrite_follow_up(question, history)
        print(f"Rewritten Follow-up Query: {standalone_q}")

        # Step 2: Determine appropriate route for the rewritten question
        sub_route = self.classify_query(standalone_q, [])
        print(f"Sub-route for follow-up: {sub_route}")

        # Step 3: Fetch data or execute query based on sub-route
        if sub_route == "SQL" or "incident" in standalone_q.lower() or re.search(r'\bINC\d+\b', standalone_q, re.I) or any(w in standalone_q.lower() for w in ['count', 'how many', 'who opened', 'when opened']):
            raw_result = sql_interface.sql_assistent(standalone_q)
            return self.draft_answer(question, raw_result)
        elif sub_route == "VECTOR":
            raw_result = vector_interface.vector_search(standalone_q, top_k=5, similarity_threshold=0.6)
            return self.draft_answer(question, raw_result)
        elif sub_route == "GENERAL":
            return self.general(standalone_q)
        else:
            raw_result = sql_interface.sql_assistent(standalone_q)
            return self.draft_answer(question, raw_result)

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
                                "Do NOT output code blocks or tool calls (e.g. incident_search, ```tool ````). "
                                "Do NOT hallucinate or add unmentioned details."
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