from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
import bcrypt
import google.generativeai as genai
from flask import render_template, make_response
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime, timedelta


app = Flask(__name__)
# Add these lines to configure sessions
app.config['SECRET_KEY'] = 'b36dd7112dmsh3b62d6610452179p13e36ejsn775dc48b9b14'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
PERSONAL_API_KEY = 'AIzaSyBOLJaZgumeGMEiTNi2XtJLXkVgfxHtOe8'


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
    stored_api_key = user[0] if user else None
    conn.close()

    if request.method == 'POST':
        api_key = request.form['api_key']
        if api_key:
            session['api_key'] = api_key
            cursor.execute('UPDATE users SET api_key = ? WHERE email = ?', (api_key, email))
            conn.commit()
        else:
            session['api_key'] = PERSONAL_API_KEY  # Use your personal API key if none provided
        return redirect(url_for('generate_diet_plan'))
    
    session['api_key'] = stored_api_key or PERSONAL_API_KEY  # Default to personal API key if not set
    return render_template('enter_api_key.html', api_key=stored_api_key)


import json

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('home'))

@app.route('/generate_diet_plan', methods=['GET', 'POST'])
def generate_diet_plan():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    api_key = session.get('api_key')
    if not api_key:
        return redirect(url_for('enter_api_key'))
    
    # email = session['email']
    # conn = sqlite3.connect('diet_planner.db')
    # cursor = conn.cursor()
    # cursor.execute('SELECT api_key FROM users WHERE email = ?', (email,))
    # user = cursor.fetchone()
    # api_key = user[0] if user else None
    # conn.close()
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


def fetch_diet_plan(api_key, goal, food_type, protein, calories, height, weight, bmi, plan_duration):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash',
                                  generation_config={"response_mime_type": "application/json"})
    
    # Prepare the prompt with more relevant details for an Indian context
    prompt = f"""
    Create a detailed {plan_duration.lower()} diet plan for an individual with the following details:
    Goal: {goal}
    Food Type: {food_type}
    {"Minimum Protein: " + protein if protein else ""}
    {"Maximum Calories: " + calories if calories else ""}
    {"Height: " + height if height else ""}
    {"Weight: " + weight if weight else ""}
    {"BMI: " + bmi if bmi else ""}
    
    Please include typical high-protein Indian foods that are commonly available in India. Use measurements in grams and milliliters. 
    Strictly use grams/kg and litres/ml as quantities.
    make it float values and remove 'g' and 'ml' except for Food_weight,
    The output should be a JSON list with each meal containing:
    - Meal
    - Food_Item
    - Food_weight
    - Protein (g)
    - Carbs (g)
    - Fibre (g)
    - Sugar (g)
    - Calories
    - Fats (g)

    Ensure the diet plan is balanced, practical, and aligns with common dietary practices in India. Provide detailed nutritional values and avoid using non-local ingredients.
    """

    response = model.generate_content(prompt)
    print(response)
    return response.text





import requests 
from flask import jsonify
@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    try:
        # Get and decode diet plan
        diet_plan = request.form["diet_plan"]
        if not diet_plan:
            return jsonify({"error": "No diet plan provided."}), 400
        
        # Debug print
        print(f"Received diet_plan: {diet_plan}")
        
        try:
            # Convert string back to list
            diet_plan = json.loads(diet_plan)

            # Calculate total nutrition
            total_nutrition = {
                "protein_g": 0,
                "carbs_g": 0,
                "fibre_g": 0,
                "sugar_g": 0,
                "calories": 0,
                "fats_g": 0,
            }
            for item in diet_plan:
                total_nutrition["protein_g"] += float(item.get("Protein", 0))
                total_nutrition["carbs_g"] += float(item.get("Carbs", 0))
                total_nutrition["fibre_g"] += float(item.get("Fibre", 0))
                total_nutrition["sugar_g"] += float(item.get("Sugar", 0))
                total_nutrition["calories"] += float(item.get("Calories", 0))
                total_nutrition["fats_g"] += float(item.get("Fats", 0))

            # Generate HTML content
            html_content = render_template('export_pdf.html', diet_plan=diet_plan, total_nutrition=total_nutrition)
            
            # Set up the request for the API
            url = "https://cloudlayer-io.p.rapidapi.com/v1/html/pdf"
            headers = {
                "x-rapidapi-key": "b36dd7112dmsh3b62d6610452179p13e36ejsn775dc48b9b14",
                "x-rapidapi-host": "cloudlayer-io.p.rapidapi.com",
                "Content-Type": "application/json"
            }
            payload = {
                "html": html_content,
                "timeout": 30000
            }
            
            # Make the request to the API
            response = requests.post(url, json=payload, headers=headers)  # Use json=payload instead of data=payload
            
            if response.status_code == 200:
                # If the response is successful, return the PDF
                pdf_content = response.content
                response = make_response(pdf_content)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = 'attachment; filename=diet_plan.pdf'
                return response
            else:
                # Handle errors
                return jsonify({"error": "Error creating PDF", "details": response.json()}), response.status_code

        except json.JSONDecodeError as e:
            return jsonify({"error": "Invalid JSON format", "details": str(e)}), 400

    except Exception as e:
        return jsonify({"error": "An error occurred", "details": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)
