from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..config import get_settings
from ..dialogue import Orchestrator, SQLiteProfileStore
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
    stt_provider = PrismaSTTProvider(api_key=settings.gnani_api_key, base_url=settings.gnani_base_url)
    tts_provider = TimbreTTSProvider(api_key=settings.gnani_api_key, base_url=settings.gnani_base_url)

    app.state.stt_provider = stt_provider
    app.state.tts_provider = tts_provider
    app.state.orchestrator = Orchestrator(
        profile_store=profile_store,
        decision_provider=SarvamPrismProvider(settings.sarvam_api_key),
        reasoning_provider=Sarvam105BReasoningProvider(settings.sarvam_api_key),
        conversation_provider=Sarvam105BConversationsProvider(settings.sarvam_api_key),
        schemes=load_all_schemes(),
    )

    yield

    profile_store.close()
    await stt_provider.aclose()
    await tts_provider.aclose()


app = FastAPI(title="Adhikar", lifespan=lifespan)
app.include_router(router)
