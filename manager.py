import requests
from default_prompts import MANAGER_PROMPT
from database import SQLInterface, VectorInterface


OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "gemma3:4b-it-q4_K_M"
sql_interface = SQLInterface()
vector_interface = VectorInterface()

class Manager:
    def classify_query(self, user_question):
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
                        "content": user_question
                    }
                ],
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        result = data["message"]["content"].strip().upper()

        return result

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


    def chat(self, question):
        route = self.classify_query(question)
        print(f"Route : {route}")

        if route == "SQL":
            raw_result = sql_interface.sql_assistent(question)
            return self.draft_answer(question, raw_result)
        
        elif route == "VECTOR":
            raw_result = vector_interface.vector_search(question)
            return self.draft_answer(question, raw_result)
        
        elif route == "GENERAL":
            result = self.general(question)
            return result
        
        elif route == "INVALID":
            return (
                "I can only answer questions related to Infrastructure, "
                "Databases, and Software"
                "And give details related to incidents"
            )
        
        else:
            return "Unknown route. Please refine your question."

        
if __name__ == "__main__":
    manager = Manager()

    while True:
        ask = input('ask : ')

        if ask == 'stop':
            break
        else:
            result = manager.chat(ask)

            print(
                f"Result: {result}"
            )