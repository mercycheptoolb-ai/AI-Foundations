# HW4: Campus Customs, an AI-powered campus apparel shop

A Yale apparel storefront (React + Vite) with a FastAPI backend and a **Bulldog Assistant** chatbot: a PydanticAI agent using OpenAI's `gpt-5.6-luna` through the Portkey gateway. The assistant looks up real prices and stock by size, fills the page with product cards when you browse a category, remembers logged-in shoppers, and keeps an append-only audit trail of every agent loop.

## What's where

| Path | What it is |
|---|---|
| `backend/` | FastAPI app (`main.py`), agent (`agent.py`), tools (`tools.py`), types (`models.py`), system prompt (`prompts/prompt.md`), audit trail (`audit.py`), accounts and memory |
| `frontend/` | React + TypeScript + Vite website ("Varsity Locker Room" design) |
| `output/harness.md` | **How the whole system works**: database, agent, tools, model fields, safety rules, specs |
| `output/audit_trail.json` | Append-only log of agent-loop activity |
| `output/usability.md`, `output/design.md` | Problem 9 and 10 write-ups |
| `output/app_check.html` | Live site check with screenshots (open in a browser) |
| `AI_prompts.md` | Log of the prompts used for each problem |
| `data/` | Not included: see `data/README.md` |

## Run it

Needs Python 3.10+ and Node 20.19+ or 22.12+.

1. Put the course data in `data/` (`campus_customs.db` and `products/`, from the course's `data.zip`).
2. Copy `.env.example` to `.env` and set `PORTKEY_API_KEY`.
3. One-time install, from `hw4/`:

   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt && npm --prefix frontend install
   ```

4. Start the backend, from `hw4/backend/`:

   ```bash
   source ../.venv/bin/activate && uvicorn main:app --reload --port 8000
   ```

5. Start the website, from `hw4/` in a second terminal:

   ```bash
   npm --prefix frontend run dev
   ```

6. Open http://localhost:5180. The chat bubble is at the bottom right.

More detail, including loop limits, caps, and safety rules, is in `output/harness.md` §13.

## Not in this repository

The real `.env` (API key), `data/campus_customs.db`, the product photos, and `data.zip` are kept out with `.gitignore`.
