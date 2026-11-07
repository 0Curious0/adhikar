# Adhikar

A voice-first app that helps low-literacy, low-income Indians find out which government welfare
schemes they're eligible for and file grievances about them — built on Gnani AI's voice stack
(Prisma for STT, Timbre for TTS).

## Plan

**MVP scope:** 5 schemes (Widow Pension, PM-KISAN, Ayushman Bharat PM-JAY, PDS, VB-G RAM G) made
reliable across 4 of Prisma's 10 supported languages (Hindi, English, Tamil, Telugu). The other
schemes/languages are roadmap, not built — a narrow, polished demo beats a broad, shaky one.
VB-G RAM G (Viksit Bharat - Guarantee for Rozgar and Ajeevika Mission (Gramin) Act, 2025) supersedes
MGNREGA; its actual provisions aren't verified yet, see `src/adhikar/schemes/data/vb_g_ram_g.json`.

**Two voice input channels, two STT paths:**
- Web — Prisma's realtime WebSocket streaming (`stt/v3/stream`)
- WhatsApp — Prisma's single-file REST endpoint (`stt/v3`); voice notes are short enough that no
  async job queue is needed

**Stack:** Python + FastAPI backend, React + TypeScript frontend.

## Implementation status

| Piece | Status |
|---|---|
| STT provider (`adhikar.stt`) — REST + realtime streaming, Prisma v2.5 | Done, tested |
| TTS provider (`adhikar.tts`) — REST + realtime streaming, Timbre v2.5 | Done, tested |
| Scheme knowledge base (versioned per-scheme JSON) | 5 scheme JSON files drafted; models/loader not built |
| FastAPI backend | Not started |
| Frontend | Not started |
| WhatsApp bot integration | Not started |

See `CLAUDE.md` for architecture details and decisions behind the above.

## Running this project

```bash
uv sync                                        # install dependencies
echo "GNANI_API_KEY=..." > .env                # see adhikar.config.Settings for all env vars
uv run pytest                                  # run the test suite
uv run python scripts/realtime_stt_demo.py     # manual mic -> live transcript check
uv run python scripts/tts_demo.py              # manual text -> synthesized speech check
```
