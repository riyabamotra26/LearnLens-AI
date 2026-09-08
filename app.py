import os
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session, flash
from google import genai
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "learnlens-secret-key"

DATABASE = "learnlens.db"


QUESTIONS = [
    {
        "id": 1,
        "topic": "Variables",
        "question": "Which symbol is used to assign a value in Python?",
        "options": ["==", "=", ":", "->"]
    },
    {
        "id": 2,
        "topic": "Variables",
        "question": "Which is a valid Python variable name?",
        "options": ["2name", "student_name", "student-name", "class"]
    },
    {
        "id": 3,
        "topic": "Variables",
        "question": "What is the data type of 3.14?",
        "options": ["int", "str", "float", "bool"]
    },
    {
        "id": 4,
        "topic": "Conditions",
        "question": "Which keyword is used to check a condition?",
        "options": ["if", "for", "def", "print"]
    },
    {
        "id": 5,
        "topic": "Conditions",
        "question": "Which operator means not equal to?",
        "options": ["=", "==", "!=", ">="]
    },
    {
        "id": 6,
        "topic": "Conditions",
        "question": "Which block runs when the if-condition is false?",
        "options": ["for", "else", "def", "while"]
    },
    {
        "id": 7,
        "topic": "Loops",
        "question": "Which loop is commonly used to iterate over a list?",
        "options": ["if", "for", "def", "else"]
    },
    {
        "id": 8,
        "topic": "Loops",
        "question": "Which keyword immediately stops a loop?",
        "options": ["stop", "exit", "break", "skip"]
    },
    {
        "id": 9,
        "topic": "Loops",
        "question": "What does range(3) generate?",
        "options": [
            "1, 2, 3",
            "0, 1, 2",
            "0, 1, 2, 3",
            "3 only"
        ]
    },
    {
        "id": 10,
        "topic": "Functions",
        "question": "Which keyword defines a function in Python?",
        "options": ["function", "define", "def", "fun"]
    },
    {
        "id": 11,
        "topic": "Functions",
        "question": "Which keyword sends a value back from a function?",
        "options": ["print", "return", "break", "send"]
    },
    {
        "id": 12,
        "topic": "Functions",
        "question": "What is the information passed to a function called?",
        "options": ["argument", "loop", "class", "operator"]
    }
]


CORRECT_ANSWERS = {
    1: "=",
    2: "student_name",
    3: "float",
    4: "if",
    5: "!=",
    6: "else",
    7: "for",
    8: "break",
    9: "0, 1, 2",
    10: "def",
    11: "return",
    12: "argument"
}
STUDY_RESOURCES = {
    "Variables": {
        "lesson": "Variables and Data Types",
        "task": "Revise variable naming, assignment and Python data types.",
        "practice": "Complete 5 variable and data-type questions.",
        "time": "20 minutes"
    },
    "Conditions": {
        "lesson": "Conditional Statements",
        "task": "Revise if, elif, else and comparison operators.",
        "practice": "Solve 5 condition-based Python problems.",
        "time": "25 minutes"
    },
    "Loops": {
        "lesson": "Loops in Python",
        "task": "Study for loops, while loops, range and break.",
        "practice": "Write 3 programs using loops.",
        "time": "30 minutes"
    },
    "Functions": {
        "lesson": "Python Functions",
        "task": "Revise function definition, arguments and return values.",
        "practice": "Create 3 simple Python functions.",
        "time": "25 minutes"
    }
}


def get_database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_database()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            overall_score INTEGER NOT NULL,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS topic_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            percentage INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (attempt_id) REFERENCES quiz_attempts (id)
        )
""")


    connection.commit()
    connection.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_database()

        try:
            connection.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, hashed_password)
            )

            connection.commit()

        except sqlite3.IntegrityError:
            connection.close()
            flash("An account with this email already exists.")
            return render_template("register.html")

        connection.close()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_database()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.")

    return render_template("login.html")




@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_database()

    attempts = connection.execute(
        """
        SELECT id, overall_score, attempted_at
        FROM quiz_attempts
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (session["user_id"],)
    ).fetchall()

    latest_attempt = attempts[-1] if attempts else None
    topic_progress = []

    if latest_attempt:
        topic_progress = connection.execute(
            """
            SELECT topic, percentage, status
            FROM topic_scores
            WHERE attempt_id = ?
            ORDER BY id ASC
            """,
            (latest_attempt["id"],)
        ).fetchall()

    connection.close()

    chart_labels = [
        f"Attempt {number}"
        for number in range(1, len(attempts) + 1)
    ]

    chart_scores = [
        attempt["overall_score"]
        for attempt in attempts
    ]

    latest_score = (
        latest_attempt["overall_score"]
        if latest_attempt
        else 0
    )

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        attempts=attempts,
        attempt_count=len(attempts),
        latest_score=latest_score,
        topic_progress=topic_progress,
        chart_labels=chart_labels,
        chart_scores=chart_scores
    )
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        topic_results = {
            "Variables": {
                "correct": 0,
                "total": 0
            },
            "Conditions": {
                "correct": 0,
                "total": 0
            },
            "Loops": {
                "correct": 0,
                "total": 0
            },
            "Functions": {
                "correct": 0,
                "total": 0
            }
        }

        total_correct = 0

        for question in QUESTIONS:
            question_id = question["id"]
            topic = question["topic"]

            selected_answer = request.form.get(
                f"question_{question_id}"
            )

            topic_results[topic]["total"] += 1

            if selected_answer == CORRECT_ANSWERS[question_id]:
                total_correct += 1
                topic_results[topic]["correct"] += 1

        analysis = []

        for topic, result in topic_results.items():
            percentage = round(
                result["correct"] / result["total"] * 100
            )

            if percentage < 50:
                status = "Weak"
            elif percentage < 75:
                status = "Improving"
            else:
                status = "Strong"

            analysis.append({
                "topic": topic,
                "correct": result["correct"],
                "total": result["total"],
                "percentage": percentage,
                "status": status
            })

        overall_percentage = round(
            total_correct / len(QUESTIONS) * 100
        )
        session["analysis"] = analysis
        session["overall_percentage"] = overall_percentage
        connection = get_database()

        cursor = connection.execute(
            """
            INSERT INTO quiz_attempts (user_id, overall_score)
            VALUES (?, ?)
            """,
            (session["user_id"], overall_percentage)
        )

        attempt_id = cursor.lastrowid

        for item in analysis:
            connection.execute(
                """
                INSERT INTO topic_scores
                (attempt_id, topic, percentage, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    item["topic"],
                    item["percentage"],
                    item["status"]
                )
            )

        connection.commit()
        connection.close()

        return render_template(
            "result.html",
            total_correct=total_correct,
            total_questions=len(QUESTIONS),
            overall_percentage=overall_percentage,
            analysis=analysis,
            user_name=session["user_name"]
        )

    return render_template(
        "quiz.html",
        questions=QUESTIONS,
        user_name=session["user_name"]
    )
@app.route("/study-plan")
def study_plan():
    if "user_id" not in session:
        return redirect(url_for("login"))

    analysis = session.get("analysis")

    if not analysis:
        flash("Please complete the diagnostic quiz first.")
        return redirect(url_for("quiz"))

    priority_order = {
        "Weak": 1,
        "Improving": 2,
        "Strong": 3
    }

    sorted_analysis = sorted(
        analysis,
        key=lambda item: priority_order[item["status"]]
    )

    personalized_plan = []

    for item in sorted_analysis:
        topic = item["topic"]
        resource = STUDY_RESOURCES[topic]

        if item["status"] == "Weak":
            priority = "High Priority"
            recommendation = "Learn this topic first."
        elif item["status"] == "Improving":
            priority = "Medium Priority"
            recommendation = "Revise this topic after completing weak topics."
        else:
            priority = "Low Priority"
            recommendation = "You are strong in this topic. Try advanced practice."

        personalized_plan.append({
            "topic": topic,
            "percentage": item["percentage"],
            "status": item["status"],
            "priority": priority,
            "recommendation": recommendation,
            "lesson": resource["lesson"],
            "task": resource["task"],
            "practice": resource["practice"],
            "time": resource["time"]
        })

    return render_template(
        "study_plan.html",
        user_name=session["user_name"],
        overall_percentage=session.get("overall_percentage", 0),
        personalized_plan=personalized_plan
    )
def get_offline_answer(question):
    question = question.lower().strip()

    if "variable" in question:
        return (
            "A variable stores data in Python.\n\n"
            "Example:\n"
            "name = 'Riya'\n"
            "age = 18\n\n"
            "Here, name and age are variables."
        )

    elif (
    " if " in f" {question} "
    or "condition" in question
    or "if-else" in question
    ):
        return (
            "The if statement checks a condition.\n\n"
            "Example:\n"
            "age = 18\n"
            "if age >= 18:\n"
            "    print('Eligible')\n"
            "else:\n"
            "    print('Not eligible')"
        )

    elif "loop" in question or "for" in question:
        return (
            "A loop repeats a block of code.\n\n"
            "Example:\n"
            "for number in range(3):\n"
            "    print(number)\n\n"
            "Output: 0, 1, 2"
        )

    elif "function" in question or "def" in question:
        return (
            "A function is a reusable block of code.\n\n"
            "Example:\n"
            "def greet(name):\n"
            "    return 'Hello ' + name\n\n"
            "print(greet('Riya'))"
        )

    elif "list" in question:
        return (
            "A list stores multiple values in one variable.\n\n"
            "Example:\n"
            "subjects = ['Python', 'SQL', 'HTML']\n"
            "print(subjects[0])\n\n"
            "Output: Python"
        )

    else:
        return (
            "I could not find an offline answer for this doubt. "
            "Please ask about Python variables, conditions, loops, "
            "functions or lists."
        )
@app.route("/assistant", methods=["GET", "POST"])
def assistant():
    if "user_id" not in session:
        return redirect(url_for("login"))

    question = ""
    answer = ""

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if question:
            try:
                client = genai.Client(
                    api_key=os.environ.get("GEMINI_API_KEY")
                )

                prompt = (
                    "You are LearnLens AI, a friendly Python learning "
                    "assistant for beginners. Answer only educational and "
                    "programming-related questions. Explain in simple "
                    "language, include a short Python example when useful, "
                    "and keep the answer concise.\n\n"
                    f"Student question: {question}"
                )

                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt
                )

                answer = response.text

            except Exception as error:
                print("Gemini API error:",error)
        
            
                answer = (
                    get_offline_answer(question)
                    + "\n\nNote: Offline learning mode is currently active."
                )

    return render_template(
        "assistant.html",
        user_name=session["user_name"],
        question=question,
        answer=answer
    )



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    create_database()
    app.run(debug=True)


    