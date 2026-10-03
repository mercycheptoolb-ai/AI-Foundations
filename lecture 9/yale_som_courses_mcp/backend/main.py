"""Yale SOM course explorer API desk.

Run from backend/:  uvicorn main:app --reload --port 8000
Open API docs:      http://127.0.0.1:8000/docs
Frontend (Vite):    http://127.0.0.1:5173
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import run_agent

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "yale_som_classes.json"
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

app = FastAPI(title="Yale SOM Courses", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_courses() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


@app.get("/api/health")
def health():
    return {"ok": True, "courses_file": str(DATA_PATH.name)}


@app.get("/api/courses")
def list_courses(q: str | None = Query(default=None)):
    """Return courses for the React catalog (optional text filter)."""
    courses = load_courses()
    if not q:
        return {"count": len(courses), "courses": courses}
    needle = q.lower().strip()
    matched = [
        c
        for c in courses
        if needle in json.dumps(c, ensure_ascii=False).lower()
    ]
    return {"count": len(matched), "courses": matched}


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    result = run_agent(body.message)
    return ChatResponse(
        reply=result.get("reply", ""),
        tools_used=list(result.get("tools_used") or []),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
