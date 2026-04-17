from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from controllers.chat_controller import chat_endpoint
from typing import Final
import os

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="ShopSight API", version="0.1.0")
    # Allow the dev frontend to talk to the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_api_route("/health", lambda: {"status": "ok"}, methods=["GET"])
    app.add_api_route("/chat", chat_endpoint, methods=["POST"])
    return app


app = create_app()
