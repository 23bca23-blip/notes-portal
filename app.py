from flask import Flask, render_template, request, redirect, send_from_directory, session
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "simple_secret_key"

# ---------------- PATH SETUP ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# ---------------- DATABASE ---------------- #
def init_db():
    db = sqlite3.connect("notes.db")

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    subject TEXT,
    semester TEXT,
    year TEXT,
    batch TEXT,
    filename TEXT,
    uploader TEXT,
    date TEXT,
    downloads INTEGER DEFAULT 0
)
    """)

    admin = db.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if not admin:
        db.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            ("admin", "admin123", "admin")
        )

    db.commit()
    db.close()

init_db()

# ---------------- AUTH ---------------- #
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = sqlite3.connect("notes.db")
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        db.close()

        if user:
            session["username"] = user[1]
            session["role"] = user[3]
            return redirect("/")
        else:
            return "Invalid login"

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = sqlite3.connect("notes.db")
        try:
            db.execute(
                "INSERT INTO users (username, password, role) VALUES (?,?,?)",
                (username, password, "student")
            )
            db.commit()
        except:
            return "Username already exists"
        finally:
            db.close()

        return redirect("/login")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- HOME ---------------- #
@app.route("/")
def index():
    if "username" not in session:
        return redirect("/login")

    return render_template(
        "index.html",
        username=session["username"],
        role=session["role"]
    )

# ---------------- UPLOAD ---------------- #
@app.route("/upload_page")
def upload_page():
    if "username" not in session:
        return redirect("/login")

    return render_template(
    "upload.html",
    username=session["username"],
    role=session["role"]
)


@app.route("/upload", methods=["POST"])
def upload():
    if "username" not in session:
        return redirect("/login")

    title = request.form["title"]
    subject = request.form["subject"]
    semester = request.form["semester"]
    year = request.form["year"]
    batch = request.form["batch"]
    file = request.files["file"]

    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        date = datetime.now().strftime("%Y-%m-%d")

        db = sqlite3.connect("notes.db")
        db.execute(
            """INSERT INTO notes
            (title, subject, semester, year, batch, filename, uploader, date)
            VALUES (?,?,?,?,?,?,?,?)""",
            (title, subject, semester, year, batch, file.filename, session["username"], date)
        )
        db.commit()
        db.close()

    return redirect("/notes")

# ---------------- NOTES ---------------- #
@app.route("/notes")
def notes_page():
    if "username" not in session:
        return redirect("/login")

    semester = request.args.get("semester", "")
    subject = request.args.get("subject", "")
    year = request.args.get("year", "")
    batch = request.args.get("batch", "")
    search = request.args.get("search", "")
    sort = request.args.get("sort")

    query = "SELECT * FROM notes WHERE 1=1"
    params = []

    if semester:
        query += " AND semester=?"
        params.append(semester)

    if subject:
        query += " AND subject=?"
        params.append(subject)

    if year:
        query += " AND year=?"
        params.append(year)

    if batch:
        query += " AND batch=?"
        params.append(batch)

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    if sort == "latest":
        query += " ORDER BY date DESC"
    elif sort == "oldest":
        query += " ORDER BY date ASC"

    db = sqlite3.connect("notes.db")
    notes = db.execute(query, params).fetchall()
    db.close()

    return render_template(
        "notes.html",
        notes=notes,
        username=session["username"],
        role=session["role"]
    )

# ---------------- DOWNLOAD ---------------- #
@app.route("/download/<filename>")
def download(filename):
    db = sqlite3.connect("notes.db")
    db.execute(
        "UPDATE notes SET downloads = downloads + 1 WHERE filename=?",
        (filename,)
    )
    db.commit()
    db.close()

    return send_from_directory(
    app.config['UPLOAD_FOLDER'],
    filename,
    as_attachment=False
)

# ---------------- DELETE (ADMIN) ---------------- #
@app.route("/delete/<int:note_id>")
def delete(note_id):
    if session.get("role") != "admin":
        return "Unauthorized"

    db = sqlite3.connect("notes.db")
    db.execute("DELETE FROM notes WHERE id=?", (note_id,))
    db.commit()
    db.close()

    return redirect("/notes")

# ---------------- ADMIN DASHBOARD ---------------- #
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "Unauthorized"

    db = sqlite3.connect("notes.db")

    users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    notes = db.execute("SELECT COUNT(*) FROM notes").fetchone()[0]

    db.close()

    return render_template("admin.html", users=users, notes=notes)

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    app.run(debug=True)


