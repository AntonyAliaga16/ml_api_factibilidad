# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import os

MODEL_PATH = "modelo_factibilidad.pkl"

app = Flask(__name__)
CORS(app)

# CARGAR MODELO
model = None

try:
    model = joblib.load(MODEL_PATH)
    print(f"Modelo cargado desde {MODEL_PATH}")
except Exception as e:
    print(f"No se pudo cargar modelo: {e}")
    model = None

# HOME
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "API Factibilidad funcionando",
        "endpoints": {
            "/ping": "GET",
            "/predict": "POST"
        }
    })

# PING
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "pong"})

# PREDICCION
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json() or {}
    try:
        costoTotal = float(data.get("costoTotal", 0))
        costoMateriales = float(data.get("costoMateriales", 0))
        tiempoEntrega = float(data.get("tiempoEntrega", 0))
    except Exception as e:
        return jsonify({
            "error": "Campos inválidos",
            "detail": str(e)
        }), 400

    # CALCULOS REALES
    ganancia = costoTotal - costoMateriales
    roi = (
        (ganancia / costoMateriales) * 100
        if costoMateriales > 0 else 0
    )
    mbb = (
        (ganancia / costoTotal) * 100
        if costoTotal > 0 else 0
    )

    # MACHINE LEARNING
    pred = None
    prob = None

    if model is not None:
        try:
            # FEATURES PARA ML
            features = np.array([
                costoTotal,
                costoMateriales,
                tiempoEntrega,
                roi,
                mbb
            ]).reshape(1, -1)
            pred = int(model.predict(features)[0])
            try:
                prob = model.predict_proba(features)[0].tolist()
            except:
                prob = None
        except Exception as e:
            print(" Error ML:", e)

    # ANALISIS
    if pred == 1:
        analisis = (
            "Proyecto factible según el modelo de Machine Learning."
        )
    elif pred == 0:
        analisis = (
            "Proyecto con riesgo financiero u operativo."
        )
    else:
        # fallback reglas simples
        if roi >= 25 and mbb >= 25:
            analisis = (
                "Altamente factible y rentable."
            )
        elif roi >= 12 and mbb >= 10:
            analisis = (
                "Factible con observaciones."
            )
        elif roi >= 5:
            analisis = (
                "Riesgo moderado."
            )
        else:
            analisis = (
                "No factible."
            )

    # RESPUESTA FINAL
    return jsonify({

        "source": "model" if pred is not None else "rules",

        # RESULTADOS FINANCIEROS
        "roi": round(roi, 2),
        "mbb": round(mbb, 2),

        # IA
        "factible": pred,
        "probabilidad": prob,

        # TEXTO
        "analisis": analisis,

        # INPUTS
        "input": {
            "costoTotal": costoTotal,
            "costoMateriales": costoMateriales,
            "tiempoEntrega": tiempoEntrega
        }
    })
# RUN
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
