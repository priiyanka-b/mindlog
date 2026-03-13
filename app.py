from flask import Flask, request, jsonify, render_template
import psycopg2
import psycopg2.extras
from emotion_model import analyze_emotions
import google.generativeai as genai
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-2.5-flash')

app = Flask(__name__)

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            sentiment TEXT,
            anxiety FLOAT DEFAULT 0,
            sadness FLOAT DEFAULT 0,
            fear FLOAT DEFAULT 0,
            joy FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# ---------- Pages ----------

@app.route("/")
def journal_page():
    return render_template("journal.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/entries-page")
def entries_page():
    return render_template("entries.html")

@app.route("/therapist-page")
def therapist_page():
    return render_template("therapist.html")

# ---------- Journal API ----------

@app.route("/journal", methods=["POST"])
def add_entry():
    data = request.get_json()
    text = data["text"]
    emotions = analyze_emotions(text)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO entries(text, sentiment, anxiety, sadness, fear, joy)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        text, "analyzed",
        emotions.get("anxiety", 0),
        emotions.get("sadness", 0),
        emotions.get("fear", 0),
        emotions.get("joy", 0)
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "saved"})

# ---------- History ----------

@app.route("/history")
def history():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT text, anxiety, sadness, fear, joy, created_at
        FROM entries ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{
        "text": r["text"], "anxiety": r["anxiety"],
        "sadness": r["sadness"], "fear": r["fear"],
        "joy": r["joy"], "date": str(r["created_at"])
    } for r in rows])

# ---------- All Entries ----------

@app.route("/entries")
def entries():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT text, anxiety, sadness, fear, joy, created_at
        FROM entries ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{
        "text": r["text"], "anxiety": r["anxiety"],
        "sadness": r["sadness"], "fear": r["fear"],
        "joy": r["joy"], "date": str(r["created_at"])
    } for r in rows])

# ---------- Streak ----------

@app.route("/streak")
def streak():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DATE(created_at)
        FROM entries
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at) DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return jsonify({"streak": 0})

    streak_count = 0
    today = datetime.now().date()

    for i, (date_val,) in enumerate(rows):
        expected = today - timedelta(days=i)
        if date_val == expected:
            streak_count += 1
        else:
            break

    return jsonify({"streak": streak_count})

# ---------- Weekly Report ----------

@app.route("/report", methods=["POST"])
def report():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT text, anxiety, sadness, fear, joy, created_at
        FROM entries ORDER BY created_at DESC LIMIT 7
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return jsonify({"report": "Not enough entries yet. Write at least a few journal entries first!"})

    entries_text = ""
    for r in rows:
        entries_text += f"Date: {r['created_at']}\nEntry: {r['text']}\nJoy:{r['joy']:.2f} Anxiety:{r['anxiety']:.2f} Sadness:{r['sadness']:.2f} Fear:{r['fear']:.2f}\n\n"

    prompt = f"""
You are a compassionate mental wellness analyst.
Analyze these journal entries from the past week and write a warm,
personal weekly mental wellness report for the user.

Entries:
{entries_text}

Your report should include:
1. Overall emotional pattern this week in 2-3 sentences
2. One specific observation about their emotional triggers or patterns
3. Their emotional highlight (best moment) and low point
4. One small, actionable suggestion for next week

Keep it warm, personal, and under 200 words. Do not use bullet points, write in paragraphs.
"""
    response = model.generate_content(prompt)
    return jsonify({"report": response.text})

# ---------- Therapist Chat ----------

@app.route("/therapist", methods=["POST"])
def therapist():
    data = request.get_json()
    user_message = data["message"]
    chat_history = data.get("chat_history", [])

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT text, joy, anxiety, sadness, fear, created_at
        FROM entries ORDER BY created_at DESC LIMIT 7
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    journal_context = ""
    for r in rows:
        journal_context += f"Date: {r['created_at']}, Entry: {r['text']} (joy:{r['joy']:.2f}, anxiety:{r['anxiety']:.2f}, sadness:{r['sadness']:.2f}, fear:{r['fear']:.2f})\n"

    history_text = ""
    for msg in chat_history[-6:]:
        role = "User" if msg["role"] == "user" else "Therapist"
        history_text += f"{role}: {msg['text']}\n"

    prompt = f"""You are a warm, empathetic mental wellness therapist having a casual conversation.
You have context from the user's recent journal entries below — use it ONLY when relevant, don't dump it all at once.
Respond naturally like a real person. Keep replies SHORT — 1-2 sentences max for casual messages.
Only give longer responses when the user shares something emotional or asks for help.
Never start with a paragraph about their journal unless they bring it up first.

User's recent journal entries (background context only):
{journal_context}

Conversation so far:
{history_text}
User: {user_message}
Therapist:"""

    response = model.generate_content(prompt)
    return jsonify({"reply": response.text.strip()})

if __name__ == "__main__":
    app.run(debug=True)