"""Dash chat UI for the PydanticAI finance agent."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from dash import Dash, Input, Output, State, dcc, html, no_update

import test_agent


def message(text: str, role: str, tools: list[str] | None = None) -> html.Div:
    children: list[Any] = [html.Div(text, className="bubble"), html.Div("YOU" if role == "user" else "LISA · AI FINANCE DESK", className="meta")]
    if tools:
        children.insert(1, html.Div([html.Span("TOOLS USED", className="tool-label"), " · " + " · ".join(tools)], className="tool-used"))
    return html.Div(children, className=f"message {role}")


def run_agent(prompt: str) -> tuple[str, list[str]]:
    test_agent.memory.steps = 0
    before = len(json.loads(test_agent.AUDIT_FILE.read_text())) if test_agent.AUDIT_FILE.exists() else 0
    result = asyncio.run(test_agent.agent.run(prompt, deps=test_agent.memory))
    entries = json.loads(test_agent.AUDIT_FILE.read_text())[before:] if test_agent.AUDIT_FILE.exists() else []
    tools = list(dict.fromkeys(entry["tool"] for entry in entries if entry.get("event") == "tool_call"))
    return result.output, tools


app = Dash(__name__)
app.title = "LISA · Finance Chat"
app.layout = html.Div([
    html.Header([html.Div("BLACKPINK · FINANCE LAB", className="eyebrow"), html.H1("LISA"), html.P("Market moves, with receipts."), html.Div("● LIVE AGENT", className="live")], className="hero"),
    html.Main([
        html.Section([
            html.Div([html.Div("LISA", className="chat-name"), html.Div("PydanticAI finance analyst", className="chat-sub")], className="chat-head"),
            html.Div(id="chat-window", children=[message("Hey bestie ✦ Ask about a stock price, returns, Sharpe ratio, or market news.", "assistant")], className="chat-window"),
            dcc.Loading(html.Div(id="thinking", className="thinking", children="🦆 LISA is thinking…"), type="default", delay_show=250),
            html.Div([dcc.Textarea(id="chat-input", placeholder="Try: What is TSLA's 3 year Sharpe ratio?", rows=2, className="chat-input"), html.Button("SEND ↗", id="send", className="send")], className="composer"),
            html.Div("Enter to send · Shift+Enter for a new line", className="hint"),
            dcc.Store(id="history", data=[]),
        ], className="panel"),
        html.Aside([html.Div("SAFETY + MEMORY", className="eyebrow"), html.H2("Finance, with receipts."), html.P("Prices and calculations come from tools. Each run appends observable tool events to audit_log.json."), html.Div("● yfinance prices", className="note"), html.Div("● Sharpe + returns", className="note"), html.Div("● OpenAI native web search", className="note"), html.Div("● 8-step stop limit", className="note")], className="side"),
    ], className="layout"),
], className="page")


@app.callback(Output("chat-window", "children"), Output("thinking", "children"), Output("history", "data"), Input("send", "n_clicks"), State("chat-input", "value"), State("history", "data"), prevent_initial_call=True)
def chat(_clicks: int, text: str | None, history: list[dict[str, str]]) -> tuple[Any, Any, Any]:
    if not text or not text.strip():
        return no_update, no_update, no_update
    user_text = text.strip()
    try:
        answer, tools = run_agent(user_text)
        updated = history + [{"role": "user", "content": user_text}, {"role": "assistant", "content": answer}]
        return [message(item["content"], item["role"]) for item in updated[:-1]] + [message(answer, "assistant", tools)], "🦆 LISA is thinking…", updated
    except Exception as exc:
        return [message(user_text, "user"), message(f"I hit a snag: {exc}", "assistant")], "🦆 LISA is thinking…", history + [{"role": "user", "content": user_text}]


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=8050)
