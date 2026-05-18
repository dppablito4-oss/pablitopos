"""UI component managers for the POS application."""

from .customer_display_manager import CustomerDisplayManager
from .ui_clients import ClientUIManager
from .ui_dashboard import DashboardUIManager
from .ui_fiados import FiadosUIManager
from .ui_history import HistoryUIManager
from .ui_products import ProductUIManager
from .ui_sales import SalesUIManager
from .ui_sales_helpers import SalesUIHelpers
from .ui_update_info import UpdateInfoMethods

__all__ = [
    "ClientUIManager",
    "CustomerDisplayManager",
    "DashboardUIManager",
    "FiadosUIManager",
    "HistoryUIManager",
    "ProductUIManager",
    "SalesUIManager",
    "SalesUIHelpers",
    "UpdateInfoMethods",
]
