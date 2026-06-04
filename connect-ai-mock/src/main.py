"""
Connect AI Mock API Server

A mock server for the CData Connect AI Query APIs.
Supports Static Mode (default) for quick testing.
Supports user-based scenarios via username:PAT credentials.
"""
import os
import asyncio
import base64
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from src.data import init_store, get_store
from src.routes import metadata_router, sql_router


# Configuration from environment
PORT = int(os.getenv("MOCK_PORT", "8080"))
DATA_DIR = os.getenv("MOCK_DATA_DIR", None)
GLOBAL_DELAY_MS = int(os.getenv("MOCK_GLOBAL_DELAY_MS", "0"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize mock data store on startup."""
    print("=" * 60)
    print("Connect AI Mock API Server")
    print("=" * 60)
    print(f"Mode: Static")
    print(f"Port: {PORT}")
    if DATA_DIR:
        print(f"Data Directory: {DATA_DIR}")
    if GLOBAL_DELAY_MS > 0:
        print(f"Global Delay: {GLOBAL_DELAY_MS}ms")
    print("=" * 60)

    # Initialize the mock data store
    store = init_store(DATA_DIR)
    print(f"Loaded {len(store.catalogs)} catalogs")
    print(f"Loaded {len(store.tables)} tables")
    print(f"Loaded {len(store.table_data)} table data files")
    print("=" * 60)
    print("Server ready. Accept any Basic Auth credentials.")
    print("=" * 60)

    yield

    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Connect AI Mock API",
    description="Mock server for CData Connect AI Query APIs",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Delay middleware - supports global delay and per-scenario delays
@app.middleware("http")
async def add_delay(request: Request, call_next):
    """Add configured delay to responses (global + scenario-based)."""
    delay_ms = GLOBAL_DELAY_MS

    # Check for scenario-specific delay from credentials
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        try:
            encoded = auth_header[6:]
            decoded = base64.b64decode(encoded).decode("utf-8")
            if ":" in decoded:
                username, password = decoded.split(":", 1)
                store = get_store()
                scenario = store.get_scenario((username, password))
                if scenario and scenario.delay_ms > 0:
                    delay_ms = max(delay_ms, scenario.delay_ms)
        except Exception:
            pass  # Ignore decoding errors, use global delay

    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    response = await call_next(request)
    return response


# Include routers
app.include_router(metadata_router)
app.include_router(sql_router)


@app.get("/")
async def root():
    """Health check / info endpoint."""
    return {
        "name": "Connect AI Mock API",
        "version": "1.0.0",
        "mode": "static",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/favicon.ico")
@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
async def favicon():
    """Return empty response for browser icon requests."""
    return Response(status_code=204)


def main():
    """Run the server."""
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="warning",   # suppress access logs so subprocess pipes don't fill up
        access_log=False,
    )


if __name__ == "__main__":
    main()
