from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from ..dialogue import Orchestrator, SQLiteActivityLogStore, SQLiteProfileStore
from ..nlg import Sarvam105BConversationsProvider
from ..nlu import Sarvam105BReasoningProvider, SarvamPrismProvider
from ..schemes import load_all_schemes
from ..stt import PrismaSTTProvider
from ..tts import TimbreTTSProvider
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    profile_store = SQLiteProfileStore(settings.profile_db_path)
    # Same SQLite file as profile_store, different table — no new config, no concurrent-write
    # concern beyond what SQLiteProfileStore already accepts for this single-process app.
    activity_log = SQLiteActivityLogStore(settings.profile_db_path)
    stt_provider = PrismaSTTProvider(api_key=settings.gnani_api_key, base_url=settings.gnani_base_url)
    tts_provider = TimbreTTSProvider(api_key=settings.gnani_api_key, base_url=settings.gnani_base_url)
    schemes = load_all_schemes()

    app.state.stt_provider = stt_provider
    app.state.tts_provider = tts_provider
    app.state.profile_store = profile_store
    app.state.activity_log = activity_log
    app.state.schemes = schemes
    app.state.orchestrator = Orchestrator(
        profile_store=profile_store,
        activity_log=activity_log,
        decision_provider=SarvamPrismProvider(settings.sarvam_api_key),
        reasoning_provider=Sarvam105BReasoningProvider(settings.sarvam_api_key),
        conversation_provider=Sarvam105BConversationsProvider(settings.sarvam_api_key),
        schemes=schemes,
    )

    yield

    profile_store.close()
    activity_log.close()
    await stt_provider.aclose()
    await tts_provider.aclose()


app = FastAPI(title="Adhikar", lifespan=lifespan)
# Vite's dev server (and `vite preview`) run on a different origin than uvicorn, so the browser
# enforces CORS on every /chat, /voice, /stt/stream, /tts/stream call. Hardcoded, not a Settings
# field: these are fixed local dev ports, not something that varies per deployment yet.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
