from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="OutreachIQ API",
    description="AI-powered LinkedIn outreach message generator.",
    version="1.0.0",
)

app.include_router(router)