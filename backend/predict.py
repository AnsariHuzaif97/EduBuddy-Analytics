import sys
import os

from inference import predict_student

def analyze_student(student_input):
    # Base prediction
    result = predict_student(student_input)
    prob = result["success_probability"]
    prediction = result["prediction"]
    
    # Current Behavior
    current_behavior = {
        "active_days": student_input.get("active_days", 0),
        "total_clicks": student_input.get("total_clicks", 0),
        "avg_assignment_score": student_input.get("avg_assignment_score", 0)
    }
    
    # Target Behavior
    target_behavior = {
        "active_days": 89,
        "total_clicks": 1607,
        "avg_assignment_score": 79.8
    }
    
    improvement_needed = {
        "extra_days": max(0, round(target_behavior["active_days"] - current_behavior["active_days"])),
        "extra_clicks": max(0, round(target_behavior["total_clicks"] - current_behavior["total_clicks"])),
        "marks_improvement": max(0, round(target_behavior["avg_assignment_score"] - current_behavior["avg_assignment_score"], 1))
    }
    
    # Calculate Weekly Plan
    module_length = student_input.get("module_presentation_length", 268)
    activity_span = student_input.get("activity_span", 0)
    remaining_days = max(1, module_length - activity_span)
    remaining_weeks = max(1, round(remaining_days / 7))
    
    weekly_plan = {}
    if improvement_needed["extra_days"] > 0:
        weekly_plan["days_per_week"] = max(1, round(improvement_needed["extra_days"] / remaining_weeks))
    if improvement_needed["extra_clicks"] > 0:
        weekly_plan["clicks_per_week"] = max(1, round(improvement_needed["extra_clicks"] / remaining_weeks))
    
    if prob > 0.75:
        risk = "Low"
    elif prob > 0.4:
        risk = "Moderate"
    else:
        risk = "High"
        
    simulation = {}
    
    def simulate_change(feature):
        temp_input = student_input.copy()
        current = student_input.get(feature, 0)
        target = target_behavior.get(feature, current)
        
        gap = max(0, target - current)
        step = max(1, gap) # Jump directly to target to show real impact!
        
        new_value = current + step
        temp_input[feature] = new_value
        
        # Adjust derived features logically
        if temp_input.get("active_days", 0) > 0:
            temp_input["avg_clicks_per_day"] = temp_input["total_clicks"] / temp_input["active_days"]
        
        # An active student spans their learning over the module length
        # Roughly estimate activity_span based on active_days and module length
        if temp_input["active_days"] > 0:
            expected_span = min(temp_input.get("module_presentation_length", 268), temp_input["active_days"] * (268.0 / 89.0))
            temp_input["activity_span"] = max(temp_input.get("activity_span", 0), expected_span)
            
        sim_pred = predict_student(temp_input)
        return sim_pred["success_probability"]

    simulation["study_days"] = simulate_change("active_days")
    simulation["assignment"] = simulate_change("avg_assignment_score")
    simulation["lms"] = simulate_change("total_clicks")
    
    temp_ideal = student_input.copy()
    temp_ideal.update(target_behavior)
    if temp_ideal.get("active_days", 0) > 0:
        temp_ideal["avg_clicks_per_day"] = temp_ideal["total_clicks"] / temp_ideal["active_days"]
        
    expected_ideal_span = min(temp_ideal.get("module_presentation_length", 268), temp_ideal["active_days"] * (268.0 / 89.0))
    temp_ideal["activity_span"] = max(temp_ideal.get("activity_span", 0), expected_ideal_span)
        
    simulation["ideal"] = predict_student(temp_ideal)["success_probability"]
    
    prediction_label = "SUCCESS" if prediction == 1 else "AT RISK"
    
    return {
        "prediction": prediction_label,
        "success_probability": prob,
        "risk_level": risk,
        "current_behavior": current_behavior,
        "target_behavior": target_behavior,
        "improvement_needed": improvement_needed,
        "simulation": simulation,
        "remaining_weeks": remaining_weeks,
        "weekly_plan": weekly_plan,
        "pipeline": result.get("pipeline"),
        "input_df": result.get("input_df")
    }

if __name__ == "__main__":
    sample_student = {
        "code_module": "AAA",
        "code_presentation": "2013J",
        "gender": "M",
        "region": "East Anglian Region",
        "highest_education": "HE Qualification",
        "imd_band": "50-60%",
        "age_band": "35-55",
        "num_of_prev_attempts": 0,
        "studied_credits": 60,
        "disability": "N",
        "module_presentation_length": 268,
        "total_clicks": 400,
        "active_days": 25,
        "avg_clicks_per_day": 16.0,
        "activity_span": 60,
        "avg_assignment_score": 65.0
    }
    
    res = analyze_student(sample_student)

    print("----- AI Exam Companion Result -----")
    print(f"Prediction: {res['prediction']}")
    print(f"Predicted Success Probability: {res['success_probability']:.4f}")
    print(f"Risk Level: {res['risk_level']}\n")

    # ---------------- TARGET ----------------
    print("--- Target Behavior for Successful Students ---")
    print(f"Target active study days: {res['target_behavior']['active_days']}")
    print(f"Target LMS clicks: {res['target_behavior']['total_clicks']}")
    print(f"Target assignment score: {res['target_behavior']['avg_assignment_score']}\n")

    # ---------------- CURRENT ----------------
    print("--- Your Current Behavior ---")
    print(f"Active study days: {res['current_behavior']['active_days']}")
    print(f"LMS clicks: {res['current_behavior']['total_clicks']}")
    print(f"Assignment score: {res['current_behavior']['avg_assignment_score']}")

    # ---------------- IMPROVEMENT ----------------
    print("\n--- Improvement Needed ---")
    print(f"Extra study days needed: {res['improvement_needed']['extra_days']}")
    print(f"Extra LMS clicks needed: {res['improvement_needed']['extra_clicks']}")
    print(f"Assignment marks to improve: {res['improvement_needed']['marks_improvement']}")

    # ---------------- SIMULATION ----------------
    print("\n--- Success Improvement Simulation ---")
    print(f"If you study {res['improvement_needed']['extra_days']} more days, success probability becomes: {res['simulation']['study_days']:.4f}")
    print(f"If assignment score improves by {res['improvement_needed']['marks_improvement']} marks, probability becomes: {res['simulation']['assignment']:.4f}")
    print(f"If LMS engagement increases by {res['improvement_needed']['extra_clicks']} clicks, probability becomes: {res['simulation']['lms']:.4f}")
    print(f"\nIf you reach successful student behavior, success probability becomes: {res['simulation']['ideal']:.4f}")

    # ---------------- RECOMMENDATIONS ----------------
    print("\n--- Recommendations ---")
    if res['improvement_needed']['extra_clicks'] > 0:
        print(f"- Increase LMS activity by ~{res['improvement_needed']['extra_clicks']} more clicks")
    if res['improvement_needed']['extra_days'] > 0:
        print(f"- Increase study days by ~{res['improvement_needed']['extra_days']} more days")
        print("- Start studying earlier and maintain consistency")
    if res['improvement_needed']['marks_improvement'] > 0:
        print(f"- Improve assignment score by ~{res['improvement_needed']['marks_improvement']} marks")

    # ---------------- WEEKLY STUDY PLAN ----------------
    if len(res['weekly_plan']) > 0 or res['improvement_needed']['marks_improvement'] > 0:
        print(f"\n--- Your Personalized Weekly Study Plan ({res['remaining_weeks']} weeks remaining) ---")
        if "days_per_week" in res['weekly_plan']:
            print(f"- Days to Study: Log in and study {res['weekly_plan']['days_per_week']} to {res['weekly_plan']['days_per_week'] + 1} days every week.")
        if "clicks_per_week" in res['weekly_plan']:
            print(f"- Engagement: Generate about {res['weekly_plan']['clicks_per_week']} clicks per week reading materials and taking quizzes.")
        if res['improvement_needed']['marks_improvement'] > 0:
            print(f"- Grades: Focus your study time deeply on assignments to raise your average by {res['improvement_needed']['marks_improvement']} marks.")

