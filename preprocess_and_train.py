import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
import joblib
from sklearn.metrics import classification_report

CSV_PATH = "proformas_dataset.csv"
MODEL_OUT = "modelo_factibilidad.pkl"

# Cargar dataset
df = pd.read_csv(CSV_PATH)

# Convertir texto de factibilidad a etiquetas numéricas
def map_analisis(x):
    if pd.isna(x): return 1
    x = str(x).lower()
    if "altamente" in x or "rentable" in x: return 2
    if "requiere" in x or "control" in x: return 1
    if "no factible" in x or "alto riesgo" in x: return 0
    return 1

df["label"] = df["analisisFactibilidad"].apply(map_analisis)
X = df[["roi", "ccc", "icj"]]
y = df["label"]

# Imputar valores faltantes
imputer = SimpleImputer(strategy="mean")
X_imputed = imputer.fit_transform(X)

# Entrenar modelo
X_train, X_test, y_train, y_test = train_test_split(X_imputed, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# Evaluación
pred = model.predict(X_test)
print("✅ Precisión:", model.score(X_test, y_test))
print("📊 Reporte de clasificación:\n", classification_report(y_test, pred))

# Guardar modelo entrenado
joblib.dump({"model": model, "imputer": imputer}, MODEL_OUT)
print(f"💾 Modelo guardado en: {MODEL_OUT}")
