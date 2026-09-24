# AI Prompts

This file records the prompts used while working through `hw2`. Each problem gets its own section with the problem number, title, the initial prompt, and any follow-up prompts.

## Setup Requests

- Use the `PORTKEY_API_KEY` from the root `.env` file for AI calls. Load it from the environment; never hard-code, print, commit, or expose the key.
- Work in the `hw2` folder for today's problems.

## Problem 2: Seller brief

### Prompt

> We are now moving to problem two titled Seller brief. Here write assets/seller_brief.md which records the company name and website of a company or companies I will select later on, gives reasons why I chose the company and any information i want to collect abou the company

<!-- Add one section like the above for each new problem. Include a follow-up subsection when one is provided. -->

## Problem 3: Agent system prompt

### Prompt

> We are now moving to problem 3 titled agent system prompt. In this problem, I want to build a PydanticAI agent for the whole assignment. Create an agent system prompt file prompts/sales_agents.md. To build a company profile when I ask for it, ensure that you include the following: What profile fields to collect - include - Company overview and history; Products or services offered; Target customers and market served; Business model and sources of revenue; Pricing, packages, or purchasing options; Competitive position and key competitors; Recent news, announcements, or strategic changes; Financial, operational, or growth information; Risks, weaknesses, or open questions. Crawl through the company website. You can pull this from the terminal. Do not invent facts - only use verified information from the website. And use Michelle Obama's personality. Save this profile in assets/company-profile.json

## Problem 4: Build agent + profile run

### Prompt

> We are now moving to problem 4 titled build agent + profile run. Here i want to build one PydanticAI agent in sales_agent.py that loads prompts/sales_agent.md into its systems prompt. Add the Playwright web crawler package and any other necessary tool the agent will need to look through a company's website and write a profile file. The agent will use the input query text to figure out what I want. For this problem, I will ask you to build a profile of Open Capital. Use these bits in my harness: Harness checklist: Tools — the list above; Memory — chat history + current portfolio state; Stopping Rules — clear finish / max-step cutoff so it cannot loop forever; Guardrails — universe allow-list; no inventing data; refuse unsafe asks; Audit trail — forensic log of thoughts, tool calls, observations. When i run the agent, makes sure it writes its agent-loop iterations (date and time, thoughts, tool calls - name + args + result summary - and when the run stops) to output/audit_log.json. Run the agent on Open Capital's website and produce a detauled profile of the company in the file assets/company_profile.json. The script should take a text query and a --url from the terminal and pass both into the agent. Use the company URL from my seller brief (the fields I care about should already be in prompt/sales_agent.md). Use this command structure to run the agent: python sales_agent.py "Build a profile of this company." --url https://www.company_url.com

## Problem 5: Expand prompt + find customers

### Prompt

> We are now moving to problem 5 titled expand prompt + find customers. Update prompts/sales_agent.md with instructions for finding three good customer targets for Open Capital using assets/company_profile.json as the source of truth. Search for plausible customer companies, validate that each is a genuine fit rather than a random or competing business, verify useful business context and a public contact email from the company website, and draft a targeted outreach email for each target without sending anything. Save the targets to output/targets.json, save the email drafts to output/emails.json, and update output/audit_log.json with the search steps, tool calls, evidence summaries, and stop reason. Use this command structure: python sales_agent.py "Find 3 good customer targets for this company and draft outreach emails." --profile assets/company_profile.json

## Problem 6: Agent harness summary

### Prompt

> We are now moving to problem 6 titled agent harness summary. Create HARNESS.md at the project root. Keep it readable and explain the controls for the agent without requiring anyone to read sales_agent.py: use only the approved tools listed for the assignment; apply clear completion conditions and a maximum step cutoff so the agent cannot loop forever; do not invent facts, send emails, take unsafe actions, expose secrets, or allow runaway costs. Include the evidence, audit, website-crawl, retry, and cost-control rules needed to keep the agent under control.

## Problem 7: Rank targets and emails

### Prompt

> We are now moving to problem 7 titled rank targets and emails. Create output/reflection.md and record my reflection on the selected customer targets and drafted outreach emails. Rank the targets as ThriveAgric first, Bopinc second, and AgroMall third. Note that the ranking is based on perceived organizational size and ability to pay, but that the agent found no pricing data and therefore could not verify that alignment. Record that the emails were too generic, explained each organization back to itself, did not reference specific relevant Open Capital work, and should have focused more on Open Capital's capabilities and included links to similar work where possible.

## Problem 8: Sales dashboard webpage

### Prompt

> We are now moving to problem 8 titled Sales dashboard webpage. Create a standalone `hw2/dashboard.html` that displays Open Capital's profile, ranked target customers, contact information, and drafted outreach emails in a human-skimmable dashboard. Embed the profile, targets, and emails directly in the HTML so the page works by double-clicking it with no extra setup and does not read JSON files at runtime. Use a creative but clear layout, a mix of dark blue and light blue colors, good typography, visual personality, clear hierarchy, and restrained animated transitions between sections.

## Problem 9: Submit zip

### Prompt

> We are now moving to problem 9 titled submit zip. Zip everything in the `hw2` folder and save the archive as `hw2.zip` at the project root. Exclude the `.env` file and verify that no environment file is included in the archive.
