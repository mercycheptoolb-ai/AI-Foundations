"""Tools the Campus Customs agent can call.

All tools are read-only. The product tools touch only the catalogue and inventory
tables. The two customer tools (Problem 8) read only the logged-in shopper's own users
row and chat_messages, filtered by the session's user_id. No tool can read passwords,
sessions, or other shoppers' data.
"""

import json
import re
import sqlite3

from pydantic_ai import ModelRetry, RunContext

import memory
from db import db
from models import (
    LOW_STOCK_THRESHOLD,
    CatalogueOverview,
    ChatHistorySearch,
    CustomerProfileInfo,
    PageContext,
    PastMessage,
    ShopDeps,
    ViewedProduct,
    ViewingContext,
    Category,
    CategorySummary,
    MatchMethod,
    PriceInfo,
    PriceQuote,
    ProductDescription,
    ProductMatch,
    SearchResults,
    AlternativeMatch,
    Alternatives,
    PageSearch,
    QuoteItem,
    QuoteLine,
    Size,
    SizeStock,
    SortOrder,
    StockInfo,
    StockStatus,
)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_RESULTS = 15
RESIDENTIAL_COLLEGES = [
    "Benjamin Franklin", "Berkeley", "Branford", "Davenport", "Ezra Stiles", "Grace Hopper",
    "Jonathan Edwards", "Morse", "Pauli Murray", "Pierson", "Saybrook", "Silliman",
    "Timothy Dwight", "Trumbull",
]
SCHOOLS = [
    "Divinity School", "School of Architecture", "School of Art", "School of Drama",
    "School of Engineering", "Forest School", "Law School", "School of Management",
    "School of Medicine", "School of Music", "School of Nursing", "School of Public Health",
]

# ---------- display cleanup ----------
# Catalogue names were generated from file names ("Ua Mens Tech L S 2 0"), and a
# few descriptions are placeholder stubs. Fix them for display only.
_NAME_FIXES = [
    (r"\bUa\b", "UA"), (r"\bCreqneck\b", "Crewneck"), (r"\b1 4 Zip\b", "1/4 Zip"),
    (r"\bL S 2 0\b", "L/S 2.0"), (r"\bMens\b", "Men's"), (r"\bT Shirt\b", "T-Shirt"),
    (r"\bVs\b", "vs."), (r"\bOf\b", "of"),
]
STUB_MARKER = "filename-based stub"


def display_name(name: str) -> str:
    for pattern, repl in _NAME_FIXES:
        name = re.sub(pattern, repl, name)
    return name


def display_description(description: str) -> str:
    return "" if STUB_MARKER in description else description


def category_for(garment_type: str) -> Category | None:
    """Map one of the 22 messy garment_type spellings onto a clean category."""
    g = garment_type.lower()
    if "hood" in g:
        return "hoodie"
    if "quarter-zip" in g or "1/4" in g:
        return "quarter-zip"
    if "t-shirt" in g:
        return "t-shirt"
    if "jacket" in g:
        return "jacket"
    if "long-sleeve" in g:
        return "long-sleeve"
    if "crew" in g or "mockneck" in g or "sweater" in g:
        return "crewneck"
    return None


# ---------- query parsing ----------

# Multi-word phrases folded into one token before splitting.
_PHRASES = [
    (r"long[\s-]?sleeves?", "long-sleeve"),
    (r"(?:quarter|1/4|half)[\s-]?zips?", "quarter-zip"),
    (r"\bt[\s-]?shirts?\b", "t-shirt"),
    (r"crew[\s-]?necks?", "crewneck"),
    (r"full[\s-]?zips?", "full-zip"),
]
# Spelling variants mapped to one form (applied to both query and product words).
SYNONYMS = {
    "grey": "gray", "tee": "t-shirt", "tshirt": "t-shirt", "hoody": "hoodie", "hooded": "hoodie",
    "hood": "hoodie", "quarterzip": "quarter-zip", "longsleeve": "long-sleeve",
}
# Query words that point at a category. ("shirt" alone is too vague to count.)
CATEGORY_WORDS: dict[str, Category] = {
    "hoodie": "hoodie", "crewneck": "crewneck", "mockneck": "crewneck", "t-shirt": "t-shirt",
    "quarter-zip": "quarter-zip", "jacket": "jacket", "fleece": "jacket", "bomber": "jacket",
    "coat": "jacket", "long-sleeve": "long-sleeve",
}
# Words that describe a kind of item rather than name a specific product. A product name
# lookup may leave these unmatched; every other word must match.
GENERIC_TERMS = set(CATEGORY_WORDS) | {
    "shirt", "top", "sweatshirt", "pullover", "zip", "full-zip", "sweater", "logo", "crest",
    "men", "women", "unisex", "new", "navy", "blue", "gray", "white", "black", "red", "green",
    "yellow", "pink", "purple", "orange", "gold", "heather", "light", "dark", "maroon", "crimson",
}
STOPWORDS = {
    "a", "about", "above", "all", "also", "an", "and", "any", "anything", "apparel", "are",
    "around", "at", "available", "below", "best", "buy", "by", "can", "carry", "cheap",
    "cheaper", "cheapest", "clothes", "clothing", "college", "color", "colors", "cool", "cost",
    "could", "do", "does", "dollar", "dollars", "expensive", "find", "for", "from", "gear", "get",
    "gift", "good", "got", "great", "have", "i", "in", "is", "it", "item", "items", "just", "less",
    "like", "looking", "me", "merch", "more", "most", "my", "need", "nice", "of", "on", "one",
    "ones", "or", "over", "please", "price", "priced", "residential", "sell", "show", "size",
    "sizes", "some", "something", "stock", "than", "that", "the", "them", "they", "thing",
    "things", "this", "to", "under", "university", "usd", "want", "what", "which", "with",
    "would", "yale", "you", "your",
}


def _norm(word: str) -> str:
    word = SYNONYMS.get(word, word)
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = SYNONYMS.get(word[:-1], word[:-1])  # hoodies -> hoodie, brooks -> brook
    return word


def _fold_phrases(text: str) -> str:
    text = re.sub(r"['’]s\b", "", text.lower())  # possessives: "dad's" -> "dad"
    text = text.replace("'", "").replace("’", "")
    for pattern, repl in _PHRASES:
        text = re.sub(pattern, repl, text)
    return text


def _words(text: str) -> set[str]:
    """Whole words in a product field (hyphenated words also count by their parts)."""
    out: set[str] = set()
    for w in re.findall(r"[a-z0-9/-]+", _fold_phrases(text)):
        w = w.strip("-")
        out.add(_norm(w))
        if "-" in w:
            out.update(_norm(p) for p in w.split("-") if p)
    return out


def _query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for w in re.findall(r"[a-z0-9/-]+", _fold_phrases(query)):
        w = _norm(w.strip("-"))
        if not w or w in STOPWORDS or len(w) < 2 or (w.isdigit() and len(w) <= 3):
            continue  # short numbers are prices or sizes, not keywords
        if w not in terms:
            terms.append(w)
    return terms


# ---------- data helpers ----------

def _stock_by_product(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    stock: dict[str, dict[str, int]] = {}
    for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    return stock


def _in_stock_sizes(sizes: dict[str, int]) -> list[str]:
    return [s for s in SIZE_ORDER if sizes.get(s, 0) > 0]


def _short(text: str, limit: int = 140) -> str:
    if not text:
        return "(no description available)"
    return text if len(text) <= limit else text[: text.rfind(" ", 0, limit)] + "…"


def body_color(row: sqlite3.Row) -> str | None:
    """The garment's own color. The catalogue's colors list is every color visible on the
    ONE item: body color first, then logo/print colors."""
    colors = json.loads(row["colors"])
    return colors[0] if colors else None


def _term_hits(row: sqlite3.Row, terms: list[str]) -> tuple[set[str], set[str], int]:
    """(terms matched anywhere, terms matched in the name, weighted score)."""
    fields = [
        (3, _words(row["name"])),
        (2, _words(" ".join(json.loads(row["search_tags"])))),
        (2, _words(body_color(row) or "")),
        (2, _words(row["garment_type"])),
        (1, _words(row["description"])),
    ]
    hit: set[str] = set()
    score = 0
    for t in terms:
        w = sum(weight for weight, words in fields if t in words)
        if w:
            hit.add(t)
            score += w
    return hit, {t for t in terms if t in fields[0][1]}, score


def _match_score(row: sqlite3.Row, terms: list[str]) -> tuple[int, int]:
    """(distinct query terms matched, weighted score). Name hits count most."""
    if not terms:
        return 0, 0
    hit, _, score = _term_hits(row, terms)
    return len(hit), score


def _resolve(product: str) -> tuple[sqlite3.Row, MatchMethod]:
    """Find one catalogue row from a product_id or a product name.

    Raises ModelRetry (the model sees the message and tries again) when nothing
    matches or the name is ambiguous, rather than guessing the wrong product.
    """
    text = product.strip()
    if not text:
        raise ModelRetry("Pass a product_id (from search results) or a product name.")
    with db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (text,)).fetchone()
        if row:
            return row, "product_id"
        rows = conn.execute("SELECT * FROM catalogue").fetchall()

    lowered = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    for r in rows:
        if lowered in (r["name"].lower(), display_name(r["name"]).lower()) or slug == r["product_id"]:
            return r, "name"

    terms = _query_terms(text)
    key_terms = {t for t in terms if t not in GENERIC_TERMS}
    cats = {CATEGORY_WORDS[t] for t in terms if t in CATEGORY_WORDS}
    category = cats.pop() if len(cats) == 1 else None

    scored = []
    for r in rows:
        hit, in_name, score = _term_hits(r, terms)
        if hit:
            scored.append((r, hit, in_name, score))
    scored.sort(key=lambda x: (-len(x[1]), -x[3], x[0]["name"]))
    options = "; ".join(f"{display_name(r['name'])} (product_id {r['product_id']})" for r, *_ in scored[:5])

    # A candidate must match every distinctive word (college, school, brand, team...)
    # and, if the shopper named a kind of item, be that kind of item.
    candidates = [
        x for x in scored
        if key_terms <= x[1] and (category is None or category_for(x[0]["garment_type"]) == category)
    ]
    if key_terms:
        in_name = [x for x in candidates if key_terms <= x[2]]
        if len(in_name) == 1:
            candidates = in_name  # e.g. "dad hoodie": only one hoodie has "Dad" in its name
    if len(candidates) == 1:
        return candidates[0][0], "closest_match"
    if not candidates:
        raise ModelRetry(
            f"No product matches {product!r}."
            + (f" Closest partial matches: {options}." if options else "")
            + " Tell the shopper we don't carry that exact item (offer close matches if relevant), or search again."
        )
    many = "; ".join(f"{display_name(r['name'])} (product_id {r['product_id']})" for r, *_ in candidates[:6])
    raise ModelRetry(
        f"{product!r} could be several products: {many}. Call again with the exact product_id, "
        "or mention them and ask the shopper which one they mean."
    )


def _status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK_THRESHOLD else "in_stock"


# ---------- tools ----------

def rank_products(
    query: str = "",
    category: Category | None = None,
    color: str | None = None,
    size: Size | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    sort: SortOrder = "relevance",
) -> tuple[list[tuple], dict[str, dict[str, int]], list[str]]:
    """Filter and rank the whole catalogue. Shared by the search tool (top 15 for the model)
    and by the page grid (all matches for the website), so both use the same logic.

    Returns ([(row, matched_terms, score, in_stock, size_ok), ...] best first, stock, terms).
    """
    terms = _query_terms(query)
    hinted: Category | None = None
    if category is None:
        cats = {CATEGORY_WORDS[t] for t in terms if t in CATEGORY_WORDS}
        if len(cats) == 1:
            hinted = cats.pop()  # "hoodies under $60" -> category filter
    color_l = _norm(color.lower().strip()) if color else None

    with db() as conn:
        stock = _stock_by_product(conn)
        rows = conn.execute("SELECT * FROM catalogue").fetchall()

    def run(cat_filter: Category | None, used: list[str]) -> list[tuple]:
        found = []
        for r in rows:
            body = (body_color(r) or "").lower()
            if cat_filter and category_for(r["garment_type"]) != cat_filter:
                continue
            if color_l and not (color_l in _words(body) or color_l in body):
                continue  # match the garment color, not logo colors
            if max_price is not None and r["price"] > max_price:
                continue
            if min_price is not None and r["price"] < min_price:
                continue
            matched, score = _match_score(r, used)
            if used and matched == 0:
                continue
            sizes = stock.get(r["product_id"], {})
            in_stock = bool(_in_stock_sizes(sizes))
            size_ok = None if size is None else sizes.get(size, 0) > 0
            found.append((r, matched, score, in_stock, size_ok))
        return found

    # When a category filter is active, words naming that category ("hoodie") are already
    # covered by the filter. Left in as keywords they would match every item in the category,
    # so "Champion hoodies" would return all 27 hoodies instead of the 2 Champion ones.
    cat = category or hinted
    used = [t for t in terms if not (cat and CATEGORY_WORDS.get(t) == cat)]
    found = run(cat, used)
    if not found and hinted:
        # The guessed category was wrong ("Morse hoodie": no Morse hoodies). Search every
        # category for the distinctive words instead.
        used = [t for t in terms if t not in CATEGORY_WORDS] or terms
        found = run(None, used)
    terms = used

    def key(item: tuple):
        r, matched, score, in_stock, size_ok = item
        price = r["price"] if sort == "price_low_to_high" else -r["price"] if sort == "price_high_to_low" else 0
        # Best keyword match first (so a named product stays on top even if it's sold out
        # in the requested size, and equally good matches stay together), then in-size and
        # in-stock items first.
        relevance = -score if sort == "relevance" and terms else 0
        return (-matched, relevance, size_ok is False, not in_stock, price, -score, r["name"])

    found.sort(key=key)
    return found, stock, terms


def search_products(
    query: str = "",
    category: Category | None = None,
    color: str | None = None,
    size: Size | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    sort: SortOrder = "relevance",
    limit: int = 8,
) -> SearchResults:
    """Search the Campus Customs catalogue: use it when the shopper is browsing or hasn't
    named a specific product, and before recommending products.

    For a product the shopper named, skip this and call get_price, check_stock,
    get_product_description, or price_quote directly with the name.

    Args:
        query: Keywords, e.g. "Brooks Brothers bomber", "Branford", "baseball", "vintage bulldog", "dad". Leave empty to browse by filters only.
        category: Optional product category filter.
        color: Optional garment color filter, e.g. "navy", "gray", "white" (matches the item's own color, not logo colors).
        size: Optional size. Products sold out in this size are still returned (after in-size products with an equally good keyword match), flagged requested_size_in_stock=false.
        max_price: Optional maximum price in USD.
        min_price: Optional minimum price in USD.
        sort: "relevance" (default), or sort by price, e.g. for "cheapest" / "most expensive" questions.
        limit: Max results to return (1-15).
    """
    limit = max(1, min(limit, MAX_RESULTS))
    found, stock, terms = rank_products(query, category, color, size, max_price, min_price, sort)
    matches = [
        ProductMatch(
            product_id=r["product_id"],
            name=display_name(r["name"]),
            category=category_for(r["garment_type"]),
            garment_type=r["garment_type"],
            price=r["price"],
            garment_color=body_color(r),
            short_description=_short(display_description(r["description"])),
            in_stock_sizes=_in_stock_sizes(stock.get(r["product_id"], {})),
            requested_size_in_stock=size_ok,
        )
        for r, _, _, _, size_ok in found[:limit]
    ]
    notes = []
    if not matches:
        notes.append("No products matched. Try fewer filters or different keywords before telling the shopper we don't carry it.")
    elif len(found) > limit:
        notes.append(f"Showing the top {limit} of {len(found)} matches.")
    if terms and len(found) > 1 and found[0][1:3] == found[1][1:3]:
        tied = [display_name(x[0]["name"]) for x in found if x[1:3] == found[0][1:3]][:4]
        notes.append(f"These match the query equally well: {'; '.join(tied)}. If the shopper named one product, mention them all or ask which one they mean.")
    in_size = sum(1 for x in found if x[4]) if size else None
    if size and found and in_size == 0:
        notes.append(f"Every match is sold out in size {size} (requested_size_in_stock=false).")
    elif size and in_size != len(found):
        notes.append(
            f"{in_size} of the {len(found)} matches are in stock in size {size}; the rest are sold out "
            f"in {size} (requested_size_in_stock=false). If you put these on the page, say {in_size}: "
            "only in-size items appear on the grid."
        )
    return SearchResults(
        matches=matches, total_found=len(found), in_size_found=in_size, note=" ".join(notes) or None
    )


def get_product_description(product: str) -> ProductDescription:
    """Look up a product's description, color, and type from the catalogue.

    Call this when the shopper asks what a product looks like, what color it is, or for
    details about it.

    Args:
        product: The product_id (best, from search results) or the product's name.
    """
    row, matched_by = _resolve(product)
    return ProductDescription(
        product_id=row["product_id"],
        name=display_name(row["name"]),
        matched_by=matched_by,
        category=category_for(row["garment_type"]),
        garment_type=row["garment_type"],
        description=display_description(row["description"]) or None,
        garment_color=body_color(row),
        logo_colors=json.loads(row["colors"])[1:],
    )


def get_price(product: str) -> PriceInfo:
    """Look up a product's current price from the catalogue.

    Call this for EVERY price question ("how much is…?", "is it under $50?"). Never state a
    price you didn't get from this tool or from search results in this turn.

    Args:
        product: The product_id (best, from search results) or the product's name.
    """
    row, matched_by = _resolve(product)
    return PriceInfo(
        product_id=row["product_id"],
        name=display_name(row["name"]),
        matched_by=matched_by,
        price=row["price"],
        price_display=f"${row['price']:,.2f}",
    )


def price_quote(items: list[QuoteItem], budget: float | None = None) -> PriceQuote:
    """Add up the cost of several items (and compare with a budget), using catalogue prices.

    Call this for ANY total: "how much for 2 hoodies and a tee?", "12 of these for my team",
    "can I get X and Y with $100?". Quote total_display and remaining_budget from the result.

    Args:
        items: Products and how many of each, e.g. [{"product": "yale-dad-hoodie", "quantity": 2}].
        budget: The shopper's budget in USD, if they gave one.
    """
    lines = []
    for item in items:
        row, matched_by = _resolve(item.product)
        line_total = round(row["price"] * item.quantity, 2)
        lines.append(QuoteLine(
            product_id=row["product_id"],
            name=display_name(row["name"]),
            matched_by=matched_by,
            quantity=item.quantity,
            unit_price=row["price"],
            line_total=line_total,
        ))
    total = round(sum(line.line_total for line in lines), 2)
    remaining = round(budget - total, 2) if budget is not None else None
    return PriceQuote(
        lines=lines,
        total=total,
        total_display=f"${total:,.2f}",
        budget=budget,
        remaining_budget=remaining,
        within_budget=None if budget is None else remaining >= 0,
    )


def check_stock(product: str, size: Size | None = None) -> StockInfo:
    """Look up how many units of a product are in stock, by size.

    Call this for EVERY availability question ("do you have it in M?", "how many are
    left?", "is it in stock?"), every time it's asked; stock changes, so never reuse an
    earlier answer. If the shopper names a size, pass it.

    Args:
        product: The product_id (best, from search results) or the product's name.
        size: The size the shopper asked about, if any (XS, S, M, L, XL, XXL).
    """
    row, matched_by = _resolve(product)
    with db() as conn:
        quantities = {
            r["size"]: r["quantity"]
            for r in conn.execute(
                "SELECT size, quantity FROM inventory WHERE product_id = ?", (row["product_id"],)
            )
        }
    sizes = [
        SizeStock(size=sz, quantity=quantities[sz], status=_status(quantities[sz]))
        for sz in SIZE_ORDER
        if sz in quantities
    ]
    in_stock = [x.size for x in sizes if x.quantity > 0]
    sold_out = [x.size for x in sizes if x.quantity <= 0]
    name = display_name(row["name"])
    available = ", ".join(f"{x.size} ({x.quantity})" for x in sizes if x.quantity > 0)

    requested_qty = quantities.get(size, 0) if size else None
    if size is None:
        summary = f"{name}: in stock in {available}." if in_stock else f"{name} is sold out in every size."
        if in_stock and sold_out:
            summary += f" Sold out in {', '.join(sold_out)}."
    elif requested_qty <= 0:
        summary = f"{name} is SOLD OUT in size {size}."
        summary += f" Still in stock: {available}." if in_stock else " It is sold out in every size."
    elif requested_qty <= LOW_STOCK_THRESHOLD:
        summary = f"{name}: only {requested_qty} left in size {size}."
    else:
        summary = f"{name}: {requested_qty} in stock in size {size}."

    return StockInfo(
        product_id=row["product_id"],
        name=name,
        matched_by=matched_by,
        requested_size=size,
        requested_size_quantity=requested_qty,
        requested_size_status=_status(requested_qty) if size else None,
        sizes=sizes,
        in_stock_sizes=in_stock,
        sold_out_sizes=sold_out,
        total_units=sum(x.quantity for x in sizes),
        summary=summary,
    )


def catalogue_overview() -> CatalogueOverview:
    """Summarize what the shop sells: categories with counts and price ranges, sizes offered,
    and which residential colleges and schools have their own gear.

    Use this for broad questions like "what do you sell?", "what price range do hoodies
    cover?", or "do you have Silliman / residential college gear?".
    """
    with db() as conn:
        rows = conn.execute("SELECT name, garment_type, price FROM catalogue").fetchall()
    by_cat: dict[str, list[float]] = {}
    for r in rows:
        by_cat.setdefault(category_for(r["garment_type"]) or "other", []).append(r["price"])
    names = [r["name"] for r in rows]
    colleges = [c for c in RESIDENTIAL_COLLEGES if any(c.lower() in n.lower() for n in names)]
    schools = [sc for sc in SCHOOLS if any(sc.lower() in n.lower() for n in names)]
    return CatalogueOverview(
        total_products=len(rows),
        categories=[
            CategorySummary(category=c, product_count=len(p), min_price=min(p), max_price=max(p))
            for c, p in sorted(by_cat.items(), key=lambda kv: -len(kv[1]))
        ],
        sizes_offered=SIZE_ORDER,
        colleges_with_merch=colleges,
        colleges_without_merch=[c for c in RESIDENTIAL_COLLEGES if c not in colleges],
        schools_with_merch=schools,
    )


# ---------- similar items (Problem 9) ----------

# Words too common to say two products are alike ("yale", "sweatshirt", "logo"...).
_NOT_DISTINCTIVE = GENERIC_TERMS | STOPWORDS | {
    "campus", "customs", "university", "yale", "sweatshirt", "long-sleeve", "long", "sleeve",
    "short", "front", "chest", "left", "lettering", "graphic", "print", "printed", "style",
    "merch", "classic", "cotton", "apparel", "ribbed", "cuffs", "hem", "collar", "pocket",
    # garment construction words: they describe the cut, not a theme
    "tri-blend", "double-knit", "zip-up", "full-zip", "quarter-zip", "reverse-weave", "text",
    "ivy", "league", "charcoal", "cream", "ivory", "coral", "multicolor", "maroon",
    "full", "quarter", "zip", "kangaroo", "drawstring", "hood", "crew", "neck", "pullover",
    "tri", "blend", "double", "knit", "fleece", "reverse", "weave", "raglan", "heavyweight",
    "men", "mens", "women", "unisex", "performance", "tech", "1/4", "campu", "custom",
}


def _theme_words(row: sqlite3.Row) -> set[str]:
    words = _words(row["name"]) | _words(" ".join(json.loads(row["search_tags"])))
    return {w for w in words if w not in _NOT_DISTINCTIVE and len(w) > 2 and not w.isdigit()}


FAMILY_WORDS = {"dad", "mom", "grandma", "grandpa", "grandmother", "grandfather", "sister", "brother", "aunt", "uncle", "parent", "family"}


def _series(row: sqlite3.Row) -> set[str]:
    """Named collections a shopper might want more of: a residential college, a school, or
    the family line (Yale Dad / Mom / Grandpa...)."""
    name = row["name"].lower()
    found = {c for c in RESIDENTIAL_COLLEGES + SCHOOLS if c.lower() in name}
    if set(re.findall(r"[a-z]+", name)) & FAMILY_WORDS:
        found.add("family")
    return found


def _label(stem: str, *rows: sqlite3.Row) -> str:
    """Show a shared theme as it's written in a product name ("Brooks", not the stem "brook")."""
    for r in rows:
        for word in re.findall(r"[A-Za-z][A-Za-z'-]+", display_name(r["name"])):
            if _norm(word.lower()) == stem:
                return word
    return stem.title()


def find_alternatives(product: str, size: Size | None = None, limit: int = 4) -> Alternatives:
    """Find similar products that ARE in stock (in the shopper's size), ranked by how alike
    they are: same category, shared theme (brand, residential college, team, design), same
    garment color, similar price.

    Call it when a product is sold out in the size the shopper wants (or in every size), or
    when they ask for "something similar" / "other options". Offer 2-3 of the results.

    Args:
        product: The product_id (best) or name of the product they wanted.
        size: The shopper's size, if known (XS, S, M, L, XL, XXL). Results are in stock in it.
        limit: Max alternatives to return (1-6).
    """
    target, _ = _resolve(product)
    limit = max(1, min(limit, 6))
    with db() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
        stock = _stock_by_product(conn)
    cat = category_for(target["garment_type"])
    themes = _theme_words(target)
    series = _series(target)
    color = (body_color(target) or "").lower()

    scored = []
    for r in rows:
        if r["product_id"] == target["product_id"]:
            continue
        sizes = stock.get(r["product_id"], {})
        if (size and sizes.get(size, 0) <= 0) or not _in_stock_sizes(sizes):
            continue  # only suggest things they can actually buy
        reasons, score = [], 0.0
        if cat and category_for(r["garment_type"]) == cat:
            score += 5
            reasons.append(f"also a {cat}")
        same_series = series & _series(r)
        if same_series:
            score += 4
            s = next(iter(same_series))
            reasons.append("also from the Yale Dad / Mom family line" if s == "family" else f"also {s}")
        shared = sorted(themes & _theme_words(r))
        if shared and not same_series:
            score += 2.5 * min(len(shared), 3)
            reasons.append("also " + " / ".join(_label(w, target, r) for w in shared[:2]))
        r_color = (body_color(r) or "").lower()
        if color and r_color and (color in r_color or r_color in color):
            score += 1
            reasons.append(f"also {r_color}")
        diff = abs(r["price"] - target["price"])
        score -= diff / 20
        if diff <= 10:
            reasons.append("similar price")
        if score > 0:
            scored.append((score, r, reasons, bool(same_series)))
    in_size = lambda r: stock.get(r["product_id"], {}).get(size, 0) if size else sum(stock.get(r["product_id"], {}).values())  # noqa: E731
    scored.sort(key=lambda x: (-x[0], abs(x[1]["price"] - target["price"]), -in_size(x[1]), x[1]["name"]))
    top = scored[:limit]
    # Variety: if something from the same college / school / family line is in stock but
    # didn't make the cut (other categories rank lower), give it the last slot.
    if series and not any(x[3] for x in top):
        extra = next((x for x in scored[limit:] if x[3]), None)
        if extra and top:
            top[-1] = extra

    matches = [
        AlternativeMatch(
            product_id=r["product_id"],
            name=display_name(r["name"]),
            category=category_for(r["garment_type"]),
            price=r["price"],
            garment_color=body_color(r),
            in_stock_sizes=_in_stock_sizes(stock.get(r["product_id"], {})),
            requested_size_quantity=stock.get(r["product_id"], {}).get(size) if size else None,
            why_similar="; ".join(reasons) or "similar item",
        )
        for _, r, reasons, _ in top
    ]
    return Alternatives(
        for_product_id=target["product_id"],
        for_product_name=display_name(target["name"]),
        size=size,
        matches=matches,
        note=None if matches else f"Nothing similar is in stock{' in size ' + size if size else ''}.",
    )


# ---------- customer memory tools (Problem 8) ----------
# Both read ONLY ctx.deps.customer, which main.py fills from the session cookie, so the
# agent can see the logged-in shopper's own account and chats and nobody else's.

def get_customer_profile(ctx: RunContext[ShopDeps]) -> CustomerProfileInfo:
    """Look up the logged-in shopper's own account: name, email, customer since, and how much
    chat history is saved.

    Use it when the shopper asks about their account ("what email is my account under?",
    "how long have I been a customer?"). Returns logged_in=false for guests.
    """
    c = ctx.deps.customer
    if c is None:
        return CustomerProfileInfo(logged_in=False)
    count, first = memory.message_stats(c.user_id)
    return CustomerProfileInfo(
        logged_in=True,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        member_since=c.member_since,
        saved_messages=count,
        first_chat_at=first,
    )


def search_chat_history(ctx: RunContext[ShopDeps], query: str = "", limit: int = 6) -> ChatHistorySearch:
    """Search this shopper's OWN earlier chats with you, including ones older than the recent
    messages you can already see.

    Use it for "what was that hoodie you recommended last time?" or "what did I ask about
    before?". Past prices and stock may be out of date: look them up again before quoting.

    Args:
        query: Words to look for, e.g. "bomber", "gift dad". Leave empty for the latest messages.
        limit: Max messages to return (1-10).
    """
    c = ctx.deps.customer
    if c is None:
        return ChatHistorySearch(
            logged_in=False, matches=[], note="Guest: no saved history. Suggest logging in to keep chats."
        )
    rows = memory.search_messages(c.user_id, query, max(1, min(limit, 10)))
    names = _names_for({pid for r in rows for pid in memory.ids_from_products_json(r["products_json"])})
    matches = [
        PastMessage(
            role=r["role"],
            content=r["content"] if len(r["content"]) <= 400 else r["content"][:400] + "…",
            created_at=r["created_at"],
            products_shown=[names[pid] for pid in memory.ids_from_products_json(r["products_json"]) if pid in names],
        )
        for r in rows
    ]
    return ChatHistorySearch(
        logged_in=True,
        matches=matches,
        note=None if matches else "No earlier messages matched.",
    )


def _names_for(product_ids: set[str]) -> dict[str, str]:
    if not product_ids:
        return {}
    ids = list(product_ids)
    with db() as conn:
        marks = ",".join("?" * len(ids))
        return {
            r["product_id"]: display_name(r["name"])
            for r in conn.execute(f"SELECT product_id, name FROM catalogue WHERE product_id IN ({marks})", ids)
        }


ALL_TOOLS = [
    search_products,
    get_product_description,
    get_price,
    check_stock,
    price_quote,
    find_alternatives,
    catalogue_overview,
    get_customer_profile,
    search_chat_history,
]


# ---------- page context (Problem 8) ----------

GRID_CONTEXT_LIMIT = 12  # how many grid cards to name in the agent's context


def resolve_page(page: PageContext | None) -> ViewingContext:
    """Turn the browser's page context into facts from the database.

    Only product ids are taken from the browser, and they must exist in the catalogue.
    Names come from the catalogue, so page context can't smuggle text into the prompt.
    """
    if page is None:
        return ViewingContext()
    ctx = ViewingContext(page_type=page.page_type, path=page.path[:200])
    wanted = ([page.product_id] if page.product_id else []) + page.grid_product_ids
    if not wanted:
        return ctx
    with db() as conn:
        marks = ",".join("?" * len(set(wanted)))
        rows = {
            r["product_id"]: r
            for r in conn.execute(
                f"SELECT product_id, name, garment_type FROM catalogue WHERE product_id IN ({marks})",
                list(set(wanted)),
            )
        }

    def viewed(pid: str) -> ViewedProduct:
        r = rows[pid]
        return ViewedProduct(product_id=pid, name=display_name(r["name"]), garment_type=r["garment_type"])

    if page.page_type == "product" and page.product_id in rows:
        ctx.product = viewed(page.product_id)
    if page.page_type == "chat_results":
        grid = [pid for pid in dict.fromkeys(page.grid_product_ids) if pid in rows]
        ctx.grid_count = len(grid)
        ctx.grid = [viewed(pid) for pid in grid[:GRID_CONTEXT_LIMIT]]
    return ctx


def describe_page(view: ViewingContext) -> str:
    """One line about the page, used in the agent's instructions and in saved history."""
    if view.product:
        return f"the product page for {view.product.name} (product_id {view.product.product_id})"
    if view.page_type == "chat_results" and view.grid_count:
        return f"a grid of {view.grid_count} products you put on the page"
    return {
        "home": "the home page",
        "products": "the full product catalogue",
        "chat_results": "a page of chat search results",
        "about": "the About Us page",
        "login": "the log-in page",
        "signup": "the create-account page",
    }.get(view.page_type, "the website")


def existing_product_ids(product_ids: list[str]) -> list[str]:
    """Keep only ids that exist in the catalogue (order kept, duplicates dropped)."""
    ids = list(dict.fromkeys(pid.strip() for pid in product_ids if pid and pid.strip()))
    if not ids:
        return []
    with db() as conn:
        marks = ",".join("?" * len(ids))
        found = {r[0] for r in conn.execute(f"SELECT product_id FROM catalogue WHERE product_id IN ({marks})", ids)}
    return [pid for pid in ids if pid in found]


def _card_blurb(row: sqlite3.Row, limit: int = 110) -> str:
    text = display_description(row["description"])
    if not text:
        # Placeholder description in the catalogue: fall back to facts we do have.
        color = body_color(row)
        kind = row["garment_type"]
        text = f"{color.capitalize()} {kind}." if color else f"{kind[0].upper()}{kind[1:]}."
        return text + " Officially licensed Yale apparel; click for sizes and stock."
    return text if len(text) <= limit else text[: text.rfind(" ", 0, limit)] + "…"


def product_cards(product_ids: list[str]) -> list[dict]:
    """Build product cards from the database for the ids the agent chose.

    Unknown ids are dropped, so the model can't make up a product, price, or image.
    """
    ids = list(dict.fromkeys(pid.strip() for pid in product_ids if pid and pid.strip()))
    if not ids:
        return []
    with db() as conn:
        marks = ",".join("?" * len(ids))
        rows = {
            r["product_id"]: r
            for r in conn.execute(f"SELECT * FROM catalogue WHERE product_id IN ({marks})", ids)
        }
        stock = _stock_by_product(conn)
    return [
        {
            "product_id": pid,
            "name": display_name(rows[pid]["name"]),
            "garment_type": rows[pid]["garment_type"],
            "price": rows[pid]["price"],
            "image_url": f"/images/{rows[pid]['image_file_path']}",
            "colors": json.loads(rows[pid]["colors"]),
            "in_stock_sizes": _in_stock_sizes(stock.get(pid, {})),
            "short_description": _card_blurb(rows[pid]),
        }
        for pid in ids
        if pid in rows
    ]


# ---------- page grid (Problem 7) ----------

MAX_PAGE_RESULTS = 120  # more than the whole catalogue, so a page search is never cut short


def page_results(spec: PageSearch) -> dict | None:
    """Run the agent's page_search against the database and build the grid for the website.

    The model only chooses the filters; the matching products, prices, and images come from
    the catalogue here, so the page can't show an invented product. With a size filter,
    items sold out in that size are left off the grid (the shopper is browsing for that size).
    Returns None when nothing matches.
    """
    found, _, _ = rank_products(
        spec.query, spec.category, spec.color, spec.size, spec.max_price, spec.min_price, spec.sort
    )
    if spec.size:
        found = [x for x in found if x[4]]
    if not found:
        return None
    ids = [x[0]["product_id"] for x in found[:MAX_PAGE_RESULTS]]
    return {
        "title": spec.title,
        "search": spec.model_dump(exclude={"title"}),
        "total_found": len(found),
        "products": product_cards(ids),
    }

