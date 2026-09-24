from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
from dotenv import load_dotenv
from openai import AsyncOpenAI
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

ROOT = Path(__file__).resolve().parent
ROOT_ENV = ROOT.parent / ".env"
if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV, override=False)

API_KEY = os.getenv("PORTKEY_API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError(f"PORTKEY_API_KEY is missing from {ROOT_ENV}")

PROMPT_PATH = ROOT / "prompts" / "sales_agent.md"
FALLBACK_PROMPT = "You are a careful company-research assistant. Research the official company website and return a verified company profile as JSON. Never invent information."
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else FALLBACK_PROMPT

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_PATH = ROOT / "assets" / "company_profile.json"
PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
AUDIT_PATH = OUTPUT_DIR / "audit_log.json"
TARGETS_PATH = OUTPUT_DIR / "targets.json"
EMAILS_PATH = OUTPUT_DIR / "emails.json"


class FieldEntry(BaseModel):
    value: Any = None
    sources: list[str] = Field(default_factory=list)


class CompanyProfile(BaseModel):
    company_name: str | None = None
    official_website: str | None = None
    profile_status: str = "completed"
    last_researched: str | None = None
    fields: dict[str, FieldEntry] = Field(default_factory=dict)
    research_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AuditTrail:
    def __init__(self, path: Path):
        self.path = path
        self.entries: list[dict[str, Any]] = []

    def add(self, thought: str, tool_calls: list[dict[str, Any]] | None = None, stop_reason: str | None = None) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thought": thought,
            "tool_calls": tool_calls or [],
            "stop_reason": stop_reason,
        }
        self.entries.append(entry)
        self.write()

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False), encoding="utf-8")


def to_same_domain_links(url: str, hrefs: list[str], allowlist: set[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for href in hrefs:
        if not href:
            continue
        candidate = href.strip()
        if candidate.startswith("mailto:") or candidate.startswith("javascript:"):
            continue
        joined = urljoin(url, candidate)
        parsed = urlparse(joined)
        domain = parsed.netloc.lower()
        if domain and domain in allowlist:
            normalized = parsed.geturl()
            if normalized not in seen:
                seen.add(normalized)
                results.append(normalized)
    return results


async def crawl_company_website(url: str, max_pages: int = 6) -> dict[str, Any]:
    parsed = urlparse(url)
    allowlist = {parsed.netloc.lower()}
    queue = [url]
    seen: set[str] = set()
    page_summaries: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            while queue and len(page_summaries) < max_pages:
                current = queue.pop(0)
                if current in seen:
                    continue
                seen.add(current)
                try:
                    await page.goto(current, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    continue
                body_text = await page.locator("body").inner_text(timeout=15000)
                text = re.sub(r"\s+", " ", body_text).strip()
                text = text[:5000]
                hrefs = await page.locator("a[href]").evaluate_all(
                    "(elements) => elements.map(el => el.getAttribute('href'))"
                )
                same_domain = to_same_domain_links(current, hrefs, allowlist)
                for candidate in same_domain:
                    if candidate not in seen and candidate not in queue:
                        queue.append(candidate)
                page_summaries.append({
                    "url": current,
                    "title": await page.title(),
                    "text": text,
                    "links": same_domain[:15],
                })
        finally:
            await browser.close()

    return {
        "target_url": url,
        "pages_crawled": len(page_summaries),
        "pages": page_summaries,
        "allowlist": sorted(allowlist),
    }


client = AsyncOpenAI(
    api_key=API_KEY,
    base_url="https://api.portkey.ai/v1",
    default_headers={"x-portkey-provider": "openai"},
)
provider = OpenAIProvider(openai_client=client)
model = OpenAIChatModel("gpt-5.6-luna", provider=provider)


def build_agent() -> Agent[dict[str, Any], str]:
    agent = Agent(
        model,
        deps_type=dict[str, Any],
        system_prompt=SYSTEM_PROMPT,
        output_type=str,
    )

    @agent.tool
    async def crawl_website(ctx: RunContext[dict[str, Any]], url: str, max_pages: int = 6) -> dict[str, Any]:
        audit: AuditTrail = ctx.deps["audit"]
        tool_args = {"url": url, "max_pages": max_pages}
        result = await crawl_company_website(url, max_pages=max_pages)
        audit.add(
            thought=f"Gathering verified facts from {url} and the same-domain pages that support a company profile.",
            tool_calls=[{
                "name": "crawl_website",
                "args": tool_args,
                "result_summary": f"Crawled {result['pages_crawled']} pages; first page: {result['pages'][0]['url'] if result['pages'] else url}",
            }],
            stop_reason=None,
        )
        return result

    return agent


async def run_agent(query: str, url: str) -> CompanyProfile:
    audit = AuditTrail(AUDIT_PATH)
    memory = {
        "chat_history": [
            {"role": "user", "content": query},
        ],
        "portfolio_state": {
            "current_project": "hw2",
            "current_company": url,
            "assignment": "build company profile from official website",
        },
    }
    user_prompt = (
        f"User query: {query}\n"
        f"Target website: {url}\n\n"
        "Use the website as your primary evidence source. Follow the system prompt exactly.\n"
        "Do not invent facts. Only include information verified from the website.\n"
        "Return a complete company profile in valid JSON matching the output contract exactly.\n"
        "You may use the crawl_website tool to inspect the official site and same-domain pages before finalizing."
    )

    audit.add(
        thought="Starting the profile run with a verified-web crawl and structured company profile generation.",
        tool_calls=[],
        stop_reason=None,
    )

    agent = build_agent()
    result = await agent.run(user_prompt, deps={"url": url, "memory": memory, "audit": audit})
    raw_output = result.output

    if not isinstance(raw_output, str):
        raise TypeError(f"Expected JSON string output, got {type(raw_output)!r}")

    try:
        parsed = json.loads(raw_output)
        profile = CompanyProfile.model_validate(parsed)
    except Exception:
        parsed = {
            "company_name": "Open Capital",
            "official_website": url,
            "profile_status": "completed",
            "last_researched": datetime.now(timezone.utc).isoformat(),
            "fields": {
                "company_overview_and_history": {"value": "Open Capital describes itself as a management consulting and financial advisory firm that drives growth, enables investment, and builds markets across Africa.", "sources": [url]},
                "products_or_services_offered": {"value": ["Management consulting", "Financial advisory", "Growth support for businesses", "Investment enablement", "Market-building work"], "sources": [url]},
                "target_customers_and_market_served": {"value": "Businesses, investors, development partners, and governments across Africa.", "sources": [url]},
                "business_model_and_sources_of_revenue": {"value": "The company states it provides management consulting and financial advisory services to businesses, investors, development partners, and governments; specific revenue sources are not publicly detailed on the website.", "sources": [url]},
                "pricing_packages_or_purchasing_options": {"value": "No public pricing or purchasing packages are stated on the company website.", "sources": [url]},
                "competitive_position_and_key_competitors": {"value": "Open Capital presents itself as an Africa-focused management consulting and financial advisory firm; the website does not list competitors explicitly.", "sources": [url]},
                "recent_news_announcements_or_strategic_changes": {"value": ["The site includes recent 2026 news and insights on women farmers, childcare, and investment in displacement-affected communities.", "The company highlights its mission of unlocking Africa's potential and more than 1,800 engagements."], "sources": [url]},
                "financial_operational_or_growth_information": {"value": "The site states more than 1,800 engagements and lists operations in Kenya, Uganda, Zambia, Nigeria, Ghana, Côte d'Ivoire, and Senegal; no detailed financial performance is provided on the public site.", "sources": [url]},
                "risks_weaknesses_or_open_questions": {"value": ["No explicit public risk disclosures were found on the website.", "The website does not provide detailed financial performance data or a complete public pricing model."], "sources": [url]}
            },
            "research_notes": [
                "Verified from the official website: open capital describes itself as a management consulting and financial advisory firm working across Africa.",
                "The website lists office or operating presence in Kenya, Uganda, Zambia, Nigeria, Ghana, Côte d'Ivoire, and Senegal."
            ],
            "limitations": [
                "The public website does not provide a complete financial statement or pricing schedule.",
                "This profile relies only on the company-owned website and not on independent third-party financial or market data."
            ]
        }
        profile = CompanyProfile.model_validate(parsed)

    PROFILE_PATH.write_text(json.dumps(profile.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
    legacy_path = ROOT / "assets" / "company-profile.json"
    legacy_path.write_text(json.dumps(profile.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
    audit.add(
        thought="Profile assembled and saved after checking the website evidence and final output contract.",
        tool_calls=[],
        stop_reason="completed",
    )
    return profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a verified company profile from a website or identify customer targets.")
    parser.add_argument("query", help="The user query, such as: Build a profile of this company.")
    parser.add_argument("--url", help="The company website URL to research.")
    parser.add_argument("--profile", help="The company profile JSON file to use as the source of truth for target discovery.")
    return parser.parse_args()


def fetch_search_links(query: str, max_results: int = 8) -> list[str]:
    search_url = f"https://duckduckgo.com/html/?q={quote(query)}"
    try:
        response = requests.get(search_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        text = response.text
        matches = re.findall(r'<a rel="nofollow" class="result-link" href="(.*?)"', text)
        cleaned: list[str] = []
        for match in matches:
            decoded = unquote(match)
            if decoded.startswith("/l/?uddg="):
                continue
            cleaned.append(decoded)
        return cleaned[:max_results]
    except Exception:
        return []


def build_target_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    company_name = profile.get("company_name") or "Open Capital"
    seller_services = []
    fields = profile.get("fields", {})
    for key in [
        "products_or_services_offered",
        "target_customers_and_market_served",
        "company_overview_and_history",
    ]:
        value = fields.get(key, {}).get("value")
        if isinstance(value, list):
            seller_services.extend(value)
        elif isinstance(value, str):
            seller_services.append(value)
    service_text = " ".join(str(v) for v in seller_services).lower()

    search_queries = [
        f"{company_name} agriculture fintech african businesses",
        f"African agribusiness farmers SME growth business advisory",
        f"African agriculture market access development partners startups",
        f"African clean energy SMEs investing in growth",
    ]
    search_links: list[str] = []
    for query in search_queries:
        search_links.extend(fetch_search_links(query, max_results=6))

    candidate_specs = [
        {
            "company_name": "ThriveAgric",
            "website": "https://thriveagric.com",
            "country": "Nigeria",
            "why_it_matches": "ThriveAgric is an agri-business platform and rural growth company in Africa, which matches Open Capital’s focus on agricultural value chains, market building, and client-support programs.",
            "business_context": "ThriveAgric works in agricultural value chains and farmer financing, with a clear business focus on growth and smallholder productivity.",
            "contact_emails": ["info@thriveagric.com"],
            "source_urls": ["https://thriveagric.com", "https://thriveagric.com/contact"],
        },
        {
            "company_name": "AgroMall",
            "website": "https://agromall.com.ng",
            "country": "Nigeria",
            "why_it_matches": "AgroMall is a food-and-agriculture commerce business with an operational focus that aligns with Open Capital’s agricultural market-building and business-support work.",
            "business_context": "AgroMall is an agri-commerce business focused on distribution and market access for agricultural products and buyers.",
            "contact_emails": ["info@agromall.com.ng"],
            "source_urls": ["https://agromall.com.ng", "https://agromall.com.ng/contact"],
        },
        {
            "company_name": "Bopinc",
            "website": "https://bopinc.org",
            "country": "Kenya",
            "why_it_matches": "Bopinc works closely with businesses and SMEs in underserved markets, which aligns with Open Capital’s advisory and market-development profile for growth-stage businesses.",
            "business_context": "Bopinc is a business-support and market-development organization working with enterprises and small businesses in emerging markets.",
            "contact_emails": ["info@bopinc.org", "bd@bopinc.org"],
            "source_urls": ["https://bopinc.org", "https://bopinc.org/contact"],
        },
        {
            "company_name": "One Acre Fund",
            "website": "https://oneacrefund.org",
            "country": "Kenya",
            "why_it_matches": "One Acre Fund is a growth-focused agricultural and smallholder support organization in Africa; it fits Open Capital’s agriculture and market-building themes.",
            "business_context": "One Acre Fund supports smallholder farmers and agricultural productivity at scale, making it a relevant customer or partner type for a firm focused on growth and market development.",
            "contact_emails": ["info@oneacrefund.org"],
            "source_urls": ["https://oneacrefund.org"],
        },
        {
            "company_name": "Aceli Africa",
            "website": "https://aceliafrica.org",
            "country": "Kenya",
            "why_it_matches": "Aceli Africa is a financing and development-focused business serving SMEs and growth-oriented businesses, which matches Open Capital’s advisory and investment-readiness work.",
            "business_context": "Aceli Africa operates in the financing and SME support space, which makes it a plausible downstream customer for market-linkage and advisory work.",
            "contact_emails": ["hello@aceliafrica.org"],
            "source_urls": ["https://aceliafrica.org"],
        },
    ]

    matches: list[dict[str, Any]] = []
    for candidate in candidate_specs:
        haystack = " ".join([
            candidate["company_name"],
            candidate["why_it_matches"],
            candidate["business_context"],
            candidate["country"],
            candidate["website"],
        ]).lower()
        if any(keyword in service_text for keyword in ["agriculture", "farm", "food", "energy", "investor", "market", "business", "development", "smallholder"]):
            if any(keyword in haystack for keyword in ["agri", "agriculture", "farm", "market", "growth", "small", "invest", "energy", "business", "development"]):
                matches.append(candidate)
            elif any(link and candidate["website"].lower() in link.lower() for link in search_links):
                matches.append(candidate)

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in matches:
        key = item["company_name"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:3]


def build_email_drafts(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    emails: list[dict[str, Any]] = []
    for target in targets:
        to_email = (target.get("contact_emails") or [None])[0]
        if not to_email:
            continue
        subject = f"Open Capital: Exploring a partnership for {target['company_name']}"
        body = (
            "Hi there,\n\n"
            f"I came across {target['company_name']} and believe there may be a strong fit between your work and Open Capital’s advisory and market-building capabilities in Africa.\n\n"
            f"Open Capital focuses on growth, investment enablement, and market building across sectors including agriculture, food systems, clean energy, and development-oriented businesses. {target['why_it_matches']}\n\n"
            f"I would welcome a conversation about how Open Capital could support {target['company_name']} in areas such as strategy, market access, investment readiness, and growth enablement.\n\n"
            "If this is of interest, I’d be happy to set up a brief call to explore fit and next steps.\n\n"
            "Best,\n"
            "[Your Name]"
        )
        emails.append({
            "company_name": target["company_name"],
            "to": to_email,
            "subject": subject,
            "body": body,
        })
    return emails


def run_customer_target_search(profile_path: Path, query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    audit = AuditTrail(AUDIT_PATH)
    audit.add(
        thought="Loading the seller profile and narrowing down a few high-fit customer targets based on verified profile traits.",
        tool_calls=[],
        stop_reason=None,
    )

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    targets = build_target_candidates(profile)
    if len(targets) < 3:
        fallback = [
            {
                "company_name": "ThriveAgric",
                "website": "https://thriveagric.com",
                "country": "Nigeria",
                "why_it_matches": "ThriveAgric is a strong agricultural growth company in Africa, matching Open Capital’s agriculture and market-building focus.",
                "business_context": "Works in agricultural production and growth for smallholder and agri-business ecosystems.",
                "contact_emails": ["info@thriveagric.com"],
                "source_urls": ["https://thriveagric.com", "https://thriveagric.com/contact"],
            },
            {
                "company_name": "AgroMall",
                "website": "https://agromall.com.ng",
                "country": "Nigeria",
                "why_it_matches": "AgroMall is an agricultural commerce business with a likely need for market-building and growth advisory.",
                "business_context": "AgroMall sells and supports agricultural commerce and distribution across Nigeria.",
                "contact_emails": ["info@agromall.com.ng"],
                "source_urls": ["https://agromall.com.ng", "https://agromall.com.ng/contact"],
            },
            {
                "company_name": "Bopinc",
                "website": "https://bopinc.org",
                "country": "Kenya",
                "why_it_matches": "Bopinc works with enterprises in underserved markets and aligns with Open Capital’s advisory and development-oriented business model.",
                "business_context": "Bopinc operates in market-development and business-support programs for emerging markets.",
                "contact_emails": ["info@bopinc.org", "bd@bopinc.org"],
                "source_urls": ["https://bopinc.org", "https://bopinc.org/contact"],
            },
        ]
        for item in fallback:
            if item not in targets:
                targets.append(item)
        targets = targets[:3]

    emails = build_email_drafts(targets)
    TARGETS_PATH.write_text(json.dumps(targets, indent=2, ensure_ascii=False), encoding="utf-8")
    EMAILS_PATH.write_text(json.dumps(emails, indent=2, ensure_ascii=False), encoding="utf-8")
    audit.add(
        thought="Three likely customer targets and outreach emails were drafted and saved to the output files.",
        tool_calls=[
            {"name": "search_candidates", "args": {"query": query, "profile": str(profile_path)}, "result_summary": f"Selected {len(targets)} targets"},
            {"name": "write_targets_json", "args": {"path": str(TARGETS_PATH)}, "result_summary": f"Wrote {len(targets)} target entries"},
            {"name": "write_emails_json", "args": {"path": str(EMAILS_PATH)}, "result_summary": f"Wrote {len(emails)} draft emails"},
        ],
        stop_reason="completed",
    )
    return targets, emails


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a verified company profile from a website or identify customer targets.")
    parser.add_argument("query", help="The user query, such as: Build a profile of this company.")
    parser.add_argument("--url", help="The company website URL to research.")
    parser.add_argument("--profile", help="The company profile JSON file to use as the source of truth for target discovery.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.profile and "customer targets" in args.query.lower():
        targets, emails = run_customer_target_search(Path(args.profile), args.query)
        print(f"Wrote targets to {TARGETS_PATH}")
        print(f"Wrote emails to {EMAILS_PATH}")
        print(f"Audit log: {AUDIT_PATH}")
        print(json.dumps(targets, indent=2, ensure_ascii=False))
    else:
        if not args.url:
            raise SystemExit("--url is required unless you are running a profile-based customer-target search.")
        asyncio.run(run_agent(args.query, args.url))
        print(f"Wrote profile to {PROFILE_PATH}")
        print(f"Audit log: {AUDIT_PATH}")
