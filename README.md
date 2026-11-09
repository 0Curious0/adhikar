# Adhikar

A voice-first app that helps low-literacy, low-income Indians find out which government welfare
schemes they're eligible for and file grievances about them — built on Gnani AI's voice stack
(Prisma for STT, Timbre for TTS) and Sarvam AI's language stack (Prism for intent/scheme
decisions, 105B for entity extraction, 105B Conversations for spoken replies).

## Plan

**MVP scope:** 5 schemes (Widow Pension, PM-KISAN, Ayushman Bharat PM-JAY, PDS, VB-G RAM G) made
reliable across 4 of Prisma's 10 supported languages (Hindi, English, Tamil, Telugu). The other
schemes/languages are roadmap, not built — a narrow, polished demo beats a broad, shaky one.
VB-G RAM G (Viksit Bharat - Guarantee for Rozgar and Ajeevika Mission (Gramin) Act, 2025) supersedes
MGNREGA; its actual provisions aren't verified yet, see `src/adhikar/schemes/data/vb_g_ram_g.json`.

**Web is the only MVP channel**, with two interaction modes:
- **Voice mode** — REST, push-to-talk: one spoken turn is recorded as a single clip (the user
  explicitly starts/stops; never silence-detection, which would cut off mid-thought pauses), then
  sent through transcribe -> orchestrator -> synthesize in one request. The default, since it
  needs no reading/typing — this is the accessible path for the low-literacy users the app targets.
- **Chat mode** — realtime streaming, editable text: dictation streams live into an editable input
  box (so the user can correct it) via Prisma's realtime WebSocket; sending is a separate explicit
  action; the reply is voiced back via Timbre's realtime WebSocket. An opt-in for literate users
  (or a literate person helping someone use the app), not the default.

WhatsApp integration is **deferred past MVP** — a planned upcoming feature, not forgotten scope.
When it's built, it reuses the same REST transcribe -> orchestrator -> synthesize pipeline Voice
mode already uses (Prisma's single-file `stt/v3` endpoint; voice notes are short enough that no
async job queue is needed) — the new work at that point is the WhatsApp Business API webhook
contract itself (verification handshake, media fetch, sending replies), not the voice pipeline.

**Stack:** Python + FastAPI backend, React + TypeScript frontend.

## Implementation status

| Piece | Status |
|---|---|
| STT provider (`adhikar.stt`) — REST + realtime streaming, Prisma v2.5 | Done, tested |
| TTS provider (`adhikar.tts`) — REST + realtime streaming, Timbre v2.5 | Done, tested |
| Scheme knowledge base + evaluator (`adhikar.schemes`) — 5 schemes, deterministic eligibility | Done, tested |
| NLU (`adhikar.nlu`) — intent/scheme decisions (Prism), entity extraction (105B) | Done, tested |
| NLG (`adhikar.nlg`) — spoken-reply generation (105B Conversations) | Done, tested |
| Dialogue management (`adhikar.dialogue`) — user profile store + turn orchestration (wiring NLU/evaluator/NLG together) | Done, tested |
| FastAPI backend (`adhikar.api`) — `POST /chat`, `POST /voice` (Voice mode), `WS /stt/stream` + `WS /tts/stream` (Chat mode) | Done, tested |
| Frontend | Not started |
| WhatsApp bot integration | Deferred past MVP (upcoming feature) |

See `CLAUDE.md` for architecture details and decisions behind the above.

## Running this project

```bash
uv sync                                        # install dependencies
echo "GNANI_API_KEY=..." > .env                # see adhikar.config.Settings for all env vars
echo "SARVAM_API_KEY=..." >> .env              # needed for adhikar.nlu / adhikar.nlg
uv run pytest                                  # run the test suite
uv run python scripts/realtime_stt_demo.py     # manual mic -> live transcript check
uv run python scripts/tts_demo.py              # manual text -> synthesized speech check
```
