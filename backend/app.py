import os
import time
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from manager import Manager
from database import SQLInterface, VectorInterface, ConversationInterface, UserInterface

# ============================================================
# 1. LOGGING CONFIGURATION (app.log)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "app.log")

# ------------ Setup Formatter & Handlers -----------
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s]: %(message)s")

file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# -------------- Root Logger Setup ------------------
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger("incident_backend.api")
logger.info(f"Logging initialized. App log path: {LOG_FILE}")

# ---------- Initialize Core Services ---------------
manager = Manager()
sql_interface = SQLInterface()
vector_interface = VectorInterface()
conversation_interface = ConversationInterface()
user_interface = UserInterface()


# ============================================================
# 2. FASTAPI APP INITIALIZATION & CORS
# ============================================================
app = FastAPI(
    title="Incident Manager Assistant API",
    description="RESTful API Interface for Infrastructure Incident Management Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 3. TRANSACTION LOGGING MIDDLEWARE
# ============================================================
@app.middleware("http")
async def log_transactions(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    query_params = str(request.query_params) if request.query_params else ""

    logger.info(f"[TRANSACTION START] {method} {path} | Params: {query_params} | Client: {client_ip}")

    try:
        response = await call_next(request)
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        status_code = response.status_code

        logger.info(
            f"[TRANSACTION END] {method} {path} | Status: {status_code} | "
            f"Duration: {process_time_ms}ms | Client: {client_ip}"
        )
        return response
    except Exception as exc:
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            f"[TRANSACTION ERROR] {method} {path} | Error: {str(exc)} | "
            f"Duration: {process_time_ms}ms | Client: {client_ip}"
        )
        raise exc


# ============================================================
# 4. REQUEST / RESPONSE PYDANTIC SCHEMAS
# ============================================================
class ChatRequest(BaseModel):
    user_id: int = Field(default=1, description="ID of the user interacting with the chatbot")
    question: str = Field(..., description="Question or prompt for the Incident Assistant", min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "question": "How many critical incidents do we currently have?"
            }
        }


class ChatResponse(BaseModel):
    user_id: int
    question: str
    answer: str
    route: str
    timestamp: str


class UserCreateRequest(BaseModel):
    user_name: str = Field(..., description="Name of the user")
    user_role: str = Field(default="User", description="Role of the user, e.g. Engineer, Manager")

    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "Arjun Menon",
                "user_role": "DevOps Engineer"
            }
        }


class SQLQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question to generate and run SQL for")


class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="Error message or incident query for semantic search")
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


# ============================================================
# 5. API ENDPOINTS
# ============================================================

@app.get("/", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify backend service status."""
    return {
        "status": "healthy",
        "service": "Incident Manager API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
def chat_endpoint(request: ChatRequest):
    """
    Main Chat Interface Endpoint.
    Classifies the user query (SQL, VECTOR, GENERAL, FOLLOW_UP, INVALID),
    retrieves data, generates an answer, saves transaction history to database,
    and returns response with route metadata.
    """
    try:
        logger.info(f"Processing chat endpoint for user_id={request.user_id}")
        answer, route = manager.chat(user_id=request.user_id, question=request.question)
        
        return ChatResponse(
            user_id=request.user_id,
            question=request.question,
            answer=answer,
            route=route,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your request: {str(e)}"
        )


@app.get("/api/history/{user_id}", tags=["Conversation History"])
def get_chat_history(user_id: int, limit: int = 10):
    """
    Retrieve conversation history for a specific user.
    """
    try:
        messages = conversation_interface.get_last_messages(user_id=user_id, limit=limit)
        return {
            "user_id": user_id,
            "count": len(messages),
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Error fetching history for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation history: {str(e)}"
        )


@app.post("/api/users", tags=["Users"])
def create_user(request: UserCreateRequest):
    """
    Create a new user in identity schema.
    """
    try:
        user_info = user_interface.insert_user(user_name=request.user_name, user_role=request.user_role)
        return {
            "status": "success",
            "message": "User created successfully",
            "user": user_info
        }
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create user: {str(e)}"
        )


@app.get("/api/users/{user_name}", tags=["Users"])
def get_user_profile(user_name: str):
    """
    Get user profile details by user_name.
    """
    try:
        user = user_interface.get_user(user_name=user_name)
        if not user:
            raise HTTPException(status_code=404, detail=f"User '{user_name}' not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user: {str(e)}"
        )


@app.get("/api/logs", tags=["System Logs"])
def get_recent_logs(lines: int = 50):
    """
    Retrieve the last N lines from app.log to inspect API transactions.
    """
    try:
        if not os.path.exists(LOG_FILE):
            return {"logs": [], "message": "Log file app.log does not exist yet."}
        
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:]
            
        return {
            "log_file": LOG_FILE,
            "total_lines": len(all_lines),
            "requested_lines": lines,
            "logs": [line.strip() for line in recent]
        }
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to read log file: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
