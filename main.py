from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import guild

app = FastAPI(title="Bot Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bot-dashboard-iota.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guild.router, prefix="/guild")

@app.get("/")
async def root():
    return {"status": "Bot Dashboard API is running ✅"}
