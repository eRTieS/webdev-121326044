# Agent log

One entry per agent session, newest at the bottom. Be honest: what went wrong is the useful part.

<!-- Copy this block for each session:

## YYYY-MM-DD · <short title>
- Goal:
- Delegated:
- Checkpoints:
- Went wrong:
- Changed by hand:

-->

## 2026-10-14 · Exercise 1 MCP server
- Goal: work through Exercise 1, steps 1–10, in file`mcp-server/server.py`.
- Delegated: Claude Code recorded the step 8 transcript, pointed `.gemini/settings.json` and `.vscode/mcp.json` at `server.py`, created `package.json` with the `mcp` script, ran the description experiment and filled in the practice copy's logs.
- Checkpoints: the step's own test commands after every step; the real self-check (`node mcp-server/check.mjs -- npm run --silent mcp`) at 12/12;.
- Went wrong: Gemini 2.5 Flash is no longer available to new users, and Gemini 3.8 Flash kept answering 503 "high demand" and then hit the free daily quota after one successful run, so I paied to finish the experiment; a review found inputs that still crash the server (a `tools/call` without `params` or `name`, `"arguments": null`, a non-string `query`), and they are not fixed yet.
- Changed by hand: 

## 2026-10-14 · Gemini CLI explains the protocol
- Goal: understand each part of the protocol with the exercise's prompts: reading stdin line by line and logging to stderr, `initialize` and `notifications/initialized`, `tools/list` and its JSON Schema, the shape of a `tools/call` result, and tool errors versus protocol errors.
- Delegated: explanations only; every prompt told Gemini not to write the code.
- Checkpoints: Gemini wrote no files; the self-check still passes 12/12.
- Went wrong: I used the prompts as written, so they asked about Node.js (`readline`, `console.error`, `readFileSync`) although my server is in Python; in the last prompt I left the `<paste it here>` placeholder instead of my `handle` function, so Gemini searched the folder itself and read `check.mjs`, `messages.jsonl` and the README but never `server.py`, and explained the expected replies instead of reviewing my handler.
- Changed by hand: nothing, the session produced explanations and no code.

## 2026-10-14 · Gemini CLI: connecting the server and the description experiment
- Goal: step 9: check that Gemini loads both tools, ask "What does lecture 7 cover?" without naming a tool, record the usage, and compare a vaguer and a much more precise `find_lecture` description.
- Delegated: the tool choice; Gemini decided which tool to call and I allowed each call.
- Checkpoints: `/mcp` showed `my-project` with 2 tools; `/mcp desc` showed which description was really loaded; Gemini's local session logs showed which tool each run called.
- Went wrong: at first I edited the description and asked the same question four more times in the same session; `/mcp` does not restart the server, so Gemini still had the original description, and with the answer already in the conversation it once answered from memory, once read `lectures.json` and `course.json` directly, and once read the self-check files before calling the tool; none of that measured the description, so I redid both runs with `/quit` and a fresh session each time. I also quit the vague-description session without running `/stats`, so `USAGE.md` only has the first session.
- Changed by hand: the `find_lecture` description in `server.py` between runs; the precise description stayed in.

## 2026-10-14 · Claude Code: step 9 write-up and step 10
- Goal: understand what step 9 asks, tell which Gemini runs were valid, and finish the README, `USAGE.md` and this log.
- Delegated: reading Gemini's session logs to see which runs were fresh sessions and which tool each one called; the Gemini rows and price note in `USAGE.md`; "How to start it" and "The description experiment" in `mcp-server/README.md`; a code block around my transcript; this log.
- Checkpoints: I ran every Gemini session myself and pasted the output; the self-check passed 12/12 with both `python3 mcp-server/server.py` and `npm run --silent mcp`; no commit or push by the agent.
- Went wrong: Claude added at first wrote the two models' tokens as one summed row, which I had split into one row per model.
- Changed by hand: ran the step 8 session and pasted the transcript; changed the `mcp` script in `package.json` from `python` to `python3`.
