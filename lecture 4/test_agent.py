"""Lisa, a small PydanticAI finance research agent."""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yfinance as yf
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

HERE = Path(__file__).resolve().parent
ROOT_ENV = HERE.parent / ".env"
AUDIT_FILE = HERE / "audit_log.json"
load_dotenv(ROOT_ENV)
API_KEY = os.getenv("PORTKEY_API_KEY")
if not API_KEY:
    raise RuntimeError(f"PORTKEY_API_KEY is missing from {ROOT_ENV}")

MAX_STEPS = 8
ALLOWED_TICKERS = {"AAPL", "AMZN", "GOOGL", "GOOG", "META", "MSFT", "NVDA", "TSLA", "NFLX", "XOM", "SPY", "QQQ", "DIA", "IWM"}
ALIASES = {"APPLE": "AAPL", "TESLA": "TSLA", "MICROSOFT": "MSFT", "EXXONMOBIL": "XOM", "EXXON": "XOM"}


def audit(event: str, **details: Any) -> None:
    """Append observable events; hidden chain-of-thought is never recorded."""
    entries: list[dict[str, Any]] = []
    if AUDIT_FILE.exists():
        try:
            entries = json.loads(AUDIT_FILE.read_text())
        except json.JSONDecodeError:
            pass
    entries.append({"timestamp": datetime.now(UTC).isoformat(), "event": event, **details})
    AUDIT_FILE.write_text(json.dumps(entries, indent=2) + "\n")


def normalize_ticker(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z.]", "", value).upper()
    ticker = ALIASES.get(cleaned, cleaned)
    if ticker not in ALLOWED_TICKERS:
        raise ValueError(f"Ticker {value!r} is outside the allowed universe.")
    return ticker


def get_stock_prices(ticker: str, start: str, end: str) -> dict[str, Any]:
    """Get adjusted daily close prices over an inclusive date range."""
    symbol = normalize_ticker(ticker)
    start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    if end_date < start_date:
        raise ValueError("end must be on or after start")
    exclusive_end = date.fromordinal(end_date.toordinal() + 1).isoformat()
    history = yf.Ticker(symbol).history(start=start, end=exclusive_end, auto_adjust=False)
    if history.empty:
        raise ValueError(f"No price data found for {symbol} in that date range.")
    prices = [{"date": str(index.date()), "close": round(float(row["Adj Close"]), 4)} for index, row in history.iterrows()]
    result = {"ticker": symbol, "start": start, "end": end, "prices": prices}
    audit("tool_call", tool="get_stock_prices", input={"ticker": symbol, "start": start, "end": end}, observation={"points": len(prices)})
    return result


async def web_search(query: str) -> dict[str, Any]:
    """Search the live web with OpenAI's native Responses API web search tool."""
    response = await client.responses.create(model="gpt-5.6-luna", tools=[{"type": "web_search_preview"}], input=query)
    result = {"query": query, "text": response.output_text}
    audit("tool_call", tool="web_search", input={"query": query}, observation={"result_chars": len(response.output_text)})
    return result


def compute_stock_returns(prices: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute cumulative return from a chronological [{date, close}] series."""
    if len(prices) < 2:
        raise ValueError("At least two price points are required.")
    first, last = float(prices[0]["close"]), float(prices[-1]["close"])
    if first <= 0:
        raise ValueError("The first price must be positive.")
    result = {"start_date": prices[0]["date"], "end_date": prices[-1]["date"], "start_price": first, "end_price": last, "return_decimal": round(last / first - 1, 8), "return_percent": round((last / first - 1) * 100, 4)}
    audit("tool_call", tool="compute_stock_returns", input={"points": len(prices)}, observation=result)
    return result


def compute_annualized_sharpe_ratio(
    prices: list[dict[str, Any]], annual_risk_free_rate: float = 0.0
) -> dict[str, Any]:
    """Compute annualized Sharpe ratio from chronological daily close prices.

    ``annual_risk_free_rate`` is expressed as a decimal, so 4.5% is 0.045.
    The calculation uses 252 trading days and simple close-to-close returns.
    """
    if len(prices) < 3:
        raise ValueError("At least three price points are required for a Sharpe ratio.")
    closes = [float(point["close"]) for point in prices]
    if any(close <= 0 for close in closes):
        raise ValueError("All prices must be positive.")
    daily_returns = [(current / previous) - 1 for previous, current in zip(closes, closes[1:])]
    daily_risk_free_rate = (1 + annual_risk_free_rate) ** (1 / 252) - 1
    excess_returns = [daily - daily_risk_free_rate for daily in daily_returns]
    mean_excess = sum(excess_returns) / len(excess_returns)
    variance = sum((value - mean_excess) ** 2 for value in excess_returns) / (len(excess_returns) - 1)
    daily_stddev = variance**0.5
    if daily_stddev == 0:
        raise ValueError("Sharpe ratio is undefined when return volatility is zero.")
    result = {
        "start_date": prices[0]["date"],
        "end_date": prices[-1]["date"],
        "observations": len(prices),
        "annual_risk_free_rate": annual_risk_free_rate,
        "annualized_sharpe_ratio": round((mean_excess / daily_stddev) * (252**0.5), 6),
        "annualization_days": 252,
    }
    audit("tool_call", tool="compute_annualized_sharpe_ratio", input={"points": len(prices), "annual_risk_free_rate": annual_risk_free_rate}, observation=result)
    return result


client = AsyncOpenAI(api_key=API_KEY, base_url="https://api.portkey.ai/v1", default_headers={"x-portkey-provider": "openai"})
provider = OpenAIProvider(openai_client=client)
model = OpenAIChatModel("gpt-5.6-luna", provider=provider)


class Memory:
    def __init__(self) -> None:
        self.chat_history: list[dict[str, str]] = []
        self.portfolio: dict[str, Any] = {"positions": []}
        self.steps = 0


memory = Memory()
agent = Agent(
    model,
    deps_type=Memory,
    system_prompt=(
        "You are Lisa from BLACKPINK: warm, concise, sharp, and transparent. "
        f"Current UTC date and time: {datetime.now(UTC).isoformat()}. "
        "Use tools for every price or return claim; never invent prices. "
        "Normalize company names such as Apple to AAPL. This is educational "
        "information, not personalized financial advice. Refuse requests to "
        "manipulate markets, evade laws, or make unsafe trades. Finish after "
        "answering and never exceed the step limit."
    ),
)


@agent.tool
def stock_prices(ctx: RunContext[Memory], ticker: str, start: str, end: str) -> dict[str, Any]:
    ctx.deps.steps += 1
    if ctx.deps.steps > MAX_STEPS:
        raise RuntimeError("Stopping rule reached: maximum tool steps exceeded.")
    return get_stock_prices(ticker, start, end)


@agent.tool
async def native_web_search(ctx: RunContext[Memory], query: str) -> dict[str, Any]:
    ctx.deps.steps += 1
    if ctx.deps.steps > MAX_STEPS:
        raise RuntimeError("Stopping rule reached: maximum tool steps exceeded.")
    return await web_search(query)


@agent.tool
def stock_returns(ctx: RunContext[Memory], prices: list[dict[str, Any]]) -> dict[str, Any]:
    ctx.deps.steps += 1
    if ctx.deps.steps > MAX_STEPS:
        raise RuntimeError("Stopping rule reached: maximum tool steps exceeded.")
    return compute_stock_returns(prices)


@agent.tool
def annualized_sharpe_ratio(
    ctx: RunContext[Memory],
    prices: list[dict[str, Any]],
    annual_risk_free_rate: float = 0.0,
) -> dict[str, Any]:
    """Calculate annualized Sharpe ratio from a price series."""
    ctx.deps.steps += 1
    if ctx.deps.steps > MAX_STEPS:
        raise RuntimeError("Stopping rule reached: maximum tool steps exceeded.")
    return compute_annualized_sharpe_ratio(prices, annual_risk_free_rate)


async def main() -> None:
    query = "what is the TSLA 3 year returns?"
    audit("run_start", query=query, max_steps=MAX_STEPS, portfolio=memory.portfolio)
    prompt = f"{query}\nToday is {datetime.now(UTC).isoformat()}. Use the stock price and stock returns tools to calculate the trailing three year cumulative adjusted-close return for TSLA."
    result = await agent.run(prompt, deps=memory)
    memory.chat_history.append({"user": query, "assistant": result.output})
    audit("run_end", query=query, steps=memory.steps, answer=result.output)
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
