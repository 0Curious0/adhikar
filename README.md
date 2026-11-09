# Adhikar

A voice-first app that helps low-literacy, low-income Indians find out which government welfare
schemes they're eligible for and file grievances about them — built on Gnani AI's voice stack
(Prisma for STT, Timbre for TTS) and Sarvam AI's language stack (Prism for intent/scheme
decisions, 105B for entity extraction, 105B Conversations for spoken replies).

## Plan

**MVP scope:** 5 schemes (Widow Pension, PM-KISAN, Ayushman Bharat PM-JAY, PDS, VB-G RAM G) made
reliable across the 10 languages Sarvam and Gnani both support (Hindi, English, Bengali, Gujarati,
Kannada, Malayalam, Marathi, Punjabi, Tamil, Telugu — Sarvam's Odia support is left out since
Gnani's STT/TTS doesn't cover it). The other schemes are roadmap, not built — a narrow, polished
demo beats a broad, shaky one.
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
| FastAPI backend (`adhikar.api`) — `POST /chat`, `POST /voice` (Voice mode), `WS /stt/stream` + `WS /tts/stream` (Chat mode), plus read-only `GET /schemes`, `GET /profile/{user_id}`, `GET /activity/{user_id}` | Done, tested |
| Frontend (`frontend/`) — React + TypeScript + Vite; homepage, Voice mode, Chat mode, all-schemes page, activity-history page; 10-language UI chrome | Done |
| WhatsApp bot integration | Deferred past MVP (upcoming feature) |

See `CLAUDE.md` for architecture details and decisions behind the above.

## Running this project

Backend:

```bash
uv sync                                        # install dependencies
echo "GNANI_API_KEY=..." > .env                # see adhikar.config.Settings for all env vars
echo "SARVAM_API_KEY=..." >> .env              # needed for adhikar.nlu / adhikar.nlg
uv run pytest                                  # run the test suite
uv run uvicorn adhikar.api.app:app --reload    # run the backend (localhost:8000)
uv run python scripts/realtime_stt_demo.py     # manual mic -> live transcript check
uv run python scripts/tts_demo.py              # manual text -> synthesized speech check
```

Frontend (needs the backend running first):

```bash
cd frontend
npm install
npm run dev                                    # dev server on localhost:5173 — the backend's
                                                # CORS config allows this origin by default
                                                # (override with ALLOWED_ORIGINS for a deployed
                                                # frontend domain, e.g. on Vercel)
```
