import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import datetime
import random
import os

st.set_page_config(page_title="Smart  Nutri Diet Planner", layout="wide")

@st.cache_data
def load_data():
    try:
        m = pd.read_csv("Main meals dataset.CSV").fillna("")
        m['MEALS :'] = m['MEALS :'].ffill()

        c = pd.read_csv("CONDITION.CSV").fillna("")

        return m, c
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

meals_df, condition_df = load_data()

def calculate_metrics(w, h, a, g, act, goal):
    height_m = h / 100
    bmi = w / (height_m ** 2)
    status = "Normal"
    if bmi < 18.5: status = "Underweight"
    elif 18.5 <= bmi < 24.9: status = "Normal"
    elif 25 <= bmi < 29.9: status = "Overweight"
    else: status = "Obese"

    if g == "Male": bmr = 10*w + 6.25*h - 5*a + 5
    elif g == "Female": bmr = 10*w + 6.25*h - 5*a - 161
    else: bmr = 10*w + 6.25*h - 5*a - 78

    factors = {"Sedentary": 1.2, "Lightly Active": 1.375, "Moderately Active": 1.55, "Very Active": 1.725}
    tdee = bmr * factors.get(act, 1.2)

    if "Loss" in goal: cal = tdee - 500
    elif "Gain" in goal: cal = tdee + 500
    else: cal = tdee
    return round(bmi, 1), status, int(cal)

def generate_diet(pref, cond, selected_allergies):

    df = meals_df.copy()
    plan = []
    used_foods = set()

    for day in range(1, 8):

        row = {"Day": f"Day {day}"}

        for meal in ["BREAKFAST", "LUNCH", "SNACKS", "DINNER"]:

            options = df[df["MEALS :"] == meal]

            if not options.empty:

                unused = options[
                    ~options["FOODS"].isin(used_foods)
                ]

                if not unused.empty:
                    options = unused

                selected = options.sample(1).iloc[0]

                food = str(selected["FOODS"])

                if "beverage" in df.columns:
                    bev = str(selected["beverage"]).strip()

                    if bev and bev.lower() != "nan":
                        food = food + " + " + bev

                row[meal] = food
                used_foods.add(str(selected["FOODS"]))

            else:
                row[meal] = "No Food Found"

        detox = df[df["MEALS :"] == "DETOX DRINK"]

        if not detox.empty:
            row["DETOX"] = detox.sample(1).iloc[0]["FOODS"]
        else:
            row["DETOX"] = "-"

        plan.append(row)

    return pd.DataFrame(plan)

st.title("🥗  Personalized Diet Planner")

with st.form("user_data"):
    c1, c2, c3 = st.columns(3)
    u_name = c1.text_input("Full Name", value="Mike ")
    u_age = c2.number_input("Age", 10, 100, 25)
    u_gen = c3.selectbox("Gender", ["Male", "Female", "Other"])
    u_h = c1.number_input("Height (cm)", 100, 250, 170)
    u_w = c2.number_input("Weight (kg)", 30, 200, 65)
    u_goal = c3.selectbox("Goal", ["Weight Loss", "Weight Gain", "Maintain", "Muscle Gain", "Muscle Loss"])
    u_act = c1.selectbox("Activity", ["Sedentary", "Lightly Active", "Moderately Active", "Very Active"])
    u_pref = c2.selectbox("Preference", ["Vegetarian", "Eggitarian", "Non-Veg", "Jain"])

    # Condition and Allergy Inputs
    u_cond = c3.selectbox("Condition", ["None"] + sorted(list(condition_df['CONDITION'].unique())))
    u_allergies = st.multiselect("Select Allergies", ["Gluten", "Dairy", "Peanut", "Egg", "Soy", "Nuts", "Fish"])

    submit = st.form_submit_button("Generate & Download Plan")

if submit:
    bmi, status, cals = calculate_metrics(u_w, u_h, u_age, u_gen, u_act, u_goal)
    st.session_state.diet = generate_diet(u_pref, u_cond, u_allergies)
    st.session_state.user = {
        "name": u_name, "age": u_age, "bmi": bmi, "status": status,
        "cals": cals, "goal": u_goal, "date": str(datetime.date.today()),
        "allergies": ", ".join(u_allergies) if u_allergies else "None"
    }

if "diet" in st.session_state:
    u = st.session_state.user
    st.success(f"Plan Generated for {u['name']}!")
    st.table(st.session_state.diet)

    # --- ENHANCED PDF ENGINE ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(46, 125, 50); pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 22)
    pdf.cell(190, 30, "PERSONALIZED DIET PLAN", ln=True, align='C')

    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10); pdf.ln(15)
    pdf.cell(95, 7, f"Name: {u['name']}"); pdf.cell(95, 7, f"Date: {u['date']}", ln=True, align='R')
    pdf.cell(95, 7, f"Age: {u['age']}"); pdf.cell(95, 7, f"Goal: {u['goal']}", ln=True, align='R')
    pdf.cell(95, 7, f"BMI: {u['bmi']} ({u['status']})"); pdf.cell(95, 7, f"Calories: {u['cals']} kcal", ln=True, align='R')
    pdf.cell(190, 7, f"Allergies: {u['allergies']}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(230, 230, 230)
    headers = ["Day", "Breakfast (8 AM)", "Lunch (1 PM)", "Snacks (5 PM)", "Dinner (8 PM)", "Detox"]
    widths = [12, 40, 40, 35, 40, 23]
    for i, h_text in enumerate(headers):
        pdf.cell(widths[i], 10, h_text, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font("Arial", size=7.5)
    for _, row in st.session_state.diet.iterrows():
        items = [str(row['Day']), str(row['BREAKFAST']), str(row['LUNCH']), str(row['SNACKS']), str(row['DINNER']), str(row['DETOX'])]

        # Row height logic based on longest string
        max_len = max([len(str(x)) for x in items])
        h = 10 if max_len < 30 else (18 if max_len < 60 else 24)

        curr_x, curr_y = pdf.get_x(), pdf.get_y()
        if curr_y > 240: pdf.add_page(); curr_y = pdf.get_y()

        for i, text in enumerate(items):
            pdf.set_xy(curr_x, curr_y)
            # Center multi-cell text vertically by calculating offset
            pdf.multi_cell(widths[i], h/2 if h > 10 else h, text, border=1, align='C')
            curr_x += widths[i]
        pdf.set_y(curr_y + h)

    fname = f"{u['name']}_{u['goal'].replace(' ', '')}_Plan.pdf"
    pdf.output(fname)
    with open(fname, "rb") as f:
        st.download_button("📥 Download Diet Plan", f, file_name=fname)
