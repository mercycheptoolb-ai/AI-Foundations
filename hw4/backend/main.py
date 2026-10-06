"""Campus Customs API: products, images, accounts, and the shopping-assistant chat.

Run from the backend/ folder (with the hw4 virtualenv active):
    uvicorn main:app --reload --port 8000

The website (Vite dev server on :5180) proxies /api and /images here.
The chatbot is a PydanticAI agent wired up in agent.py, with its system prompt
in prompts/prompt.md, tools in tools.py, and types in models.py.
"""

import json
import logging
import re
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import (
    AgentRunError,
    ContentFilterError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)

import audit
import auth
import memory
from agent import AgentNotConfigured, build_history, run_chat
from db import DATA_DIR, db, init_db
from models import ChatHistoryMessage, ChatReply, ChatRequest, PageContext, PageSearch, ShopDeps
from tools import (
    describe_page,
    display_description,
    display_name,
    existing_product_ids,
    category_for,
    page_results,
    product_cards,
    resolve_page,
)

logger = logging.getLogger("campus_customs")

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes the submitted values back, which would
    # include passwords. Return only where the problem is and what it was.
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"loc": list(e.get("loc", [])), "msg": e.get("msg", "Invalid input")}
                for e in exc.errors()
            ]
        },
    )

# Product photos: catalogue.image_file_path is "products/<file>.jpg",
# so it maps directly to /images/products/<file>.jpg. Only the products
# folder is mounted so the database file itself is never downloadable.
app.mount(
    "/images/products",
    StaticFiles(directory=DATA_DIR / "products"),
    name="product-images",
)


def product_from_row(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": display_name(row["name"]),
        "garment_type": row["garment_type"],
        "category": category_for(row["garment_type"]),
        "description": display_description(row["description"]),
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_url": f"/images/{row['image_file_path']}",
        "price": row["price"],
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
        stock = {}
        for i in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(i["product_id"], {})[i["size"]] = i["quantity"]
    # stock_by_size powers the "In stock in my size" filter on the Products page (Problem 9).
    return [
        {**product_from_row(r), "total_stock": r["total_stock"], "stock_by_size": stock.get(r["product_id"], {})}
        for r in rows
    ]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?",
            (product_id,),
        ).fetchall()

    sizes = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    return {**product_from_row(row), "sizes": sizes}


# ---------- Chat ----------

HISTORY_FOR_MODEL = 20  # recent messages sent to the agent as context
HISTORY_FOR_WIDGET = 50  # recent messages shown when a logged-in shopper opens chat
GUEST_HISTORY_CHARS = 12_000  # guests send their own history; keep only this much of it

# Payment details typed into chat are removed before the message reaches the
# model or the database (the bot also tells shoppers not to share them).
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
CVV_RE = re.compile(r"(?i)\b(cvv2?|cvc2?|csc|security code)(\W{0,3})\d{3,4}\b")


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def redact_sensitive(text: str) -> str:
    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return "[card number removed]" if _luhn_ok(digits) else m.group(0)

    return CVV_RE.sub(r"\1\2[removed]", CARD_RE.sub(card, text))


# The model provider (Azure OpenAI behind Portkey) runs its own content filter. It refuses some
# messages outright (self-harm talk, threats, attempts to pull out the system prompt), or blocks
# the reply. No model answer exists then, so the server picks a safe reply itself. It fails safe:
# unless the message is clearly a prompt-extraction attempt, the reply mentions 988 / 911.
_ME = r"my\s?self"  # not "me": "finals are killing me" isn't a crisis
_PEOPLE = (r"(?:him|her|them|someone|somebody|everyone|my\s+(?:roommate|mom|dad|mother|father|brother|"
           r"sister|wife|husband|girlfriend|boyfriend|partner|ex|friend|teacher|professor|boss|family|kids?))")
CRISIS_RE = re.compile(
    r"(?i)\b(?:suicid\w*|(?<![\d.]\s)(?<!\d)kms\b|unalive|"
    r"kill(?:ing)?\s+" + _ME + r"|(?:hurt|harm|hang)(?:ing)?\s+" + _ME + r"|cut(?:ting)?\s+" + _ME + r"(?!\s+(?:some\s+)?slack)|"
    r"self[-\s]?harm|(?<!show\s)off\s+" + _ME + r"|"
    r"(?:wanna|want\s+to|going\s+to|gonna)\s+(?:die(?!\s+(?:laughing|of\s+laughter|if|when|for))|end\s+(?:it|my\s+life)\b(?!\s+on\b))|"
    r"wish\s+i\s+(?:was|were)\s+dead|better\s+off\s+(?:dead|without\s+me)|"
    r"end(?:ing)?\s+(?:it\s+all|my\s+life)|take\s+my\s+(?:own\s+)?life|overdos\w*|"
    r"(?:no\s+reason|nothing)\s+to\s+live|can['’]?t\s+go\s+on|done\s+with\s+life|"
    r"want\s+(?:it|everything)\s+(?:all\s+)?to\s+(?:stop|end)|"
    r"(?:don['’]?t|do\s+not)\s+(?:wanna|want\s+to)\s+(?:be\s+alive|live(?!\s+(?:in|on|at|near|with)\b))|"
    # hurting someone else
    r"(?:kill|hurt|stab|shoot|beat\s+up)\s+" + _PEOPLE + r"\b|"
    # Spanish
    r"matarme|no\s+quiero\s+vivir|mejor\s+sin\s+m[ií]|quitarme\s+la\s+vida)"
)
# Clear requests for the hidden instructions only, so a distress message that happens to say
# "your rules" still gets the reply with 988.
PROBE_RE = re.compile(
    r"(?i)\b(?:system\s+prompt|"
    r"(?:reveal|show|print|repeat|tell|give|share|what\s+(?:is|are))\s+(?:me\s+|us\s+)?(?:your|the)\s+"
    r"(?:system\s+|hidden\s+|secret\s+)?(?:prompt|instructions|rules)(?!\s+(?:on|for|about)\b)|"
    r"(?:ignore|forget|disregard)\s+(?:all\s+)?(?:of\s+)?(?:your|the|my)?\s*(?:previous|prior|above|earlier)?\s*"
    r"(?:instructions|rules|prompts?)|"
    r"jailbreak|developer\s+mode|(?-i:DAN))\b"  # "DAN" in capitals only, not "Dan"
)
CRISIS_REPLY = (
    "I'm really sorry you're going through this, and I'm glad you said something. If you or anyone "
    "else is in danger, call **911** now. If you're thinking about hurting yourself, call or text "
    "**988** (the Suicide & Crisis Lifeline in the US) any time. If you're a Yale student, Yale Mental "
    "Health & Counseling can help too. You don't have to handle this alone."
)
BLOCKED_REPLY = (
    "Sorry, I can't help with that one. If you're going through something hard, you can call or text "
    "**988** any time, or **911** in an emergency. I'm here whenever you need help with Yale gear."
)
DECLINE_REPLY = "Sorry, I can't share that. I'm happy to help you find Yale gear, check sizes and stock, or compare prices!"
TANGLED_REPLY = "Sorry, I got a bit tangled up on that one. Could you ask it a different way?"
UNCONFIRMED_REPLY = "Sorry, I couldn't confirm that from our catalogue just now. Could you ask again, maybe naming the product?"


def _filtered_reply(message: str) -> tuple[str, str]:
    """(kind, reply) when the provider's content filter stopped the run."""
    if CRISIS_RE.search(message):
        return "crisis", CRISIS_REPLY
    if PROBE_RE.search(message):
        return "declined", DECLINE_REPLY
    return "blocked", BLOCKED_REPLY


def _guest_turns(req: ChatRequest) -> list[tuple]:
    """Browser-sent history for guests: redacted, ids checked, newest turns kept within a size budget.

    Shopper turns sent from a product page get the same "[Was viewing: …]" note as saved
    history (the name comes from the catalogue, not the browser).
    """
    turns: list[tuple] = []
    budget = GUEST_HISTORY_CHARS
    for t in reversed(req.history):
        content = redact_sensitive(t.content)
        budget -= len(content)
        if budget < 0:
            break
        note = None
        if t.role == "user" and t.page_product_id:
            seen = resolve_page(PageContext(page_type="product", product_id=t.page_product_id))
            note = describe_page(seen) if seen.product else None
        turns.append((t.role, content, existing_product_ids(t.product_ids), note, t.page_product_id))
    return list(reversed(turns))


def _previous_page_product(turns: list[tuple]) -> str | None:
    """Product page the shopper was on for their previous message (if any)."""
    for turn in reversed(turns):
        if turn[0] == "user":
            return turn[4] if len(turn) > 4 else None
    return None


def _page_note(raw: str | None) -> str | None:
    """Saved page context of a shopper turn -> short note for the agent's history."""
    ctx = memory.load_json(raw)
    if not ctx:
        return None
    if ctx.get("product_name"):
        return f"the product page for {ctx['product_name']} ({ctx.get('product_id')})"
    return ctx.get("description")


def _saved_page_results(raw: str | None) -> dict | None:
    """Rebuild a saved page grid from its filters (fresh prices and stock from the DB)."""
    spec = memory.load_json(raw)
    if not spec:
        return None
    try:
        return page_results(PageSearch(**spec))
    except ValueError:
        return None


@app.post("/api/chat", response_model=ChatReply)
async def chat(req: ChatRequest, request: Request) -> ChatReply:
    """One shopper message in, one agent reply (plus product cards) out."""
    user = auth.current_user(request)
    auth.throttle(request, "chat", f"user{user['id']}" if user else None)
    raw = req.message.strip()
    message = redact_sensitive(raw)
    if not message:
        raise HTTPException(400, "Please type a message.")

    # Who is chatting (from the session cookie, never from the request body) and what
    # they're looking at (browser ids, checked against the catalogue).
    customer = memory.load_customer(user["id"]) if user else None
    view = resolve_page(req.page)

    # Logged-in shoppers: history comes from the database (only their own rows).
    # Guests: the browser sends the conversation so far.
    if customer:
        turns = [
            (
                r["role"],
                r["content"],
                memory.ids_from_products_json(r["products_json"]),
                _page_note(r["page_context_json"]),
                (memory.load_json(r["page_context_json"]) or {}).get("product_id"),
            )
            for r in memory.recent_messages(customer.user_id, HISTORY_FOR_MODEL)
        ]
    else:
        turns = _guest_turns(req)

    # Did the shopper open a new product page since their previous message? If they're still
    # on the same page, the product being discussed in the chat takes priority for "it".
    if view.product and any(t[0] == "user" for t in turns):
        view.changed = _previous_page_product(turns) != view.product.product_id

    deps = ShopDeps(customer=customer, page=view)
    # On a product page, put the page right next to the question (same format as the
    # history notes), so "how much is it?" means the product on screen even if the last
    # few messages were about a different one. The raw message is what gets saved.
    prompt = message + (f"\n\n[Now viewing: {describe_page(view)}]" if view.product and view.changed else "")
    run_id = audit.new_run_id()

    def fallback(kind: str, reply: str) -> ChatReply:
        """A canned reply instead of the agent's; the audit trail records which one."""
        audit.append({"time": audit.now(), "run": run_id, "event": "fallback_reply", "kind": kind})
        return ChatReply(reply=reply, logged_in=customer is not None)

    try:
        output = await run_chat(
            prompt, build_history(turns), deps,
            run_id=run_id, message_chars=len(message), redacted_sensitive=message != raw,
        )
    except AgentNotConfigured as e:
        raise HTTPException(503, f"The shopping assistant isn't set up yet: {e}")
    except UsageLimitExceeded:
        return fallback("usage_limit", TANGLED_REPLY)
    except ContentFilterError:  # the provider filtered the model's reply (or the model refused)
        return fallback(*_filtered_reply(message))
    except UnexpectedModelBehavior:
        # e.g. the reply kept failing the price/stock grounding check
        return fallback("gave_up", UNCONFIRMED_REPLY)
    except ModelHTTPError as e:
        if audit.is_content_filter(e):  # the provider refused the message itself
            return fallback(*_filtered_reply(message))
        logger.warning("model request failed: HTTP %s", e.status_code)
        raise HTTPException(503, "The shopping assistant is having trouble right now. Please try again in a moment.")
    except AgentRunError as e:
        logger.warning("agent run failed: %s", type(e).__name__)
        raise HTTPException(503, "The shopping assistant is having trouble right now. Please try again in a moment.")
    except Exception as e:  # network errors from the OpenAI client, etc.
        logger.exception("chat failed: %s", type(e).__name__)
        raise HTTPException(503, "The shopping assistant is having trouble right now. Please try again in a moment.")

    if (output.product_ids or output.page_search) and CRISIS_RE.search(message) and re.search(r"\b(?:911|988)\b", output.message):
        # Safety rule 10, backed in code: when the shopper may be in danger (or may hurt someone)
        # and the model answered with emergency help, no product tiles or grid go with it.
        # (Both checks, so "will two hurt my budget?" keeps its grid.)
        output.product_ids, output.page_search = [], None
        audit.append({"time": audit.now(), "run": run_id, "event": "safety_override",
                      "detail": "crisis wording: product tiles and page grid removed"})
    cards = product_cards(output.product_ids)
    # Problem 7: the agent asked for a page grid -> run that search against the DB.
    page = page_results(output.page_search) if output.page_search else None
    if customer:
        page_context = {"page_type": view.page_type, "description": describe_page(view)}
        if view.product:
            page_context |= {"product_id": view.product.product_id, "product_name": view.product.name}
        memory.save_exchange(
            customer.user_id,
            message,
            output.message,
            cards,
            page_context,
            output.page_search.model_dump() if output.page_search and page else None,
        )
    return ChatReply(reply=output.message, products=cards, page_results=page, logged_in=customer is not None)


@app.get("/api/chat/history", response_model=list[ChatHistoryMessage])
def chat_history(request: Request) -> list[ChatHistoryMessage]:
    """The logged-in shopper's recent chat (empty for guests)."""
    user = auth.current_user(request)
    if not user:
        return []
    rows = memory.recent_messages(user["id"], HISTORY_FOR_WIDGET)
    return [
        ChatHistoryMessage(
            role=r["role"],
            content=r["content"],
            products=product_cards(memory.ids_from_products_json(r["products_json"])),
            page_results=_saved_page_results(r["page_search_json"]),
            created_at=r["created_at"],
        )
        for r in rows
        if r["role"] in ("user", "assistant")
    ]


@app.delete("/api/chat/history")
def clear_chat_history(request: Request) -> dict:
    """Let a logged-in shopper erase their own saved chat history."""
    user = auth.current_user(request)
    if not user:
        raise HTTPException(401, "Log in to manage your chat history.")
    return {"deleted": memory.clear_history(user["id"])}
