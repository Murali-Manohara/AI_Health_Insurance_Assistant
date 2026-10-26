import joblib
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Insurance Claim Payout Predictor", page_icon="🏥", layout="centered"
)

st.title("🏥 Insurance Claim Payout Prediction App")
st.write(
    "Enter the policy and claim details below to predict the estimated claim"
    " payout amount."
)


@st.cache_resource
def load_model():
  return joblib.load("insurance_claim_model.pkl")


try:
  model = load_model()
  expected_features = model.feature_names_in_
except Exception as e:
  st.error(
      f"Error loading model: {e}. Ensure 'insurance_claim_model.pkl' is in the"
      " same directory."
  )
  st.stop()

with st.form("prediction_form"):
  st.subheader("📋 Policy & Claim Details")

  col1, col2 = st.columns(2)

  with col1:
    age = st.number_input("Policyholder Age", min_value=18, max_value=70, value=45)
    days_hospitalised = st.number_input(
        "Days Hospitalised", min_value=0, max_value=365, value=4
    )
    icu_days = st.number_input("ICU Days", min_value=0, max_value=5, value=1)
    procedures_claimed = st.number_input(
        "Procedures Claimed", min_value=0, max_value=50, value=2
    )
    prior_daycare_claims_year = st.number_input(
        "Prior Daycare Claims (Past Year)", min_value=0, max_value=20, value=0
    )

  with col2:
    extended_stay_flag = st.selectbox(
        "Extended Stay Flag",
        options=[0, 1],
        format_func=lambda x: "Yes (1)" if x == 1 else "No (0)",
    )
    plan = st.selectbox("Plan Type", options=["Basic", "Gold", "Premium"])
    pre_existing = st.selectbox(
        "Pre-existing Condition", options=["yes", "no"]
    )
    claim_type = st.selectbox(
        "Claim Type",
        options=[
            "Hospitalisation",
            "Major surgery",
            "Medical management",
            "Other surgery",
        ],
    )
    documents_complete = st.selectbox(
        "Documents Complete", options=["yes", "no"]
    )

  submitted = st.form_submit_button("Predict Claim Payout 🚀")

if submitted:
  raw_input = pd.DataFrame({
      "age": [age],
      "days_hospitalised": [days_hospitalised],
      "icu_days": [icu_days],
      "procedures_claimed": [procedures_claimed],
      "prior_daycare_claims_year": [prior_daycare_claims_year],
      "extended_stay_flag": [extended_stay_flag],
      "plan": [plan],
      "pre_existing": [pre_existing],
      "claim_type": [claim_type],
      "documents_complete": [documents_complete],
  })

  encoded_input = pd.get_dummies(raw_input)
  final_input = encoded_input.reindex(columns=expected_features, fill_value=0)

  prediction = model.predict(final_input)[0]

  st.success("Prediction Generated Successfully!")
  st.metric(
      label="Estimated Claim Payout", value=f"₹{max(0, prediction):,.2f}"
  )