"""
completar_indicadores_auto.py
-------------------------------------
Detecta el dataset más reciente generado por extract_proformas_advanced.py
y completa los indicadores ROI, CCC e ICJ con valores realistas, sin borrar datos previos.

Uso:
  python completar_indicadores_auto.py
"""

import os
import pandas as pd
from datetime import datetime

# -------- Funciones de ayuda --------
def clean_number(x):
    """Convierte valores tipo 'S/. 12,000.50' o '12.000,50' en float."""
    if pd.isna(x):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    x = str(x)
    x = x.replace("S/.", "").replace("S/", "").replace("$", "").replace("s/", "").strip()
    x = x.replace(",", "")
    try:
        return float(x)
    except ValueError:
        return None


def calcular_indicadores(costo_total, costo_mat=None, tiempo=None):
    """Devuelve ROI, CCC e ICJ con valores realistas."""
    if not costo_total or costo_total <= 0:
        return None, None, None

    # --- ROI (Rentabilidad sobre la inversión) ---
    if costo_mat and costo_mat > 0:
        ganancia = costo_total - costo_mat
        roi = round((ganancia/costo_total) * 100, 2)
    else:
        # márgenes realistas según tamaño del proyecto
        if costo_total < 10000:
            roi = 25.0
        elif costo_total < 50000:
            roi = 20.0
        else:
            roi = 15.0

    # --- CCC (Ciclo de Conversión de Caja) ---
    if tiempo and tiempo > 0:
        ccc = round(tiempo + (costo_total / 100000), 2)  # más grande el proyecto, más demora
    else:
        if costo_total < 10000:
            ccc = 30
        elif costo_total < 50000:
            ccc = 35
        else:
            ccc = 45

    # --- ICJ (Índice de Capacidad de Justificación) ---
    if costo_mat and costo_mat > 0:
        ganancia = costo_total - costo_mat
        icj = round(ganancia / (costo_mat + 0.1 * costo_total), 3)
    else:
        ganancia = costo_total * (roi / 100)
        icj = round(ganancia / (0.3 * costo_total), 3)

    return roi, ccc, icj


def buscar_csv_mas_reciente():
    """Busca el archivo CSV de proformas más reciente en la carpeta actual."""
    archivos = [f for f in os.listdir(".") if f.startswith("proformas_dataset_") and f.endswith(".csv")]
    if not archivos:
        print("❌ No se encontró ningún archivo que empiece con 'proformas_dataset_'.")
        return None
    archivos.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    return archivos[0]


# -------- Programa principal --------
def main():
    archivo = buscar_csv_mas_reciente()
    if not archivo:
        return

    print(f"📁 Usando dataset más reciente: {archivo}")

    # Intentar leer CSV con la codificación correcta
    try:
        df = pd.read_csv(archivo, sep=";", quotechar='"', engine="python", encoding="utf-8")
    except Exception:
        print("⚠️ Reintentando lectura con codificación Latin-1...")
        df = pd.read_csv(archivo, sep=";", quotechar='"', engine="python", encoding="latin1")

    # Si por alguna razón no se separaron bien las columnas, intentar con coma
    if len(df.columns) == 1:
        try:
            df = pd.read_csv(archivo, sep=",", quotechar='"', engine="python", encoding="latin1")
        except:
            pass

    # Asegurar columnas
    for col in ["costoTotal", "costoMateriales", "tiempoEntrega", "roi", "ccc", "icj"]:
        if col not in df.columns:
            df[col] = None

    # Limpiar datos numéricos
    df["costoTotal"] = df["costoTotal"].apply(clean_number)
    df["costoMateriales"] = df["costoMateriales"].apply(clean_number)
    df["tiempoEntrega"] = df["tiempoEntrega"].apply(clean_number)

    # Calcular nuevos indicadores solo donde falten
    nuevos_roi, nuevos_ccc, nuevos_icj = [], [], []
    for _, row in df.iterrows():
        if pd.isna(row["roi"]) or pd.isna(row["ccc"]) or pd.isna(row["icj"]):
            roi, ccc, icj = calcular_indicadores(
                row["costoTotal"], row["costoMateriales"], row["tiempoEntrega"]
            )
        else:
            roi, ccc, icj = row["roi"], row["ccc"], row["icj"]

        nuevos_roi.append(roi)
        nuevos_ccc.append(ccc)
        nuevos_icj.append(icj)

    df["roi"] = nuevos_roi
    df["ccc"] = nuevos_ccc
    df["icj"] = nuevos_icj

    # Guardar nuevo archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    salida = f"proformas_dataset_completado_{timestamp}.csv"
    df.to_csv(salida, index=False)
    print(f"✅ Archivo completado guardado como: {salida}")
    print(f"📊 Filas procesadas: {len(df)}")
    print("🏁 Proceso finalizado correctamente.")


if __name__ == "__main__":
    main()
