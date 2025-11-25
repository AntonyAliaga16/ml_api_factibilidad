"""
train_model.py
---------------------------------
Entrena un modelo de machine learning usando el dataset de proformas.
Predice si una proforma es factible según los indicadores.

Uso:
  python train_model.py
"""

import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

def buscar_csv_mas_reciente():
    archivos = [f for f in os.listdir(".") if f.startswith("proformas_dataset_completado_") and f.endswith(".csv")]
    if not archivos:
        print("❌ No se encontró ningún archivo 'proformas_dataset_completado_'.")
        return None
    archivos.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    return archivos[0]

def main():
    archivo = buscar_csv_mas_reciente()
    if not archivo:
        return

    print(f"Usando dataset: {archivo}")
    # Leer con separador correcto
    df = pd.read_csv(archivo, sep=";", encoding="latin-1", on_bad_lines="skip")

    # Asegurar columnas necesarias
    columnas_necesarias = ["costoTotal", "costoMateriales", "tiempoEntrega", "roi", "ccc", "icj", "factible"]
    for col in columnas_necesarias:
        if col not in df.columns:
            print(f"⚠️ Falta columna: {col}, se crea vacía.")
            df[col] = None

    # Convertir a numérico
    for col in ["costoTotal", "costoMateriales", "tiempoEntrega", "roi", "ccc", "icj"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Quitar filas sin factible
    df = df.dropna(subset=["factible"])
    df = df.fillna(0)

    X = df[["costoTotal", "costoMateriales", "tiempoEntrega", "roi", "ccc", "icj"]]
    y = df["factible"].astype(int)

    # Dividir datos
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Entrenar modelo
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluar
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n✅ Precisión del modelo: {acc*100:.2f}%")
    print("\n📋 Reporte de clasificación:\n", classification_report(y_test, y_pred))

    # Guardar modelo
    joblib.dump(model, "modelo_factibilidad.pkl")
    print("\n💾 Modelo guardado como: modelo_factibilidad.pkl")

if __name__ == "__main__":
    main()
