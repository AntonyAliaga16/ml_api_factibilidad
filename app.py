# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import os

MODEL_PATH = "modelo_factibilidad.pkl"

app = Flask(__name__)
CORS(app)  # permite llamadas desde tu app móvil

# Cargar modelo (si existe)
model = None
try:
    model = joblib.load(MODEL_PATH)
    print(f"✅ Modelo cargado desde {MODEL_PATH}")
except Exception as e:
    print(f"⚠️ No se pudo cargar el modelo: {e}")
    model = None

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "API de predicción de factibilidad lista 🚀",
        "endpoints": {
            "/ping": "GET",
            "/predict": "POST JSON {costoTotal,costoMateriales,tiempoEntrega,roi,ccc,icj}"
        }
    })

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "pong"})

@app.route("/predict", methods=["POST"])
def predict():
    # Si no hay modelo, devolvemos simulación razonable (fallback)
    data = request.get_json() or {}
    try:
        costoTotal = float(data.get("costoTotal", 0))
        costoMateriales = float(data.get("costoMateriales", 0))
        tiempoEntrega = float(data.get("tiempoEntrega", 0))
    except Exception as e:
        return jsonify({"error": "Campos numéricos inválidos", "detail": str(e)}), 400

    # Si modelo disponible, intentar predecir — en tu caso el modelo puede devolver factible/prob etc.
    if model is not None:
        try:
            features = np.array([
                costoTotal,
                costoMateriales,
                tiempoEntrega,
                float(data.get("roi", 0)),
                float(data.get("ccc", 0)),
                float(data.get("icj", 0))
            ]).reshape(1, -1)

            pred = None
            prob = None
            try:
                pred = int(model.predict(features)[0])
            except Exception:
                pred = None
            try:
                prob = model.predict_proba(features)[0].tolist()
            except Exception:
                prob = None

            # Aquí puedes transformar la predicción en texto / indicadores; por ahora devolvemos pred + prob
            return jsonify({
                "source": "model",
                "factible": pred,
                "probabilidad": prob,
                "input": {"costoTotal": costoTotal, "costoMateriales": costoMateriales, "tiempoEntrega": tiempoEntrega}
            })
        except Exception as e:
            # si algo falla en modelo, caemos a fallback
            print("Error al predecir con modelo:", e)

    # Fallback: generar indicadores simples y un análisis basado en reglas
    roi_sim = 100 * ((costoTotal - costoMateriales) / (costoMateriales if costoMateriales > 0 else max(1, costoTotal)))
    ccc_sim = tiempoEntrega * 1.5
    icj_sim = (costoTotal - costoMateriales) / (costoTotal if costoTotal > 0 else 1)

    # Reglas simples para el texto (ajusta como quieras)
    if roi_sim >= 25 and icj_sim >= 1.25 and ccc_sim < 45:
        analisis = "Altamente factible: retorno alto, buena competitividad y ciclo de caja rápido."
    elif roi_sim >= 12 and icj_sim >= 1.10:
        analisis = "Factible con observaciones: positivo pero revisar costos/plazos."
    elif roi_sim >= 5 and icj_sim >= 1.0:
        analisis = "Riesgo moderado: viable, puede optimizarse."
    else:
        analisis = "No factible: pérdidas potenciales o competitividad insuficiente."

    return jsonify({
        "source": "simulated",
        "roi": round(roi_sim, 2),
        "ccc": round(ccc_sim, 2),
        "icj": round(icj_sim, 2),
        "analisis": analisis,
        "input": {"costoTotal": costoTotal, "costoMateriales": costoMateriales, "tiempoEntrega": tiempoEntrega}
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
