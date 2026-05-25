"""Generate pre-invoice PDF from HR project data using ReportLab."""

import calendar
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

DARK_BLUE  = colors.HexColor("#1F3864")
MED_BLUE   = colors.HexColor("#2E75B6")
LIGHT_BLUE = colors.HexColor("#D6E4F0")
GRAY       = colors.HexColor("#888888")
LGRAY      = colors.HexColor("#CCCCCC")

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _style(name, **kw) -> ParagraphStyle:
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kw)


def generate_prefactura_rrhh_pdf(
    proyecto,
    personas: list,
    mes: int,
    anio: int,
    output_path: str,
    numero_prefactura: str,
    empresa_nombre: str = "Mi Empresa S.A.",
    empresa_cuit: str = "",
) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm,   bottomMargin=2 * cm,
        title=f"Pre-Factura {numero_prefactura}",
        author=empresa_nombre,
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    s_title    = _style("s_title",    fontSize=22, textColor=DARK_BLUE, alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Bold")
    s_subtitle = _style("s_subtitle", fontSize=9,  textColor=GRAY,      alignment=TA_CENTER, spaceAfter=10)
    s_section  = _style("s_section",  fontSize=9,  textColor=colors.white, backColor=DARK_BLUE, leading=18, leftIndent=6, fontName="Helvetica-Bold")
    s_label    = _style("s_label",    fontSize=9,  textColor=colors.HexColor("#444444"))
    s_value    = _style("s_value",    fontSize=9,  fontName="Helvetica-Bold")
    s_footer   = _style("s_footer",   fontSize=7,  textColor=GRAY, alignment=TA_CENTER)
    s_th       = _style("s_th",       fontSize=8,  textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_td       = _style("s_td",       fontSize=8)
    s_td_r     = _style("s_td_r",     fontSize=8,  alignment=TA_RIGHT)

    periodo     = f"{MESES[mes].capitalize()} {anio}"
    dias_mes    = calendar.monthrange(anio, mes)[1]
    hoy_str     = date.today().strftime("%d/%m/%Y")
    col_widths  = [2.2*cm, 5.8*cm, 2.4*cm, 1.8*cm, 3.3*cm, 3.3*cm]

    story = []

    # ── Title ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("PRE-FACTURA", s_title))
    story.append(Paragraph("DOCUMENTO INTERNO — NO VÁLIDO COMO FACTURA FISCAL", s_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=DARK_BLUE))
    story.append(Spacer(1, 0.35*cm))

    # ── Metadata ──────────────────────────────────────────────────────────────
    def meta_row(l1, v1, l2, v2):
        return [Paragraph(l1, s_label), Paragraph(v1, s_value),
                Paragraph(l2, s_label), Paragraph(v2, s_value)]

    meta = Table([
        meta_row("N° Prefactura:", numero_prefactura, "Período:", periodo),
        meta_row("Fecha emisión:", hoy_str,           "Días del período:", str(dias_mes)),
    ], colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.5*cm))

    # ── Emisor ────────────────────────────────────────────────────────────────
    story.append(Paragraph("EMISOR (PROVEEDOR)", s_section))
    emisor = Table([
        [Paragraph("Razón Social:", s_label), Paragraph(empresa_nombre, s_value),
         Paragraph("CUIT:", s_label),         Paragraph(empresa_cuit or "—", s_value)],
    ], colWidths=[3*cm, 6*cm, 2*cm, 7*cm])
    emisor.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(emisor)
    story.append(Spacer(1, 0.3*cm))

    # ── Receptor ──────────────────────────────────────────────────────────────
    story.append(Paragraph("RECEPTOR (CLIENTE)", s_section))
    receptor = Table([
        [Paragraph("Razón Social:", s_label), Paragraph(proyecto.cliente_nombre, s_value),
         Paragraph("CUIT:",         s_label), Paragraph(proyecto.cliente_cuit or "—", s_value)],
        [Paragraph("Proyecto:",     s_label), Paragraph(proyecto.nombre, s_value),
         Paragraph("ID Proyecto:",  s_label), Paragraph(proyecto.id, s_value)],
    ], colWidths=[3*cm, 6*cm, 2.5*cm, 6.5*cm])
    receptor.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(receptor)
    story.append(Spacer(1, 0.5*cm))

    # ── Recursos ──────────────────────────────────────────────────────────────
    story.append(Paragraph("DETALLE DE RECURSOS HUMANOS", s_section))
    story.append(Spacer(1, 0.2*cm))

    headers = [Paragraph(h, s_th) for h in
               ("ID", "Nombre", "Ingreso", "Moneda", "Tarifa Mensual", "Subtotal")]
    rows = [headers]

    total_por_moneda: dict[str, float] = {}
    for p in personas:
        sub = p.tarifa_mensual
        total_por_moneda[p.moneda] = total_por_moneda.get(p.moneda, 0.0) + sub
        rows.append([
            Paragraph(p.id, s_td),
            Paragraph(p.nombre, s_td),
            Paragraph(p.fecha_ingreso.strftime("%d/%m/%Y"), s_td),
            Paragraph(p.moneda, s_td),
            Paragraph(f"{p.tarifa_mensual:,.2f}", s_td_r),
            Paragraph(f"{sub:,.2f}", s_td_r),
        ])

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tstyle = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  MED_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, -1), 0.4, LGRAY),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])
    for i in range(1, len(rows)):
        if i % 2 == 0:
            tstyle.add("BACKGROUND", (0, i), (-1, i), LIGHT_BLUE)
    tbl.setStyle(tstyle)
    story.append(tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Totales ───────────────────────────────────────────────────────────────
    iva_pct = 21
    totals_data = []
    grand_totals: dict[str, float] = {}
    for moneda, subtotal in total_por_moneda.items():
        iva     = round(subtotal * iva_pct / 100, 2)
        total   = round(subtotal + iva, 2)
        grand_totals[moneda] = total
        totals_data += [
            ["", "", "", "", Paragraph(f"Subtotal ({moneda}):", s_td_r), Paragraph(f"{moneda} {subtotal:,.2f}", s_td_r)],
            ["", "", "", "", Paragraph(f"IVA {iva_pct}%:",      s_td_r), Paragraph(f"{moneda} {iva:,.2f}",     s_td_r)],
            ["", "", "", "", Paragraph(f"TOTAL {moneda}:",       _style("s_tot", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT, textColor=colors.white)),
                             Paragraph(f"{moneda} {total:,.2f}", _style("s_tot2", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT, textColor=colors.white))],
        ]

    tot_tbl = Table(totals_data, colWidths=col_widths)
    tot_style = TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    # Color total rows (every 3rd, starting at index 2)
    for i in range(2, len(totals_data), 3):
        tot_style.add("BACKGROUND", (4, i), (-1, i), DARK_BLUE)
        tot_style.add("BOX",        (4, i), (-1, i), 1, DARK_BLUE)
    tot_tbl.setStyle(tot_style)
    story.append(tot_tbl)
    story.append(Spacer(1, 1*cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=LGRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Pre-factura N° {numero_prefactura} · Período {periodo} · "
        f"Generada automáticamente el {hoy_str} · DOCUMENTO INTERNO",
        s_footer,
    ))

    doc.build(story)
    return output_path
