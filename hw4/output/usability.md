# Campus Customs: Usability Improvements (Problem 9)

Four improvements: two on the website and two in the agent/backend. Each section says **what was added**, **why it helps a Campus Customs shopper or the business**, and **where to see it** in the running app (http://localhost:5180). This file was written as a plan before building and updated with results as each piece shipped.

| # | Improvement | Type | See it at |
|---|---|---|---|
| 1 | Shop filters (category, in stock in my size, sort) | Front end | **Products** page |
| 2 | Suggested questions in chat + "Ask about this item" | Front end | Chat panel on any page; button on every product page |
| 3 | "Similar items in your size" tool (`find_alternatives`) | Agent | Ask about a sold-out size, or tap "Show me similar items" |
| 4 | Faster, cheaper answers (no redundant searches) | Agent | Questions about a named product: one fewer model round trip (about 8 s → 4.5 s). About 20–24% faster on average across the benchmark (below). |

---

## Front end

### 1. Shop filters on the Products page

**What we added:** a filter bar above the product grid on `/products`.

- **Category pills with live counts:** All 102 · Hoodies 27 · Crewnecks 29 · T-shirts 25 · Quarter-zips 11 · Jackets 8 · Long-sleeves 2. The counts update as other filters change, and categories with no matches are greyed out.
- **"In stock in [size]"** (XS–XXL) hides every item that's sold out in that size. Cards running low show a pink **"Only 5 left in M"** badge.
- **Sort:**
  - **Featured (best availability):** items with the most sizes in stock come first, so the first screen isn't full of things sold out in most sizes.
  - Price low → high, Price high → low, Name A → Z.
- The existing search box, a live result line ("**21 hoodies in stock in M**"), and **Clear filters**.
- **Everything lives in the URL** (`/products?category=hoodie&size=M&sort=price_asc`). Refresh, the browser Back button, and a shared link all keep the filters. A product opened from a filtered list shows **"← Back to results"**, which returns to the same filtered list (a direct visit still says "← All products").
- Behind it: `GET /api/products` now also returns each product's `category` and `stock_by_size`.

**Why it helps:**

- **Shoppers:** before this, the only way to narrow 102 products was the search box or the chatbot. Most people shop by type and size ("hoodies I can actually get in a medium"). The size filter means they never click into an item only to find their size is gone, and "Only 2 left" makes low stock clear.
- **The business:** shoppers who reach an in-stock item quickly are more likely to buy it, and low-stock badges create gentle urgency.

**Check it:** Products, then **Hoodies**, then In stock in **M**, then Sort **Price: low to high**. You should see 21 hoodies, $45 first, with low-stock badges. Refresh, or open a product and press Back, and the filters are still there.

### 2. Suggested questions in the chat + "Ask about this item"

**What we added:**

- **One-tap suggestion chips** above the chat input. They change with the page:
  - **Home / catalogue:** "What hoodies do you have?", "Gift ideas under $50", "Show me residential college gear", "Navy crewnecks in M". Logged-in shoppers with saved chats also get "What did we talk about last time?"
  - **Product page:** "Which sizes are in stock?", "Tell me about this item", "Show me similar items", "How much is it?"
  - **Chat results grid:** "Sort these by price", "Which of these are in stock in M?", "Show me something cheaper"
- While a reply is loading, the chips stay in place but are disabled.
- Tapping a chip doesn't erase anything the shopper had started typing.
- Keyboard focus moves to the chat input.
- On phones, the chips sit in **one swipeable row**, so they don't take over the small chat panel.
- An **"💬 Ask about this item"** button on every product page (under the price). It opens the chat with that product's chips. Because of Problem 8's page context, "Which sizes are in stock?" is answered for the product on screen.

**Why it helps:**

- **Shoppers:** many don't know what the assistant can do, or don't want to type on a phone. One tap gets a real answer, and the chips teach what kinds of questions work.
- **The business:** more shoppers use the assistant. Chips like "Show me similar items" and "Gift ideas under $50" surface products people wouldn't have found by scrolling.

**Check it:** open any product page and click **Ask about this item**, then tap **Show me similar items**. Or open the chat on Home and tap **Gift ideas under $50**: 30 items appear on the page.

---

## Agent / backend

### 3. "Similar items in your size": the `find_alternatives` tool

**What we added:** a new read-only agent tool, `find_alternatives(product, size)` in `backend/tools.py`, with return types `Alternatives` / `AlternativeMatch` in `models.py`. Given the product a shopper wanted and their size, it returns similar items that are **in stock in that size**. The ranking uses:

- the same category (jacket → jackets)
- a shared theme from the product name and tags: residential college, brand, team, or design ("Bulldog", "Football", "Brooks Brothers"). Construction words like "full-zip" or "kangaroo pocket" are ignored.
- the same garment color
- a similar price

Items from the **same residential college, school, or family line** (Yale Dad / Mom / Grandpa…) get a bonus. If one is in stock but didn't make the top picks, it takes the last slot. For example, a sold-out Morse 1/4 Zip in L also suggests the Morse Logo T-Shirt.

Each result carries a short `why_similar` ("also a jacket; also navy blue; similar price", "also Brooks / Brothers", "also Morse") and the units in stock in that size. The prompt tells the agent to call it right after any "sold out in your size", and for "something similar", then show 2–3 options as chat tiles. The grounding check knows these per-size counts, so "School of Art Fleece Sweater (20 in M)" is accepted, while an invented count is still rejected.

**Why it helps:**

- **Shoppers:** "Sorry, sold out in M" used to be a dead end. Now it's "The bomber is sold out in M. These fleece jackets *are* in stock in M," with photos one tap away. All suggestions come from the catalogue and inventory, so they're real and buyable; the model can't invent them, and their prices and stock pass the grounding check.
- **The business:** it recovers sales that a sold-out size would otherwise lose, and it moves stock in sizes that are actually available.

**Check it:** ask "Do you have the Brooks Brothers bomber jacket in M?" The agent says it's sold out in M and suggests similar jackets in stock in M. Or open a product and tap **Show me similar items**.

Examples from testing:

- Bomber in M → three fleece jackets in stock in M.
- Football Left Chest Tee in M → the other football tees.
- Vintage Bulldog hoodie in M → other Vintage Bulldog designs.
- Yale Dad Hoodie in S → Yale Grandpa, Aunt, and Mom hoodies.
- Morse 1/4 Zip in L → other college quarter-zips, plus the Morse Logo T-Shirt.

### 4. Faster, cheaper answers: no redundant searches

**What we found (measured first):** we benchmarked 8 typical shopper questions with the response cache bypassed, so every call was a real model call. For products the shopper named, the agent usually (4 of the 5 named-product questions) ran `search_products` first, then `get_price` / `check_stock` / `get_product_description` / `price_quote`. That's an extra model round trip, and each round trip re-sends about 4,500 tokens of prompt and tool definitions.

**What we changed:**

- The lookup tools already accept product **names**, so the prompt and the tool descriptions now tell the agent to call them **directly** for named products. It only searches when the shopper is browsing, or if a lookup can't match the name. It also batches independent lookups (e.g. two prices) in one step.
- We also tried a lower "reasoning effort" setting. It made **no measurable difference** (6.55 s against a 6.38 s baseline), so we left it out rather than add a setting that doesn't help.
- OpenAI's prompt cache was already serving about 93% of input tokens, because the static prompt comes first and the per-chat context last. We kept that order.

**Results** (same 8 questions, response cache bypassed, one real model call each):

| | Before | After (final, incl. improvement 3) | Change |
|---|---|---|---|
| Time per answer (mean) | 6.38 s | **4.86 s** | **−24%** |
| Time per answer (median) | 5.82 s | **4.44 s** | −24% |
| Model requests per answer | 2.50 | **2.12** | −15% |
| Input tokens per answer | 11,760 | **10,719** | −9% |
| Output tokens per answer | 189 | **160** | −15% |

Questions about a named product dropped from 3 model requests to 2: for example, "How much is the Basic Hoodie Big Yale?" went from 8.5 s to 4.7 s. Browsing and store questions make the same number of calls as before, so most of the gain is on named products.

Each figure is one real call per question, so expect some noise. A later independent re-run of the same benchmark gave **5.07 s** mean (median 4.29 s) and the same 2.12 requests: about **20–24% faster** than the baseline.

The one question that does *more* work now is the sold-out bomber. It also calls `find_alternatives`, which is improvement 3 earning its keep. Answers stayed accurate: the same prices, stock, and totals, all still passing the grounding check.

**Why it helps:**

- **Shoppers:** faster replies in a chat window that's competing with their attention.
- **The business:** fewer model requests and tokens per conversation means a lower API bill for the same answers.

**Check it:** ask "How much is the Basic Hoodie Big Yale?" or "Tell me about the Branford quarter zip". Both used to take a search plus a lookup (3 model requests); now they take one direct lookup (2 requests).

---

## How these were tested

**Adversarial review** (front-end UX in a real browser, agent quality, and claims and code), with a skeptic re-testing each finding.

- **Confirmed working:**
  - pill and low-stock badge counts match the database for every size
  - every claim in this file
  - mobile layout and keyboard access
  - the re-run benchmark
- **Fixed and re-tested:**
  - the grounding check rejected correct per-size counts for suggested alternatives, and read "in M: 2025 Yale vs. Harvard T-Shirt" as a stock count
  - alternatives ignored same-college and family-line items, and some labels showed word stems or fabric words
  - the product page's back link dropped filters
  - "Featured" was just A–Z
  - "1 long-sleeves"
  - chips erased a typed draft, took a lot of room on phones, and dropped keyboard focus
  - this file overstated the speed-up as applying to "every reply"


- **Real-browser runs (headless Chrome)**, all checks passing (15/15 main suite, 10/10 for the fixes):
  - **Filters:** pill counts; Hoodies → 27 cards; size M → 21; "Only 5 left in M" badges; price sort starting at $45; the result line; persistence through refresh and Back; Clear → 102.
  - **Chat:** home chips; product-page "Ask about this item" opens the chat with product chips; tapping "Show me similar items" returns similar-item tiles (not the bomber itself).
  - **Fixes:** "← Back to results" keeps filters; Featured puts items with all 6 sizes in stock first; "1 long-sleeve in stock in XXL"; a chip keeps a typed draft, chips are disabled while loading, and focus moves to the input; one row of chips on mobile.
- **Live agent checks:**
  - "Show me similar items" on the bomber page → `find_alternatives`.
  - "Which sizes are in stock?" → exact per-size counts.
  - "Sort these by price" → page re-sorted. "Which of these are in stock in M?" → 21 of 27, page filtered.
  - "Gift ideas under $50" → 30 on the page. "What did we talk about last time?" → recalls the saved chat.
- **Fact-checks:** benchmark answers ($68.00, 20 in L, $168.00 total, sold out in M) and alternative-item stock all checked against the database.
