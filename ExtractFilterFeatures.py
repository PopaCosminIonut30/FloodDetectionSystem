
import os
import h5py
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb

# === CONFIG ===
INPUT_FOLDER = "C:/Users/popac/PycharmProjects/PythonProject1/Data"
OUTPUT_CSV = "processed_data_for_prediction.csv"
FLOOD_MODEL_PATH = "C:/Users/popac/PycharmProjects/PythonProject1/flood_model.pkl"
DROUGHT_MODEL_PATH = "C:/Users/popac/PycharmProjects/PythonProject1/drought_model.pkl"

FEATURES = [
    "NDVI", "NDWI", "NDMI",
    "VV Band", "VH Band",
    "Water Percentage", "Water Distance",
    "Dry Percentage", "Drought Mask", "SAR Urban Mask"
]
STATS = ["mean", "std", "min", "max"]

# === HELPERS ===
def summarize(data):
    flat = data.flatten()
    flat = flat[~np.isnan(flat)]
    if flat.size == 0:
        return {s: np.nan for s in STATS}
    return {
        "mean": np.mean(flat),
        "std": np.std(flat),
        "min": np.min(flat),
        "max": np.max(flat)
    }

def extract_features_from_file(file_path):
    row = {
        "label": -1
    }
    filename = os.path.basename(file_path)
    try:
        date_str, lat_str, lon_str = filename.split("_")[1:4]
        row["year"] = int(date_str.split("-")[0])
        row["lat"] = round(float(lat_str), 5)
        row["lon"] = round(float(lon_str), 5)
    except:
        print(f"⚠️ Skipping bad filename: {filename}")
        return None

    try:
        with h5py.File(file_path, 'r') as f:
            for feat in FEATURES:
                if feat in f["Satellite Data"]:
                    data = np.array(f["Satellite Data"][feat])
                    stats = summarize(data)
                    for stat_name, val in stats.items():
                        row[f"single_{feat.replace(' ', '_')}_{stat_name}"] = val
    except Exception as e:
        print(f"❌ Failed to process {filename}: {e}")
        return None

    return row

def preprocess(df):
    df = df.dropna(axis=1, thresh=len(df) * 0.5)
    df = df.fillna(df.median(numeric_only=True))
    df["lat_rounded"] = df["lat"].round(3)
    df["lon_rounded"] = df["lon"].round(3)
    return df

# === STEP 1: EXTRACT + PREPROCESS ===
print("\n Extracting and preprocessing features...")
all_rows = []
for fname in os.listdir(INPUT_FOLDER):
    if fname.endswith(".h5"):
        row = extract_features_from_file(os.path.join(INPUT_FOLDER, fname))
        if row:
            all_rows.append(row)

df = pd.DataFrame(all_rows)
df = preprocess(df)
df.to_csv(OUTPUT_CSV, index=False)
print(f" Saved preprocessed data to: {OUTPUT_CSV}")

# === STEP 2: LOAD MODELS ===
print("\n Loading models...")
flood_model = joblib.load(FLOOD_MODEL_PATH)
drought_model = joblib.load(DROUGHT_MODEL_PATH)

# === STEP 3: FLOOD PREDICTION ===
print("\n Predicting flood risk...")
flood_features = flood_model.get_booster().feature_names
X_flood = df.reindex(columns=flood_features, fill_value=0)
df["flood_predicted_label"] = flood_model.predict(X_flood)
df["flood_probability"] = flood_model.predict_proba(X_flood)[:, 1]

# === STEP 4: DROUGHT PREDICTION ===
print("\n Predicting drought risk...")
drought_features = drought_model.get_booster().feature_names
X_drought = df.reindex(columns=drought_features, fill_value=0)
df["drought_predicted_label"] = drought_model.predict(X_drought)
df["drought_probability"] = drought_model.predict_proba(X_drought)[:, 1]

# === STEP 5: SAVE EVERYTHING ===
# df.to_csv(OUTPUT_CSV, index=False)
# print(f"\n✅ Final results saved to: {OUTPUT_CSV}")

print("\n Prediction Preview:")
print(df[["lat", "lon", "flood_predicted_label", "flood_probability", "drought_predicted_label", "drought_probability"]].to_string(index=False))
