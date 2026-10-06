# Campus Customs: Design (Problem 10)

**Concept: "Varsity Locker Room · Game Night at 57 Broadway."** A black locker room lit in varsity pink. Products hang as numbered roster cards, pennants lead to your college, a scoreboard ticker reports what's really on the shelves, and the Bulldog Assistant is the team's equipment manager. It's chosen from three competing directions (varsity, editorial, neon) by a judged design panel, keeping the best ideas from the other two.

## The system

| | What changed | Why it helps people stay and buy |
|---|---|---|
| **Fonts** | **Graduate** (varsity block) for headlines and numbers; **Barlow Condensed** (athletic labels, uppercase) for nav, prices, buttons, and chips; **Barlow** for reading text. | Reads instantly as campus apparel rather than a generic web shop. Condensed labels fit more information in a scannable space. |
| **Colour hierarchy** | Pink is ranked: **solid pink** = the one main action per screen; **pink text** = prices and real low-stock; **dashed pink stitch** = only things the Bulldog Assistant picked; chalk headings; grey metadata. Pink switches to a darker ink on light paper surfaces for contrast. | The eye goes to price and the next step, not decoration. Shoppers learn that "pink stitch = the assistant chose this for me." |
| **Motion** | Cards lift like a trading card being picked up; chat results "run out of the tunnel" in a stagger; the scoreboard count rolls up; buttons press like stickers; chat slides up like a clipboard; typing dots do "the wave." Everything is off under *reduce motion*. | Feedback on every action makes the site feel alive and responsive without slowing anyone down. |
| **Product presentation** | **Photo stage normaliser.** Each photo is checked once: 45 dark photos sit on pure black, 57 white photos blend onto warm paper, and the 28 white photos with baked-in black side bars get the bars clipped away. Each roster card shows a **jersey-number patch**, athletic-tape badges ("Sold out", "Only 2 left in M"), and a **size-run strip** (XS S M L XL XXL, crossed out when sold out). The product page is a **locker cubby** with a vent strip and floor spotlight, size **nameplates** (sold-out ones get tape across), and a "scouting report" description. | Mismatched black/white photo boxes made the catalogue look unfinished; now every product looks shot for this store. Shoppers see available sizes **before** clicking, so fewer dead-end clicks. |
| **Chat feel** | A stitched **bulldog mascot built in HTML** with moods (blinks when idle, tilts its head while thinking, hops when it finds something) and a status line ("Looking that up…" / "Found 27 for you"). Assistant bubbles carry the pink stitch; suggestion chips are numbered like plays; a play-diagram watermark sits behind messages. On phones, the chat is a bottom sheet. | A friendly face and visible "working on it" states make people more willing to ask, and the assistant is how shoppers find their size. |

## Signature ideas

1. **Call a number.** Every card on screen has a jersey number, in the current filter and sort. Shoppers can ask *"is #3 in stock in M?"* or tap *"Compare #1 and #2"*. The chat swaps the number for that product before asking the agent, and the number shows as a little patch in the bubble. **Why:** typing long product names is the hardest part of asking an AI. Numbers make a 102-item wall easy to talk about ("I liked #23").
2. **Play Call.** When the assistant puts results on the page, the banner becomes an LED scoreboard ("Play call · From your chat", with a rolling count), and stitched cards run on with matching numbers. Hovering a chat tile **lights up its card** on the page, and a fresh answer pulses the cards it mentions. On phones, the closed chat shows a score badge. **Why:** asking and seeing results become one visible motion, and the eye travels from answer → card → price.
3. **Scoreboard ticker.** An LED strip under the navbar, built from live data: "102 styles on the roster ◆ 29 crewnecks ◆ … ◆ Low stock: Basic Hoodie Big Yale · only 2 left in XL ▸". It pauses on hover, and the low-stock items link to their product. **Why:** truthful urgency (115 size slots really have 1–5 left) instead of fake sales, and something new to tap on every page.
4. **Pennant wall** (Home). Felt pennants for **your college**, **the family line** (Yale Dad, Mom, Grandpa…), and **teams & schools**, each with a live count ("3 styles"). Empty ones are hidden. "Don't see yours?" asks the assistant. **Why:** identity is why people buy campus gear. One tap puts each shopper in front of their shelf, and gift-buying parents find "Yale Dad" immediately.
5. **Dead ends hand off to the assistant.**
   - Sold-out sizes show **"Sold out in M? Find similar in stock"**.
   - A search with no results offers **"Ask the Bulldog Assistant about '…'"**.
   - Product pages get numbered one-tap questions.
   - Home ends with a **"bench"** band of starter questions.

   **Why:** 145 of 612 size slots are sold out. That's where shoppers leave, so each of those moments now routes to an assistant that finds in-stock alternatives.
6. **Touches of the locker room.**
   - **Hero:** a hanging #57 jersey with a computed stat row.
   - **Sign-up:** the jersey shows **your name as you type it**.
   - **About:** the address becomes an admission ticket.
   - **404:** a "Fumble" scoreboard.
   - **Navbar:** a "CC" chenille patch and varsity stripe, and a name tape for logged-in shoppers.
   - **Footer:** category links and a giant outlined wordmark.

## Ground rules kept

- Black and pink only: the product photos supply every other colour.
- No invented offers or popularity claims: the home picks are labelled "hand-picked", not "best sellers", and every count and stock line comes from the API.
- Every earlier feature and test selector still works.
- Text meets AA contrast, including sold-out labels, size strips, and placeholders.
- Keyboard focus is visible everywhere (including the clipped pennant shapes), and the chat panel takes focus when it opens.
- All motion respects *reduce motion*: the ticker becomes a scrollable row, counts show their final value, and nothing sways or hops.
- On phones, the header is compact and scrolls away, the headline and "Shop" button come first, and the filters sit in one swipeable row.
- The bulldog is a generic HTML mascot, not a Yale logo.
