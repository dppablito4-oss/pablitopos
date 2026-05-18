"""
UI Helpers para mejorar la funcionalidad de ventas
Incluye:
- Toggle de descuento (% vs monto fijo)
- Campo de precio editable
- Verificación de stock
"""

import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox

class SalesUIHelpers:
    """Helper class para mejorar la UI de ventas"""

    @staticmethod
    def _scroll_units(target, units: int):
        try:
            target.yview_scroll(units, "units")
        except Exception:
            pass
        return "break"

    @staticmethod
    def bind_mousewheel(widget, target=None):
        """Vincula la rueda del mouse a un widget con yview_scroll."""
        scroll_target = target or widget

        def on_mousewheel(event):
            delta = event.delta if hasattr(event, "delta") else 0
            if delta == 0 and hasattr(event, "num"):
                delta = 120 if event.num == 4 else -120
            units = int(-1 * (delta / 120)) if delta else 0
            if units != 0:
                return SalesUIHelpers._scroll_units(scroll_target, units)
            return "break"

        widget.bind("<MouseWheel>", on_mousewheel, add="+")
        widget.bind("<Button-4>", lambda e: SalesUIHelpers._scroll_units(scroll_target, -1), add="+")
        widget.bind("<Button-5>", lambda e: SalesUIHelpers._scroll_units(scroll_target, 1), add="+")

    @staticmethod
    def bind_mousewheel_to_children(container):
        """Activa la rueda en todos los hijos scrollables del contenedor."""
        try:
            children = container.winfo_children()
        except Exception:
            return

        scrollables = (tb.Treeview, tk.Listbox, tk.Text, tk.Canvas)

        for child in children:
            if isinstance(child, scrollables):
                SalesUIHelpers.bind_mousewheel(child)
            # Recurse into frames to reach nested widgets
            SalesUIHelpers.bind_mousewheel_to_children(child)
    
    @staticmethod
    def setup_placeholder(entry, placeholder="0.00"):
        """Configura un entry para que se limpie al recibir foco si tiene el valor placeholder."""
        entry.placeholder_val = placeholder
        
        def on_focus_in(event):
            if entry.get().strip() == entry.placeholder_val:
                entry.delete(0, tk.END)
                entry.config(foreground='white') # Color normal al editar

        def on_focus_out(event):
            if not entry.get().strip():
                entry.insert(0, entry.placeholder_val)
                # Opcional: cambiar color a gris para indicar placeholder
                # entry.config(foreground='grey')

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        
        # Inicializar
        if not entry.get():
            entry.insert(0, placeholder)

    @staticmethod
    def create_discount_toggle_ui(parent_frame, app_instance):
        """
        Crea un toggle entre descuento por porcentaje y monto fijo
        """
        # Frame contenedor para el descuento
        discount_frame = tb.Frame(parent_frame)
        discount_frame.grid(row=0, column=2, columnspan=2, padx=12, pady=2, sticky="w")
        
        # Label
        tb.Label(discount_frame, text="Descuento:").pack(side=tk.LEFT, padx=(0,6))
        
        # Entry para el valor
        app_instance.entry_global_discount = tb.Entry(discount_frame, width=8)
        SalesUIHelpers.setup_placeholder(app_instance.entry_global_discount, "0.00")
        app_instance.entry_global_discount.pack(side=tk.LEFT, padx=3)
        app_instance.entry_global_discount.bind("<KeyRelease>", lambda e: app_instance.sales_ui.update_totals())
        
        # Variable para el tipo de descuento
        app_instance.discount_type = tk.StringVar(value="fixed")  # 'fixed' o 'percent'
        
        # Botón toggle
        app_instance.btn_discount_type = tb.Button(
            discount_frame,
            text="S/",
            width=3,
            bootstyle="secondary-outline",
            command=lambda: SalesUIHelpers.toggle_discount_type(app_instance)
        )
        app_instance.btn_discount_type.pack(side=tk.LEFT, padx=3)
        
        return discount_frame

    # ... (toggle_discount_type y calculate_discount_amount se mantienen igual, no los toco en este replace) ...

    @staticmethod
    def create_product_edit_controls(parent_frame, app_instance):
        """
        Crea campo para editar Precio del producto seleccionado.
        """
        # Usamos un frame interno
        edit_frame = tb.Frame(parent_frame)
        edit_frame.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        
        # --- Solo Precio ---
        tb.Label(edit_frame, text="Precio:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(5,2))
        
        app_instance.entry_custom_price = tb.Entry(edit_frame, width=10)
        app_instance.entry_custom_price.pack(side=tk.LEFT, padx=2)
        
        # Botón reset precio pequeño
        tb.Button(
            edit_frame,
            text="↺",
            bootstyle="link",
            command=lambda: SalesUIHelpers.reset_to_original_price(app_instance)
        ).pack(side=tk.LEFT)
        
        return edit_frame
    
    @staticmethod
    def toggle_discount_type(app_instance):
        """Alterna entre descuento en soles y porcentaje"""
        if app_instance.discount_type.get() == "fixed":
            # Cambiar a porcentaje
            app_instance.discount_type.set("percent")
            app_instance.btn_discount_type.config(text="%")
        else:
            # Cambiar a soles
            app_instance.discount_type.set("fixed")
            app_instance.btn_discount_type.config(text="S/")
        
        # Actualizar totales con el nuevo tipo
        app_instance.sales_ui.update_totals()
    
    @staticmethod
    def calculate_discount_amount(app_instance):
        """
        Calcula el monto real de descuento basado en el tipo
        
        Returns:
            float: Monto de descuento en soles
        """
        try:
            discount_value = float(app_instance.entry_global_discount.get().strip() or 0)
        except ValueError:
            discount_value = 0.0
        
        if app_instance.discount_type.get() == "percent":
            # Calcular el porcentaje del subtotal
            subtotal = sum(item["subtotal"] for item in app_instance.sale_items)
            discount_amount = round(subtotal * (discount_value / 100), 2)
        else:
            # Es un monto fijo
            discount_amount = discount_value
        
        return discount_amount
    
    @staticmethod
    def create_editable_price_field(parent_frame, app_instance):
        """
        Crea un campo para editar el precio del producto antes de agregarlo
        
        Args:
            parent_frame: Frame donde se agregará el control
            app_instance: Instancia de la app principal
        """
        price_frame = tb.Frame(parent_frame)
        
        tb.Label(price_frame, text="Precio:").pack(side=tk.LEFT, padx=(0,6))
        
        app_instance.entry_custom_price = tb.Entry(price_frame, width=10)
        app_instance.entry_custom_price.pack(side=tk.LEFT, padx=3)
        
        # Botón para usar precio original
        tb.Button(
            price_frame,
            text="Precio Original",
            bootstyle="info-outline",
            command=lambda: SalesUIHelpers.reset_to_original_price(app_instance)
        ).pack(side=tk.LEFT, padx=3)
        
        return price_frame
    
    @staticmethod
    def reset_to_original_price(app_instance):
        """Restaura el precio original del producto seleccionado"""
        if app_instance.selected_product:
            original_price = app_instance.selected_product["price"]
            app_instance.entry_custom_price.delete(0, tk.END)
            app_instance.entry_custom_price.insert(0, f"{original_price:.2f}")
    
    @staticmethod
    def check_and_display_stock(app_instance, product):
        """
        Verifica y muestra el stock disponible de un producto
        
        Args:
            app_instance: Instancia de la app principal
            product: Tuple con datos del producto (id, code, name, unit, price, stock, price_includes_igv)
            
        Returns:
            str: Mensaje de stock para mostrar
        """
        # Índice 5 es stock
        stock = product[5] if len(product) > 5 else None
        
        if stock is None:
            return "Sin control de stock"
        else:
            if stock <= 0:
                return f"⚠️ SIN STOCK"
            elif stock <= 5:
                return f"⚠️ Stock bajo: {stock}"
            else:
                return f"Stock: {stock}"
    
    @staticmethod
    def validate_stock_before_add(app_instance, product_id, quantity):
        """
        Valida que haya stock suficiente antes de agregar el producto
        
        Args:
            app_instance: Instancia de la app principal
            product_id: ID del producto
            quantity: Cantidad a agregar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        reserved = 0.0
        if hasattr(app_instance, "sale_items"):
            reserved = sum(item.get("quantity", 0) for item in app_instance.sale_items if item.get("product_id") == product_id)

        available, message = app_instance.product_service.check_stock_availability(product_id, quantity, already_reserved=reserved)
        
        if not available:
            if hasattr(app_instance, "show_warning"):
                app_instance.show_warning("Stock Insuficiente", message)
            else:
                # Use ttkbootstrap Messagebox (styled) as fallback
                try:
                    Messagebox.showwarning("Stock Insuficiente", message)
                except Exception:
                    # Last resort: use tkinter.messagebox if ttkbootstrap unavailable
                    try:
                        from tkinter import messagebox as _tkmb
                        _tkmb.showwarning("Stock Insuficiente", message)
                    except Exception:
                        pass
            return False, message
        
        return True, "OK"
    
    @staticmethod
    def add_stock_indicator_to_product_list(tree, products, product_service, reserved_items=None):
        """Llena el catálogo de productos mostrando stock con semáforo."""
        _ = product_service  # mantenemos la firma por compatibilidad
        tree.delete(*tree.get_children())

        reserved_map = {}
        if reserved_items:
            for reserved in reserved_items:
                pid = reserved.get("product_id")
                qty = reserved.get("quantity", 0)
                if not pid:
                    continue
                reserved_map[pid] = reserved_map.get(pid, 0) + qty

        for product in products:
            product_id = product[0]
            name = product[2]
            unit = product[3]
            price = product[4]
            stock = product[5] if len(product) > 5 else None
            reserved_qty = reserved_map.get(product_id, 0)

            if stock is None:
                stock_display = "Sin control"
                tag = "normal"
            else:
                try:
                    stock_val = float(stock) - float(reserved_qty)
                except (TypeError, ValueError):
                    stock_val = None

                if stock_val is None:
                    stock_display = str(stock)
                    tag = "normal"
                elif stock_val <= 0:
                    stock_display = "SIN STOCK"
                    tag = "no_stock"
                elif stock_val <= 5:
                    stock_display = f"{int(stock_val) if stock_val.is_integer() else round(stock_val, 2)} (bajo)"
                    tag = "low_stock"
                else:
                    stock_display = f"{int(stock_val) if stock_val.is_integer() else round(stock_val, 2)}"
                    tag = "normal"

            tree.insert(
                "",
                "end",
                iid=str(product_id),
                values=(name, unit, f"S/ {price:.2f}", stock_display),
                tags=(tag,)
            )

        tree.tag_configure("no_stock", background="#FDE4E4", foreground="#5A0B0B")
        tree.tag_configure("low_stock", background="#FFF3CD", foreground="#665200")
        tree.tag_configure("normal", background="", foreground="")
