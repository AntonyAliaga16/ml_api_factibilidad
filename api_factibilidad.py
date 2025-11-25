from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)

obj = joblib.load("modelo_factibilidad.pkl")
model = obj["model"]
imputer = obj["imputer"]

labels = {
    0: "Proyecto no factible o de alto riesgo.",
    1: "Proyecto factible, requiere control financiero.",
    2: "Proyecto altamente factible y rentable."
}

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    roi = float(data.get("roi", 0))
    ccc = float(data.get("ccc", 0))
    icj = float(data.get("icj", 0))

    X = np.array([[roi, ccc, icj]])
    X = imputer.transform(X)
    pred = model.predict(X)[0]

    return jsonify({
        "prediccion": labels[pred],
        "roi": roi,
        "ccc": ccc,
        "icj": icj
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
