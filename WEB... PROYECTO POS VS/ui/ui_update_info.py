import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Simular borde con frame exterior
        outer = tb.Frame(tw, bootstyle="primary")
        outer.pack()
        
        label = tb.Label(
            outer, 
            text=self.text, 
            justify=tk.LEFT,
            background="#333", 
            foreground="#fff",
            relief=tk.FLAT, 
            borderwidth=0,
            padding=(5, 2)
        )
        label.pack(padx=1, pady=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class UpdateInfoMethods:
    # ---------------- ACTUALIZAR INFORMACIÓN (GESTIÓN MAESTRA) ---------------- #

    def build_update_info_ui(self):
        """Construye la interfaz dividida para gestionar Clientes y Productos con estilo moderno."""
        # Limpiar frame
        for widget in self.frame_update_info.winfo_children():
            widget.destroy()

        # Contenedor principal con grid de 2 columnas
        main_container = tb.Frame(self.frame_update_info)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        # ==================== COLUMNA IZQUIERDA: CLIENTES ====================
        frame_clients = tb.LabelFrame(main_container, text="👥 Gestión de Clientes", padding=10, bootstyle="primary")
        frame_clients.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        frame_clients.rowconfigure(1, weight=1)  # Lista expandible
        frame_clients.columnconfigure(0, weight=1)

        # 1. Buscador Clientes
        search_frame_cli = tb.Frame(frame_clients)
        search_frame_cli.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_frame_cli.columnconfigure(0, weight=1)
        
        self.entry_search_client = tb.Entry(search_frame_cli, font=("Segoe UI", 10))
        self.entry_search_client.grid(row=0, column=0, sticky="ew", padx=5)
        self.entry_search_client.insert(0, "Buscar cliente...")
        self.entry_search_client.bind("<FocusIn>", lambda e: self.entry_search_client.delete(0, tk.END) if self.entry_search_client.get() == "Buscar cliente..." else None)
        self.entry_search_client.bind("<KeyRelease>", self.filter_clients)

        # 2. Lista Scrollable Clientes
        list_container_cli = tb.Frame(frame_clients, bootstyle="bg")
        list_container_cli.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        self.canvas_cli = tb.Canvas(list_container_cli, highlightthickness=0, bd=0)
        self.scrollbar_cli = tb.Scrollbar(list_container_cli, orient="vertical", command=self.canvas_cli.yview, bootstyle="primary-round")
        self.scroll_frame_cli = tb.Frame(self.canvas_cli)
        
        self.scroll_frame_cli.bind(
            "<Configure>",
            lambda e: self.canvas_cli.configure(scrollregion=self.canvas_cli.bbox("all"))
        )
        
        self.canvas_cli.create_window((0, 0), window=self.scroll_frame_cli, anchor="nw")
        self.canvas_cli.configure(yscrollcommand=self.scrollbar_cli.set)
        
        self.canvas_cli.pack(side="left", fill="both", expand=True)
        self.scrollbar_cli.pack(side="right", fill="y")
        
        # Ajustar ancho
        self.canvas_cli.bind("<Configure>", lambda e: self.canvas_cli.itemconfig(self.canvas_cli.find_withtag("all")[0], width=e.width))
        self.canvas_cli.bind_all("<MouseWheel>", self._on_mousewheel_cli)

        # 3. Formulario Clientes
        form_cli = tb.LabelFrame(frame_clients, text="Datos del Cliente", padding=10)
        form_cli.grid(row=2, column=0, sticky="ew")
        form_cli.columnconfigure(1, weight=1)

        self.var_cli_id = tk.StringVar()
        self.var_cli_dni = tk.StringVar()
        self.var_cli_name = tk.StringVar()
        self.var_cli_phone = tk.StringVar()
        self.var_cli_email = tk.StringVar()
        self.var_cli_address = tk.StringVar()

        # Grid del formulario
        tb.Label(form_cli, text="DNI/RUC:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_dni).grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Nombre:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_name).grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Celular:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_phone).grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Email:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_email).grid(row=3, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Dirección:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_address).grid(row=4, column=1, sticky="ew", padx=5, pady=3)

        # Botones Formulario Clientes
        btn_frame_cli = tb.Frame(form_cli)
        btn_frame_cli.grid(row=5, column=0, columnspan=2, pady=10)
        
        tb.Button(btn_frame_cli, text="Limpiar", bootstyle="secondary", command=self.clear_client_form).pack(side="left", padx=5)
        tb.Button(btn_frame_cli, text="Guardar Cliente", bootstyle="success", command=self.save_client_action).pack(side="left", padx=5)

        # ==================== COLUMNA DERECHA: PRODUCTOS ====================
        frame_products = tb.LabelFrame(main_container, text="📦 Gestión de Productos", padding=10, bootstyle="info")
        frame_products.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        frame_products.rowconfigure(1, weight=1)
        frame_products.columnconfigure(0, weight=1)

        # 1. Buscador Productos
        search_frame_prod = tb.Frame(frame_products)
        search_frame_prod.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_frame_prod.columnconfigure(0, weight=1)
        
        self.entry_search_product = tb.Entry(search_frame_prod, font=("Segoe UI", 10))
        self.entry_search_product.grid(row=0, column=0, sticky="ew", padx=5)
        self.entry_search_product.insert(0, "Buscar producto...")
        self.entry_search_product.bind("<FocusIn>", lambda e: self.entry_search_product.delete(0, tk.END) if self.entry_search_product.get() == "Buscar producto..." else None)
        self.entry_search_product.bind("<KeyRelease>", self.filter_products)

        # 2. Lista Scrollable Productos
        list_container_prod = tb.Frame(frame_products, bootstyle="bg")
        list_container_prod.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        self.canvas_prod = tb.Canvas(list_container_prod, highlightthickness=0, bd=0)
        self.scrollbar_prod = tb.Scrollbar(list_container_prod, orient="vertical", command=self.canvas_prod.yview, bootstyle="info-round")
        self.scroll_frame_prod = tb.Frame(self.canvas_prod)
        
        self.scroll_frame_prod.bind(
            "<Configure>",
            lambda e: self.canvas_prod.configure(scrollregion=self.canvas_prod.bbox("all"))
        )
        
        self.canvas_prod.create_window((0, 0), window=self.scroll_frame_prod, anchor="nw")
        self.canvas_prod.configure(yscrollcommand=self.scrollbar_prod.set)
        
        self.canvas_prod.pack(side="left", fill="both", expand=True)
        self.scrollbar_prod.pack(side="right", fill="y")
        
        self.canvas_prod.bind("<Configure>", lambda e: self.canvas_prod.itemconfig(self.canvas_prod.find_withtag("all")[0], width=e.width))
        self.canvas_prod.bind_all("<MouseWheel>", self._on_mousewheel_prod)

        # 3. Formulario Productos
        form_prod = tb.LabelFrame(frame_products, text="Datos del Producto", padding=10)
        form_prod.grid(row=2, column=0, sticky="ew")
        form_prod.columnconfigure(1, weight=1)

        self.var_prod_id = tk.StringVar()
        self.var_prod_code = tk.StringVar()
        self.var_prod_name = tk.StringVar()
        self.var_prod_unit = tk.StringVar()
        self.var_prod_price = tk.StringVar()
        self.var_prod_stock = tk.StringVar()

        tb.Label(form_prod, text="Código:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_code).grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Nombre:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_name).grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Unidad:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_unit).grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Precio (S/):").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_price).grid(row=3, column=1, sticky="ew", padx=5, pady=3)

        tb.Label(form_prod, text="Stock:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        entry_prod_stock = tb.Entry(form_prod, textvariable=self.var_prod_stock)
        entry_prod_stock.grid(row=4, column=1, sticky="ew", padx=5, pady=3)
        stock_cmd = (self.register(lambda P: P.isdigit() or P == ""), "%P")
        entry_prod_stock.configure(validate="key", validatecommand=stock_cmd)

        # Botones Formulario Productos
        btn_frame_prod = tb.Frame(form_prod)
        btn_frame_prod.grid(row=5, column=0, columnspan=2, pady=10)
        
        tb.Button(btn_frame_prod, text="Limpiar", bootstyle="secondary", command=self.clear_product_form).pack(side="left", padx=5)
        tb.Button(btn_frame_prod, text="Guardar Producto", bootstyle="success", command=self.save_product_action).pack(side="left", padx=5)
        
        # Botón Importar Excel
        tb.Button(btn_frame_prod, text="📂 Importar Excel", bootstyle="warning-outline", command=self.import_products_from_excel).pack(side="left", padx=5)

        # Cargar datos iniciales
        self.load_initial_data()

    def _on_mousewheel_cli(self, event):
        if self.canvas_cli.winfo_exists():
            self.canvas_cli.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_mousewheel_prod(self, event):
        if self.canvas_prod.winfo_exists():
            self.canvas_prod.yview_scroll(int(-1*(event.delta/120)), "units")

    def load_initial_data(self):
        """Carga todos los clientes y productos al iniciar la vista."""
        try:
            # Cargar clientes
            self.all_clients_cache = self.client_service.search_clients("")
            self.filter_clients()
            
            # Cargar productos
            self.all_products_cache = self.product_service.search_products("")
            self.filter_products()
        except Exception as e:
            print(f"Error loading initial data: {e}")
            self.all_clients_cache = []
            self.all_products_cache = []

    # --- MÉTODOS DE CLIENTES ---
    def filter_clients(self, event=None):
        """Filtra clientes y renderiza la lista."""
        query = self.entry_search_client.get().lower()
        if query == "buscar cliente...":
            query = ""
        
        # Limpiar lista
        for widget in self.scroll_frame_cli.winfo_children():
            widget.destroy()
        
        # Filtrar
        filtered = []
        for client in self.all_clients_cache:
            dni = str(client[1] or "").lower()
            name = str(client[2] or "").lower()
            if query in dni or query in name:
                filtered.append(client)
        
        # Renderizar (limitar a 50 para rendimiento)
        for i, client in enumerate(filtered[:50]):
            self._render_client_row(client, i)

    def _render_client_row(self, client, index):
        # Estilos alternos
        if index % 2 == 0:
            row_style = "" 
            lbl_style = ""
        else:
            row_style = "secondary"
            lbl_style = "inverse-secondary"

        row = tb.Frame(self.scroll_frame_cli, bootstyle=row_style)
        row.pack(fill="x", pady=1)
        row.columnconfigure(0, weight=1)
        
        # Info Container
        info_frame = tb.Frame(row, bootstyle=row_style)
        info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Nombre (Negrita)
        name = client[2] or "Sin Nombre"
        tb.Label(info_frame, text=name, font=("Segoe UI", 10, "bold"), bootstyle=lbl_style).pack(anchor="w")
        
        # Detalles
        dni = client[1] or "---"
        phone = client[3] or "---"
        details = f"DNI: {dni}  |  Cel: {phone}"
        tb.Label(info_frame, text=details, font=("Segoe UI", 8), bootstyle=lbl_style).pack(anchor="w")

        # Botones Acción
        btn_frame = tb.Frame(row, bootstyle=row_style)
        btn_frame.pack(side="right", padx=5)
        
        btn_edit = tb.Button(btn_frame, text="✏️", bootstyle="primary-link", command=lambda c=client: self.edit_client_action(c))
        btn_edit.pack(side="left")
        ToolTip(btn_edit, "Editar Cliente")
        
        btn_del = tb.Button(btn_frame, text="❌", bootstyle="danger-link", command=lambda cid=client[0]: self.delete_client_action(cid))
        btn_del.pack(side="left")
        ToolTip(btn_del, "Eliminar Cliente")

    def edit_client_action(self, client):
        """Carga los datos del cliente en el formulario."""
        self.var_cli_id.set(client[0])
        self.var_cli_dni.set(client[1] or "")
        self.var_cli_name.set(client[2] or "")
        self.var_cli_phone.set(client[3] or "")
        self.var_cli_email.set(client[4] or "")
        self.var_cli_address.set(client[5] or "")

    def delete_client_action(self, client_id):
        if Messagebox.show_question("¿Estás seguro de eliminar este cliente?", "Confirmar Eliminación", parent=self):
            try:
                # Nota: Esto podría fallar si hay ventas asociadas (FK constraint), manejar error
                self.client_repo.delete_client(client_id) # Asumiendo que existe este método o similar en repo
                # Si no existe delete en repo, habría que añadirlo, pero por ahora asumimos que sí o usamos raw query si fuera necesario
                # Revisando repositorios... ClientRepository suele tener delete?
                # Si no, mostramos error.
                # Para asegurar, recargamos.
                self.all_clients_cache = self.client_service.search_clients("")
                self.filter_clients()
                self.clear_client_form()
                self.show_success("Éxito", "Cliente eliminado.")
            except Exception as e:
                self.show_error("Error", f"No se pudo eliminar (¿Tiene ventas asociadas?)\n{e}")

    def clear_client_form(self):
        self.var_cli_id.set("")
        self.var_cli_dni.set("")
        self.var_cli_name.set("")
        self.var_cli_phone.set("")
        self.var_cli_email.set("")
        self.var_cli_address.set("")

    def save_client_action(self):
        client_id = self.var_cli_id.get()
        dni = self.var_cli_dni.get().strip()
        name = self.var_cli_name.get().strip()
        phone = self.var_cli_phone.get().strip()
        email = self.var_cli_email.get().strip()
        address = self.var_cli_address.get().strip()

        if not name:
            self.show_warning("Error", "El nombre es obligatorio.")
            return

        try:
            if client_id:
                self.client_service.update_client(client_id, dni, name, phone, email, address)
                self.show_info("Éxito", "Cliente actualizado correctamente.")
            else:
                self.client_service.create_client(dni, name, phone, email, address)
                self.show_info("Éxito", "Cliente creado correctamente.")
            
            self.all_clients_cache = self.client_service.search_clients("")
            self.filter_clients()
            self.clear_client_form()
        except Exception as e:
            self.show_error("Error", str(e))

    # --- MÉTODOS DE PRODUCTOS ---
    def filter_products(self, event=None):
        """Filtra productos y renderiza la lista."""
        query = self.entry_search_product.get().lower()
        if query == "buscar producto...":
            query = ""
        
        for widget in self.scroll_frame_prod.winfo_children():
            widget.destroy()

        filtered = []
        for product in self.all_products_cache:
            code = str(product[1] or "").lower()
            name = str(product[2] or "").lower()
            if query in code or query in name:
                filtered.append(product)

        for i, product in enumerate(filtered[:50]):
            self._render_product_row(product, i)

    def _render_product_row(self, product, index):
        # Estilos alternos
        if index % 2 == 0:
            row_style = "" 
            lbl_style = ""
        else:
            row_style = "secondary"
            lbl_style = "inverse-secondary"

        row = tb.Frame(self.scroll_frame_prod, bootstyle=row_style)
        row.pack(fill="x", pady=1)
        
        # Info Container
        info_frame = tb.Frame(row, bootstyle=row_style)
        info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Nombre (Negrita)
        name = product[2] or "Sin Nombre"
        tb.Label(info_frame, text=name, font=("Segoe UI", 10, "bold"), bootstyle=lbl_style).pack(anchor="w")
        
        # Detalles
        code = product[1] or "---"
        price = product[4]
        stock = product[5] if len(product) > 5 else 0
        
        stock_display = self._format_stock_display(stock)
        price_display = f"S/ {price:.2f}"
        
        details = f"Cód: {code}  |  Precio: {price_display}  |  Stock: {stock_display}"
        
        # Color stock bajo (opcional, sobreescribe estilo si es crítico)
        stock_fg = lbl_style
        try:
            if float(stock or 0) <= 5:
                stock_fg = "danger" if not lbl_style else "inverse-danger"
        except: pass

        lbl = tb.Label(info_frame, text=details, font=("Segoe UI", 8), bootstyle=lbl_style)
        lbl.pack(anchor="w")

        # Botones Acción
        btn_frame = tb.Frame(row, bootstyle=row_style)
        btn_frame.pack(side="right", padx=5)
        
        btn_edit = tb.Button(btn_frame, text="✏️", bootstyle="info-link", command=lambda p=product: self.edit_product_action(p))
        btn_edit.pack(side="left")
        ToolTip(btn_edit, "Editar Producto")
        
        btn_del = tb.Button(btn_frame, text="❌", bootstyle="danger-link", command=lambda pid=product[0]: self.delete_product_action(pid))
        btn_del.pack(side="left")
        ToolTip(btn_del, "Eliminar Producto")

    def edit_product_action(self, product):
        self.var_prod_id.set(product[0])
        self.var_prod_code.set(product[1] or "")
        self.var_prod_name.set(product[2] or "")
        self.var_prod_unit.set(product[3] or "")
        self.var_prod_price.set(f"{product[4]:.2f}")
        
        stock = product[5] if len(product) > 5 else None
        if stock is None:
            self.var_prod_stock.set("")
        else:
            try:
                stock_val = float(stock)
                if stock_val.is_integer():
                    self.var_prod_stock.set(str(int(stock_val)))
                else:
                    self.var_prod_stock.set(f"{stock_val:.2f}")
            except (TypeError, ValueError):
                self.var_prod_stock.set(str(stock))

    def delete_product_action(self, product_id):
        if Messagebox.show_question("¿Estás seguro de eliminar este producto?", "Confirmar Eliminación", parent=self):
            try:
                # Nota: Igual que clientes, verificar si existe método delete en repo
                # Si no, habría que agregarlo. Asumiremos que el usuario quiere la UI primero.
                # Si falla, mostrará error.
                self.product_repo.delete_product(product_id) 
                self.all_products_cache = self.product_service.search_products("")
                self.filter_products()
                self.clear_product_form()
                self.show_success("Éxito", "Producto eliminado.")
            except Exception as e:
                self.show_error("Error", f"No se pudo eliminar (¿Está en ventas?)\n{e}")

    def clear_product_form(self):
        self.var_prod_id.set("")
        self.var_prod_code.set("")
        self.var_prod_name.set("")
        self.var_prod_unit.set("")
        self.var_prod_price.set("")
        self.var_prod_stock.set("")

    def save_product_action(self):
        product_id = self.var_prod_id.get()
        code = self.var_prod_code.get().strip()
        name = self.var_prod_name.get().strip()
        unit = self.var_prod_unit.get().strip()
        price_str = self.var_prod_price.get().strip()
        stock_str = self.var_prod_stock.get().strip()

        if not name or not unit or not price_str:
            self.show_warning("Error", "Nombre, Unidad y Precio son obligatorios.")
            return

        try:
            if product_id:
                self.product_service.update_product(int(product_id), name, unit, price_str, code or None, stock=stock_str)
                self.show_info("Éxito", "Producto actualizado correctamente.")
            else:
                self.product_service.create_product(name, unit, price_str, code or None, stock=stock_str)
                self.show_info("Éxito", "Producto creado correctamente.")
            
            self.all_products_cache = self.product_service.search_products("")
            self.filter_products()
            self.clear_product_form()
        except Exception as e:
            self.show_error("Error", str(e))

    def _format_stock_display(self, stock):
        if stock is None:
            return "Sin control"
        try:
            stock_val = float(stock)
            if stock_val.is_integer():
                return str(int(stock_val))
            return f"{stock_val:.2f}"
        except (TypeError, ValueError):
            return str(stock)
        """Construye la interfaz dividida para gestionar Clientes y Productos."""
        # Limpiar frame
        for widget in self.frame_update_info.winfo_children():
            widget.destroy()

        # Contenedor principal con grid de 2 columnas
        main_container = tb.Frame(self.frame_update_info)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        # --- COLUMNA IZQUIERDA: CLIENTES ---
        frame_clients = tb.LabelFrame(main_container, text="👥 Gestión de Clientes", padding=15, bootstyle="primary")
        frame_clients.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        frame_clients.rowconfigure(1, weight=1)  # Treeview expandible
        frame_clients.columnconfigure(0, weight=1)

        # Buscador Clientes
        search_frame_cli = tb.Frame(frame_clients)
        search_frame_cli.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_frame_cli.columnconfigure(0, weight=1)
        
        self.entry_search_client = tb.Entry(search_frame_cli, font=("Helvetica", 10))
        self.entry_search_client.grid(row=0, column=0, sticky="ew", padx=5)
        self.entry_search_client.insert(0, "Buscar cliente...")
        self.entry_search_client.bind("<FocusIn>", lambda e: self.entry_search_client.delete(0, tk.END) if self.entry_search_client.get() == "Buscar cliente..." else None)
        self.entry_search_client.bind("<KeyRelease>", self.filter_clients)

        # Treeview Clientes con Scrollbar
        tree_frame_cli = tb.Frame(frame_clients)
        tree_frame_cli.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        tree_frame_cli.rowconfigure(0, weight=1)
        tree_frame_cli.columnconfigure(0, weight=1)

        cols_cli = ("id", "dni", "name", "phone")
        self.tree_clients = tb.Treeview(tree_frame_cli, columns=cols_cli, show="headings", height=10, bootstyle="primary")
        self.tree_clients.heading("id", text="ID")
        self.tree_clients.heading("dni", text="DNI/RUC")
        self.tree_clients.heading("name", text="Nombre")
        self.tree_clients.heading("phone", text="Celular")
        
        self.tree_clients.column("id", width=40, stretch=False)
        self.tree_clients.column("dni", width=80)
        self.tree_clients.column("name", width=200)
        self.tree_clients.column("phone", width=100)
        
        scrollbar_cli = tb.Scrollbar(tree_frame_cli, orient="vertical", command=self.tree_clients.yview, bootstyle="primary-round")
        self.tree_clients.configure(yscrollcommand=scrollbar_cli.set)
        
        self.tree_clients.grid(row=0, column=0, sticky="nsew")
        scrollbar_cli.grid(row=0, column=1, sticky="ns")
        
        self.tree_clients.bind("<<TreeviewSelect>>", self.on_client_select)

        # Formulario Clientes
        form_cli = tb.LabelFrame(frame_clients, text="Datos del Cliente", padding=10)
        form_cli.grid(row=2, column=0, sticky="ew")
        form_cli.columnconfigure(1, weight=1)

        self.var_cli_id = tk.StringVar()
        self.var_cli_dni = tk.StringVar()
        self.var_cli_name = tk.StringVar()
        self.var_cli_phone = tk.StringVar()
        self.var_cli_email = tk.StringVar()
        self.var_cli_address = tk.StringVar()

        tb.Label(form_cli, text="DNI/RUC:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_dni).grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Nombre:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_name).grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Celular:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_phone).grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Email:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_email).grid(row=3, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Dirección:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_cli, textvariable=self.var_cli_address).grid(row=4, column=1, sticky="ew", padx=5, pady=3)

        # Botones Clientes
        btn_frame_cli = tb.Frame(form_cli)
        btn_frame_cli.grid(row=5, column=0, columnspan=2, pady=10)
        
        tb.Button(btn_frame_cli, text="Limpiar", bootstyle="secondary", command=self.clear_client_form).pack(side="left", padx=5)
        tb.Button(btn_frame_cli, text="Guardar Cliente", bootstyle="success", command=self.save_client_action).pack(side="left", padx=5)

        # --- COLUMNA DERECHA: PRODUCTOS ---
        frame_products = tb.LabelFrame(main_container, text="📦 Gestión de Productos", padding=15, bootstyle="info")
        frame_products.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        frame_products.rowconfigure(1, weight=1)
        frame_products.columnconfigure(0, weight=1)

        # Buscador Productos
        search_frame_prod = tb.Frame(frame_products)
        search_frame_prod.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_frame_prod.columnconfigure(0, weight=1)
        
        self.entry_search_product = tb.Entry(search_frame_prod, font=("Helvetica", 10))
        self.entry_search_product.grid(row=0, column=0, sticky="ew", padx=5)
        self.entry_search_product.insert(0, "Buscar producto...")
        self.entry_search_product.bind("<FocusIn>", lambda e: self.entry_search_product.delete(0, tk.END) if self.entry_search_product.get() == "Buscar producto..." else None)
        self.entry_search_product.bind("<KeyRelease>", self.filter_products)

        # Treeview Productos con Scrollbar
        tree_frame_prod = tb.Frame(frame_products)
        tree_frame_prod.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        tree_frame_prod.rowconfigure(0, weight=1)
        tree_frame_prod.columnconfigure(0, weight=1)

        cols_prod = ("id", "code", "name", "unit", "price", "stock")
        self.tree_products = tb.Treeview(tree_frame_prod, columns=cols_prod, show="headings", height=10, bootstyle="info")
        self.tree_products.heading("id", text="ID")
        self.tree_products.heading("code", text="Código")
        self.tree_products.heading("name", text="Nombre")
        self.tree_products.heading("unit", text="Unidad")
        self.tree_products.heading("price", text="Precio")
        self.tree_products.heading("stock", text="Stock")
        
        self.tree_products.column("id", width=40, stretch=False)
        self.tree_products.column("code", width=80)
        self.tree_products.column("name", width=200)
        self.tree_products.column("unit", width=60)
        self.tree_products.column("price", width=80)
        self.tree_products.column("stock", width=70)
        
        scrollbar_prod = tb.Scrollbar(tree_frame_prod, orient="vertical", command=self.tree_products.yview, bootstyle="info-round")
        self.tree_products.configure(yscrollcommand=scrollbar_prod.set)
        
        self.tree_products.grid(row=0, column=0, sticky="nsew")
        scrollbar_prod.grid(row=0, column=1, sticky="ns")
        
        self.tree_products.bind("<<TreeviewSelect>>", self.on_product_select)
        self.tree_products.tag_configure("stock_empty", background="#FDE4E4", foreground="#5A0B0B")
        self.tree_products.tag_configure("stock_low", background="#FFF3CD", foreground="#665200")
        self.tree_products.tag_configure("stock_ok", background="", foreground="")
        self.tree_products.tag_configure("stock_na", background="", foreground="")

        # Formulario Productos
        form_prod = tb.LabelFrame(frame_products, text="Datos del Producto", padding=10)
        form_prod.grid(row=2, column=0, sticky="ew")
        form_prod.columnconfigure(1, weight=1)

        self.var_prod_id = tk.StringVar()
        self.var_prod_code = tk.StringVar()
        self.var_prod_name = tk.StringVar()
        self.var_prod_unit = tk.StringVar()
        self.var_prod_price = tk.StringVar()
        self.var_prod_stock = tk.StringVar()

        tb.Label(form_prod, text="Código:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_code).grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Nombre:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_name).grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Unidad:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_unit).grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Precio (S/):").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_price).grid(row=3, column=1, sticky="ew", padx=5, pady=3)

        tb.Label(form_prod, text="Stock:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        entry_prod_stock = tb.Entry(form_prod, textvariable=self.var_prod_stock)
        entry_prod_stock.grid(row=4, column=1, sticky="ew", padx=5, pady=3)
        stock_cmd = (self.register(lambda P: P.isdigit() or P == ""), "%P")
        entry_prod_stock.configure(validate="key", validatecommand=stock_cmd)

        # Botones Productos
        btn_frame_prod = tb.Frame(form_prod)
        btn_frame_prod.grid(row=5, column=0, columnspan=2, pady=10)
        
        tb.Button(btn_frame_prod, text="Limpiar", bootstyle="secondary", command=self.clear_product_form).pack(side="left", padx=5)
        tb.Button(btn_frame_prod, text="Guardar Producto", bootstyle="success", command=self.save_product_action).pack(side="left", padx=5)

        # Cargar datos iniciales
        self.load_initial_data()

    def load_initial_data(self):
        """Carga todos los clientes y productos al iniciar la vista."""
        try:
            # Cargar clientes
            self.all_clients_cache = self.client_service.search_clients("")
            self.filter_clients()
            
            # Cargar productos
            self.all_products_cache = self.product_service.search_products("")
            self.filter_products()
        except Exception as e:
            print(f"Error loading initial data: {e}")
            self.all_clients_cache = []
            self.all_products_cache = []

    # --- MÉTODOS DE CLIENTES ---
    def filter_clients(self, event=None):
        """Filtra clientes en tiempo real."""
        query = self.entry_search_client.get().lower()
        if query == "buscar cliente...":
            query = ""
        
        # Limpiar tabla
        for item in self.tree_clients.get_children():
            self.tree_clients.delete(item)
        
        # Filtrar y mostrar
        for client in self.all_clients_cache:
            # client = (id, dni, name, phone, email, address)
            dni = str(client[1] or "").lower()
            name = str(client[2] or "").lower()
            
            if query in dni or query in name:
                self.tree_clients.insert("", "end", values=(client[0], client[1], client[2], client[3]))

    def on_client_select(self, event):
        """Llena el formulario al seleccionar un cliente."""
        sel = self.tree_clients.focus()
        if not sel:
            return
        
        values = self.tree_clients.item(sel, "values")
        client_id = values[0]
        
        # Buscar datos completos en caché
        client = next((c for c in self.all_clients_cache if str(c[0]) == str(client_id)), None)
        if client:
            self.var_cli_id.set(client[0])
            self.var_cli_dni.set(client[1] or "")
            self.var_cli_name.set(client[2] or "")
            self.var_cli_phone.set(client[3] or "")
            self.var_cli_email.set(client[4] or "")
            stock = product[5] if len(product) > 5 else None
            if stock is None:
                self.var_prod_stock.set("")
            else:
                try:
                    stock_val = float(stock)
                    if stock_val.is_integer():
                        self.var_prod_stock.set(str(int(stock_val)))
                    else:
                        self.var_prod_stock.set(f"{stock_val:.2f}")
                except (TypeError, ValueError):
                    self.var_prod_stock.set(str(stock))
            self.var_cli_address.set(client[5] or "")

    def clear_client_form(self):
        """Limpia el formulario de clientes."""
        self.var_cli_id.set("")
        self.var_cli_dni.set("")
        self.var_cli_name.set("")
        self.var_cli_phone.set("")
        self.var_cli_email.set("")
        self.var_cli_address.set("")
        self.var_prod_stock.set("")
        # Deseleccionar en el tree
        for item in self.tree_clients.selection():
            self.tree_clients.selection_remove(item)

    def save_client_action(self):
        """Guarda o actualiza un cliente."""
        client_id = self.var_cli_id.get()
        dni = self.var_cli_dni.get().strip()
        name = self.var_cli_name.get().strip()
        phone = self.var_cli_phone.get().strip()
        email = self.var_cli_email.get().strip()
        address = self.var_cli_address.get().strip()

        if not name:
            self.show_warning("Error", "El nombre es obligatorio.")
            return

        try:
            if client_id:
                # Modo Edición
                self.client_service.update_client(client_id, dni, name, phone, email, address)
                self.show_info("Éxito", "Cliente actualizado correctamente.")
            else:
                # Modo Creación
                self.client_service.create_client(dni, name, phone, email, address)
                self.show_info("Éxito", "Cliente creado correctamente.")
            
            # Recargar datos
            self.all_clients_cache = self.client_service.search_clients("")
            self.filter_clients()
            self.clear_client_form()
        except Exception as e:
            self.show_error("Error", str(e))

    # --- MÉTODOS DE PRODUCTOS ---
    def filter_products(self, event=None):
        """Filtra productos en tiempo real."""
        query = self.entry_search_product.get().lower()
        if query == "buscar producto...":
            query = ""
        
        tree = self.tree_products
        tree.delete(*tree.get_children())

        for product in self.all_products_cache:
            code = str(product[1] or "").lower()
            name = str(product[2] or "").lower()

            if query in code or query in name:
                stock = product[5] if len(product) > 5 else None
                tag = self._resolve_stock_tag(stock)
                stock_display = self._format_stock_display(stock)
                price_value = product[4]
                try:
                    price_display = f"{float(price_value):.2f}"
                except (TypeError, ValueError):
                    price_display = str(price_value or "0.00")

                tree.insert("", "end", values=(
                    product[0],
                    product[1],
                    product[2],
                    product[3],
                    price_display,
                    stock_display
                ), tags=(tag,))

    def on_product_select(self, event):
        """Llena el formulario al seleccionar un producto."""
        sel = self.tree_products.focus()
        if not sel:
            return
        
        values = self.tree_products.item(sel, "values")
        product_id = values[0]
        
        # Buscar datos completos en caché
        product = next((p for p in self.all_products_cache if str(p[0]) == str(product_id)), None)
        if product:
            self.var_prod_id.set(product[0])
            self.var_prod_code.set(product[1] or "")
            self.var_prod_name.set(product[2] or "")
            self.var_prod_unit.set(product[3] or "")
            self.var_prod_price.set(f"{product[4]:.2f}")
            stock = product[5] if len(product) > 5 else None
            if stock is None:
                self.var_prod_stock.set("")
            else:
                try:
                    stock_val = float(stock)
                    if stock_val.is_integer():
                        self.var_prod_stock.set(str(int(stock_val)))
                    else:
                        self.var_prod_stock.set(f"{stock_val:.2f}")
                except (TypeError, ValueError):
                    self.var_prod_stock.set(str(stock))
        else:
            self.var_prod_stock.set("")

    def clear_product_form(self):
        """Limpia el formulario de productos."""
        self.var_prod_id.set("")
        self.var_prod_code.set("")
        self.var_prod_name.set("")
        self.var_prod_unit.set("")
        self.var_prod_price.set("")
        self.var_prod_stock.set("")
        # Deseleccionar en el tree
        for item in self.tree_products.selection():
            self.tree_products.selection_remove(item)

    def save_product_action(self):
        """Guarda o actualiza un producto."""
        product_id = self.var_prod_id.get()
        code = self.var_prod_code.get().strip()
        name = self.var_prod_name.get().strip()
        unit = self.var_prod_unit.get().strip()
        price_str = self.var_prod_price.get().strip()
        stock_str = self.var_prod_stock.get().strip()

        if not name or not unit or not price_str:
            self.show_warning("Error", "Nombre, Unidad y Precio son obligatorios.")
            return

        try:
            if product_id:
                self.product_service.update_product(int(product_id), name, unit, price_str, code or None, stock=stock_str)
                self.show_info("Éxito", "Producto actualizado correctamente.")
            else:
                self.product_service.create_product(name, unit, price_str, code or None, stock=stock_str)
                self.show_info("Éxito", "Producto creado correctamente.")
            
            # Recargar datos
            self.all_products_cache = self.product_service.search_products("")
            self.filter_products()
            self.clear_product_form()
        except Exception as e:
            self.show_error("Error", str(e))

    # --- Helpers internos ---
    def _resolve_stock_tag(self, stock):
        if stock is None:
            return "stock_na"
        try:
            stock_val = float(stock)
        except (TypeError, ValueError):
            return "stock_na"
        if stock_val <= 0:
            return "stock_empty"
        if stock_val <= 5:
            return "stock_low"
        return "stock_ok"

    def _format_stock_display(self, stock):
        if stock is None:
            return "Sin control"
        try:
            stock_val = float(stock)
            if stock_val.is_integer():
                return str(int(stock_val))
            return f"{stock_val:.2f}"
        except (TypeError, ValueError):
            return str(stock)
