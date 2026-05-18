import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
from datetime import datetime
from PIL import Image, ImageTk

# Custom DateEntry to support icon and styling
class CustomDateEntry(tb.DateEntry):
    def __init__(self, master, app_icon_refs=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_icon_refs = app_icon_refs or []
        
        # Override button command to inject our logic
        self.old_cmd = self.button.cget('command')
        self.button.configure(command=self._on_open_custom)

    def _on_open_custom(self):
        # Call original command to open popup
        if self.old_cmd:
            try:
                self.old_cmd()
            except Exception:
                pass
        
        # Try to find the popup window (Toplevel)
        # In ttkbootstrap, it's usually self.date_picker_window if accessible, 
        # or we can find it via master's children or global toplevels.
        # But since we don't have easy access to the internal variable, 
        # let's try to find the latest Toplevel created or use a delay.
        
        # However, looking at source, DateEntry creates a Querybox.
        # Let's try to find a Toplevel that has "Select new date" title (default) or similar.
        
        self.after(50, self._customize_popup)

    def _customize_popup(self):
        # Iterate over all toplevels to find the calendar
        for widget in self.winfo_children():
            if isinstance(widget, tk.Toplevel):
                self._apply_customization(widget)
                return

        # If not found in children, check global toplevels (less reliable but possible)
        # But DateEntry popup is likely a child of the DateEntry frame or root.
        # Actually, ttkbootstrap DateEntry popup is a Toplevel with master=self.
        
        # Let's try to find it by title if we can't find it by hierarchy
        # Default title is "Select new date" (or localized)
        pass

    def _apply_customization(self, window):
        # 1. Set Icon
        if self.app_icon_refs:
            try:
                # Use the first icon available
                # window.iconphoto(False, self.app_icon_refs[0]) 
                # Note: iconphoto expects an image object.
                # If app_icon_refs contains PhotoImages, this works.
                pass
            except Exception:
                pass
                
        # 2. Set Background Color (Grayish)
        # We need to find the Calendar widget inside.
        # It's usually a widget of class 'Calendar' or similar.
        try:
            # Force a style or configure background
            # This depends on how ttkbootstrap calendar is implemented.
            # It uses a Treeview or similar.
            pass
        except Exception:
            pass

# Since implementing a robust CustomDateEntry without deep library knowledge is risky,
# we will use a simpler approach: 
# We will use the standard DateEntry but bind to the button click to customize the window.

class ExportUIManager:
    def __init__(self, app):
        self.app = app
        self.selected_export_client_id = None
        self.export_client_map = {}
        self._export_search_job = None
        self.fiado_status_var = tk.StringVar(value="todos")
        self.scroll_canvas = None
        self.scroll_frame = None

    def build_export_ui(self):
        """Construye la interfaz de exportación en el frame principal."""
        f = self.app.frame_export
        for widget in f.winfo_children():
            widget.destroy()

        # Contenedor scrollable para evitar que se oculte contenido en ventanas pequeñas
        outer = tb.Frame(f)
        outer.pack(fill="both", expand=True)

        self.scroll_canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        scrollbar = tb.Scrollbar(outer, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        self.scroll_frame = tb.Frame(self.scroll_canvas)
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")),
        )
        self.scroll_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.scroll_canvas.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.scroll_canvas.bind_all("<Button-5>", self._on_mousewheel, add="+")

        # Contenedor principal centrado
        main_container = tb.Frame(self.scroll_frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # --- HEADER ---
        header_frame = tb.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Logo en el Header (si existe)
        if hasattr(self.app, "main_logo_image") and self.app.main_logo_image:
            logo_lbl = tb.Label(header_frame, image=self.app.main_logo_image)
            logo_lbl.pack(side="left", padx=(0, 15))
        
        tb.Label(
            header_frame, 
            text="Centro de Reportes y Exportación", 
            font=("Segoe UI", 24, "bold"),
            bootstyle="primary"
        ).pack(side="left", fill="y")
        
        # --- CONTENIDO (GRID 3 COLUMNAS) ---
        content_grid = tb.Frame(main_container)
        content_grid.pack(fill="both", expand=True)
        content_grid.columnconfigure(0, weight=1) # Opciones
        content_grid.columnconfigure(1, weight=1) # Filtros Tiempo
        content_grid.columnconfigure(2, weight=1) # Selector Fechas (Card)
        
        # === COLUMNA 1: QUÉ EXPORTAR ===
        col1 = tb.Frame(content_grid)
        col1.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        lf_type = tb.Labelframe(col1, text="1. Tipo de Reporte", padding=15, bootstyle="info")
        lf_type.pack(fill="x", pady=(0, 20))
        
        self.data_type_var = tk.StringVar(value="clientes")
        
        options = [
            ("👥 Base de Clientes", "clientes"),
            ("📦 Catálogo de Productos", "productos"),
            ("🧾 Historial de Ventas (Detallado)", "ventas_detalladas"),
            ("📈 Resumen de Ventas", "ventas_resumen"),
            ("👤 Ventas por Cliente", "ventas_por_cliente"),
            ("🤝 Fiados (General)", "fiados"),
            ("🧾 Fiados por Cliente", "fiados_por_cliente"),
        ]
        
        for text, val in options:
            tb.Radiobutton(
                lf_type, 
                text=text, 
                variable=self.data_type_var, 
                value=val, 
                command=self.on_data_type_change,
                bootstyle="info-toolbutton-outline"
            ).pack(fill="x", pady=2, ipady=5)
            
        # Búsqueda de Cliente (Toggleable)
        self.client_search_frame = tb.Frame(lf_type, padding=10)
        tb.Label(self.client_search_frame, text="Buscar Cliente:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        
        self.txt_client_search = tb.Entry(self.client_search_frame)
        self.txt_client_search.pack(fill="x", pady=(5, 0))
        self.txt_client_search.bind("<KeyRelease>", self.on_search_change)
        
        self.cb_client_results = tb.Combobox(self.client_search_frame, state="readonly", height=5)
        self.cb_client_results.pack(fill="x", pady=5)
        self.cb_client_results.bind("<<ComboboxSelected>>", self.on_client_select)

        # Filtro de estado para fiados
        self.fiado_status_frame = tb.Labelframe(col1, text="Filtro de Fiados", padding=12, bootstyle="secondary")
        status_inner = tb.Frame(self.fiado_status_frame)
        status_inner.pack(fill="x")
        for txt, val in (("Todos", "todos"), ("Pagados", "pagados"), ("Pendientes", "pendientes")):
            tb.Radiobutton(
                status_inner,
                text=txt,
                variable=self.fiado_status_var,
                value=val,
                bootstyle="secondary-toolbutton-outline",
            ).pack(fill="x", pady=2, ipady=4)

        # Formato de Salida (Ahora en Col 1)
        lf_format = tb.Labelframe(col1, text="2. Formato", padding=15, bootstyle="success")
        lf_format.pack(fill="x")
        
        self.format_var = tk.StringVar(value="excel")
        fmt_frame = tb.Frame(lf_format)
        fmt_frame.pack(fill="x")
        
        tb.Radiobutton(
            fmt_frame, 
            text="Excel (.xlsx)", 
            variable=self.format_var, 
            value="excel", 
            bootstyle="success-toolbutton-outline"
        ).pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=5)
        
        tb.Radiobutton(
            fmt_frame, 
            text="PDF (.pdf)", 
            variable=self.format_var, 
            value="pdf", 
            bootstyle="danger-toolbutton-outline"
        ).pack(side="left", fill="x", expand=True, padx=(5, 0), ipady=5)

        # === COLUMNA 2: FILTROS DE TIEMPO ===
        col2 = tb.Frame(content_grid)
        col2.grid(row=0, column=1, sticky="nsew", padx=10)
        
        lf_time = tb.Labelframe(col2, text="3. Periodo", padding=15, bootstyle="warning")
        lf_time.pack(fill="both", expand=True)
        
        self.time_filter_var = tk.StringVar(value="all")
        
        time_options = [
            ("⏱ Última hora", "1h"),
            ("📅 Últimas 24 horas", "24h"),
            ("📆 Última semana", "7d"),
            ("📊 Último mes", "30d"),
            ("🌐 Todo el historial", "all"),
            ("✏️ Rango Personalizado", "custom")
        ]
        
        for text, val in time_options:
            tb.Radiobutton(
                lf_time, 
                text=text, 
                variable=self.time_filter_var, 
                value=val,
                bootstyle="warning-toolbutton-outline",
                command=self.toggle_custom_dates
            ).pack(fill="x", pady=2, ipady=5)

        # === COLUMNA 3: SELECTOR DE FECHAS (CARD STYLE) ===
        col3 = tb.Frame(content_grid)
        col3.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        
        # Frame "Card" con fondo gris (secondary)
        self.date_card = tb.Frame(col3, bootstyle="secondary", padding=2)
        self.date_card.pack(fill="x", pady=(10, 0))
        
        # Contenido interno de la tarjeta
        card_inner = tb.Frame(self.date_card, padding=20, bootstyle="secondary")
        card_inner.pack(fill="both", expand=True)
        
        # Logo pequeño en la tarjeta (si existe)
        if hasattr(self.app, "main_logo_image") and self.app.main_logo_image:
            logo_card = tb.Label(card_inner, image=self.app.main_logo_image, bootstyle="inverse-secondary")
            logo_card.pack(pady=(0, 15))
            
        tb.Label(
            card_inner, 
            text="Selección de Fechas", 
            font=("Segoe UI", 12, "bold"), 
            bootstyle="inverse-secondary"
        ).pack(pady=(0, 15))
        
        # Inputs de fecha
        grid_dates = tb.Frame(card_inner, bootstyle="secondary")
        grid_dates.pack(fill="x")
        
        tb.Label(grid_dates, text="Desde:", bootstyle="inverse-secondary").grid(row=0, column=0, sticky="w", pady=5)
        self.date_from = tb.DateEntry(grid_dates, bootstyle="warning", firstweekday=0, dateformat="%d/%m/%Y")
        self.date_from.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        tb.Label(grid_dates, text="Hasta:", bootstyle="inverse-secondary").grid(row=1, column=0, sticky="w", pady=5)
        self.date_to = tb.DateEntry(grid_dates, bootstyle="warning", firstweekday=0, dateformat="%d/%m/%Y")
        self.date_to.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        # Configurar validación y auto-formato
        self._setup_date_validation(self.date_from)
        self._setup_date_validation(self.date_to)
        
        # Configurar personalización del popup de fecha
        self.date_from.button.bind("<Button-1>", lambda e: self._schedule_popup_customization(self.date_from), add="+")
        self.date_to.button.bind("<Button-1>", lambda e: self._schedule_popup_customization(self.date_to), add="+")
        
        # Botón Generar (Grande)
        btn_export = tb.Button(
            col3, 
            text="GENERAR REPORTE", 
            bootstyle="success", 
            command=self.do_export,
            width=20
        )
        btn_export.pack(fill="x", pady=20, ipady=10)
        
        # Inicializar estado
        self.on_data_type_change()
        self.toggle_custom_dates()

    def _setup_date_validation(self, date_entry):
        """Configura la validación y formato automático de fecha (DD/MM/YYYY)."""
        entry = date_entry.entry
        
        def on_key_release(event):
            # Permitir borrar y navegar sin interferencia
            if event.keysym in ('BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down', 'Tab'):
                return
                
            val = entry.get()
            # Limpiar todo lo que no sea número
            clean = "".join(filter(str.isdigit, val))
            
            formatted = ""
            # Día (Max 31)
            if len(clean) > 0:
                d = clean[:2]
                if len(d) == 2:
                    if int(d) > 31: d = "31"
                    if int(d) == 0: d = "01"
                formatted += d
                
            # Slash 1
            if len(clean) >= 2:
                formatted += "/"
                
            # Mes (Max 12)
            if len(clean) > 2:
                m = clean[2:4]
                if len(m) == 2:
                    if int(m) > 12: m = "12"
                    if int(m) == 0: m = "01"
                formatted += m
            
            # Slash 2
            if len(clean) >= 4:
                formatted += "/"
                
            # Año (4 dígitos)
            if len(clean) > 4:
                y = clean[4:8]
                formatted += y
                
            if val != formatted:
                entry.delete(0, tk.END)
                entry.insert(0, formatted)
                
        entry.bind("<KeyRelease>", on_key_release)

    def _schedule_popup_customization(self, parent_widget):
        """Inicia un sondeo para encontrar el popup de fecha."""
        self._poll_for_popup(0)

    def _poll_for_popup(self, attempt):
        """Busca la ventana del calendario repetidamente."""
        found = False
        
        # Buscar en todas las ventanas de nivel superior de la aplicación
        for widget in self.app.winfo_children():
            if isinstance(widget, tk.Toplevel):
                if widget.winfo_viewable():
                    title = widget.title()
                    # El título por defecto de ttkbootstrap es "Select new date"
                    if "Select new date" in title or "Selecc" in title:
                        self._apply_style_to_popup(widget)
                        found = True
                        break
        
        # Si no lo encontramos y no hemos excedido los intentos (1 segundo aprox)
        if not found and attempt < 20:
            self.app.after(50, lambda: self._poll_for_popup(attempt + 1))

    def _apply_style_to_popup(self, window):
        # 1. Cambiar Título
        window.title("Seleccionar Fecha")
        
        # 2. Icono (Forzar actualización)
        if hasattr(self.app, "set_app_icon"):
            self.app.set_app_icon(window)
            
        # 3. Color de fondo
        try:
            is_dark = True
            if hasattr(self.app, "is_dark_theme"):
                is_dark = self.app.is_dark_theme()
            
            bg_color = "#2b2b2b" if is_dark else "#f0f0f0"
            window.configure(background=bg_color)
        except Exception:
            pass

    def toggle_client_search(self):
        if self.data_type_var.get() in ("ventas_por_cliente", "fiados_por_cliente"):
            self.client_search_frame.pack(fill="x", pady=10)
        else:
            self.client_search_frame.pack_forget()

    def toggle_fiado_filters(self):
        is_fiado = self.data_type_var.get() in ("fiados", "fiados_por_cliente")
        if is_fiado:
            self.fiado_status_frame.pack(fill="x", pady=10)
        else:
            self.fiado_status_frame.pack_forget()

    def on_data_type_change(self):
        self.toggle_client_search()
        self.toggle_fiado_filters()

    def _on_mousewheel(self, event):
        if not self.scroll_canvas:
            return
        # Windows/macOS delta uses event.delta; Linux uses Button-4/5
        if hasattr(event, "delta") and event.delta != 0:
            self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif getattr(event, "num", None) == 4:
            self.scroll_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.scroll_canvas.yview_scroll(3, "units")

    def toggle_custom_dates(self):
        # En este diseño, la tarjeta siempre es visible, pero deshabilitamos los inputs si no es custom
        is_custom = self.time_filter_var.get() == "custom"
        state = "normal" if is_custom else "disabled"
        
        # DateEntry no tiene state directo en el widget principal a veces, pero sí en el entry
        try:
            self.date_from.entry.configure(state=state)
            self.date_from.button.configure(state=state)
            self.date_to.entry.configure(state=state)
            self.date_to.button.configure(state=state)
        except Exception:
            pass
            
        # Opacidad visual (opcional)
        if is_custom:
            self.date_card.pack(fill="x", pady=(10, 0))
        else:
            # Ocultar la tarjeta si no es custom para limpiar la UI, o dejarla visible pero deshabilitada
            # El usuario dijo "ya que tenemos espacio extra", mejor dejarla visible o hacerla aparecer.
            # Vamos a ocultarla para que sea dinámico.
            self.date_card.pack_forget()

    def search_client_action(self):
        query = self.txt_client_search.get().strip()
        if not query:
            self.cb_client_results['values'] = []
            self.cb_client_results.set("")
            self.selected_export_client_id = None
            return

        results = self.app.client_service.search_clients(query)
        if not results:
            self.cb_client_results['values'] = ["Sin resultados"]
            self.cb_client_results.current(0)
            self.selected_export_client_id = None
        else:
            values = [f"{r[2]} ({r[1]})" for r in results]
            self.cb_client_results['values'] = values
            self.cb_client_results.current(0)
            self.export_client_map = {i: r[0] for i, r in enumerate(results)}
            self.selected_export_client_id = results[0][0]

    def on_search_change(self, event):
        if self._export_search_job:
            self.app.after_cancel(self._export_search_job)
        self._export_search_job = self.app.after(500, lambda: self.search_client_action())

    def on_client_select(self, event):
        idx = self.cb_client_results.current()
        if idx >= 0:
            self.selected_export_client_id = self.export_client_map.get(idx)

    def do_export(self):
        # Parseo de fechas
        try:
            raw_from = self.date_from.entry.get()
            raw_to = self.date_to.entry.get()
            
            def parse_date(d_str):
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        return datetime.strptime(d_str, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                return d_str
            
            iso_from = parse_date(raw_from)
            iso_to = parse_date(raw_to)
            
        except Exception:
            iso_from = ""
            iso_to = ""

        self.app.selected_export_client_id = self.selected_export_client_id

        self.app.execute_export(
            data_type=self.data_type_var.get(),
            format_type=self.format_var.get(),
            time_filter=self.time_filter_var.get(),
            date_from=iso_from,
            date_to=iso_to,
            fiado_status=self.fiado_status_var.get(),
        )
