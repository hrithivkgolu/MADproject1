from flask import Flask, render_template, request, redirect, url_for,session,flash, abort
import sqlite3

app = Flask(__name__)
DB = "databases/users.db"
app.secret_key = "madhrithivkproj1"

@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    response.cache_control.no_cache = True
    response.cache_control.must_revalidate = True
    response.cache_control.max_age = 0
    return response
@app.route("/")
def home():
    return render_template("index.html")


#Account Creation
@app.route("/auth", methods=["GET", "POST"])
def auth():
    message = request.args.get("nessage")
    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, account_type FROM users WHERE (email=? or username=?) AND password=?",
            (email,email, password)
        )
        user = cur.fetchone()
        if user==None:
            flash("invalid username or password")
            return redirect(url_for("auth"))
        if user[1]=="company":
            status = cur.execute("SELECT approval FROM company where user_id=?",(user[0],)).fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["account_type"] = user[1]

            if session["account_type"] == "admin":
                flash("Login successfull")
                return redirect(url_for("admin"))

            elif session["account_type"] == "student":
                return redirect(url_for("student",user_id=session["user_id"]))

            elif session["account_type"] == "company":
                if status[0]=="approved":
                    return redirect(url_for("company",user_id=session["user_id"] ))
                else:
                    flash("User not approved!", "error")

        else:
            return redirect(url_for("register"))

    return render_template("auth.html", message=message)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        account_type = request.form["account_type"]
        username = request.form["username"]

        try:
            with sqlite3.connect(DB) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO users
                    (name, email, password, account_type, username)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, email, password, account_type, username))
                
                user_id = cur.lastrowid

            flash("User added successfully!", "success")

            if account_type == "company":
                return redirect(url_for("company_details", user_id=user_id))
            elif account_type == "student":
                return redirect(url_for("student_details", user_id=user_id))
            else:
                return redirect(url_for("auth"))

        except sqlite3.IntegrityError as e:
            flash(f"Error: Username Exists {e}", "error")
            return redirect(url_for("register"))  

        except sqlite3.DatabaseError as e:
            flash(f"Database error: {e}", "error")
            return redirect(url_for("register"))

        except Exception as e:
            flash(f"Unexpected error: {e}", "error")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/company/details/<int:user_id>",methods=["GET","POST"])
def company_details(user_id):

    if request.method == "POST":

        company_name = request.form["company_name"]
        hr_name = request.form["hr_name"]
        hr_email = request.form["hr_email"]

        with sqlite3.connect(DB) as conn:

            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO company
                (user_id, company_name, hr_name, hr_email)
                VALUES(?,?,?,?)
            """, (user_id,
                  company_name,
                  hr_name,
                  hr_email))

        flash("Company profile submitted... Await approval")
        return redirect(url_for("auth"))

    return render_template(
        "company/company_details.html",
        user_id=user_id
    )

@app.route("/student/details/<int:user_id>",methods=["GET","POST"])
def student_details(user_id):

    if request.method == "POST":

        student_name = request.form["student_name"]
        email = request.form["email"]
        course = request.form["course"]
        cgpa = request.form["cgpa"]
        graduation_year = request.form["graduation_year"]

        with sqlite3.connect(DB) as conn:

            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO student
                (user_id, name, email, course, cgpa, graduation_year)
                VALUES(?,?,?,?,?,?)
            """, (user_id,
                  student_name,
                  email,
                  course,
                  cgpa,
                  graduation_year))

        flash("User Created Please Login")
        return redirect(url_for("auth"))

    return render_template(
        "student/student_details.html",
        user_id=user_id
    )





#Admin
@app.route("/admin")
def admin():
    if "user_id" not in session:
        flash("Invalid session. Please login.")
        return redirect("/auth?message=invalid")   

    return render_template("admin/admin.html")

@app.route("/admin/overview")
def overview():
    search_query = request.args.get("search")
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    studentsearch=None
    companysearch=None
    if search_query:
        cur.execute("""
            SELECT * FROM student
            WHERE name LIKE ?
        """, ('%' + search_query + '%',))
        studentsearch = cur.fetchall()
        cur.execute("""
            SELECT * FROM company 
            WHERE company_name LIKE ?
        """, ('%' + search_query + '%',))
        companysearch = cur.fetchall()
    result = None
    if studentsearch:
        result = studentsearch
    if companysearch:
        result = companysearch

    cur.execute("""
        SELECT COUNT(*) FROM users
        WHERE account_type='student'
    """)
    students = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM users
        WHERE account_type='company'
    """)
    companies = cur.fetchone()[0]

    cur.execute("""
        SELECT * FROM company
        WHERE approval='pending'
    """)
    not_approved = cur.fetchall()

    cur.execute("SELECT * FROM placement")
    drives = cur.fetchall()

    conn.close()

    return render_template(
        "admin/overview.html",
        students=students,
        companies=companies,
        result = result,
        unapproved=not_approved,
        drives=drives,
        search_query=search_query
    )


#Admin Companies
@app.route("/admin/companies")
def view_companies():

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT company_id, company_name, hr_name,
               hr_email, approval
        FROM company
    """)

    companies = cur.fetchall()
    conn.close()

    return render_template(
        "admin/company.html",
        companies=companies
    )

@app.route("/admin/company/<int:id>/approve")
def approve_company(id):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "UPDATE company SET approval='approved' WHERE company_id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin/companies")

@app.route("/admin/company/<int:id>/blacklist")
def reject_company(id):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "UPDATE company SET approval='blacklisted' WHERE company_id=?",
        (id,)
    )
    
    conn.commit()
    conn.close()

    return redirect("/admin/companies")

@app.route("/admin/company/<int:id>/delete")
def delete_company(id):

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    result = cur.execute("SELECT user_id FROM company WHERE company_id=?",(id,)).fetchone()
    cur.execute("DELETE FROM users WHERE id=?",(result[0],))


    conn.commit()
    conn.close()

    return redirect("/admin/companies")



#Admin Users
@app.route("/admin/users")
def view_users():

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, name, email, created_at, account_type
        FROM users
    """)

    users = cur.fetchall()
    conn.close()

    return render_template(
        "admin/users.html",
        users=users
    )#note:- make the id like STD__ and COMP__ for better

@app.route("/admin/users/<int:id>/delete")
def delete_users(id):

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM users WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin/users")



#Admin Students
@app.route("/admin/student")
def view_student():

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, email, cgpa, course, graduation_year
        FROM student
    """)

    student = cur.fetchall()
    conn.close()

    return render_template(
        "admin/student.html",
        student=student
    )

@app.route("/admin/student/<int:id>/delete")
def delete_student(id):

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    result = cur.execute("SELECT user_id FROM student WHERE id=?",(id,)).fetchone()
    cur.execute(
        "DELETE FROM users WHERE id=?",
        (result[0],)
    )

    conn.commit()
    conn.close()

    return redirect("/admin/student")


@app.route("/student")
def student():
    if "user_id" not in session:
        flash("Invalid session. Please login.")
        return redirect("/auth?message=invalid")

    user_id = session["user_id"]

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    student = cur.execute(
        'SELECT * FROM student WHERE user_id = ?', 
        (user_id,)
    ).fetchone()
    conn.close()

    if student is None:
        abort(404)

    return render_template('student/student.html', student=student)

@app.route("/student/overview")
def std_overview():
    user_id = session["user_id"]
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    student = cur.execute(
        'SELECT * FROM student WHERE user_id = ?', 
        (user_id,)
    ).fetchone()
    conn.close()

    return render_template(
        "student/overview.html",
        student=student
    )





@app.route("/company/<int:user_id>")
def company(user_id):
    if "user_id" not in session:
        flash("Invalid session. Please login.")
        return redirect("/auth?message=invalid")   

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    company = conn.execute('SELECT * FROM company WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()

    if company is None:
        abort(404)  

    return render_template('company/company.html', company=company)

@app.route("/company/overview")
def com_overview():
    user_id = session["user_id"]
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    student = cur.execute(
        'SELECT * FROM company WHERE user_id = ?', 
        (user_id,)
    ).fetchone()
    conn.close()

    return render_template(
        "company/overview.html",
        company=company
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("logout successfull!!!")
    return redirect(url_for("auth"))


if __name__ == "__main__":
    app.run(debug=True)