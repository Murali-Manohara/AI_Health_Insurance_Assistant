Health Insurance Eligibility Model
==================================

1. Install the libraries:   pip install -r requirements.txt
2. Copy this whole folder into your project.
3. Use it in Python:

       from predict_eligibility import predict_eligibility
       result = predict_eligibility(age=35, height_cm=170, weight_kg=70,
                                    smoker='No', alcoholic='No',
                                    pre_existing_condition='None')
       print(result)   # {'eligible': 'Yes', 'probability_eligible': 0.99, 'bmi': 24.22}

Valid pre_existing_condition values: see model_info.json -> allowed_values
Model scores and library versions:   see model_info.json
