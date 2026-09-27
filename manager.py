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
                f"{message['role'].upper()}: "
                f"{message['content']}\n"
            )

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
                            f"Previous conversation:\n"
                            f"{''.join(conversation_context)}\n"
                            f"\nCurrent question:\n"
                            f"{user_question}"
                        )
                    }
                ],
                "stream": False,
                "temperature": 0
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        result = data["message"]["content"].strip().upper()

        return result

    def follow_up(self, question, history):
        conversation_context = []

        for message in history:
            conversation_context.append(
                f"{message['role'].upper()}: "
                f"{message['content']}\n"
            )

        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise infrastructure engineering assistant. "
                            "Answer the user's follow-up question using ONLY the "
                            "previous conversation provided to you. "
                            "Do not invent facts. "
                            "Do not hallucinate missing information. "
                            "If the previous conversation does not contain enough "
                            "information to answer the question, clearly say that "
                            "the required information is not available in the "
                            "conversation."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Previous conversation:\n"
                            f"{''.join(conversation_context)}\n"
                            f"Follow-up question:\n"
                            f"{question}"
                        )
                    }
                ],
                "stream": False,
                "temperature": 0
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        return data.get("message", {}).get(
            "content",
            ""
        ).strip()

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
                                "You are a precise and helpfull software assistant. "
                                "Dont hallucinate your self keep answers straight forward"
                                "For valid questions, keep answers factual, concise."
                            )
                        },
                        {
                            "role": "user",
                            "content": question
                        }
                    ],
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()

            # Defensive check
            if "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            else:
                return "Facing some error please try again"

        except requests.exceptions.RequestException as e:
            return f"Error contacting Ollama: {e}"

    def draft_answer(self, question, raw_result):
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise assistant. "
                            "Take the raw data provided and draft a short, factual, "
                            "and well-organized answer to the user's question. "
                            "Do not hallucinate. keep answers factual, concise"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\nRaw result: {raw_result}"
                    }
                ],
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()


    def chat(self, user_id, question):
        history = conversation.get_last_messages(user_id, limit=5)
        route = self.classify_query(question, history)
        print(f"Route : {route}")

        if route == "SQL":

            raw_result = sql_interface.sql_assistent(question)

            answer = self.draft_answer(
                question,
                raw_result
            )

        elif route == "VECTOR":

            raw_result = vector_interface.vector_search(
                question
            )

            answer = self.draft_answer(
                question,
                raw_result
            )

        elif route == "GENERAL":

            answer = self.general(question)

        elif route == "FOLLOW_UP":

            answer = self.follow_up(
                question,
                history
            )

        elif route == "INVALID":

            answer = (
                "I can only answer questions related to "
                "Infrastructure, Databases, Software, "
                "Cloud, DevOps, and incidents."
            )

        else:

            answer = (
                "Unknown route. Please refine your question."
            )

        # Store user message
        conversation.save_message(
            user_id,
            "user",
            question
        )

        # Store assistant response
        conversation.save_message(
            user_id,
            "assistant",
            answer
        )

        return answer
            
if __name__ == "__main__":
    manager = Manager()
    user_id = 1

    while True:
        ask = input('ask : ')

        if ask == 'stop':
            break
        else:
            result = manager.chat(2, ask)

            print(
                f"Result: {result}"
            )