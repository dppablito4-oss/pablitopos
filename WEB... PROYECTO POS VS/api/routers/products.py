from fastapi import APIRouter, HTTPException

from api.schemas import ProductCreate, ProductOut, ProductUpdate
from db_connection import get_default_database
from repositories.product_repo import ProductRepository
from services.product_service import ProductService

router = APIRouter()


def _service() -> ProductService:
    db = get_default_database()
    return ProductService(ProductRepository(db))


def _row_to_product(row) -> ProductOut:
    return ProductOut(
        id=row[0],
        code=row[1],
        name=row[2],
        unit=row[3],
        price=row[4],
        stock=row[5],
        price_includes_igv=row[6] if len(row) > 6 else 0,
    )


@router.get("/", response_model=list[ProductOut])
def list_products(q: str | None = None):
    service = _service()
    rows = service.search_products(q or "")
    return [_row_to_product(r) for r in rows]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int):
    service = _service()
    row = service.get_product_by_id(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return _row_to_product(row)


@router.post("/", response_model=ProductOut)
def create_product(payload: ProductCreate):
    service = _service()
    try:
        product_id = service.create_product(
            payload.name,
            payload.unit,
            payload.price,
            code=payload.code,
            stock=payload.stock,
            price_includes_igv=payload.price_includes_igv or 0,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    row = service.get_product_by_id(product_id)
    return _row_to_product(row)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate):
    service = _service()
    try:
        service.update_product(
            product_id,
            payload.name,
            payload.unit,
            payload.price,
            code=payload.code,
            stock=payload.stock,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    row = service.get_product_by_id(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return _row_to_product(row)


@router.delete("/{product_id}")
def delete_product(product_id: int):
    service = _service()
    service.delete_product(product_id)
    return {"status": "ok"}
