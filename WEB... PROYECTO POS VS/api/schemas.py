from typing import Optional
from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    dni: Optional[str] = None
    full_name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    pass


class ClientOut(ClientBase):
    id: int
    created_at: Optional[str] = None


class ProductBase(BaseModel):
    code: Optional[str] = None
    name: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    price: float
    stock: Optional[float] = None
    price_includes_igv: Optional[int] = 0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
