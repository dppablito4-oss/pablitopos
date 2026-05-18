"""Database repository layer for the POS application."""

from .company_repo import CompanyRepository
from .client_repo import ClientRepository
from .product_repo import ProductRepository
from .sale_repo import SaleRepository
from .settings_repo import SettingsRepository
from .fiado_repo import FiadoRepository

__all__ = [
    "CompanyRepository",
    "ClientRepository",
    "ProductRepository",
    "SaleRepository",
    "SettingsRepository",
    "FiadoRepository",
]
