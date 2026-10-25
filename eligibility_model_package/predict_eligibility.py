# predict_eligibility.py
# Load the saved model and predict insurance eligibility.
# Keep this file, eligibility_model.pkl and model_info.json in the same folder.

import json
import os

import joblib
import pandas as pd

FOLDER = os.path.dirname(os.path.abspath(__file__))
MODEL = joblib.load(os.path.join(FOLDER, "eligibility_model.pkl"))
with open(os.path.join(FOLDER, "model_info.json")) as f:
    INFO = json.load(f)

CONDITIONS = {name.lower(): name for name in INFO["allowed_values"]["pre_existing_condition"]}


def calculate_bmi(height_cm, weight_kg):
    return round(weight_kg / (height_cm / 100) ** 2, 2)


def predict_eligibility(age, height_cm, weight_kg, smoker, alcoholic, pre_existing_condition):
    # ---- check the inputs ----
    if not 18 <= age <= 100:
        raise ValueError("age must be between 18 and 100")
    if not 100 <= height_cm <= 250:
        raise ValueError("height_cm must be between 100 and 250")
    if not 20 <= weight_kg <= 300:
        raise ValueError("weight_kg must be between 20 and 300")

    smoker = str(smoker).strip().capitalize()
    alcoholic = str(alcoholic).strip().capitalize()
    if smoker not in ("Yes", "No"):
        raise ValueError("smoker must be Yes or No")
    if alcoholic not in ("Yes", "No"):
        raise ValueError("alcoholic must be Yes or No")

    condition = CONDITIONS.get(str(pre_existing_condition).strip().lower())
    if condition is None:
        raise ValueError("pre_existing_condition must be one of: " + ", ".join(CONDITIONS.values()))

    # ---- build the model input (BMI is calculated here) ----
    bmi = calculate_bmi(height_cm, weight_kg)
    row = pd.DataFrame([{
        "age": age,
        "bmi": bmi,
        "smoker": smoker,
        "alcoholic": alcoholic,
        "pre_existing_condition": condition,
    }])[INFO["feature_columns"]]

    # ---- predict ----
    label = int(MODEL.predict(row)[0])
    probability = float(MODEL.predict_proba(row)[0, 1])
    return {
        "eligible": "Yes" if label == 1 else "No",
        "probability_eligible": round(probability, 4),
        "bmi": bmi,
    }


if __name__ == "__main__":
    print(predict_eligibility(28, 172, 68, "No", "No", "None"))
    print(predict_eligibility(45, 165, 82, "No", "Yes", "Hypertension"))
    print(predict_eligibility(62, 170, 95, "Yes", "Yes", "Heart_Disease"))
