# Diet-Planner-using-Generative-AI
A diet planner application using Flask, SQLite, Generative AI (Gemini Flash 1.5) and Tailwind CSS.

## Features

- User Signup and Login
- Generate Diet Plans (Day-wise, Week-wise, Month-wise)
- Track and display total nutrition
- Export diet plans to PDF

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/sajidkassari/Diet-Planner-using-Generative-AI.git
    cd Diet-Planner-using-Generative-AI
    ```

2. Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

4. Set up Tailwind CSS:
    ```bash
    npm install -D tailwindcss
    npx tailwindcss init
    ```

5. Run the application:
    ```bash
    flask run
    ```
6. Sign up and Enter your Gemini API key

7. Generate Diet Plans


## Usage

1. Sign up or log in to the application.
2. Enter your Gemini API key(if you don't have an API key you can continue without an API key).
3. Fill in the required details to generate a diet plan.
4. View the diet plan and export it to PDF.
