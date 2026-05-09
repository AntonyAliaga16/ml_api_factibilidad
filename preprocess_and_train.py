import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score

import joblib
# ---------------- CONFIG ----------------
CSV_PATH = "proformas_dataset.csv"
MODEL_OUT = "modelo_factibilidad.pkl"
# ---------------- CARGAR DATASET ----------------
df = pd.read_csv(CSV_PATH)

print("Dataset cargado:")
print(df.head())
# ---------------- VALIDAR COLUMNAS ----------------
required_columns = [
    "costoTotal",
    "costoMateriales",
    "tiempoEntrega",
    "roi",
    "mbb",
    "analisisFactibilidad"
]
for col in required_columns:

    if col not in df.columns:

        raise Exception(
            f"Falta columna requerida: {col}"
        )
# ---------------- MAPEAR ETIQUETAS ----------------
def map_analisis(x):

    if pd.isna(x):
        return 1
    x = str(x).lower()
    # ALTA FACTIBILIDAD
    if (
        "altamente factible" in x
        or "rentable" in x
        or "alta rentabilidad" in x
    ):
        return 2
    # NO FACTIBLE
    if (
        "no factible" in x
        or "alto riesgo" in x
        or "riesgo financiero" in x
    ):
        return 0
    # FACTIBLE INTERMEDIO
    return 1
df["label"] = df["analisisFactibilidad"].apply(
    map_analisis
)
print("\nDistribución labels:")
print(df["label"].value_counts())
# ---------------- FEATURES ----------------
X = df[[
    "costoTotal",
    "costoMateriales",
    "tiempoEntrega",
    "roi",
    "mbb"
]]
y = df["label"]
# ---------------- LIMPIEZA NUMÉRICA ----------------
for col in X.columns:

    X[col] = pd.to_numeric(
        X[col],
        errors="coerce"
    )
# ---------------- IMPUTACIÓN ----------------
imputer = SimpleImputer(
    strategy="mean"
)
X_imputed = imputer.fit_transform(X)
# ---------------- TRAIN TEST SPLIT ----------------
X_train, X_test, y_train, y_test = train_test_split(
    X_imputed,
    y,
    test_size=0.2,
    random_state=42
)
# ---------------- MODELO ----------------
model = RandomForestClassifier(
    n_estimators=200,
    random_state=42
)
model.fit(X_train, y_train)
# ---------------- EVALUACIÓN ----------------
pred = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    pred
)
print("\nPrecisión:")
print(round(accuracy * 100, 2), "%")
print("\nReporte clasificación:\n")
print(
    classification_report(
        y_test,
        pred
    )
)
# ---------------- IMPORTANCIA VARIABLES ----------------
feature_names = [
    "costoTotal",
    "costoMateriales",
    "tiempoEntrega",
    "roi",
    "mbb"
]
importances = model.feature_importances_
print("\n Importancia variables:\n")
for name, importance in zip(
    feature_names,
    importances
):
    print(
        f"{name}: {round(importance * 100, 2)}%"
    )
# ---------------- GUARDAR ----------------
joblib.dump(
    {
        "model": model,
        "imputer": imputer,
        "features": feature_names
    },
    MODEL_OUT
)
print(f"\n Modelo guardado en:")
print(MODEL_OUT)
