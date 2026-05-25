"""Generate a pre-invoice Excel file from structured OC data."""

import json
import os
import logging
from datetime import datetime

import openpyxl
from openpyxl.styles import (
    Font, Alignment, PatternFill, Border, Side, numbers
)

log = logging.getLogger(__name__)

# ── Palette ───────────────────────────────────────────────────────────────────
DARK_BLUE  = "1F3864"
MED_BLUE   = "2E75B6"
LIGHT_BLUE = "D6E4F0"
WHITE      = "FFFFFF"
GRAY       = "808080"

def _fill(hex_color: str) -> PatternFill:
    return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")

def _font(bold=False, size=10, color="000000", italic=False) -> Font:
    return Font(name="Calibri", bold=bold, size=size, color=color, italic=italic)

def _border() -> Border:
    s = Side(style="thin")
    return Border(left=s, right=s, top=s, bottom=s)

def _center(wrap=False) -> Alignment:
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)

def _right() -> Alignment:
    return Alignment(horizontal="right", vertical="center")

def _left() -> Alignment:
    return Alignment(horizontal="left", vertical="center")


# ── Builder ───────────────────────────────────────────────────────────────────
def generate_prefactura(oc_data: dict, output_dir: str, numero: str | None = None) -> str:
    if numero is None:
        numero = f"PF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    moneda = oc_data.get("moneda", "ARS")
    num_fmt = f'"{moneda} "#,##0.00'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Prefactura"

    # Column widths: A=5, B=38, C=13, D=18, E=18
    for col, w in zip("ABCDE", (5, 38, 13, 18, 18)):
        ws.column_dimensions[col].width = w

    r = 1  # current row cursor

    # ── Title row ──────────────────────────────────────────────────────────────
    ws.merge_cells(f"A{r}:E{r}")
    ws[f"A{r}"] = "PRE-FACTURA"
    ws[f"A{r}"].font = _font(bold=True, size=20, color=DARK_BLUE)
    ws[f"A{r}"].alignment = _center()
    ws.row_dimensions[r].height = 44
    r += 1

    # ── Metadata ───────────────────────────────────────────────────────────────
    meta = [
        ("N° Prefactura", numero,         "Fecha emisión", datetime.now().strftime("%d/%m/%Y")),
        ("Ref. OC",       oc_data.get("numero_oc") or "", "Fecha OC", oc_data.get("fecha") or ""),
    ]
    for label_a, val_a, label_d, val_d in meta:
        ws[f"A{r}"] = label_a; ws[f"A{r}"].font = _font(bold=True)
        ws[f"B{r}"] = val_a;   ws[f"B{r}"].font = _font()
        ws[f"D{r}"] = label_d; ws[f"D{r}"].font = _font(bold=True)
        ws[f"E{r}"] = val_d;   ws[f"E{r}"].font = _font()
        ws.row_dimensions[r].height = 18
        r += 1

    r += 1  # spacer

    # ── Client block ───────────────────────────────────────────────────────────
    ws.merge_cells(f"A{r}:E{r}")
    ws[f"A{r}"] = "DATOS DEL CLIENTE"
    ws[f"A{r}"].font = _font(bold=True, color=WHITE)
    ws[f"A{r}"].fill = _fill(DARK_BLUE)
    ws[f"A{r}"].alignment = _left()
    ws.row_dimensions[r].height = 22
    r += 1

    cliente = oc_data.get("cliente", {})
    client_rows = [
        ("Razón Social", cliente.get("nombre", ""), "CUIT", cliente.get("cuit", "")),
        ("Dirección",    cliente.get("direccion", ""), "", ""),
    ]
    for label_a, val_a, label_d, val_d in client_rows:
        ws[f"A{r}"] = label_a; ws[f"A{r}"].font = _font(bold=True)
        ws.merge_cells(f"B{r}:C{r}")
        ws[f"B{r}"] = val_a;   ws[f"B{r}"].font = _font()
        ws[f"D{r}"] = label_d; ws[f"D{r}"].font = _font(bold=True)
        ws[f"E{r}"] = val_d;   ws[f"E{r}"].font = _font()
        ws.row_dimensions[r].height = 18
        r += 1

    r += 1  # spacer

    # ── Items table header ─────────────────────────────────────────────────────
    headers = ("#", "Descripción", "Cantidad", "Precio Unit.", "Subtotal")
    aligns  = (_center(), _center(), _center(), _right(), _right())
    for col, (hdr, aln) in zip("ABCDE", zip(headers, aligns)):
        c = ws[f"{col}{r}"]
        c.value = hdr
        c.font = _font(bold=True, color=WHITE)
        c.fill = _fill(MED_BLUE)
        c.alignment = aln
        c.border = _border()
    ws.row_dimensions[r].height = 24
    r += 1

    # ── Items ──────────────────────────────────────────────────────────────────
    items = oc_data.get("items", [])
    for i, item in enumerate(items, start=1):
        row_fill = _fill(LIGHT_BLUE) if i % 2 == 0 else None
        values = {
            "A": i,
            "B": item.get("descripcion", ""),
            "C": item.get("cantidad", 0),
            "D": item.get("precio_unitario", 0.0),
            "E": item.get("subtotal", 0.0),
        }
        aligns_row = {"A": _center(), "B": _left(), "C": _center(), "D": _right(), "E": _right()}
        for col, val in values.items():
            c = ws[f"{col}{r}"]
            c.value = val
            c.font = _font()
            c.border = _border()
            c.alignment = aligns_row[col]
            if row_fill:
                c.fill = row_fill
            if col in ("D", "E"):
                c.number_format = num_fmt
        ws.row_dimensions[r].height = 18
        r += 1

    r += 1  # spacer

    # ── Totals ─────────────────────────────────────────────────────────────────
    iva_pct = oc_data.get("iva_porcentaje", 21)
    totals = [
        (f"Subtotal ({moneda})",     oc_data.get("subtotal", 0.0),  False),
        (f"IVA {iva_pct}%",          oc_data.get("iva_monto", 0.0), False),
        (f"TOTAL {moneda}",          oc_data.get("total", 0.0),      True),
    ]
    for label, value, is_total in totals:
        ws.merge_cells(f"A{r}:C{r}")
        d = ws[f"D{r}"]
        e = ws[f"E{r}"]
        d.value = label
        e.value = value
        e.number_format = num_fmt
        d.border = _border()
        e.border = _border()
        d.alignment = _right()
        e.alignment = _right()
        if is_total:
            d.font = _font(bold=True, size=11, color=WHITE)
            d.fill = _fill(DARK_BLUE)
            e.font = _font(bold=True, size=11, color=WHITE)
            e.fill = _fill(DARK_BLUE)
        else:
            d.font = _font(bold=True)
            e.font = _font()
        ws.row_dimensions[r].height = 22
        r += 1

    # ── Notes ──────────────────────────────────────────────────────────────────
    notas = oc_data.get("notas")
    if notas:
        r += 1
        ws[f"A{r}"] = "Observaciones:"
        ws[f"A{r}"].font = _font(bold=True)
        r += 1
        ws.merge_cells(f"A{r}:E{r}")
        ws[f"A{r}"] = notas
        ws[f"A{r}"].font = _font(italic=True)
        ws[f"A{r}"].alignment = Alignment(wrap_text=True)
        ws.row_dimensions[r].height = 40

    # ── Footer ─────────────────────────────────────────────────────────────────
    r += 2
    ws.merge_cells(f"A{r}:E{r}")
    ws[f"A{r}"] = "DOCUMENTO INTERNO — NO VÁLIDO COMO FACTURA FISCAL"
    ws[f"A{r}"].font = _font(italic=True, size=9, color=GRAY)
    ws[f"A{r}"].alignment = _center()

    # ── Save xlsx ──────────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    stem = f"prefactura_{numero}_{datetime.now().strftime('%Y%m%d')}"
    filepath = os.path.join(output_dir, f"{stem}.xlsx")
    json_path = os.path.join(output_dir, f"{stem}.json")

    wb.save(filepath)

    # Persist raw OC data so aprobar.py can reconstruct the final invoice
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(oc_data, f, ensure_ascii=False, indent=2)

    log.info("Prefactura guardada: %s", filepath)
    return filepath, json_path
