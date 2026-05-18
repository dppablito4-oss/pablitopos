from fastapi import APIRouter, HTTPException

from api.schemas import ClientCreate, ClientOut, ClientUpdate
from db_connection import get_default_database
from repositories.client_repo import ClientRepository
from services.client_service import ClientService

router = APIRouter()


def _service() -> ClientService:
    db = get_default_database()
    return ClientService(ClientRepository(db))


def _row_to_client(row) -> ClientOut:
    return ClientOut(
        id=row[0],
        dni=row[1],
        full_name=row[2],
        phone=row[3],
        email=row[4],
        address=row[5],
        created_at=row[6],
    )


@router.get("/", response_model=list[ClientOut])
def list_clients(q: str | None = None):
    service = _service()
    rows = service.search_clients(q or "")
    return [_row_to_client(r) for r in rows]


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int):
    service = _service()
    row = service.get_client_by_id(client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return _row_to_client(row)


@router.post("/", response_model=ClientOut)
def create_client(payload: ClientCreate):
    service = _service()
    try:
        client_id = service.create_client(
            payload.dni or "",
            payload.full_name,
            payload.phone or "",
            payload.email or "",
            payload.address or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    row = service.get_client_by_id(client_id)
    return _row_to_client(row)


@router.put("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, payload: ClientUpdate):
    service = _service()
    try:
        service.update_client(
            client_id,
            payload.dni or "",
            payload.full_name,
            payload.phone or "",
            payload.email or "",
            payload.address or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    row = service.get_client_by_id(client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return _row_to_client(row)


@router.delete("/{client_id}")
def delete_client(client_id: int):
    service = _service()
    service.delete_client(client_id)
    return {"status": "ok"}
