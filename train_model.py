"""
train_model.py
---------------------------------
Entrena modelo ML para evaluar factibilidad de proformas.
Uso:
  python train_model.py
"""
import os
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    accuracy_score
)
# ARCHIVOS
MODEL_OUT = "modelo_factibilidad.pkl"
# BUSCAR CSV MÁS RECIENTE
def buscar_csv_mas_reciente():
    archivos = [
        f for f in os.listdir(".")
        if f.startswith("proformas_dataset")
        and f.endswith(".csv")
    ]
    if not archivos:
        print("No se encontró dataset")
        return None
    archivos.sort(
        key=lambda f: os.path.getmtime(f),
        reverse=True
    )
    return archivos[0]
# MAPEAR FACTIBILIDAD
def map_factible(x):
    if pd.isna(x):
        return 1
    x = str(x).lower()
    if (
        "altamente" in x
        or "rentable" in x
        or "muy factible" in x
    ):
        return 2
    if (
        "factible" in x
        or "observaciones" in x
        or "moderado" in x
    ):
        return 1
    if (
        "no factible" in x
        or "riesgo" in x
    ):
        return 0
    return 1
# MAIN
def main():
    archivo = buscar_csv_mas_reciente()
    if not archivo:
        return
    print(f" Dataset usado: {archivo}")
    # LEER CSV
    try:
        df = pd.read_csv(
            archivo,
            sep=",",
            encoding="latin-1",
            on_bad_lines="skip"
        )
    except:
        df = pd.read_csv(
            archivo,
            sep=";",
            encoding="latin-1",
            on_bad_lines="skip"
        )
    print(f" Registros cargados: {len(df)}")
    # COLUMNAS NECESARIAS
    columnas = [
        "costoTotal",
        "costoMateriales",
        "tiempoEntrega",
        "roi",
        "mbb"
    ]
    for col in columnas:
        if col not in df.columns:
            print(f" Falta columna: {col}")
            df[col] = 0
    # CREAR LABEL
    if "factible" in df.columns:
        y = df["factible"]
    elif "analisis" in df.columns:
        y = df["analisis"].apply(map_factible)
    elif "analisisFactibilidad" in df.columns:
        y = df["analisisFactibilidad"].apply(
            map_factible
        )
    else:
        print(
            " No existe columna de factibilidad."
        )
        print(
            "Se generarán etiquetas automáticas."
        )
        def generar_label(row):
            roi = row["roi"]
            mbb = row["mbb"]
            if roi >= 25 and mbb >= 25:
                return 2
            elif roi >= 10 and mbb >= 10:
                return 1
            return 0
        y = df.apply(generar_label, axis=1)
    # LIMPIAR NUMÉRICOS
    for col in columnas:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )
    df = df.fillna(0)
    # FEATURES
    X = df[columnas]
    # SPLIT
    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42
        )
    )
    # MODELO
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42
    )
    # ENTRENAR
    model.fit(X_train, y_train)
    # PREDICCIONES
    y_pred = model.predict(X_test)
    # MÉTRICAS
    acc = accuracy_score(y_test, y_pred)
    print(
        f"\n Precisión: {acc * 100:.2f}%"
    )
    print("\n Reporte:")
    print(
        classification_report(
            y_test,
            y_pred
        )
    )
    # IMPORTANCIA VARIABLES
    print("\n Importancia variables:")
    importancia = pd.DataFrame({
        "Variable": columnas,
        "Importancia": model.feature_importances_
    })
    importancia = importancia.sort_values(
        by="Importancia",
        ascending=False
    )
    print(importancia)
    # GUARDAR
    joblib.dump(model, MODEL_OUT)
    print(
        f"\n Modelo guardado en: {MODEL_OUT}"
    )
# RUN
if __name__ == "__main__":
    main()
  
