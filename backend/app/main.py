"""Porchlight HTTP entry point. The demo resets to fictional seed data on boot."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_connection, reset_demo
from .graph import prime_interest_embeddings
from .routes.core import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    reset_demo()
    with closing(get_connection()) as connection:
        members = [dict(row) for row in connection.execute("SELECT * FROM members")]
    prime_interest_embeddings(members)
    yield


app = FastAPI(title="Porchlight", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)
