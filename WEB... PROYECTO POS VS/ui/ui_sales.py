import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
import os
import subprocess
import threading
from settings import PDF_DIR
from .ui_sales_helpers import SalesUIHelpers

class SalesUIManager:
    def __init__(self, app):
        self.app = app
        self.mode = "sale"  # sale | boletin

    def build_sales_ui(self):
        """Construye la interfaz de ventas con catálogo visual de productos."""
        f = self.app.frame_sales
        f.rowconfigure(0, weight=1)
        f.rowconfigure(1, weight=0)  # Para totales y botones
        f.columnconfigure(0, weight=1)

        # Contenedor principal con dos columnas
        main_container = tb.Frame(f)
        main_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main_container.rowconfigure(0, weight=0)  # Cliente (fixed)
        main_container.rowconfigure(1, weight=1)  # Catálogo productos (expandible)
        main_container.columnconfigure(0, weight=1)  # Columna izquierda
        main_container.columnconfigure(1, weight=2)  # Columna derecha (más ancha)

        # ========== COLUMNA IZQUIERDA ==========
        # Frame Cliente (arriba, fijo)
        self.app.client_lf = tb.Labelframe(
            main_container,
            text="👤 Cliente",
            padding=8,
            bootstyle="info"
        )
        self.app.client_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        self.app.client_lf.columnconfigure(1, weight=1)

        tb.Label(self.app.client_lf, text="Buscar:").grid(row=0, column=0, padx=3, pady=2, sticky="e")
        self.app.entry_client_search = tb.Entry(self.app.client_lf, width=12)
        self.app.entry_client_search.grid(row=0, column=1, padx=3, pady=2, sticky="we")

        btn_client_search = tb.Button(
            self.app.client_lf,
            text="Buscar",
            bootstyle="info-outline",
            command=self.app.client_ui.search_or_create_client,
            width=8
        )
        btn_client_search.grid(row=0, column=2, padx=3, pady=2)
        self.app.add_help_tooltip(btn_client_search, "Busca clientes existentes o registra uno nuevo al instante.")

        self.app.label_current_client = tb.Label(
            self.app.client_lf,
            text="", # Texto vacío inicialmente
            bootstyle="danger", # Color rojo para alertas
            wraplength=150,
            font=("Arial", 8)
        )
        # Row 2 para mensajes de estado (debajo de la lista que estará en Row 1)
        self.app.label_current_client.grid(row=2, column=0, columnspan=3, sticky="w", padx=3, pady=2)

        # Small client info boxes
        self.app.var_client_name_small = tk.StringVar(value="(ninguno)")
        self.app.var_client_dni = tk.StringVar(value="")
        self.app.var_client_phone = tk.StringVar(value="")

        client_info_frame = tb.Frame(self.app.client_lf)
        # Row 3 para info del cliente seleccionado
        client_info_frame.grid(row=3, column=0, columnspan=3, sticky="we", padx=3, pady=2)
        client_info_frame.columnconfigure((0, 1, 2), weight=1)

        tb.Label(client_info_frame, text="Nombre:", font=("Arial", 8)).grid(row=0, column=0, sticky="w")
        tb.Label(client_info_frame, textvariable=self.app.var_client_name_small, font=("Arial", 8, "bold"), wraplength=120).grid(row=1, column=0, sticky="w")

        tb.Label(client_info_frame, text="DNI:", font=("Arial", 8)).grid(row=0, column=1, sticky="w")
        tb.Label(client_info_frame, textvariable=self.app.var_client_dni, font=("Arial", 8)).grid(row=1, column=1, sticky="w")

        tb.Label(client_info_frame, text="Cel:", font=("Arial", 8)).grid(row=0, column=2, sticky="w")
        tb.Label(client_info_frame, textvariable=self.app.var_client_phone, font=("Arial", 8)).grid(row=1, column=2, sticky="w")

        self.app.client_ui.setup_client_autocomplete()

        # Frame Catálogo de Productos (abajo, expandible)
        self.app.prod_lf = tb.Labelframe(
            main_container,
            text="📦 Catálogo de Productos",
            padding=8,
            bootstyle="success"
        )
        self.app.prod_lf.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        self.app.prod_lf.rowconfigure(1, weight=1)  # Treeview expandible
        self.app.prod_lf.columnconfigure(0, weight=1)

        # Buscador de productos
        search_frame = tb.Frame(self.app.prod_lf)
        search_frame.grid(row=0, column=0, sticky="we", pady=(0, 5))
        search_frame.columnconfigure(1, weight=1)

        tb.Label(search_frame, text="🔍 Buscar:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.app.entry_product_catalog_search = tb.Entry(search_frame)
        self.app.entry_product_catalog_search.grid(row=0, column=1, sticky="we")
        self.app.entry_product_catalog_search.bind("<KeyRelease>", self.app.product_ui.filter_sales_products)

        # Treeview de productos
        tree_frame = tb.Frame(self.app.prod_lf)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ("name", "unit", "price", "stock")
        self.app.tree_sales_products = tb.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            bootstyle="success",
            height=10
        )
        self.app.tree_sales_products.heading("name", text="Producto")
        self.app.tree_sales_products.heading("unit", text="Unidad")
        self.app.tree_sales_products.heading("price", text="Precio")
        self.app.tree_sales_products.heading("stock", text="Stock")

        self.app.tree_sales_products.column("name", width=160)
        self.app.tree_sales_products.column("unit", width=50, anchor="center")
        self.app.tree_sales_products.column("price", width=60, anchor="e")
        self.app.tree_sales_products.column("stock", width=70, anchor="center")

        self.app.tree_sales_products.grid(row=0, column=0, sticky="nsew")
        
        scrollbar_products = tb.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.app.tree_sales_products.yview,
            bootstyle="success-round"
        )
        self.app.tree_sales_products.configure(yscrollcommand=scrollbar_products.set)
        scrollbar_products.grid(row=0, column=1, sticky="ns")

        # Bind selección de producto
        self.app.tree_sales_products.bind("<<TreeviewSelect>>", self.app.product_ui.on_sales_product_select)

        # Frame para agregar producto seleccionado
        add_frame = tb.Frame(self.app.prod_lf)
        add_frame.grid(row=2, column=0, sticky="we", pady=(5, 0))
        add_frame.columnconfigure(1, weight=1)

        tb.Label(add_frame, text="Cantidad:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.app.entry_quantity = tb.Combobox(add_frame, width=5, values=[str(i) for i in range(1, 11)])
        self.app.entry_quantity.current(0) # Seleccionar "1" por defecto
        self.app.entry_quantity.pack(side=tk.LEFT, padx=(0, 10))

        # Toggle ingreso/egreso para boletines (oculto en modo venta)
        self.app.flow_type_var = tk.StringVar(value="ingreso")
        self.boletin_flow_frame = tb.Frame(add_frame)
        tb.Label(self.boletin_flow_frame, text="Tipo:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        tb.Radiobutton(
            self.boletin_flow_frame,
            text="Ingreso",
            value="ingreso",
            variable=self.app.flow_type_var,
            bootstyle="success-toolbutton"
        ).pack(side=tk.LEFT)
        tb.Radiobutton(
            self.boletin_flow_frame,
            text="Egreso",
            value="egreso",
            variable=self.app.flow_type_var,
            bootstyle="danger-toolbutton"
        ).pack(side=tk.LEFT, padx=(4, 0))
        self.boletin_flow_frame.pack(side=tk.LEFT, padx=(0, 10))
        self.boletin_flow_frame.pack_forget()
        
        # --- NUEVO: Controles de Edición (Nombre y Precio) ---
        SalesUIHelpers.create_product_edit_controls(add_frame, self.app)
        # ------------------------------

        btn_add_product = tb.Button(
            add_frame,
            text="➕ Agregar",
            bootstyle="success",
            command=lambda: self.add_item_to_sale(),
            width=12
        )
        btn_add_product.pack(side=tk.LEFT, padx=10)
        self.app.add_help_tooltip(btn_add_product, "Agrega el producto seleccionado al detalle del comprobante.")

        # Inicializar cache y cargar productos
        self.app.sales_products_cache = []
        self.app.selected_product = None

        # ========== COLUMNA DERECHA: Detalle del Comprobante ==========
        detail_lf = tb.Labelframe(
            main_container,
            text="📋 Detalle del Comprobante",
            padding=8,
            bootstyle="primary"
        )
        detail_lf.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))
        detail_lf.rowconfigure(0, weight=1)
        detail_lf.columnconfigure(0, weight=1)

        columns = ("item", "description", "unit", "quantity", "unit_price", "subtotal")
        self.app.tree_detail = tb.Treeview(detail_lf, columns=columns, show="headings", bootstyle="dark", height=15)
        self.app.tree_detail.heading("item", text="Ítem")
        self.app.tree_detail.heading("description", text="Producto")
        self.app.tree_detail.heading("unit", text="Unidad")
        self.app.tree_detail.heading("quantity", text="Cant.")
        self.app.tree_detail.heading("unit_price", text="P.Unit")
        self.app.tree_detail.heading("subtotal", text="Subtotal")

        self.app.tree_detail.column("item", width=35, anchor="center")
        self.app.tree_detail.column("description", width=180)
        self.app.tree_detail.column("unit", width=50, anchor="center")
        self.app.tree_detail.column("quantity", width=50, anchor="e")
        self.app.tree_detail.column("unit_price", width=70, anchor="e")
        self.app.tree_detail.column("subtotal", width=70, anchor="e")

        # Resaltar egresos en el detalle
        self.app.tree_detail.tag_configure("expense", background="#ffeceb", foreground="#b3261e")

        self.app.tree_detail.grid(row=0, column=0, sticky="nsew")
        scrollbar = tb.Scrollbar(detail_lf, orient="vertical", command=self.app.tree_detail.yview, bootstyle="round")
        self.app.tree_detail.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        action_btn_frame = tb.Frame(detail_lf)
        action_btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=3)
        action_btn_frame.columnconfigure(0, weight=1)
        action_btn_frame.columnconfigure(1, weight=1)

        btn_edit_item = tb.Button(
            action_btn_frame,
            text="✏️ Editar ítem",
            bootstyle="secondary-outline",
            command=lambda: self.edit_selected_item(),
            width=20
        )
        btn_edit_item.grid(row=0, column=0, sticky="ew", padx=(0,3))
        self.app.add_help_tooltip(btn_edit_item, "Modifica cantidad o precio del ítem seleccionado.")

        btn_delete_item = tb.Button(
            action_btn_frame,
            text="❌ Eliminar ítem",
            bootstyle="danger-outline",
            command=lambda: self.delete_selected_item(),
            width=20
        )
        btn_delete_item.grid(row=0, column=1, sticky="ew", padx=(3,0))
        self.app.add_help_tooltip(btn_delete_item, "Quita el ítem del comprobante actual.")

        # ========== BOTTOM: Totales y Acciones (ancho completo) ==========
        # Añadimos un recuadro al final que ocupa todo el ancho con totales a la izquierda
        # y botones de acción en línea a la derecha
        f.rowconfigure(1, weight=0)
        bottom_lf = tb.Labelframe(
            f,
            text="💰 Totales y Acciones",
            padding=8,
            bootstyle="danger"
        )
        bottom_lf.grid(row=1, column=0, sticky="we", padx=5, pady=(5, 5))
        bottom_lf.columnconfigure(0, weight=1)
        bottom_lf.columnconfigure(1, weight=0)

        # Totales (alineados a la izquierda)
        totals_frame = tb.Frame(bottom_lf)
        totals_frame.grid(row=0, column=0, sticky="w")
        
        # Subtotal
        tb.Label(totals_frame, text="Subtotal:").grid(row=0, column=0, padx=(3,6), pady=2, sticky="w")
        self.app.var_subtotal = tk.StringVar(value="0.00")
        tb.Label(totals_frame, textvariable=self.app.var_subtotal, bootstyle="inverse-secondary").grid(row=0, column=1, padx=3, pady=2, sticky="w")

        # Descuento Global (Toggle)
        SalesUIHelpers.create_discount_toggle_ui(totals_frame, self.app)
        
        # Checkbox IGV
        self.app.include_igv_var = tk.BooleanVar(value=True)
        # Intentar cargar valor por defecto de la empresa
        try:
            default_igv = bool((self.app.current_company_data or {}).get('include_igv', True))
            self.app.include_igv_var.set(default_igv)
        except:
            pass
            
        cb_igv = tb.Checkbutton(
            totals_frame, 
            text="Incluir IGV", 
            variable=self.app.include_igv_var,
            bootstyle="round-toggle",
            command=lambda: self.update_totals()
        )
        cb_igv.grid(row=0, column=4, padx=5, sticky="w")
        # Guardar referencias para poder ocultar cuando la empresa no usa IGV
        self.cb_igv = cb_igv

        # IGV
        # IGV Label
        igv_label = tb.Label(totals_frame, text="IGV (18%):")
        igv_label.grid(row=0, column=5, padx=(5,2), pady=2, sticky="w")
        self.app.var_igv = tk.StringVar(value="0.00")
        igv_value = tb.Label(totals_frame, textvariable=self.app.var_igv, bootstyle="inverse-secondary")
        igv_value.grid(row=0, column=6, padx=3, pady=2, sticky="w")
        self.igv_label = igv_label
        self.igv_value = igv_value

        # Adelanto (solo Boletín)
        self.app.is_adelanto_var = tk.BooleanVar(value=False)
        adelanto_toggle = tb.Checkbutton(
            totals_frame,
            text="Adelanto",
            variable=self.app.is_adelanto_var,
            bootstyle="round-toggle",
            command=lambda: self._toggle_adelanto_fields()
        )
        adelanto_toggle.grid(row=0, column=9, padx=(10, 4), sticky="w")
        self.adelanto_toggle = adelanto_toggle

        self.app.var_adelanto_amount = tk.StringVar(value="0.00")
        self.app.var_estimated_total = tk.StringVar(value="0.00")
        adelanto_frame = tb.Frame(totals_frame)
        adelanto_frame.grid(row=0, column=10, padx=6, sticky="w")
        tb.Label(adelanto_frame, text="Monto:").pack(side=tk.LEFT)
        entry_adelanto = tb.Entry(adelanto_frame, width=8, textvariable=self.app.var_adelanto_amount)
        entry_adelanto.pack(side=tk.LEFT, padx=(2, 6))
        tb.Label(adelanto_frame, text="Total est.:").pack(side=tk.LEFT)
        entry_estimado = tb.Entry(adelanto_frame, width=8, textvariable=self.app.var_estimated_total)
        entry_estimado.pack(side=tk.LEFT, padx=(2, 0))
        self.adelanto_frame = adelanto_frame
        self.entry_adelanto = entry_adelanto
        self.entry_estimado = entry_estimado
        self._toggle_adelanto_fields(force_hide=True)

        # Aplicar política de IGV según el perfil (ocultar o desactivar cuando no corresponde)
        self._apply_company_igv_policy()

        # Total
        tb.Label(totals_frame, text="Total:", font=("Arial", 10, "bold")).grid(row=0, column=7, padx=(12,6), pady=2, sticky="w")
        self.app.var_total = tk.StringVar(value="0.00")
        tb.Label(totals_frame, textvariable=self.app.var_total, bootstyle="inverse-success", font=("Arial", 11, "bold")).grid(row=0, column=8, padx=3, pady=2, sticky="w")

        # Botones de acción (alineados a la derecha dentro del mismo recuadro)
        actions_frame = tb.Frame(bottom_lf)
        actions_frame.grid(row=0, column=1, sticky="e")
        actions_frame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        btn_save_sale = tb.Button(actions_frame, text="Guardar", bootstyle="success-outline", command=lambda: self.save_sale())
        btn_save_sale.grid(row=0, column=0, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_save_sale, "Guarda la venta sin generar PDF. Útil para completar luego.")

        btn_pdf_sale = tb.Button(actions_frame, text="Guardar + PDF", bootstyle="primary-outline", command=lambda: self.save_sale_and_generate_pdf())
        btn_pdf_sale.grid(row=0, column=1, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_pdf_sale, "Guarda la venta y crea el comprobante en PDF automáticamente.")

        btn_proforma = tb.Button(actions_frame, text="Proforma", bootstyle="info-outline", command=lambda: self.save_proforma(False))
        btn_proforma.grid(row=0, column=2, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_proforma, "Genera una proforma sin afectar inventario ni numeración fiscal.")

        btn_proforma_pdf = tb.Button(actions_frame, text="Proforma + PDF", bootstyle="info", command=lambda: self.save_proforma(True))
        btn_proforma_pdf.grid(row=0, column=3, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_proforma_pdf, "Genera proforma y PDF con QR para verificación.")

        btn_boletin = tb.Button(actions_frame, text="Boletín", bootstyle="secondary-outline", command=lambda: self.save_boletin(False))
        btn_boletin.grid(row=0, column=4, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_boletin, "Boletín interno sin afectar inventario.")

        btn_boletin_pdf = tb.Button(actions_frame, text="Boletín + PDF", bootstyle="secondary", command=lambda: self.save_boletin(True))
        btn_boletin_pdf.grid(row=0, column=5, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_boletin_pdf, "Boletín interno con PDF y QR.")

        btn_adelanto = tb.Button(actions_frame, text="Adelanto", bootstyle="warning-outline", command=lambda: self.save_boletin(False, force_adelanto=True))
        btn_adelanto.grid(row=0, column=6, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_adelanto, "Recibo de adelanto (boletín) con monto parcial.")

        btn_adelanto_pdf = tb.Button(actions_frame, text="Adelanto + PDF", bootstyle="warning", command=lambda: self.save_boletin(True, force_adelanto=True))
        btn_adelanto_pdf.grid(row=0, column=7, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_adelanto_pdf, "Recibo de adelanto con PDF.")

        btn_yape_sale = tb.Button(actions_frame, text="Cobro Yape con Visor", bootstyle="warning-outline", command=lambda: self.collect_with_yape())
        btn_yape_sale.grid(row=0, column=8, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_yape_sale, "Muestra el QR de cobro y genera el comprobante automáticamente una vez confirmado el pago.")

        btn_open_last_pdf = tb.Button(actions_frame, text="Abrir último PDF", bootstyle="secondary-outline", command=self.app.open_last_pdf)
        btn_open_last_pdf.grid(row=0, column=9, padx=6, pady=2, sticky="we")
        self.app.add_help_tooltip(btn_open_last_pdf, "Abre el último comprobante generado sin buscarlo en carpetas.")

        # Guardar referencias para toggles por modo
        self.btn_group_sale = [btn_save_sale, btn_pdf_sale, btn_yape_sale]
        self.btn_group_proforma = [btn_proforma, btn_proforma_pdf]
        self.btn_group_boletin = [btn_boletin, btn_boletin_pdf]
        self.btn_group_adelanto = [btn_adelanto, btn_adelanto_pdf]
        self.actions_frame = actions_frame

        # --- CONFIGURAR MAYÚSCULAS AUTOMÁTICAS ---
        self.app.setup_uppercase_entry(
            self.app.entry_client_search,
        )
        
        # Cargar productos disponibles para ventas
        self.app.product_ui.load_products_for_sales()

    def set_mode(self, mode: str = "sale"):
        """Ajusta UI para modo venta o boletín."""
        self.mode = mode
        # Mostrar/ocultar grupos de botones
        if mode == "boletin":
            for btn in self.btn_group_sale:
                btn.grid_remove()
            for btn in self.btn_group_proforma:
                btn.grid_remove()
            for btn in self.btn_group_boletin:
                btn.grid()
            for btn in self.btn_group_adelanto:
                btn.grid()
            try:
                self.boletin_flow_frame.pack(side=tk.LEFT, padx=(0, 10))
            except Exception:
                pass
            try:
                self.app.client_lf.configure(text="👤 Cliente (opcional)")
                self.app.prod_lf.configure(text="📦 Ítems (elige Ingreso/Egreso)")
            except Exception:
                pass
            try:
                self.adelanto_toggle.grid()
            except Exception:
                pass
        else:
            for btn in self.btn_group_sale:
                btn.grid()
            for btn in self.btn_group_proforma:
                btn.grid()
            for btn in self.btn_group_boletin:
                btn.grid_remove()
            for btn in self.btn_group_adelanto:
                btn.grid_remove()
            try:
                self.boletin_flow_frame.pack_forget()
                self.app.flow_type_var.set("ingreso")
            except Exception:
                pass
            try:
                self.app.client_lf.configure(text="👤 Cliente")
                self.app.prod_lf.configure(text="📦 Catálogo de Productos")
            except Exception:
                pass
            try:
                self.app.is_adelanto_var.set(False)
                self._toggle_adelanto_fields(force_hide=True)
            except Exception:
                pass

    def _toggle_adelanto_fields(self, force_hide: bool = False):
        """Muestra/oculta los campos de adelanto."""
        try:
            if force_hide or not self.app.is_adelanto_var.get():
                self.adelanto_frame.grid_remove()
            else:
                self.adelanto_frame.grid()
            self.update_totals()
        except Exception:
            pass

    def _apply_company_igv_policy(self):
        """Oculta/desactiva controles de IGV cuando el perfil no cobra IGV."""
        company_igv_enabled = bool((self.app.current_company_data or {}).get("include_igv", True))
        if company_igv_enabled:
            # Asegurar visibles y habilitados
            try:
                self.cb_igv.state(["!disabled"])
                self.cb_igv.grid()
                self.igv_label.grid()
                self.igv_value.grid()
            except Exception:
                pass
            # Respetar preferencia inicial
            return

        # Si la empresa no usa IGV, apagar cálculo y ocultar controles
        try:
            self.app.include_igv_var.set(False)
            self.cb_igv.state(["disabled"])
            self.cb_igv.grid_remove()
            self.igv_label.grid_remove()
            self.igv_value.grid_remove()
        except Exception:
            pass
        # Recalcular totales sin IGV
        try:
            self.update_totals()
        except Exception:
            pass

    def add_item_to_sale(self):
        """Agrega el producto seleccionado a la venta con la cantidad ingresada."""
        try:
            # Verificar que haya un producto seleccionado
            if not self.app.selected_product:
                self.app.show_warning("Atención", "Primero seleccione un producto del catálogo.")
                return
            
            # Obtener la cantidad
            try:
                quantity = float(self.app.entry_quantity.get().strip())
                if quantity <= 0:
                    self.app.show_warning("Atención", "La cantidad debe ser mayor a 0.")
                    return
            except ValueError:
                self.app.show_warning("Atención", "Ingrese una cantidad válida.")
                return
            
            # --- Validar Stock ---
            valid_stock, msg_stock = SalesUIHelpers.validate_stock_before_add(
                self.app, self.app.selected_product["id"], quantity
            )
            if not valid_stock:
                return 
            
            # --- Obtener precio editable ---
            try:
                if hasattr(self.app, 'entry_custom_price'):
                    unit_price = float(self.app.entry_custom_price.get().strip())
                    if unit_price < 0:
                        self.app.show_warning("Atención", "El precio no puede ser negativo.")
                        return
                else:
                    unit_price = self.app.selected_product["price"]
            except ValueError:
                self.app.show_warning("Atención", "El precio ingresado no es válido.")
                return

            # Definir signo según ingreso/egreso (solo boletín)
            flow_type = getattr(self.app, "flow_type_var", None)
            is_expense = self.mode == "boletin" and flow_type and flow_type.get() == "egreso"
            sign = -1 if is_expense else 1
            unit_price_signed = round(unit_price * sign, 2)
            
            # Calcular subtotal
            subtotal = round(quantity * unit_price_signed, 2)
            
            # Agregar a la lista de items de venta
            if not hasattr(self.app, 'sale_items'):
                self.app.sale_items = []
            
            item_dict = {
                "product_id": self.app.selected_product["id"],
                "description": self.app.selected_product["name"],
                "unit": self.app.selected_product["unit"],
                "quantity": quantity,
                "unit_price": unit_price_signed,
                "subtotal": subtotal,
                "flow_type": "egreso" if is_expense else "ingreso",
            }
            
            self.app.sale_items.append(item_dict)
            
            # Agregar al Treeview de detalle
            item_number = len(self.app.sale_items)
            tags = ("expense",) if is_expense else ()
            self.app.tree_detail.insert(
                "",
                "end",
                values=(
                    item_number,
                    self.app.selected_product["name"],
                    self.app.selected_product["unit"],
                    f"{quantity:.2f}",
                    f"{unit_price_signed:.2f}",
                    f"{subtotal:.2f}"
                ),
                tags=tags,
            )
            
            # Actualizar totales
            self.update_totals()
            
            # Limpiar selección y cantidad
            self.app.selected_product = None
            self.app.entry_quantity.delete(0, tk.END)
            self.app.entry_quantity.insert(0, "1")
            self.app.entry_product_catalog_search.delete(0, tk.END)
            self.app.entry_product_catalog_search.focus()
            
            # Limpiar precio custom si existe
            if hasattr(self.app, 'entry_custom_price'):
                self.app.entry_custom_price.delete(0, tk.END)
            
            # Recargar productos para limpiar selección visual
            self.app.product_ui.filter_sales_products()
            
        except Exception as e:
            self.app.show_error("Error", f"Error al agregar producto: {e}")

    def append_item(self, product_id, name, unit, price):
        """Agrega un producto a la venta (usado por helpers externos)."""
        try:
            qty = float(self.app.entry_quantity.get().strip() or "1")
            if qty <= 0:
                self.app.show_error("Error", "La cantidad debe ser mayor a 0.")
                return
        except ValueError:
            self.app.show_error("Error", "La cantidad debe ser un número válido.")
            return
        
        # Calcular subtotal (sin descuento por ítem)
        subtotal = round(qty * price, 2)
        
        # Inicializar sale_items si no existe
        if not hasattr(self.app, 'sale_items'):
            self.app.sale_items = []
        
        item_number = len(self.app.sale_items) + 1
        self.app.sale_items.append({
            "product_id": product_id,
            "description": name,
            "unit": unit,
            "quantity": qty,
            "unit_price": price,
            "subtotal": subtotal
        })
        
        # Mostrar en Treeview
        self.app.tree_detail.insert("", "end", values=(
            item_number,
            name,
            unit,
            f"{qty:.2f}",
            f"{price:.2f}",
            f"{subtotal:.2f}"
        ))
        
        self.update_totals()
        
        # Limpiar campos
        self.app.entry_quantity.delete(0, tk.END)
        self.app.entry_quantity.insert(0, "1")
        # Ya no limpiamos entry_product_search porque no existe
        self.app.selected_product = None

    def delete_selected_item(self):
        sel = self.app.tree_detail.focus()
        if not sel:
            self.app.show_warning("Atención", "Seleccione un ítem para eliminar.")
            return
        index = self.app.tree_detail.index(sel)
        self.app.tree_detail.delete(sel)
        if 0 <= index < len(self.app.sale_items):
            self.app.sale_items.pop(index)
        for i, item_id in enumerate(self.app.tree_detail.get_children()):
            values = list(self.app.tree_detail.item(item_id, "values"))
            values[0] = str(i + 1)
            self.app.tree_detail.item(item_id, values=values)
        self.update_totals()
        try:
            self.app.product_ui.filter_sales_products()
        except Exception:
            pass

    def update_totals(self):
        """Calcula y actualiza las variables de subtotal, IGV y total en la UI."""
        if not hasattr(self.app, 'sale_items'):
            self.app.sale_items = []
            
        # Sumar subtotales de items
        subtotal_items = sum(item["subtotal"] for item in self.app.sale_items)
        
        # Calcular Descuento Global usando el Helper
        try:
            # Si existe el helper de descuento (si ya se inicializó la UI nueva)
            if hasattr(self.app, 'discount_type'):
                discount_val = SalesUIHelpers.calculate_discount_amount(self.app)
            else:
                # Fallback para la UI antigua o inicialización
                discount_val = float(self.app.entry_global_discount.get().strip() or 0.0)
        except ValueError:
            discount_val = 0.0
            
        # Base de cálculo (Suma de items - Descuento)
        current_mode = getattr(self, "mode", "sale")

        adelanto_active = bool(getattr(self.app, "is_adelanto_var", tk.BooleanVar(value=False)).get())
        adelanto_amount = 0.0
        if adelanto_active:
            try:
                adelanto_amount = float((self.app.var_adelanto_amount.get() or "0").replace(",", ""))
            except Exception:
                adelanto_amount = 0.0

        estimated_total_val = 0.0
        try:
            estimated_total_val = float((self.app.var_estimated_total.get() or "0").replace(",", ""))
        except Exception:
            estimated_total_val = 0.0

        if current_mode == "boletin" and adelanto_active and adelanto_amount > 0:
            total_calculado = adelanto_amount
            total = round(total_calculado, 2)
        elif current_mode == "boletin":
            total_calculado = subtotal_items - discount_val
            total = round(total_calculado, 2)
        else:
            total_calculado = max(0, subtotal_items - discount_val)
            total = max(0.0, round(total_calculado, 2))

        if self.app.include_igv_var.get():
            base_imponible = round(total / 1.18, 2)
            igv = round(total - base_imponible, 2)
        else:
            base_imponible = total
            igv = 0.00

        self.app.var_subtotal.set(f"{base_imponible:.2f}")
        self.app.var_igv.set(f"{igv:.2f}")
        self.app.var_total.set(f"{total:.2f}")

        # Si es adelanto y el total estimado está vacío/0, sugerirlo usando los items menos descuento
        if current_mode == "boletin" and adelanto_active:
            target_estimado = max(0.0, subtotal_items - discount_val)
            if estimated_total_val <= 0 and target_estimado > 0:
                try:
                    self.app.var_estimated_total.set(f"{target_estimado:.2f}")
                except Exception:
                    pass

    def edit_selected_item(self):
        sel = self.app.tree_detail.focus()
        if not sel:
            self.app.show_warning("Atención", "Seleccione un ítem para editar.")
            return
        index = self.app.tree_detail.index(sel)
        if not (0 <= index < len(self.app.sale_items)):
            self.app.show_error("Error", "Ítem seleccionado inválido.")
            return
        item = self.app.sale_items[index]

        win = tb.Toplevel(master=self.app)
        self.app.begin_modal_construction(win)
        win.title("Editar ítem")
        win.geometry("360x230")
        try:
            win.minsize(340, 210)
        except Exception:
            pass
        self.app.set_app_icon(win)

        lf = tb.Labelframe(win, text="Editar ítem", padding=8)
        lf.pack(fill="both", expand=True, padx=8, pady=8)
        lf.columnconfigure(1, weight=1)

        try:
            SalesUIHelpers.bind_mousewheel_to_children(lf)
        except Exception:
            pass

        # Habilitar rueda del mouse en controles internos
        try:
            SalesUIHelpers.bind_mousewheel_to_children(lf)
        except Exception:
            pass

        tb.Label(lf, text="Cantidad:").grid(row=0, column=0, sticky="e", padx=4, pady=6)
        entry_qty = tb.Entry(lf)
        entry_qty.grid(row=0, column=1, sticky="we", padx=4, pady=6)
        entry_qty.insert(0, f"{item.get('quantity', 0):.2f}")

        tb.Label(lf, text="Precio unitario:").grid(row=1, column=0, sticky="e", padx=4, pady=6)
        entry_price = tb.Entry(lf)
        entry_price.grid(row=1, column=1, sticky="we", padx=4, pady=6)
        entry_price.insert(0, f"{abs(item.get('unit_price', 0)):.2f}")

        flow_var = tk.StringVar(value=item.get("flow_type", "ingreso"))
        if self.mode == "boletin":
            tb.Label(lf, text="Tipo:").grid(row=2, column=0, sticky="e", padx=4, pady=6)
            flow_frame = tb.Frame(lf)
            flow_frame.grid(row=2, column=1, sticky="w", padx=4, pady=6)
            tb.Radiobutton(flow_frame, text="Ingreso", value="ingreso", variable=flow_var, bootstyle="success-toolbutton").pack(side=tk.LEFT)
            tb.Radiobutton(flow_frame, text="Egreso", value="egreso", variable=flow_var, bootstyle="danger-toolbutton").pack(side=tk.LEFT, padx=(6, 0))
            save_row = 3
        else:
            save_row = 2

        def save_edit():
            try:
                q = float(entry_qty.get())
                p = float(entry_price.get())
                if q <= 0 or p < 0:
                    raise ValueError("Valores inválidos para cantidad/precio.")
            except Exception as e:
                self.app.show_error("Error", str(e))
                return

            product_id = item.get("product_id")
            if product_id:
                other_reserved = 0.0
                for existing in self.app.sale_items:
                    if existing is item:
                        continue
                    if existing.get("product_id") == product_id:
                        other_reserved += existing.get("quantity", 0)
                available, message = self.app.product_service.check_stock_availability(
                    product_id,
                    q,
                    already_reserved=other_reserved
                )
                if not available:
                    self.app.show_warning("Stock Insuficiente", message)
                    return

            sign = -1 if (self.mode == "boletin" and flow_var.get() == "egreso") else 1
            item['quantity'] = round(q, 2)
            item['unit_price'] = round(p * sign, 2)
            item['subtotal'] = round(item['quantity'] * item['unit_price'], 2)
            item['flow_type'] = flow_var.get()

            # Update treeview row
            values = list(self.app.tree_detail.item(sel, 'values'))
            # columns: item, description, unit, quantity, unit_price, subtotal
            values[3] = f"{item['quantity']:.2f}"
            values[4] = f"{item['unit_price']:.2f}"
            values[5] = f"{item['subtotal']:.2f}"
            tags = ("expense",) if item['subtotal'] < 0 else ()
            self.app.tree_detail.item(sel, values=values, tags=tags)

            self.update_totals()
            try:
                self.app.product_ui.filter_sales_products()
            except Exception:
                pass
            win.destroy()
            
        tb.Button(lf, text="Guardar", bootstyle="success", command=save_edit).grid(row=save_row, column=0, columnspan=2, pady=10)

        win.update_idletasks()
        self.app.center_window(win, 320, 160)
        self.app.reveal_modal(win)
        self.app.make_modal(win)

    def save_sale(self):
        if not self.app.current_client:
            self.app.show_warning("Atención", "Debe seleccionar un cliente antes de guardar el comprobante.")
            return None, None, None
        
        if not self.app.sale_items:
            self.app.show_warning("Atención", "Debe agregar al menos un producto al comprobante.")
            return None, None, None
        try:
            include_igv = self.app.include_igv_var.get()
            
            # Obtener descuento global
            try:
                if hasattr(self.app, 'discount_type'):
                    discount = SalesUIHelpers.calculate_discount_amount(self.app)
                else:
                    discount = float(self.app.entry_global_discount.get().strip() or "0")
            except ValueError:
                discount = 0.0

            # Guardar Venta
            sale_id, series, number, subtotal, igv, total, serial_seguridad = self.app.sale_service.create_sale(
                self.app.series,
                self.app.current_client["id"],
                self.app.sale_items,
                discount=discount,
                include_igv=include_igv,
                product_service=self.app.product_service
            )
            
            self.app.show_info("Éxito", f"Comprobante {series}-{number:06d} guardado correctamente.")
            
            # Limpiar items y cliente después de guardar
            self.app.sale_items = []
            self.app.tree_detail.delete(*self.app.tree_detail.get_children())
            self.app.current_client = None
            self.app.label_current_client.config(text="")
            try:
                self.app.var_client_name_small.set("(ninguno)")
                self.app.var_client_dni.set("")
                self.app.var_client_phone.set("")
            except Exception:
                pass
            self.update_totals()
            
            # Reset discount
            if hasattr(self.app, 'discount_type'):
                self.app.discount_type.set("S/")
                self.app.entry_global_discount.delete(0, tk.END)
                self.app.entry_global_discount.insert(0, "0.00")
                SalesUIHelpers.setup_placeholder(self.app.entry_global_discount, "0.00")
            else:
                self.app.entry_global_discount.delete(0, tk.END)
                self.app.entry_global_discount.insert(0, "0.00")

            # Refrescar catálogos de productos para reflejar nuevo stock
            try:
                self.app.product_ui.load_products_for_sales()
            except Exception:
                pass
            try:
                self.app.all_products_cache = self.app.product_service.search_products("")
                self.app.product_ui.filter_products()
            except Exception:
                pass
            
            return sale_id, series, number

        except ValueError as e:
            self.app.show_error("Error de Validación", str(e))
            return None, None, None
        except Exception as e:
            self.app.show_error("Error Crítico", f"No se pudo guardar la venta.\n{e}")
            return None, None, None

    def save_proforma(self, generate_pdf: bool = False):
        if not self.app.current_client:
            self.app.show_warning("Atención", "Seleccione un cliente antes de generar la proforma.")
            return None, None, None

        if not self.app.sale_items:
            self.app.show_warning("Atención", "Agregue al menos un producto a la proforma.")
            return None, None, None

        try:
            include_igv = self.app.include_igv_var.get()
            try:
                if hasattr(self.app, 'discount_type'):
                    discount = SalesUIHelpers.calculate_discount_amount(self.app)
                else:
                    discount = float(self.app.entry_global_discount.get().strip() or "0")
            except ValueError:
                discount = 0.0

            sale_id, series, number, subtotal, igv, total, serial_seguridad = self.app.sale_service.create_sale(
                getattr(self.app, "proforma_series", "PF001"),
                self.app.current_client["id"],
                self.app.sale_items,
                discount=discount,
                include_igv=include_igv,
                product_service=None,
                is_proforma=True,
                is_boletin=False,
                is_adelanto=False,
            )

            self.app.show_info("Proforma generada", f"Proforma {series}-{number:06d} guardada.")

            if generate_pdf:
                def _gen_proforma_pdf():
                    try:
                        pdf_path = self.app.pdf_service.generate_sale_pdf(
                            sale_id,
                            output_dir="temp",
                            company_profile=self.app.current_company_data,
                        )
                    except Exception as exc:  # No UI calls fuera del hilo principal
                        self.app.after(0, lambda: self.app.show_error("PDF", f"No se pudo generar la proforma en PDF:\n{exc}"))
                        return
                    self.app.after(0, lambda: self._on_pdf_ready(pdf_path))

                threading.Thread(target=_gen_proforma_pdf, daemon=True).start()

            self.reset_sale_form()
            return sale_id, series, number
        except Exception as exc:
            self.app.show_error("Error", f"No se pudo generar la proforma:\n{exc}")
            return None, None, None

    def save_boletin(self, generate_pdf: bool = False, force_adelanto: bool = False):
        if not self.app.sale_items:
            self.app.show_warning("Atención", "Agregue al menos un producto al boletín.")
            return None, None, None

        try:
            include_igv = self.app.include_igv_var.get()
            try:
                if hasattr(self.app, 'discount_type'):
                    discount = SalesUIHelpers.calculate_discount_amount(self.app)
                else:
                    discount = float(self.app.entry_global_discount.get().strip() or "0")
            except ValueError:
                discount = 0.0

            client_id = None
            if self.app.current_client:
                client_id = self.app.current_client.get("id")
            # Si no hay cliente, usamos None para registro interno

            adelanto_active = force_adelanto or bool(getattr(self.app, "is_adelanto_var", tk.BooleanVar(value=False)).get())
            adelanto_amount = 0.0
            estimated_total = 0.0
            if adelanto_active:
                try:
                    adelanto_amount = float((self.app.var_adelanto_amount.get() or "0").replace(",", ""))
                except Exception:
                    adelanto_amount = 0.0
                try:
                    estimated_total = float((self.app.var_estimated_total.get() or "0").replace(",", ""))
                except Exception:
                    estimated_total = 0.0
                if adelanto_amount <= 0:
                    self.app.show_warning("Atención", "Ingrese el monto del adelanto.")
                    return None, None, None
                # Si no ingresan total estimado, usar el total de ítems menos descuento
                subtotal_items = sum(item.get("subtotal", 0.0) for item in self.app.sale_items)
                if estimated_total <= 0:
                    estimated_total = max(0.0, subtotal_items - discount)
                    try:
                        self.app.var_estimated_total.set(f"{estimated_total:.2f}")
                    except Exception:
                        pass

            sale_id, series, number, subtotal, igv, total, serial_seguridad = self.app.sale_service.create_sale(
                getattr(self.app, "boletin_series", "BL001"),
                client_id,
                self.app.sale_items,
                discount=discount,
                include_igv=include_igv,
                product_service=None,
                is_proforma=False,
                is_boletin=True,
                is_adelanto=adelanto_active,
                advance_amount=adelanto_amount,
                estimated_total=estimated_total,
            )

            self.app.show_info("Boletín generado", f"Boletín {series}-{number:06d} guardado.")

            if generate_pdf:
                client_email = ""
                client_phone = ""
                client_name = ""
                if self.app.current_client and isinstance(self.app.current_client, dict):
                    client_email = self.app.current_client.get("email", "")
                    client_phone = self.app.current_client.get("phone", "")
                    client_name = self.app.current_client.get("name", "")

                def _gen_boletin_pdf():
                    try:
                        pdf_path = self.app.pdf_service.generate_sale_pdf(
                            sale_id,
                            output_dir="temp",
                            company_profile=self.app.current_company_data,
                        )
                    except Exception as exc:
                        self.app.after(0, lambda: self.app.show_error("PDF", f"No se pudo generar el boletín en PDF:\n{exc}"))
                        return

                    def _after_success():
                        self._on_pdf_ready(pdf_path)
                        self.app.show_post_sale_options(sale_id, pdf_path, client_email, client_phone, client_name)

                    self.app.after(0, _after_success)

                threading.Thread(target=_gen_boletin_pdf, daemon=True).start()

            self.reset_sale_form()
            return sale_id, series, number
        except Exception as exc:
            self.app.show_error("Error", f"No se pudo generar el boletín:\n{exc}")
            return None, None, None

    def save_sale_and_generate_pdf(self):
        self.complete_sale(generate_pdf=True, use_customer_display=False)

    def collect_with_yape(self):
        self.complete_sale(generate_pdf=True, use_customer_display=True)

    def complete_sale(self, *, generate_pdf: bool = True, use_customer_display: bool = False):
        client_email = ""
        client_phone = ""
        client_name = ""
        if self.app.current_client and isinstance(self.app.current_client, dict):
            client_email = self.app.current_client.get("email", "")
            client_phone = self.app.current_client.get("phone", "")
            client_name = self.app.current_client.get("name", "")

        display_active = False
        try:
            if self.mode == "boletin":
                result = self.save_boletin(generate_pdf)
                if not result or result[0] is None:
                    return
            else:
                if use_customer_display:
                    if not hasattr(self.app, "customer_display"):
                        self.app.show_error("Visor", "El visor del cliente no está disponible en esta sesión.")
                        return

                    total_value = 0.0
                    try:
                        total_value = float((self.app.var_total.get() or "0").replace(",", ""))
                    except (TypeError, ValueError):
                        total_value = 0.0

                    if total_value <= 0:
                        self.app.show_warning("Atención", "El total debe ser mayor a 0 para mostrar el visor del cliente.")
                        return

                    qr_path = ((self.app.current_company_data or {}).get("yape_qr_path") or "").strip()
                    if not qr_path or not os.path.exists(qr_path):
                        self.app.show_warning(
                            "Configurar QR",
                            "Configura el QR de Yape en Perfil → Configuración de Cobro antes de usar el visor."
                        )
                        return

                    cart_items = []
                    for item in getattr(self.app, "sale_items", []):
                        cart_items.append({
                            "name": item.get("description") or item.get("name"),
                            "qty": item.get("quantity", 0),
                            "price": item.get("unit_price", 0),
                            "subtotal": item.get("subtotal", 0),
                        })

                    if not cart_items:
                        self.app.show_warning(
                            "Atención",
                            "Agrega productos al carrito antes de abrir el visor del cliente.",
                        )
                        return

                    phone_number = ((self.app.current_company_data or {}).get("phone", "") or "").strip()
                    display_active = self.app.customer_display.show_payment(
                        cart_items,
                        total_value,
                        qr_path,
                        phone_number,
                    )
                    if not display_active:
                        return

                    confirmed = self.app.show_question("Confirmar Pago", "¿Confirmar Pago?")
                    if not confirmed:
                        self.app.customer_display.close()
                        self.app.show_info("Cobro Cancelado", "Se canceló el cobro por Yape.")
                        return

                result = self.save_sale()
                if not result or result[0] is None:
                    return

                sale_id, series, number = result

                if generate_pdf:
                    try:
                        pdf_path = self.app.pdf_service.generate_sale_pdf(
                            sale_id,
                            output_dir="temp",
                            company_profile=self.app.current_company_data
                        )
                        self.app.last_pdf_path = pdf_path

                        self.app.after(
                            0,
                            lambda sid=sale_id, path=pdf_path, email=client_email, phone=client_phone, name=client_name: self.app.show_post_sale_options(sid, path, email, phone, name)
                        )
                    except Exception as e:
                        self.app.show_error("Error al generar PDF", str(e))
        finally:
            if use_customer_display and display_active:
                self.app.customer_display.close()

    # ------------------------
    # Helpers
    # ------------------------
    def _on_pdf_ready(self, pdf_path: str) -> None:
        self.app.last_pdf_path = pdf_path
        try:
            self.app.open_pdf(pdf_path)
        except Exception as exc:
            self.app.show_warning("PDF", f"PDF generado en:\n{pdf_path}\n\n(No se pudo abrir automáticamente: {exc})")

    def reset_sale_form(self):
        """Limpia el formulario de venta."""
        self.app.sale_items = []
        self.app.tree_detail.delete(*self.app.tree_detail.get_children())
        self.app.current_client = None
        self.app.label_current_client.config(text="")
        try:
            self.app.var_client_name_small.set("(ninguno)")
            self.app.var_client_dni.set("")
            self.app.var_client_phone.set("")
        except Exception:
            pass
        self.update_totals()
        
        # Reset discount
        if hasattr(self.app, 'discount_type'):
            self.app.discount_type.set("S/")
            self.app.entry_global_discount.delete(0, tk.END)
            self.app.entry_global_discount.insert(0, "0.00")
            SalesUIHelpers.setup_placeholder(self.app.entry_global_discount, "0.00")
        else:
            self.app.entry_global_discount.delete(0, tk.END)
            self.app.entry_global_discount.insert(0, "0.00")

        try:
            self.app.is_adelanto_var.set(False)
            self.app.var_adelanto_amount.set("0.00")
            self.app.var_estimated_total.set("0.00")
            self._toggle_adelanto_fields(force_hide=True)
        except Exception:
            pass

        try:
            self.app.flow_type_var.set("ingreso")
        except Exception:
            pass

        try:
            self.app.product_ui.load_products_for_sales()
        except Exception:
            pass
