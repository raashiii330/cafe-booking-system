from flask import Flask, render_template, request, redirect, session
import sqlite3
from urllib.parse import quote

app = Flask(__name__)

# Secret key
app.secret_key = "cafe-admin-secret-key-2026"

# Database
DATABASE = "cafe.db"

# Admin login
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

# Cafe WhatsApp number
# Replace this with the real cafe WhatsApp number
WHATSAPP_NUMBER = "919876543210"


# -----------------------------------------
# DATABASE CONNECTION
# -----------------------------------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------------------
# CREATE DATABASE
# -----------------------------------------

def create_database():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            guests INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending'
        )
    """)

    conn.commit()

    # Add status column if old database doesn't have it
    try:
        conn.execute("""
            ALTER TABLE bookings
            ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'
        """)
        conn.commit()

    except sqlite3.OperationalError:
        pass

    conn.close()


# -----------------------------------------
# HOME
# -----------------------------------------

@app.route("/")
def home():

    booking_status = request.args.get("booking")

    return render_template(
        "index.html",
        booking_success=booking_status
    )


# -----------------------------------------
# BOOKING
# -----------------------------------------

@app.route("/book", methods=["POST"])
def book():

    name = request.form.get("name")
    phone = request.form.get("phone")
    date = request.form.get("date")
    time = request.form.get("time")
    guests = request.form.get("guests")

    if not name or not phone or not date or not time or not guests:
        return redirect("/?booking=error")

    conn = get_db()

    conn.execute("""
        INSERT INTO bookings
        (name, phone, date, time, guests, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        phone,
        date,
        time,
        guests,
        "Pending"
    ))

    conn.commit()
    conn.close()

    return redirect("/?booking=success")


# -----------------------------------------
# ADMIN LOGIN
# -----------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect("/admin")

        error = "Invalid username or password"

    return render_template(
        "login.html",
        error=error
    )


# -----------------------------------------
# ADMIN DASHBOARD
# -----------------------------------------

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = get_db()

    # All bookings
    bookings = conn.execute("""
        SELECT *
        FROM bookings
        ORDER BY date ASC, time ASC
    """).fetchall()

    # Total bookings
    total_bookings = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
    """).fetchone()[0]

    # Total guests
    total_guests = conn.execute("""
        SELECT COALESCE(SUM(guests), 0)
        FROM bookings
    """).fetchone()[0]

    # Confirmed bookings
    confirmed_bookings = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'Confirmed'
    """).fetchone()[0]

    # Pending bookings
    pending_bookings = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'Pending'
    """).fetchone()[0]

    # Cancelled bookings
    cancelled_bookings = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'Cancelled'
    """).fetchone()[0]

    # Today's bookings
    from datetime import date

    today = date.today().isoformat()

    today_bookings = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE date = ?
    """, (today,)).fetchone()[0]

    conn.close()

    return render_template(
        "bookings.html",

        bookings=bookings,

        total_bookings=total_bookings,

        total_guests=total_guests,

        confirmed_bookings=confirmed_bookings,

        pending_bookings=pending_bookings,

        cancelled_bookings=cancelled_bookings,

        today_bookings=today_bookings
    )
# -----------------------------------------
# UPDATE STATUS
# -----------------------------------------

@app.route("/update-status/<int:id>/<status>")
def update_status(id, status):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Cancelled"
    ]

    if status not in allowed_statuses:
        return redirect("/admin")

    conn = get_db()

    conn.execute("""
        UPDATE bookings
        SET status = ?
        WHERE id = ?
    """, (
        status,
        id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


# -----------------------------------------
# DELETE BOOKING
# -----------------------------------------

@app.route("/delete/<int:id>")
def delete_booking(id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = get_db()

    conn.execute("""
        DELETE FROM bookings
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/admin")


# -----------------------------------------
# WHATSAPP
# -----------------------------------------

@app.route("/whatsapp/<int:id>")
def whatsapp_booking(id):

    if not session.get("admin_logged_in"):
        return redirect("/login")

    conn = get_db()

    booking = conn.execute("""
        SELECT *
        FROM bookings
        WHERE id = ?
    """, (id,)).fetchone()

    conn.close()

    if booking is None:
        return redirect("/admin")

    message = f"""
Hello {booking['name']},

Thank you for choosing our cafe.

Your reservation details:

Name: {booking['name']}
Phone: {booking['phone']}
Date: {booking['date']}
Time: {booking['time']}
Guests: {booking['guests']}
Status: {booking['status']}

We look forward to serving you.

Thank you!
"""

    encoded_message = quote(message)

    whatsapp_url = (
        "https://wa.me/"
        + WHATSAPP_NUMBER
        + "?text="
        + encoded_message
    )

    return redirect(whatsapp_url)


# -----------------------------------------
# LOGOUT
# -----------------------------------------

@app.route("/logout")
def logout():

    session.pop("admin_logged_in", None)

    return redirect("/login")


# -----------------------------------------
# START SERVER
# -----------------------------------------

if __name__ == "__main__":

    create_database()

    app.run(debug=True)