# AI Prompts Log — HW4

A log of the prompts I typed to my vibe coder, one section per problem.

---

## Problem 1 — Vibe coder prompts

**First prompt:**

> We are starting with problem titled Vibe coder prompts. Here create AI_prompts.md and keep it as I work. This file is the log of what I type to my vibe coder. Put one section for each problem. Each section must include the problem number and title, at least one prompt I typed in my own words as much as possible and one follow-up prompt if I needed it and one sentence on what was lacking after the first one

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 2 — Analyze the database

**First prompt:**

> We are now moving to problem 2 titled analyze the database. Here take a look at the database data/campus_customs.db in the hw4 folder. Explain to me what the fields of each table are. You can pay more attention to the catalogue, inventory and users fields. Start the file output/harness.md and write down each table and its fields, and one short line on why each field matters for the shop or the chatbot. I will keep growing this harness file in later problems (models, tools, safety, specs)

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 3 — Build the Campus Customs website

**First prompt:**

> We are now moving on to problem 3 titled build the campus customs website. Here scaffold a React + Vite + TypeScript front end for campus customs. Put a nav bar at the top that links to the main pages: Home, products, about us, log in, and create account. Pull campus customs-style wording from https://yalebulldogblue.com/ for home and about us, but write these pages in your own voice. Do not copy the original site text. On the products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description). Make each product open a single-item page (large image on one side, full product text on the other - description, price, sizes/stock when you have them). Clicking a card on products should take the shopper there. Add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk to an agent yet - a stub that will call your backend later is enough for this problem. You will need an API to reach the database. It is fine to start a simple FastAPI app in the backend/main.py just to serve products and images, then grow it into the agent backend in problem 5

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 4 — Create account and login

**First prompt:**

> We are now moving to problem 4 titled create account and login. Here build a normal create-account/login flow:
>
> * Create account: first name, last name, email, password (confirm password is a nice touch)
> * Log in: email and password
>
> New accounts go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them. The seed database already has a test user you can use while building:
>
> * email: test@campuscustoms.yale.edu
> * Password: password
>
> I will need to confirm that I can log in as this user, and that a brand-new account I create also works. Update output/harness.md with how auth works (what you store for a user and how passwords are protected)

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 5 — PydanticAI agent backend

**First prompt:**

> We are now moving to problem 5 titled PydanticAI agent backend. Here build the shop chatbot as a PydanticAI agent behind FastAPI, plugged my your front-end chat widget. Put the API app in backend/main.py - this is the file you run with Uvicorn. Keep the agent as these four files next to it:
>
> * backend/prompts/prompt.md - system prompt (grow this same file later)
> * backend/agent.py - agent entry / wiring
> * backend/tools.py - tools the agent can call
> * backend/models.py - Pydantic/PydanticAI structured types
>
> In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for products/auth). You will need my AI model API key for the agent. Put campus customs voice and safety basics into prompts/prompt.md (you will expand tools and safety later). Start or update types in models.py for chat replies/product cards as needed. In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model).
> Make sure the backend runs from the backend/folder like this: uvicorn main:app --reload --port 8000

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 6 — Tools: product info and stock

**First prompt:**

> We are now moving to problem 6 titled tools: product info and stock. Here we will give the agent tools that look up real information from campus_customs.db:
>
> * Product description
> * Price
> * How many are in stock (by size when the customer asks)
>
> The agent must use the database - it should not invent prices or quantities. If a size is out of stock, say so clearly. Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py.
> In output/harness.md, list each tool and explain which model fields you chose for lookup results and why

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 7 — Chat search that updates the page

**First prompt:**

> We are now moving to problem 7 titled chat search that updates the page. Here we will add a neat feature to the site. When a customer asks about a type of item - for example 'what hoodies do you agve' - the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info). This is an API contract: the agent returns structured product matches and then front end renders them on the website. After the dynamic product cards are loaded by the new feature, make sure the same single-item page behaviour you built in problem 3 still works: each product card - including the ones the chat just put on the page - should still open that detail view (large image + full info) when clicked. Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 8 — Customer memory

**First prompt:**

> We are now moving to problem 8 titled: customer memory. Here when a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) - put that in agent deps (or an equivalent clear patter) and/or tools the agent can call. Also pass enough page contexts that if someone is on a product page knows which item they mean. Hint: you can put code into agent context.
> Guests can still chat, but history only needs to persist for logged-in users. Document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed.

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 9 — Usability improvements

**First prompt:**

> We are now moving to problem 9 titled usability improvements. Now that the core shop works, improve it. Choose and implement:
>
> * 2 front-end usability improvements
> * 2 agent / backen udsability improvements
>
> Front-end improvements are things that make the site look better and make it easier to use. Agent / backend improvements are things that make the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper. Write output/usability.md before or as you build. For each improvements, say:
>
> * what you added
> * why it helps a campus customs shopper or the business.
>
> make sure all the improvements actually show up in the running app

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 10 — Style the website

**First prompt:**

> We are now moving to problem 10 titled style the website. Here add creative design so the site feels like a real campus customs storefront - fonts, color hierarchy, motion, product presentation, chat feel. You will get more points for imaginative and innovative design. Write output/design.md: what you changed and why it should help customers stick around and buy. Keep it concrete and short

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 11 — Site testing (app check)

**First prompt:**

> We are now moving to problem 11 titled site testing (app check). Here test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and short captions for:
>
> * Chat checking the inventory level of an item (honest stock/price from the DB)
> * The dynamic search-result cards appearing after a category question (e.g. hoodies)
> * One of the usability features I added in problem 9
>
> Make the HTML easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png)

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 12 — Audit trail, safety, finish harness

**First prompt:**

> We are now moving to problem 12 titled Audit trail, safety, finish harness. Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs. Also, think of some safety rules to give the agent and put them in prompts/prompt.md. Finish ouput/harness.md so it is clear how the system works.
>
> * Model fields in models.py and why you chose them
> * Tools and abilities
> * Safety rules
> * Specs (loop limits, result caps, models, how to run front + back)

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.

---

## Problem 13 — Push to GitHub and submit the URL

**First prompt:**

> We are now moving to problem 13 titled push to GitHub and submit the URL. Put my code in a folder named hw4 and push it to a public GitHub repository. Do not put my real .env, campus_customs. db, or product images in the GitHub repo. Use .gitignore. Include .env.example with placeholders only

**Follow-up prompt:**

> None needed yet.

**What was lacking after the first prompt:**

Nothing yet.
