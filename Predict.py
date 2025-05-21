import pandas as pd
import joblib
import os

# === LOAD MODEL ===
model_path = os.path.join("Model", "flood_model.pkl")
model = joblib.load(model_path)

# === LOAD NEW DATA ===
csv_path = os.path.join("Model", "processed_data_for_prediction.csv")
df = pd.read_csv(csv_path)

# === FIX FEATURE MISMATCH ===
model_features = model.get_booster().feature_names
X = df.reindex(columns=model_features, fill_value=0)  

# === PREDICT ===
df["predicted_label"] = model.predict(X)
df["flood_probability"] = model.predict_proba(X)[:, 1]

# === PRINT PREVIEW ===
print("\n PREDICTIONS:")
print(df[["year", "lat", "lon", "predicted_label", "flood_probability"]].to_string(index=False))

# === SAVE TO CSV ===
output_path = os.path.join("Model", "processed_data_for_prediction.csv")
df.to_csv(output_path, index=False)
print(f"\n✅ Predictions saved to: {output_path}")
