"""
completar_indicadores_auto.py
-------------------------------------
Completa ROI y MBB automáticamente
en el dataset más reciente.
"""

import os
import pandas as pd
from datetime import datetime

# LIMPIAR NUMEROS
def clean_number(x):

    if pd.isna(x):
        return None

    if isinstance(x, (int, float)):
        return float(x)

    x = str(x)

    x = (
        x.replace("S/.", "")
         .replace("S/", "")
         .replace("$", "")
         .replace("s/", "")
         .replace(",", "")
         .strip()
    )

    try:
        return float(x)
    except:
        return None


# CALCULAR INDICADORES
def calcular_indicadores(
    costo_total,
    costo_mat=None
):

    if not costo_total or costo_total <= 0:
        return None, None

    # GANANCIA
    ganancia = costo_total - (
        costo_mat if costo_mat else 0
    )

    # ROI
    if costo_mat and costo_mat > 0:
        roi = round(
            (ganancia / costo_mat) * 100,
            2
        )
    else:
        roi = 0

    # MBB
    mbb = round(
        (ganancia / costo_total) * 100,
        2
    )

    return roi, mbb


# BUSCAR DATASET
def buscar_csv_mas_reciente():

    archivos = [
        f for f in os.listdir(".")
        if f.startswith("proformas_dataset_")
        and f.endswith(".csv")
    ]

    if not archivos:
        print("No se encontró dataset.")
        return None

    archivos.sort(
        key=lambda f: os.path.getmtime(f),
        reverse=True
    )

    return archivos[0]


# MAIN
def main():

    archivo = buscar_csv_mas_reciente()

    if not archivo:
        return

    print(f"Usando dataset: {archivo}")

    # LEER CSV
    try:
        df = pd.read_csv(
            archivo,
            sep=";",
            quotechar='"',
            engine="python",
            encoding="utf-8"
        )
    except:
        df = pd.read_csv(
            archivo,
            sep=";",
            quotechar='"',
            engine="python",
            encoding="latin1"
        )

    # SI FALLA SEPARADOR
    if len(df.columns) == 1:
        try:
            df = pd.read_csv(
                archivo,
                sep=",",
                engine="python",
                encoding="latin1"
            )
        except:
            pass

    # ASEGURAR COLUMNAS
    for col in [
        "costoTotal",
        "costoMateriales",
        "roi",
        "mbb"
    ]:
        if col not in df.columns:
            df[col] = None

    # LIMPIEZA
    df["costoTotal"] = (
        df["costoTotal"]
        .apply(clean_number)
    )

    df["costoMateriales"] = (
        df["costoMateriales"]
        .apply(clean_number)
    )

    # CALCULAR
    nuevos_roi = []
    nuevos_mbb = []

    for _, row in df.iterrows():

        if (
            pd.isna(row["roi"])
            or pd.isna(row["mbb"])
        ):

            roi, mbb = calcular_indicadores(
                row["costoTotal"],
                row["costoMateriales"]
            )

        else:
            roi = row["roi"]
            mbb = row["mbb"]

        nuevos_roi.append(roi)
        nuevos_mbb.append(mbb)

    # ACTUALIZAR
    df["roi"] = nuevos_roi
    df["mbb"] = nuevos_mbb

    # ELIMINAR COLUMNAS OBSOLETAS
    columnas_eliminar = []

    for col in ["ccc", "icj"]:

        if col in df.columns:
            columnas_eliminar.append(col)

    if columnas_eliminar:
        df.drop(
            columns=columnas_eliminar,
            inplace=True
        )

    # GUARDAR
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    salida = (
        f"proformas_dataset_completado_"
        f"{timestamp}.csv"
    )

    df.to_csv(
        salida,
        index=False
    )

    print(f"Archivo guardado: {salida}")
    print(f"Filas: {len(df)}")
    print("Proceso completado.")


if __name__ == "__main__":
    main()
