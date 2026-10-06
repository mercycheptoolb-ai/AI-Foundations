"""Pydantic / PydanticAI structured types for the Campus Customs chatbot.

Three groups:
- API types: what the website sends to /api/chat and gets back.
- Agent output: the structured answer the model must return.
- Tool results: what the catalogue tools hand back to the model.
"""

from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# Normalized product categories. The catalogue's garment_type column has 22
# inconsistent spellings ("hoodie", "pullover hoodie", "hooded sweatshirt", ...);
# tools.py maps each one onto one of these.
Category = Literal["hoodie", "crewneck", "t-shirt", "quarter-zip", "jacket", "long-sleeve"]
Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
SortOrder = Literal["relevance", "price_low_to_high", "price_high_to_low"]
# Catalogue ids look like "basic-hoodie-big-yale".
ProductId = Annotated[str, Field(max_length=100, pattern=r"^[a-z0-9-]+$")]


# ---------- API (website <-> FastAPI) ----------

class ChatTurn(BaseModel):
    """One earlier message, sent by the browser when the shopper isn't logged in."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)
    product_ids: list[ProductId] = Field(default_factory=list, max_length=6)
    # (user turns) the product page the shopper was on when they sent it
    page_product_id: ProductId | None = None


PageType = Literal["home", "products", "chat_results", "product", "about", "login", "signup", "other"]


class PageContext(BaseModel):
    """Where the shopper is on the website, sent by the browser with each chat message.

    Only ids are trusted from the browser; the server looks up names in the database
    before anything reaches the agent.
    """

    path: str = Field(default="/", max_length=200)
    page_type: PageType = "other"
    product_id: ProductId | None = Field(default=None, description="The product whose page is open.")
    grid_product_ids: list[ProductId] = Field(
        default_factory=list, max_length=120, description="Cards shown on a chat-results page, in order."
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Only used for guests. Logged-in history comes from the chat_messages table.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext | None = None


class ProductCard(BaseModel):
    """A product card: a tile under a chat reply, or a card in the page grid.
    Always built from the database, never by the model."""

    product_id: str
    name: str
    garment_type: str
    price: float
    image_url: str
    colors: list[str]
    in_stock_sizes: list[str]
    short_description: str = ""


class PageResults(BaseModel):
    """Search results the website shows as a grid of product cards (Problem 7)."""

    title: str
    search: dict = Field(description="The filters that produced these results (from the agent's page_search).")
    total_found: int
    products: list[ProductCard]


class ChatReply(BaseModel):
    reply: str
    # A few products discussed in this reply, shown as small tiles in the chat panel.
    products: list[ProductCard] = Field(default_factory=list)
    # When the shopper asked about a type of item: every match, shown on the page.
    page_results: PageResults | None = None
    # Whether the server saw a logged-in session (and saved this exchange). Lets the
    # widget notice a session that expired or changed in another tab.
    logged_in: bool = False


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResults | None = None
    created_at: str


# ---------- Agent output ----------

class PageSearch(BaseModel):
    """Filters for the product grid the website shows on the page."""

    title: str = Field(
        max_length=60,
        description='Short heading for the grid, e.g. "Hoodies", "Navy crewnecks under $60", "Branford gear".',
    )
    query: str = Field(default="", description="Keywords, same as search_products' query (may be empty).")
    category: Category | None = None
    color: str | None = None
    size: Size | None = Field(default=None, description="Only show items in stock in this size.")
    max_price: float | None = None
    min_price: float | None = None
    sort: SortOrder = "relevance"


class AgentReply(BaseModel):
    """Your final answer to the shopper."""

    message: str = Field(
        description=(
            "The reply to show the shopper, in the Campus Customs voice. Light markdown is "
            "OK: **bold** and short '- ' bullet lists. Keep it brief."
        )
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=6,
        description=(
            "product_id values, copied exactly from tool results, for products to show as "
            "small tiles under the reply (most relevant first). Empty when no product applies."
        ),
    )
    page_search: PageSearch | None = Field(
        default=None,
        description=(
            "Set this when the shopper asks to see or browse a TYPE of item (e.g. 'what hoodies "
            "do you have?', 'show me navy crewnecks under $60', 'any Branford gear?'). Use the "
            "same filters as your search_products call. The website then shows EVERY matching "
            "product as a card on the page. Leave null for questions about one specific product "
            "(price, stock, details), totals, or anything that isn't browsing."
        ),
    )


# ---------- Agent dependencies ----------

@dataclass
class CustomerProfile:
    """The logged-in shopper, loaded from the users table by the session cookie."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str  # users.created_at (date only)


@dataclass
class ViewedProduct:
    product_id: str
    name: str
    garment_type: str


@dataclass
class ViewingContext:
    """Server-checked version of the browser's PageContext."""

    page_type: PageType = "other"
    path: str = "/"
    product: ViewedProduct | None = None  # on a product page
    grid: list[ViewedProduct] = field(default_factory=list)  # first cards of a chat-results grid
    grid_count: int = 0
    # True when this product page is new since the shopper's previous message (or there is
    # no previous message). Then "this"/"it" means the product on screen.
    changed: bool = True


@dataclass
class ShopDeps:
    """Per-request context for the agent: who is chatting and what they're looking at.

    Read by the dynamic instructions (agent._instructions) and by the customer tools.
    """

    customer: CustomerProfile | None = None  # None = guest
    page: ViewingContext = field(default_factory=ViewingContext)


# ---------- Tool results ----------

class ProductMatch(BaseModel):
    product_id: str
    name: str
    category: Category | None
    garment_type: str
    price: float
    garment_color: str | None = Field(description="The item's own color (each product comes in this one color).")
    short_description: str
    in_stock_sizes: list[str]
    # Set only when the search asked for a size: False means sold out in that size.
    requested_size_in_stock: bool | None = None


class SearchResults(BaseModel):
    matches: list[ProductMatch]
    total_found: int = Field(description="Products matching the filters (including ones sold out in a requested size).")
    in_size_found: int | None = Field(
        default=None,
        description="With a size filter: how many matches are in stock in that size (the number the page grid shows).",
    )
    note: str | None = None


# ---------- Lookup tool results (Problem 6) ----------
# Every lookup result starts with the same three fields so the model always
# knows exactly which product the numbers belong to and how it was found.

MatchMethod = Literal["product_id", "name", "closest_match"]
StockStatus = Literal["in_stock", "low_stock", "sold_out"]
LOW_STOCK_THRESHOLD = 5  # at or below this many units counts as "low_stock"


class ProductLookup(BaseModel):
    product_id: str = Field(description="Exact catalogue id; use it for product_ids and later lookups.")
    name: str = Field(description="Display name to use when talking to the shopper.")
    matched_by: MatchMethod = Field(
        description=(
            "How the product was found: exact product_id, exact name, or closest_match "
            "(a best guess from keywords; confirm with the shopper if it might not be what they meant)."
        )
    )


class ProductDescription(ProductLookup):
    category: Category | None
    garment_type: str
    description: str | None = Field(
        description="Catalogue description, or null when the catalogue has none (say so; don't invent one)."
    )
    garment_color: str | None = Field(
        description="The item's own color. Each product comes in this ONE color; null means not listed."
    )
    logo_colors: list[str] = Field(
        description="Colors of the logo/graphic/crest printed on it. NOT other colors the item comes in."
    )


class PriceInfo(ProductLookup):
    price: float = Field(description="Price in US dollars, straight from the catalogue.")
    price_display: str = Field(description='The price formatted for the shopper, e.g. "$68.00". Quote this.')
    currency: Literal["USD"] = "USD"


class QuoteItem(BaseModel):
    product: str = Field(description="product_id (best) or product name")
    quantity: int = Field(ge=1, le=100)


class QuoteLine(ProductLookup):
    quantity: int
    unit_price: float
    line_total: float


class PriceQuote(BaseModel):
    lines: list[QuoteLine]
    total: float = Field(description="Sum of all line totals in USD.")
    total_display: str = Field(description='The total formatted for the shopper, e.g. "$168.00". Quote this.')
    budget: float | None = None
    remaining_budget: float | None = Field(
        default=None, description="budget minus total (negative means over budget)."
    )
    within_budget: bool | None = None


class SizeStock(BaseModel):
    size: Size
    quantity: int = Field(description="Units on hand right now.")
    status: StockStatus


class StockInfo(ProductLookup):
    requested_size: Size | None = Field(description="The size that was asked about, if any.")
    requested_size_quantity: int | None = Field(description="Units on hand in the requested size (0 = sold out).")
    requested_size_status: StockStatus | None
    sizes: list[SizeStock] = Field(description="Every size we carry for this product, XS to XXL.")
    in_stock_sizes: list[Size]
    sold_out_sizes: list[Size]
    total_units: int = Field(description="Units on hand across all sizes.")
    summary: str = Field(description="One-sentence plain-English stock summary built from the numbers above.")


class AlternativeMatch(BaseModel):
    product_id: str
    name: str
    category: Category | None
    price: float
    garment_color: str | None
    in_stock_sizes: list[str]
    requested_size_quantity: int | None = Field(
        default=None, description="Units in stock in the requested size (always > 0 here)."
    )
    why_similar: str = Field(description='Short reason, e.g. "also a jacket; also Brooks Brothers; similar price".')


class Alternatives(BaseModel):
    """Similar products that ARE in stock (in the requested size), for a product the shopper wanted."""

    for_product_id: str
    for_product_name: str
    size: Size | None
    matches: list[AlternativeMatch]
    note: str | None = None


class CategorySummary(BaseModel):
    category: str
    product_count: int
    min_price: float
    max_price: float


class CatalogueOverview(BaseModel):
    total_products: int
    categories: list[CategorySummary]
    sizes_offered: list[str]
    colleges_with_merch: list[str]
    colleges_without_merch: list[str]
    schools_with_merch: list[str]


# ---------- Customer memory tool results (Problem 8) ----------

class CustomerProfileInfo(BaseModel):
    logged_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = None
    saved_messages: int = Field(default=0, description="How many chat messages are saved for this shopper.")
    first_chat_at: str | None = None


class PastMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str
    products_shown: list[str] = Field(default_factory=list, description="Names of products shown with that reply.")


class ChatHistorySearch(BaseModel):
    logged_in: bool
    matches: list[PastMessage]
    note: str | None = None

