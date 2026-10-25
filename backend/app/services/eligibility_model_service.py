"""
EligibilityModelService
Wraps the authentic Gradient Boosting model package from 'eligibility_model_package'.
Loads eligibility_model.pkl and model_info.json once via a thread-safe singleton,
validates inputs strictly according to the documented feature contract,
calculates BMI, and executes ML inference using predict() and predict_proba().
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import pandas as pd
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("eligibility_model")

# Authoritative path to the model package located in project root
PACKAGE_DIR = Path(__file__).resolve().parents[3] / "eligibility_model_package"


class ApplicantEvaluationInput(BaseModel):
    """
    Applicant data contract derived strictly from eligibility_model_package/model_info.json.
    """
    age: int = Field(..., ge=18, le=100, description="Applicant age between 18 and 100")
    height_cm: float = Field(..., ge=100, le=250, description="Height in centimeters between 100 and 250")
    weight_kg: float = Field(..., ge=20, le=300, description="Weight in kilograms between 20 and 300")
    smoker: str = Field(..., description="'Yes' or 'No'")
    alcoholic: str = Field(..., description="'Yes' or 'No'")
    pre_existing_condition: str = Field(..., description="Allowed condition category from model_info.json")

    @field_validator("smoker", "alcoholic")
    @classmethod
    def validate_yes_no(cls, v: str) -> str:
        cleaned = str(v).strip().capitalize()
        if cleaned not in ("Yes", "No"):
            raise ValueError(f"Value must be 'Yes' or 'No', got '{v}'")
        return cleaned

    @field_validator("pre_existing_condition")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        # Match case-insensitively to the authoritative condition list
        allowed_map = {
            "diabetes": "Diabetes",
            "heart_disease": "Heart_Disease",
            "heart disease": "Heart_Disease",
            "hypertension": "Hypertension",
            "multiple": "Multiple",
            "none": "None",
            "not sure": "Not sure",
            "other condition": "Other condition",
            "other": "Other condition",
            "thyroid_disorder": "Thyroid_Disorder",
            "thyroid disorder": "Thyroid_Disorder",
        }
        key = str(v).strip().lower()
        if key not in allowed_map:
            raise ValueError(
                f"pre_existing_condition must be one of: Diabetes, Heart_Disease, Hypertension, "
                f"Multiple, None, Not sure, Other condition, Thyroid_Disorder. Got '{v}'"
            )
        return allowed_map[key]


class EligibilityModelResult(BaseModel):
    outcome: str  # "ELIGIBLE" | "INELIGIBLE"
    status: str = "COMPLETED"
    probability_eligible: float
    bmi: float
    qualifying_plans: List[str]
    reason_codes: List[str]
    model_id: str
    model_version: str
    review_status: str
    explanation: str
    input_summary: Dict[str, Any]


class EligibilityModelService:
    """
    Singleton service managing the machine learning eligibility model.
    """
    _instance: Optional["EligibilityModelService"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._info = None
        self._feature_columns = None
        self._conditions_map = None
        self._load_lock = threading.Lock()
        self._is_loaded = False

    @classmethod
    def get_instance(cls) -> "EligibilityModelService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_model_loaded(self) -> None:
        """Loads the model and info metadata once safely into memory."""
        if self._is_loaded:
            return

        with self._load_lock:
            if self._is_loaded:
                return

            model_path = PACKAGE_DIR / "eligibility_model.pkl"
            info_path = PACKAGE_DIR / "model_info.json"

            if not model_path.exists():
                raise FileNotFoundError(f"Model artifact not found at: {model_path}")
            if not info_path.exists():
                raise FileNotFoundError(f"Model metadata not found at: {info_path}")

            logger.info(f"Loading eligibility model artifact from: {model_path}")
            try:
                self._model = joblib.load(str(model_path))
                with open(info_path, "r", encoding="utf-8") as f:
                    self._info = json.load(f)

                self._feature_columns = self._info.get("feature_columns", [
                    "age", "bmi", "smoker", "alcoholic", "pre_existing_condition"
                ])
                allowed_conditions = self._info["allowed_values"]["pre_existing_condition"]
                self._conditions_map = {c.lower(): c for c in allowed_conditions}
                self._is_loaded = True
                logger.info("Eligibility model and metadata loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load eligibility model: {e}")
                raise RuntimeError(f"Eligibility model initialization failed: {e}")

    def is_ready(self) -> bool:
        """Health check verifying model readiness."""
        try:
            self._ensure_model_loaded()
            return self._is_loaded and self._model is not None
        except Exception:
            return False

    def get_metadata(self) -> Dict[str, Any]:
        self._ensure_model_loaded()
        return self._info or {}

    @staticmethod
    def calculate_bmi(height_cm: float, weight_kg: float) -> float:
        """Calculates BMI using the authoritative formula: weight_kg / (height_cm / 100) ** 2."""
        return round(weight_kg / ((height_cm / 100.0) ** 2), 2)

    def evaluate(
        self,
        applicant: ApplicantEvaluationInput,
        user_role: str = "customer"
    ) -> EligibilityModelResult:
        """
        Executes inference against the loaded Gradient Boosting model pipeline.
        Enforces server-side feature ordering, BMI calculation, and role-based plan scoping.
        """
        self._ensure_model_loaded()

        # 1. Compute BMI
        bmi = self.calculate_bmi(applicant.height_cm, applicant.weight_kg)

        # 2. Construct input row strictly matching feature_columns order
        input_dict = {
            "age": applicant.age,
            "bmi": bmi,
            "smoker": applicant.smoker,
            "alcoholic": applicant.alcoholic,
            "pre_existing_condition": applicant.pre_existing_condition,
        }
        df_row = pd.DataFrame([input_dict])[self._feature_columns]

        # 3. Model Inference
        try:
            pred_label = int(self._model.predict(df_row)[0])
            pred_proba = float(self._model.predict_proba(df_row)[0, 1])
        except Exception as e:
            logger.error(f"Inference failure for applicant data: {e}")
            raise RuntimeError(f"Model prediction failed: {e}")

        # 4. Map binary class to human-readable eligibility outcome
        outcome = "ELIGIBLE" if pred_label == 1 else "INELIGIBLE"
        probability = round(pred_proba, 4)

        # 5. Role-based qualifying plans
        qualifying_plans = []
        if outcome == "ELIGIBLE":
            if user_role == "employee":
                qualifying_plans = ["EMP-INS-001", "HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001"]
            else:
                qualifying_plans = ["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001"]

        # 6. Build factual, grounded reason codes
        reason_codes = []
        reason_codes.append(f"OUTCOME_{outcome}")
        reason_codes.append(f"MODEL_PROBABILITY_{probability}")

        if bmi < 18.5:
            reason_codes.append("BMI_UNDERWEIGHT")
        elif bmi < 25.0:
            reason_codes.append("BMI_NORMAL")
        elif bmi < 30.0:
            reason_codes.append("BMI_OVERWEIGHT")
        else:
            reason_codes.append("BMI_OBESE")

        reason_codes.append(f"SMOKER_{applicant.smoker.upper()}")
        reason_codes.append(f"ALCOHOL_{applicant.alcoholic.upper()}")
        reason_codes.append(f"CONDITION_{applicant.pre_existing_condition.upper().replace(' ', '_')}")

        # Review status: Flag if borderline probability (0.45 <= p <= 0.55) or condition is 'Not sure'
        if 0.45 <= probability <= 0.55 or applicant.pre_existing_condition == "Not sure":
            review_status = "NEEDS_REVIEW"
        else:
            review_status = "NONE"

        # 7. Generate concise factual baseline explanation
        cond_text = f"None reported" if applicant.pre_existing_condition == "None" else applicant.pre_existing_condition
        if outcome == "ELIGIBLE":
            explanation = (
                f"Applicant meets underwriting standards with an eligibility confidence of {round(probability * 100, 1)}%. "
                f"Body Mass Index (BMI) is {bmi}. Smoker: {applicant.smoker}, Alcohol: {applicant.alcoholic}, Pre-existing condition: {cond_text}. "
                f"Qualified for {len(qualifying_plans)} policy tiers."
            )
        else:
            explanation = (
                f"Underwriting evaluation concluded with an ineligible determination (confidence {round(probability * 100, 1)}%). "
                f"Evaluated factors include BMI of {bmi}, tobacco usage ({applicant.smoker}), alcohol consumption ({applicant.alcoholic}), "
                f"and condition profile ({cond_text}). A licensed insurance agent is available to discuss options."
            )

        return EligibilityModelResult(
            outcome=outcome,
            status="COMPLETED",
            probability_eligible=probability,
            bmi=bmi,
            qualifying_plans=qualifying_plans,
            reason_codes=reason_codes,
            model_id=self._info.get("model_name", "Gradient Boosting"),
            model_version=self._info.get("library_versions", {}).get("scikit-learn", "1.6.1"),
            review_status=review_status,
            explanation=explanation,
            input_summary={
                "age": applicant.age,
                "height_cm": applicant.height_cm,
                "weight_kg": applicant.weight_kg,
                "bmi": bmi,
                "smoker": applicant.smoker,
                "alcoholic": applicant.alcoholic,
                "pre_existing_condition": applicant.pre_existing_condition
            }
        )


# Singleton accessor
eligibility_model_service = EligibilityModelService.get_instance()
