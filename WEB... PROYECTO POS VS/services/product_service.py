from repositories.product_repo import ProductRepository


class ProductService:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    @staticmethod
    def _normalize_code(raw_code):
        """Formatea códigos a mayúsculas y con prefijo/padding (ej. 1 -> P0001)."""
        if raw_code is None:
            return None
        code = str(raw_code).strip()
        if not code:
            return None
        code = code.upper()

        # Si es solo número, prefijar con P y pad a 4 dígitos
        if code.isdigit():
            return f"P{int(code):04d}"

        # Si comienza con letra y resto numérico, pad a 4 dígitos manteniendo prefijo
        if len(code) >= 2 and code[0].isalpha() and code[1:].isdigit():
            return f"{code[0]}{int(code[1:]):04d}"

        return code

    def search_products(self, text):
        return self.repo.search_products(text)

    def get_product_by_id(self, product_id):
        return self.repo.get_product_by_id(product_id)

    def _parse_stock_value(self, stock):
        if stock is None or str(stock).strip() == "":
            return None
        try:
            return int(round(float(stock)))
        except ValueError:
            raise ValueError("El stock debe ser numérico.")

    def create_product(self, name, unit, price, code=None, stock=None, price_includes_igv=0):
        if not name.strip():
            raise ValueError("El nombre del producto es obligatorio.")
        if not unit.strip():
            raise ValueError("La unidad de medida es obligatoria.")
        name = name.strip().upper()
        unit = unit.strip().upper()
        code = self._normalize_code(code)
        try:
            price = float(price)
        except ValueError:
            raise ValueError("El precio debe ser numérico.")
        if price < 0:
            raise ValueError("El precio no puede ser negativo.")

        stock_value = self._parse_stock_value(stock)
        if stock_value is not None and stock_value < 0:
            raise ValueError("El stock no puede ser negativo.")

        return self.repo.create_product(code, name, unit, price, stock_value, price_includes_igv)

    def update_product_price(self, product_id, price, price_includes_igv=None):
        try:
            price = float(price)
        except ValueError:
            raise ValueError("El precio debe ser numérico.")
        if price < 0:
            raise ValueError("El precio no puede ser negativo.")
        return self.repo.update_product_price(product_id, price, price_includes_igv)

    def check_stock_availability(self, product_id, quantity, already_reserved=0):
        product = self.repo.get_product_by_id(product_id)
        if not product:
            return False, "Producto no encontrado"

        stock = product[5] if len(product) > 5 else None

        if stock is None:
            return True, "OK"

        try:
            stock_value = float(stock)
        except (TypeError, ValueError):
            return True, "OK"

        disponible = stock_value - float(already_reserved or 0)
        if disponible <= 0:
            return False, "Stock agotado para este producto."

        if float(quantity) > disponible:
            restante = max(disponible, 0)
            restante_str = f"{int(restante)}" if restante.is_integer() else f"{restante:.2f}"
            return False, f"Stock insuficiente. Disponible: {restante_str}"

        return True, "OK"

    def reduce_stock(self, product_id, quantity):
        self.repo.reduce_stock(product_id, quantity)

    def update_stock(self, product_id, new_stock):
        new_stock_value = self._parse_stock_value(new_stock)
        if new_stock_value is not None and new_stock_value < 0:
            raise ValueError("El stock no puede ser negativo.")
        self.repo.update_stock(product_id, new_stock_value)

    def update_product(self, product_id, name, unit, price, code=None, stock=None):
        if not name.strip():
            raise ValueError("El nombre del producto es obligatorio.")
        if not unit.strip():
            raise ValueError("La unidad de medida es obligatoria.")
        name = name.strip().upper()
        unit = unit.strip().upper()
        code = self._normalize_code(code)
        try:
            price = float(price)
        except ValueError:
            raise ValueError("El precio debe ser numérico.")
        if price < 0:
            raise ValueError("El precio no puede ser negativo.")

        if stock is not None and str(stock).strip() != "":
            stock = self._parse_stock_value(stock)
            if stock is not None and stock < 0:
                raise ValueError("El stock no puede ser negativo.")
        else:
            stock = None

        return self.repo.update_product(product_id, code, name, unit, price, stock)

    def delete_product(self, product_id):
        return self.repo.delete_product(product_id)
