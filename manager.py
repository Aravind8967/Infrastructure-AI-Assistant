import requests
from default_prompts import MANAGER_PROMPT
from database import sql_assistent, vector_search


OLLAMA_URL = "http://localhost:11434"

LLM_MODEL = "gemma3:4b-it-q4_K_M"


def classify_query(user_question):

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

def chat(question):
    route = classify_query(question)
    print(f"Route : {route}")

    if "SQL" in route:
        result = sql_assistent(question)
        return result

    elif "VECTOR" in route:
        result = vector_search(question)
        return result

    else:
        return "GENERAL"




if __name__ == "__main__":

    questions = [
        "How many open incidents are present?",
        "Have we seen an EC2 instance failure before?",
        "What is a virtual machine?",
        "How many pending incidents are there?",
        "Did we have any Kubernetes deployment failures?",
        "How do I create an S3 bucket?"
    ]

    while True:
        ask = input('ask : ')

        if ask == 'stop':
            break
        else:
            result = chat(ask)

            print(
                f"Result: {result}"
            )