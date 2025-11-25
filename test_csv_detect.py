import pandas as pd

file = "proformas_dataset_completado_20251028_125401.csv"

# Posibles separadores
separadores = [",", ";", "\t", "|"]

for sep in separadores:
    try:
        df = pd.read_csv(file, sep=sep, encoding="latin-1", on_bad_lines="skip")
        # Considerar válido si detecta más de 3 columnas
        if len(df.columns) > 3:
            print(f"\n✅ Parece funcionar con separador: '{sep}'")
            print(f"🧾 Columnas detectadas: {list(df.columns)}")
            print("\n📊 Primeras 3 filas:")
            print(df.head(3))
            break
    except Exception as e:
        print(f"Error con separador '{sep}': {e}")
