# extract_proformas_advanced.py
"""
Extractor avanzado que:
 - Lee .docx (párrafos + tablas)
 - Lee .pdf (texto); si no hay texto usa OCR (pytesseract)
 - Busca costo total, costo materiales, tiempo/plazo (varias heurísticas)
 - Guarda dataset y issues con timestamp (no sobrescribe por defecto)
 - Guarda JSON debug por archivo para inspección manual

Uso:
 python extract_proformas_advanced.py           # crea archivos timestamped
 python extract_proformas_advanced.py --overwrite  # sobrescribe csv (opcional)
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import docx
import fitz            # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd

# ---------------- CONFIG ----------------
DATA_FOLDER = "datos_proformas"
OUT_FOLDER = "."  # donde se escriben los CSV/JSON
MARGIN_GAIN = 0.20  # margen estimado para ROI
DEFAULT_CCC = 30

# Si tesseract no está en PATH, intenta detectar ruta común en Windows
if os.name == "nt":
    default_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_tess):
        pytesseract.pytesseract.tesseract_cmd = default_tess

# ---------------- utilidades ----------------
def now_ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")

def clean_number(txt: str) -> Optional[float]:
    if txt is None: 
        return None
    txt = str(txt)
    txt = txt.replace("S/.", "").replace("S/", "").replace("s/", "").replace("$", "")
    # manejar formatos: si "1.234.567,89" --> quitar puntos y convertir coma a punto
    txt = txt.strip()
    # heurística: si hay más de one dot and one comma -> assume dots are thousand separators
    if txt.count(".") > 1 and txt.count(",") == 1:
        txt = txt.replace(".", "").replace(",", ".")
    elif txt.count(",") > 1 and txt.count(".") == 1:
        txt = txt.replace(",", "").replace(".", ".")
    else:
        # si hay coma y no punto -> coma decimal
        if txt.count(",") == 1 and txt.count(".") == 0:
            txt = txt.replace(",", ".")
        else:
            txt = txt.replace(",", "")
    # strip non digits except dot and minus
    txt = re.sub(r"[^\d\.-]", "", txt)
    try:
        return float(txt)
    except:
        return None

# ---------------- lectura documentos ----------------
def read_docx_text(path: str) -> str:
    doc = docx.Document(path)
    parts = []
    for p in doc.paragraphs:
        if p.text and p.text.strip():
            parts.append(p.text.strip())
    # tablas: formatear cada fila como "cell1 | cell2 | cell3"
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text and cell.text.strip())
            if row_text:
                parts.append(row_text)
    return "\n".join(parts)

def read_pdf_text(path: str) -> Tuple[str, bool]:
    """Devuelve (texto, used_ocr_flag). Si texto está vacío -> hacer OCR por página."""
    doc = fitz.open(path)
    fulltext = ""
    page_images_needed = []
    for i, page in enumerate(doc):
        txt = page.get_text("text")
        if txt and txt.strip():
            fulltext += txt + "\n"
        else:
            # marcar esta página para OCR
            page_images_needed.append(i)
    if page_images_needed and not fulltext.strip():
        # no text anywhere: usar OCR de todas las páginas
        ocr_text = []
        for i in page_images_needed:
            page = doc[i]
            pix = page.get_pixmap(dpi=300)
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            txt = pytesseract.image_to_string(img, lang="spa+eng")
            ocr_text.append(txt)
        return ("\n".join(ocr_text), True)
    elif page_images_needed:
        # mezclar: hay texto y alguna página sin texto -> OCR solo para esas páginas y concatenar
        for i in page_images_needed:
            page = doc[i]
            pix = page.get_pixmap(dpi=300)
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            fulltext += "\n" + pytesseract.image_to_string(img, lang="spa+eng")
        return (fulltext, True)
    else:
        return (fulltext, False)

# ---------------- patrones heurísticos ----------------
NUMBER_RE = r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})|[0-9]+(?:[.,][0-9]+)?)"

COST_PATTERNS = [
    rf"(?:costo\s*total|costo\s*del\s*proyecto|total\s*general|importe\s*total|total\s*a\s*pagar|total)[:\s\-]*S?[/.]?\s*{NUMBER_RE}",
    rf"(?:TOTAL)[:\s\-]*S?[/.]?\s*{NUMBER_RE}",
    rf"(?:importe[:\s\-]*S?[/.]?\s*{NUMBER_RE})"
]

MATERIALS_PATTERNS = [
    rf"(?:costo\s*de\s*materiales|valor\s*materiales|materiales|material)[:\s\-]*S?[/.]?\s*{NUMBER_RE}"
]

TIME_PATTERNS = [
    rf"(?:tiempo\s*de\s*entrega|plazo\s*de\s*entrega|duraci[oó]n|plazo|entrega)[:\s\-]*{NUMBER_RE}",
    rf"(\d+)\s*(?:d[ií]as|dias)\b"
]

# proximidad search (buscar número cercano a keyword si no hay match directo)
def find_number_near_keyword(text: str, keyword: str, window=120) -> Optional[float]:
    for m in re.finditer(re.escape(keyword), text, re.IGNORECASE):
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        fragment = text[start:end]
        nums = re.findall(NUMBER_RE, fragment)
        if nums:
            cand = nums[-1][0] if isinstance(nums[0], tuple) else nums[-1]
            val = clean_number(cand)
            if val is not None:
                return val
    return None

def search_patterns(text: str, patterns: List[str]) -> Optional[float]:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            groups = [g for g in m.groups() if g]
            if groups:
                cand = groups[-1]
                val = clean_number(cand)
                if val is not None:
                    return val
    return None

# ---------------- lógica de extracción por archivo ----------------
def extract_from_text(text: str) -> Dict:
    reasons = []

    # Normalizar texto
    text = re.sub(r"\s+", " ", text)

    # ---------------- COSTO TOTAL ----------------
    costo_total = None

    # Patrones robustos que toleran puntos, guiones y espacios entre etiquetas y montos
    patrones_prioritarios = [
        # Formatos como: Costo total........S/. 700.00  o  Costo total --- S/. 700.00
        r"(?:costo\s*total|total\s*general|importe\s*total|total\s*a\s*pagar|total\s*del\s*proyecto)"
        r"(?:\s*[:\-\.]*\s*)(?:S/?\.?\s*)?([0-9\.,]+)",

        # Formatos como: TOTAL S/. 700.00
        r"(?:TOTAL|COSTO TOTAL)\s*(?:[:\-\.]*\s*)(?:S/?\.?\s*)?([0-9\.,]+)",

        # Formatos con símbolo monetario primero: S/. 700.00 TOTAL
        r"(?:S/|s/|\$)\s*([0-9\.,]+)\s*(?:total|TOTAL|COSTO TOTAL)?"
    ]

    candidatos_totales = []
    for p in patrones_prioritarios:
        for m in re.findall(p, text, re.IGNORECASE):
            val = clean_number(m)
            if val and val >= 100:
                candidatos_totales.append(val)

    if candidatos_totales:
        # Prioriza el valor más grande (suele ser el total final)
        costo_total = max(candidatos_totales)
        reasons.append("costo_por_patron_prioritario")
    else:
        # Si no encontró, probar con la búsqueda por cercanía
        for kw in ["costo total", "total general", "importe total", "TOTAL", "COSTO TOTAL", "total a pagar"]:
            val = find_number_near_keyword(text, kw, window=100)
            if val and val >= 100:
                costo_total = val
                reasons.append(f"costo_cercano_a_{kw}")
                break

    # ---------------- COSTO DE MATERIALES ----------------
    costo_mat = search_patterns(text, MATERIALS_PATTERNS)
    if costo_mat and costo_mat < 100:
        costo_mat = None
    if costo_mat is not None:
        reasons.append("material_por_pattern")
    else:
        for kw in ["costo de materiales", "materiales", "valor materiales"]:
            val = find_number_near_keyword(text, kw)
            if val and val >= 100:
                costo_mat = val
                reasons.append(f"mat_cercano_a_{kw}")
                break

    # ---------------- TIEMPO DE ENTREGA ----------------
    tiempo = search_patterns(text, TIME_PATTERNS)
    if tiempo and tiempo > 365:
        tiempo = None
    if tiempo is not None:
        reasons.append("tiempo_por_pattern")
    else:
        for kw in ["tiempo de entrega", "plazo", "duracion", "días"]:
            val = find_number_near_keyword(text, kw)
            if val and 1 <= val <= 365:
                tiempo = val
                reasons.append(f"tiempo_cercano_a_{kw}")
                break

    # ---------------- VALIDACIÓN FINAL ----------------
    if costo_total is None:
        reasons.append("sin_costo_total")
        return {
            "costoTotal": None,
            "costoMateriales": costo_mat,
            "tiempoEntrega": tiempo,
            "roi": None,
            "ccc": None,
            "icj": None,
            "reasons": reasons
        }

    # Validar coherencia
    if costo_mat and costo_mat > costo_total:
        reasons.append("corrigiendo_material_mayor_que_total")
        costo_mat = None

    # ---------------- CÁLCULOS REALISTAS ----------------
    if costo_total:
        if costo_mat and costo_mat < costo_total:
            ganancia = costo_total - costo_mat
        else:
            if costo_total < 10000:
                margen = 0.25
            elif costo_total < 50000:
                margen = 0.20
            else:
                margen = 0.15
            ganancia = costo_total * margen
    else:
        ganancia = None

    roi = round((ganancia / costo_total) * 100, 2) if (ganancia and costo_total) else None

    if tiempo:
        ccc = round(tiempo + 10, 2)
    else:
        if costo_total and costo_total > 50000:
            ccc = 45
        elif costo_total and costo_total > 10000:
            ccc = 35
        else:
            ccc = 30

    if costo_mat and costo_mat > 0:
        denom = costo_mat + 0.1 * costo_total
        icj = round((ganancia / denom), 2) if denom else None
    else:
        denom = 0.3 * costo_total if costo_total else 1
        icj = round((ganancia / denom), 2) if denom else None

    return {
        "costoTotal": round(costo_total, 2),
        "costoMateriales": round(costo_mat, 2) if costo_mat else None,
        "tiempoEntrega": round(tiempo, 2) if tiempo else None,
        "roi": roi,
        "ccc": ccc,
        "icj": icj,
        "reasons": reasons
    }

# ---------------- tablas en docx: intento de sumar columna "Total" ----------------
def try_extract_from_tables_docx(path: str) -> Optional[float]:
    try:
        doc = docx.Document(path)
        # buscar en tablas una columna cuyo header contenga "total" o "importe"
        for table in doc.tables:
            headers = [cell.text.strip().lower() for cell in table.rows[0].cells]
            total_col_idx = None
            for idx, h in enumerate(headers):
                if "total" in h or "importe" in h or "subtotal" in h:
                    total_col_idx = idx
                    break
            if total_col_idx is not None:
                # sumar la columna (omitir header row)
                s = 0.0
                any_val = False
                for r in table.rows[1:]:
                    txt = r.cells[total_col_idx].text.strip()
                    val = clean_number(txt)
                    if val is not None:
                        s += val
                        any_val = True
                if any_val:
                    return s
    except Exception:
        return None
    return None

# ---------------- main runner ----------------
def run(overwrite: bool = False):
    base = Path(".").resolve()
    data_dir = base / DATA_FOLDER
    if not data_dir.exists():
        print(f"ERROR: No existe carpeta {data_dir}. Crea y coloca tus .docx/.pdf")
        return

    ts = now_ts()
    out_csv = Path(OUT_FOLDER) / f"proformas_dataset_{ts}.csv"
    issues_csv = Path(OUT_FOLDER) / f"proformas_issues_{ts}.csv"

    registros = []
    issues = []

    files = sorted([f for f in os.listdir(data_dir) if f.lower().endswith((".docx", ".pdf"))])
    if not files:
        print("No hay archivos .docx/.pdf en datos_proformas/")
        return

    for f in files:
        path = data_dir / f
        print(f"\n--- Procesando: {f}")
        debug = {"archivo": f, "text_snippet": None, "used_ocr": False, "reasons": [], "candidates": {}}
        text = ""
        used_ocr = False

        try:
            if f.lower().endswith(".docx"):
                # intentar extraer por tablas primero
                table_sum = try_extract_from_tables_docx(str(path))
                text = read_docx_text(str(path))
                debug["text_snippet"] = (text[:800]).replace("\n", " ")
                if table_sum:
                    # si tabla dio un total sensato (mayor que 0), lo usamos como costo_total candidate
                    debug["candidates"]["table_total"] = table_sum
                data = extract_from_text(text)
                # si no encontró costo_total y table_sum existe, usarlo
                if data["costoTotal"] is None and table_sum:
                    print("  > Usando total sumado desde tabla:", table_sum)
                    data = extract_from_text(f"total: {table_sum}\n" + text)
                    data["reasons"].append("usado_total_de_tabla")
            else:
                # pdf
                text, used_ocr = read_pdf_text(str(path))
                debug["used_ocr"] = used_ocr
                debug["text_snippet"] = (text[:800]).replace("\n", " ")
                data = extract_from_text(text)
        except Exception as e:
            print("  ERROR lecturando archivo:", e)
            issues.append({"archivo": f, "issue": f"error_lectura:{e}"})
            continue

        # si data tiene costoTotal None => issue
        if data["costoTotal"] is None:
            issues.append({"archivo": f, "issue": "sin_costo_total", "reasons": data.get("reasons", []) , "snippet": debug["text_snippet"]})
        # Extraer una breve descripción del texto (primeros 400 caracteres)
        descripcion = (text[:400].replace("\n", " ") if text else "")

        # Valor inicial de factibilidad (vacío, lo completarás manualmente después)
        factible = None

        registros.append({
            "archivo": f,
            "descripcion": descripcion,
            "costoTotal": data.get("costoTotal"),
            "costoMateriales": data.get("costoMateriales"),
            "tiempoEntrega": data.get("tiempoEntrega"),
            "roi": data.get("roi"),
            "ccc": data.get("ccc"),
            "icj": data.get("icj"),
            "factible": factible,
            "reasons": ";".join(data.get("reasons", []))
        })

        # guardar debug JSON por archivo para inspección manual
        debug["reasons"] = data.get("reasons", [])
        debug["candidates"].update({
            "costoTotal_candidate": data.get("costoTotal"),
            "costoMateriales_candidate": data.get("costoMateriales"),
            "tiempo_candidate": data.get("tiempoEntrega"),
        })
        debug_path = base / f"debug_{Path(f).stem}.json"
        with open(debug_path, "w", encoding="utf-8") as fh:
            json.dump(debug, fh, ensure_ascii=False, indent=2)

    # guardar csvs (no sobrescribir por defecto)
    df = pd.DataFrame(registros)
    df.to_csv(out_csv, index=False)
    print(f"\nColumnas generadas: {list(df.columns)}")
    print(f"\n✅ Dataset guardado en: {out_csv}")

    if issues:
        df_issues = pd.DataFrame(issues)
        df_issues.to_csv(issues_csv, index=False)
        print(f"⚠️ Issues guardados en: {issues_csv}")
    else:
        print("✅ No se detectaron issues automáticos.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="Sobrescribir archivos de salida (no recomendado)")
    args = parser.parse_args()
    run(overwrite=args.overwrite)
