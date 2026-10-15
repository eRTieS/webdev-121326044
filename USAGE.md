# Usage

One row per agent session. In Gemini CLI, type `/stats` before you quit and copy the input and output tokens. Copilot shows credits instead of tokens: write those in the credits column. The free tier charges nothing, so record what the session **would cost at the provider's published list price**, and note once below the table which price list you used. Leave the cost empty for rows that only show credits.

| Date | Tool | Input tokens | Output tokens | Credits (if no tokens) | List-price cost |
|---|---|---|---|---|---|
| 2026-10-14 | Gemini CLI, gemini-3.5-flash-lite (utility router + summarizer) | 3,277 | 34 | | $0.001 |
| 2026-10-14 | Gemini CLI, gemini-3.8-flash (main), same session | 25,041 | 46 | | $0.019 |

Prices used: Gemini Developer API, paid standard tier (ai.google.dev/gemini-api/docs/pricing, 2026-10-14): Gemini 3.8 Flash $0.75 input / $3.75 output per 1M tokens (introductory rate until 2026-12-31), Gemini 3.5 Flash-Lite $0.30 / $2.50; output includes thinking tokens.
