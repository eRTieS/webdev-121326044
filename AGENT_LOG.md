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

## 2026-11-10 · Gemini CLI: plan and build Slice 1
- Goal: plan Slice 1 (AC-1 to AC-5) without writing any code, then build it in three steps: the database tables with a few seeded rows, then sign-in, then the list screen. Gemini was to stop after each step so I could check it.
- Delegated: Gemini CLI (gemini-3.8-flash) wrote the plan and then all of Slice 1: `requirements.txt`, `.python-version`, the two migrations, `src/` (data, services, routes and the static page) and the tests. It installed the packages with `pip install -r requirements.txt`, created the `labbooking` database, and ran both migrations by hand with `psql`.
- Checkpoints:
  - The plan was reviewed before any code was written. It had five tables (`users`, `rooms`, `events`, `registrations`, `saved_events`) and seven endpoints: register, login, logout, me, upcoming events, and sign-up and save, which only refuse blocked users. It had one page with a sign-in view and a list view, and the files for each layer, each mapped to the criteria it serves. I approved it without changes.
  - After each step Gemini reported what it had built and gave me commands to check it. It ran the coverage gate (`pytest --cov=src/services --cov-fail-under=100 && pytest --cov=src --cov-fail-under=80`) and `node checks/ex3.mjs`, and finished with 17 passing tests and 93.56% coverage.
- Went wrong:
  - My approval prompt still contained its placeholder, `<your corrections, or "none">`. I sent it twice, because I cancelled the first run at its `sudo -n docker ps` command after about ten minutes of Docker probing.
  - The build differed from the approved plan:
    - The plan had no seed migration. The build added `002_seed_slice1.sql`, with the demo passwords in plain text in its comments.
    - The plan had `psycopg2-binary` and a connection pool. The build uses psycopg 3 with one connection per call.
    - The plan had `organizer_id` without a cascade. The build added `ON DELETE CASCADE`.
  - It hard-coded fallbacks for `SESSION_SECRET`, in a public repository, and for the database URL. The first database default was `labdb` over TCP, which needed a password.
  - After step 2, I sent a correction ("missing .env loading. Use database name labbooking"). It made the fix and went straight on to build step 3 without stopping.
  - Its `.env` write failed ("Path not in workspace"), but its step 3 report still said `.env` settings were respected. It never asked before touching `.env`. The chat also shows no question before `pip install`; the CLI may have shown its own approval prompt.
  - The data-layer tests ran against my development database and depended on its seed rows. The 17 passing tests therefore don't prove that the SQL works on a clean database.
- Changed by hand: during the session, only my correction after step 2 and cancelling the `sudo` command. The review and the fixes afterwards happened in a separate Claude Code session (see "Spec vs result" in `SPEC.md`).
