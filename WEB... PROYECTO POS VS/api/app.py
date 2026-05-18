from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.clients import router as clients_router
from api.routers.products import router as products_router

app = FastAPI(title="Pablito POS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(clients_router, prefix="/api/clients", tags=["clients"])
app.include_router(products_router, prefix="/api/products", tags=["products"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
