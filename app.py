from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
import bcrypt
import google.generativeai as genai
from flask import render_template, make_response
from xhtml2pdf import pisa
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

def init_db():
    conn = sqlite3.connect('diet_planner.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        api_key TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('diet_planner.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('signup'))
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_password))
        conn.commit()
        conn.close()
        flash('Account created successfully.')
        return redirect(url_for('enter_api_key'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('diet_planner.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        if user and bcrypt.checkpw(password.encode(), user[2].encode()):
            session['email'] = email
            return redirect(url_for('home'))
        flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/enter_api_key', methods=['GET', 'POST'])
def enter_api_key():
    if 'email' not in session:
        return redirect(url_for('login'))
    email = session['email']
    conn = sqlite3.connect('diet_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT api_key FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    api_key = user[0] if user else None
    if request.method == 'POST':
        api_key = request.form['api_key']
        cursor.execute('UPDATE users SET api_key = ? WHERE email = ?', (api_key, email))
        conn.commit()
        conn.close()
        return redirect(url_for('generate_diet_plan'))
    conn.close()
    return render_template('enter_api_key.html', api_key=api_key)

import json

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('home'))

@app.route('/generate_diet_plan', methods=['GET', 'POST'])
def generate_diet_plan():
    if 'email' not in session:
        return redirect(url_for('login'))
    email = session['email']
    conn = sqlite3.connect('diet_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT api_key FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    api_key = user[0] if user else None
    conn.close()
    diet_plan = None
    total_nutrition = {
        'protein_g': 0,
        'carbs_g': 0,
        'fibre_g': 0,
        'sugar_g': 0,
        'calories': 0,
        'fats_g': 0,
    }
    if request.method == 'POST':
        goal = request.form['goal']
        food_type = request.form['food_type']
        protien = request.form['protien']
        calories = request.form['calories']
        height = request.form['height']
        weight = request.form['weight']
        bmi = request.form['bmi']
        plan_duration = request.form['plan_duration']
        
        response_text = fetch_diet_plan(api_key, goal, food_type, protien, calories, height, weight, bmi, plan_duration)
        diet_plan = json.loads(response_text)  # Parse the JSON response into a Python list
        
        # Calculate total nutrition
        for item in diet_plan:
            total_nutrition['protein_g'] += float(item.get('Protein', 0))
            total_nutrition['carbs_g'] += float(item.get('Carbs', 0))
            total_nutrition['fibre_g'] += float(item.get('Fibre', 0))
            total_nutrition['sugar_g'] += float(item.get('Sugar', 0))
            total_nutrition['calories'] += float(item.get('Calories', 0))
            total_nutrition['fats_g'] += float(item.get('Fats', 0))

    return render_template('generate_diet_plan.html', diet_plan=diet_plan, total_nutrition=total_nutrition)

def fetch_diet_plan(api_key, goal, food_type, protien, calories, height, weight, bmi, plan_duration):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash',
                                  generation_config={"response_mime_type": "application/json"})
    
    prompt = f"""
    Create a detailed whole {plan_duration.lower()} diet plan for an individual with the following details:
    Goal: {goal}
    Food Type: {food_type}
    {"Minimum Protien: " + protien if protien else ""}
    {"Maximum Calories: " + calories if calories else ""}
    {"Height: " + height if height else ""}
    {"Weight: " + weight if weight else ""}
    {"BMI: " + bmi if bmi else ""}
    Include typical High Protien Indian foods with accurate nutrition values. Strictly use grams and mili-litres as quantities.
    The output should be a JSON list and float values (so remove 'g' and 'ml' from values) with each meal containing:
    - Meal
    - Food_Item
    - Protein (g)
    - Carbs (g)
    - Fibre (g)
    - Sugar (g)
    - Calories
    - Fats (g)
    """
    
    response = model.generate_content(prompt)
    print(response)
    return response.text





@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    diet_plan = request.form["diet_plan"]
    print(diet_plan)
    diet_plan = json.loads(diet_plan)  # Convert string back to list
    total_nutrition = {
        'protein_g': 0,
        'carbs_g': 0,
        'fibre_g': 0,
        'sugar_g': 0,
        'calories': 0,
        'fats_g': 0,
    }
    for item in diet_plan:
        total_nutrition['protein_g'] += float(item.get('Protein', 0))
        total_nutrition['carbs_g'] += float(item.get('Carbs', 0))
        total_nutrition['fibre_g'] += float(item.get('Fibre', 0))
        total_nutrition['sugar_g'] += float(item.get('Sugar', 0))
        total_nutrition['calories'] += float(item.get('Calories', 0))
        total_nutrition['fats_g'] += float(item.get('Fats', 0))

    rendered_html = render_template('export_pdf.html', diet_plan=diet_plan, total_nutrition=total_nutrition)
    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(rendered_html.encode('UTF-8')), dest=pdf)

    if pisa_status.err:
        return f"Error creating PDF: {pisa_status.err}"

    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=diet_plan.pdf'
    return response





if __name__ == '__main__':
    app.run(debug=True)
