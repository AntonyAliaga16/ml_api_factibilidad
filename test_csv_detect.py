# test_csv_detect.py
import os
import pandas as pd
# Buscar automáticamente el CSV más reciente
def buscar_csv():
    archivos = [
        f for f in os.listdir(".")
        if f.startswith("proformas_dataset")
        and f.endswith(".csv")
    ]
    if not archivos:
        return None
    archivos.sort(
        key=lambda x: os.path.getmtime(x),
        reverse=True
    )
    return archivos[0]
archivo = buscar_csv()
if not archivo:
    print(" No se encontró ningún CSV")
    exit()
print(f" Archivo detectado: {archivo}")
# Posibles separadores
separadores = [",", ";", "\t", "|"]
dataset_ok = False
for sep in separadores:
    try:
        df = pd.read_csv(
            archivo,
            sep=sep,
            encoding="latin-1",
            on_bad_lines="skip"
        )
        # Validar columnas mínimas esperadas
        columnas_necesarias = [
            "costoTotal",
            "costoMateriales",
            "roi",
            "mbb"
        ]
        columnas_encontradas = list(df.columns)
        coincidencias = sum(
            1 for c in columnas_necesarias
            if c in columnas_encontradas
        )
        # Considerar válido si encuentra varias columnas importantes
        if coincidencias >= 2:
            dataset_ok = True
            print(f"\n Separador correcto detectado: '{sep}'")
            print("\n Columnas:")
            print(columnas_encontradas)
            print("\n Primeras filas:")
            print(df.head(3))
            print("\n Tipos de datos:")
            print(df.dtypes)
            print(f"\n Total registros: {len(df)}")
            # Valores nulos
            print("\n Valores nulos:")
            print(df.isnull().sum())
            break
    except Exception as e:
        print(f" Error con separador '{sep}': {e}")
if not dataset_ok:
    print("\n No se pudo detectar correctamente el formato del CSV")
    
