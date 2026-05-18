import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter
from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.utils import ImageReader

def generate_excel(filename, title, headers, data, company=None):
    """Exporta a Excel con diseño formal, encabezado repetido y pie de página."""
    company = company or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"

    # --- CONFIGURACIÓN DE IMPRESIÓN ---
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    
    # Márgenes exactos (Corregido: usar page_margins)
    # Superior/Inferior: 1.91 cm -> 0.75"
    # Izquierda/Derecha: 1.78 cm -> 0.7"
    # Encabezado/Pie: 0.76 cm -> 0.3"
    ws.page_margins.top = 0.35
    ws.page_margins.bottom = 0.65
    ws.page_margins.left = 0.75
    ws.page_margins.right = 0.75
    ws.page_margins.header = 0.25
    ws.page_margins.footer = 0.25
    
    ws.print_title_rows = '1:11' # Repetir encabezado extendido
    ws.oddFooter.center.text = "Reporte de Ventas - Página &P de &N"
    
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = False
    
    # --- ENCABEZADO ---
    # (Fila 1 altura normal, el logo ocupará varias filas)
    
    logo_path = company.get('logo_path')
    if logo_path and os.path.exists(logo_path):
        try:
            img_reader = ImageReader(logo_path)
            iw, ih = img_reader.getSize()
            aspect = iw / ih
            target_h = 140 
            target_w = target_h * aspect
            if target_w > 350:
                target_w = 350
                target_h = target_w / aspect
            img = XLImage(logo_path)
            img.height = target_h
            img.width = target_w
            ws.add_image(img, 'A1')
        except Exception:
            pass
    
    # Info Empresa (Empieza en Fila 3 según solicitud)
    ws.merge_cells('D3:G3')
    ws['D3'] = company.get('name', 'MI EMPRESA')
    ws['D3'].font = Font(size=16, bold=True)
    ws['D3'].alignment = Alignment(horizontal='center', vertical='center')

    ws.merge_cells('D4:G4')
    ws['D4'] = f"RUC: {company.get('ruc', 'N/A')}"
    ws['D4'].font = Font(size=11)
    ws['D4'].alignment = Alignment(horizontal='center')

    ws.merge_cells('D5:G5')
    ws['D5'] = company.get('address', '')
    ws['D5'].font = Font(size=11)
    ws['D5'].alignment = Alignment(horizontal='center')

    ws.merge_cells('D6:G6')
    ws['D6'] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['D6'].font = Font(size=10, italic=True)
    ws['D6'].alignment = Alignment(horizontal='center')

    # Título en fila 8 (borrando 3 filas de espacio extra)
    ws.merge_cells('A8:G8')
    ws['A8'] = title.upper()
    ws['A8'].font = Font(size=14, bold=True, color='1F4788')
    ws['A8'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[8].height = 30

    # Línea separadora azul (Fila 9)
    ws.merge_cells('A8:G8')
    thick_blue_border = Border(bottom=Side(style='thick', color='1F4788'))
    for col in range(1, 8): # Aplicar borde a todas las celdas del rango A9:G9
        ws.cell(row=8, column=col).border = thick_blue_border
    ws.row_dimensions[9].height = 10

    # --- TABLA DE DATOS ---
    header_row = 11
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num, value=header)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')
        cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                             top=Side(style='thin'), bottom=Side(style='thin'))

    row_num = header_row + 1
    for record in data:
        for col_num, key in enumerate(record.keys(), 1):
            cell = ws.cell(row=row_num, column=col_num, value=record[key])
            cell.alignment = Alignment(horizontal='left')
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin'))
        if row_num % 2 == 0:
            for col_num in range(1, len(headers)+1):
                ws.cell(row=row_num, column=col_num).fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
        row_num += 1

    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for row_idx in range(header_row, row_num):
            cell = ws.cell(row=row_idx, column=col_idx)
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

    wb.save(filename)


def generate_pdf(filename, title, headers, data, company=None):
    """Exporta a PDF con diseño formal, encabezado repetido y pie de página."""
    company = company or {}
    
    # RESTAURADO: Márgenes originales (4.5cm top)
    # Márgenes reducidos para aprovechar el ancho ("extremo a extremo")
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            leftMargin=1.0*cm, rightMargin=1.0*cm,
                            topMargin=4.5*cm, bottomMargin=2.0*cm)
    
    elements = []
    styles = getSampleStyleSheet()

    def header_footer(canvas, doc):
        canvas.saveState()
        page_width, page_height = A4
        margin_left = doc.leftMargin
        margin_right = doc.rightMargin
        content_width = page_width - margin_left - margin_right
        
        # RESTAURADO: 1/3 Logo, 2/3 Texto
        logo_width = content_width * 0.33
        info_width = content_width * 0.66
        header_top = page_height - 1.0*cm
        
        logo_path = company.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            try:
                img_reader = ImageReader(logo_path)
                iw, ih = img_reader.getSize()
                aspect = iw / ih
                
                # RESTAURADO: Tamaño normal
                max_h = 2.5 * cm
                max_w = logo_width - 10 
                
                display_w = max_h * aspect
                display_h = max_h
                
                if display_w > max_w:
                    display_w = max_w
                    display_h = display_w / aspect
                
                x_pos = margin_left + (logo_width - display_w) / 2
                y_pos = (header_top - 2.5*cm) + (2.5*cm - display_h) / 2 + 0.3*cm
                
                canvas.drawImage(logo_path, x_pos, y_pos, width=display_w, height=display_h, mask='auto', preserveAspectRatio=True)
            except Exception as e:
                print(f"Error dibujando logo: {e}")
                pass

        info_center_x = margin_left + logo_width + (info_width / 2.0)
        
        # RESTAURADO: Fuentes normales
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawCentredString(info_center_x, header_top - 0.5*cm, company.get('name', 'MI EMPRESA'))
        
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(info_center_x, header_top - 1.0*cm, f"RUC: {company.get('ruc', 'N/A')}")
        canvas.drawCentredString(info_center_x, header_top - 1.4*cm, company.get('address', ''))
        canvas.drawCentredString(info_center_x, header_top - 1.8*cm, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        title_y = header_top - 3.0*cm
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(rl_colors.HexColor('#1F4788'))
        canvas.drawCentredString(page_width / 2.0, title_y, title.upper())
        
        canvas.setStrokeColor(rl_colors.HexColor('#1F4788'))
        canvas.setLineWidth(1)
        canvas.line(margin_left, title_y - 5, page_width - margin_right, title_y - 5)

        footer_y = 1.0*cm
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(rl_colors.black)
        canvas.drawCentredString(page_width / 2.0, footer_y, f"Reporte de Ventas - Página {doc.page}")
        
        canvas.restoreState()

    col_count = len(headers)
    # Ajuste dinámico de fuente para que quepa la información
    if col_count > 7:
        body_font_size = 6
        padding = 3
    elif col_count > 5:
        body_font_size = 7
        padding = 4
    else:
        body_font_size = 8
        padding = 6

    avail_width = A4[0] - doc.leftMargin - doc.rightMargin
    col_weights = []
    for h in headers:
        h_lower = h.lower()
        if any(x in h_lower for x in ['producto', 'descripción', 'cliente', 'nombre']):
            col_weights.append(3.5)
        elif any(x in h_lower for x in ['serie', 'fecha', 'email']):
            col_weights.append(1.8)
        else:
            col_weights.append(1.0)
    
    total_weight = sum(col_weights)
    col_widths = [ (w / total_weight) * avail_width for w in col_weights ]

    table_data = [headers]
    for record in data:
        row = [str(record.get(k, '')) for k in record.keys()]
        table_data.append(row)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), rl_colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0,0), (-1,0), rl_colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTSIZE', (0,1), (-1,-1), body_font_size),
        ('BOTTOMPADDING', (0,0), (-1,-1), padding),
        ('TOPPADDING', (0,0), (-1,-1), padding),
        ('BACKGROUND', (0,1), (-1,-1), rl_colors.beige),
        ('GRID', (0,0), (-1,-1), 0.5, rl_colors.black),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [rl_colors.white, rl_colors.lightgrey]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
