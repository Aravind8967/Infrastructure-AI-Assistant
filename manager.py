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

def general(question):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise software assistant. "
                            "You must strictly answer questions ONLY related software, infrastructure, or databases. "
                            "If the question is outside these domains like history, science, geography, respond with exactly: "
                            "'I can only answer questions related to software, infrastructure, or databases.' "
                            "Do not provide any other information, links, or explanations. "
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
        result = general(question)
        return result


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