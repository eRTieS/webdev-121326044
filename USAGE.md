# Usage

One row per agent session. In Gemini CLI, type `/stats` before you quit and copy the input and output tokens. Copilot shows credits instead of tokens: write those in the credits column. The free tier charges nothing, so record what the session **would cost at the provider's published list price**, and note once below the table which price list you used. Leave the cost empty for rows that only show credits.

| Date | Tool | Input tokens | Output tokens | Credits (if no tokens) | List-price cost |
|---|---|---|---|---|---|
| 2026-10-14 | Gemini CLI, gemini-3.5-flash-lite (utility router + summarizer) | 3,277 | 34 | | $0.001 |
| 2026-10-14 | Gemini CLI, gemini-3.8-flash (main), same session | 25,041 | 46 | | $0.019 |
| 2026-11-10 | Gemini CLI, gemini-3.8-flash (main), Slice 1 plan and build | 7,841,810 (7,424,791 from cache) | 33,391 | | $0.995 |
| 2026-11-10 | Gemini CLI, gemini-3.5-flash-lite (utility router + summarizer), same session | 12,921 | 259 | | $0.005 |
| 2026-11-10 | Gemini CLI, gemini-3-flash-preview (loop detector), same session | 22,653 | 233 | | $0.012 |

Prices used: Gemini Developer API, paid standard tier (ai.google.dev/gemini-api/docs/pricing, 2026-10-14): Gemini 3.8 Flash $0.75 input / $3.75 output per 1M tokens (introductory rate until 2026-12-31), Gemini 3.5 Flash-Lite $0.30 / $2.50; output includes thinking tokens.

For the 2026-11-10 rows (aistudio.google.com/docs/pricing, read 2026-11-11):
- Prices per 1M tokens, input / cached input / output:
  - Gemini 3.8 Flash: $0.75 / $0.075 / $3.75 (until 2026-12-31).
  - Gemini 3.5 Flash-Lite: $0.30 / $0.03 / $2.50.
  - Gemini 3 Flash Preview: $0.50 / $0.05 / $3.00.
- I assumed the cache reads are part of the input tokens `/stats` shows. So the main row is 417,019 tokens at the input price plus 7,424,791 at the cached price.
- I assumed the cache was the automatic (implicit) kind, so no cache storage price is added.
