import mysql.connector as sql
from mysql.connector import Error, IntegrityError
import random
import hashlib
import re
import os
import smtplib
import secrets
import string
from email.message import EmailMessage

class cbtconfig:
    def __init__(self, school_name, database_name="cbt_database"):
        self.__school_name = school_name
        self.database_name = database_name
        self.conn = None
        self.mycursor = None
        self.create_database()
        self.connect_database()
        self.create_tables()

    def create_database(self):
        """Create the MySQL database if it does not already exist."""
        try:
            temp_conn = sql.connect(
                host="127.0.0.1",
                port=3306,
                user="root",
                password=""
            )
            temp_cursor = temp_conn.cursor()
            temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database_name}")
            temp_conn.commit()
            temp_cursor.close()
            temp_conn.close()
            print(f"Database '{self.database_name}' is ready")
        except Error as e:
            print(f"Database could not be created: {e}")
            raise

    def connect_database(self):
        """Connect to the MySQL database after creating it."""
        try:
            self.conn = sql.connect(
                host="127.0.0.1",
                port=3306,
                user="root",
                password="",
                database=self.database_name
            )
            self.conn.autocommit = True
            self.mycursor = self.conn.cursor(dictionary=True)
            print("Database connected successfully")
        except Error as e:
            print(f"Database refused to connect: {e}")
            raise

    def create_tables(self):
        """Create all required tables if they do not already exist."""
        users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY,
                email VARCHAR(100) UNIQUE NOT NULL,
                fullname VARCHAR(100) NOT NULL,
                password VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL,
                phone VARCHAR(20) DEFAULT NULL,
                department VARCHAR(100) DEFAULT NULL
            ) ENGINE=InnoDB
        """

        subjects_table = """
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL UNIQUE,
                subject_code VARCHAR(20) NOT NULL UNIQUE,
                description TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """

        questions_table = """
            CREATE TABLE IF NOT EXISTS question (
                id INT AUTO_INCREMENT PRIMARY KEY,
                subject_id INT DEFAULT NULL,
                question TEXT NOT NULL UNIQUE,
                option_a VARCHAR(255) NOT NULL,
                option_b VARCHAR(255) NOT NULL,
                option_c VARCHAR(255) NOT NULL,
                option_d VARCHAR(255) NOT NULL,
                answer VARCHAR(255) NOT NULL,
                CONSTRAINT fk_question_subject
                    FOREIGN KEY (subject_id)
                    REFERENCES subjects(subject_id)
                    ON DELETE SET NULL
                    ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """

        results_table = """
            CREATE TABLE IF NOT EXISTS results (
                result_id INT AUTO_INCREMENT PRIMARY KEY,
                id INT NOT NULL,
                subject_id INT DEFAULT NULL,
                fullname VARCHAR(100) NOT NULL,
                percent FLOAT NOT NULL,
                grade VARCHAR(100) NOT NULL,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_results_users_id
                    FOREIGN KEY (id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
                CONSTRAINT fk_results_subject
                    FOREIGN KEY (subject_id)
                    REFERENCES subjects(subject_id)
                    ON DELETE SET NULL
                    ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """

        exams_table = """
            CREATE TABLE IF NOT EXISTS exams (
                exam_id INT AUTO_INCREMENT PRIMARY KEY,
                exam_title VARCHAR(150) NOT NULL UNIQUE,
                subject_id INT DEFAULT NULL,
                num_questions INT NOT NULL DEFAULT 10,
                duration_minutes INT NOT NULL DEFAULT 30,
                created_by INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_exams_subject
                    FOREIGN KEY (subject_id)
                    REFERENCES subjects(subject_id)
                    ON DELETE SET NULL
                    ON UPDATE CASCADE,
                CONSTRAINT fk_exams_creator
                    FOREIGN KEY (created_by)
                    REFERENCES users(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """

        self.mycursor.execute(users_table)
        self.mycursor.execute(subjects_table)
        self.mycursor.execute(questions_table)
        self.mycursor.execute(results_table)
        self.mycursor.execute(exams_table)

        # Safe migrations for existing databases
        migrations = [
            ("users",    "phone",      "VARCHAR(20) DEFAULT NULL"),
            ("users",    "department", "VARCHAR(100) DEFAULT NULL"),
            ("question", "subject_id", "INT DEFAULT NULL"),
            ("results",  "subject_id", "INT DEFAULT NULL"),
        ]
        for table, column, definition in migrations:
            try:
                self.mycursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )
            except Error:
                pass  # Column already exists

    # ------------------------------------------------------------------
    # GT SCHOOLNAME
    # ------------------------------------------------------------------
    def get_schoolname(self):
        return self.__school_name

    def validate_email(self, email):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def generate_verification_code(self, length=6):
        return "".join(str(secrets.randbelow(10)) for _ in range(length))

    def generate_strong_password(self, length=12):
        if length < 8:
            length = 8
        uppercase  = string.ascii_uppercase
        lowercase  = string.ascii_lowercase
        numbers    = string.digits
        symbols    = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        all_chars  = uppercase + lowercase + numbers + symbols
        chars = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(numbers),
            secrets.choice(symbols),
        ]
        chars.extend(secrets.choice(all_chars) for _ in range(length - 4))
        secrets.SystemRandom().shuffle(chars)
        return "".join(chars)

    # ------------------------------------------------------------------
    # EMAIL
    # ------------------------------------------------------------------
    def send_email(self, receiver_email, subject, body):
        smtp_host     = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port     = int(os.getenv("SMTP_PORT", "587"))
        smtp_user     = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email  = os.getenv("SMTP_SENDER", smtp_user)

        if not all([smtp_host, smtp_user, smtp_password, sender_email]):
            return {
                "status": False,
                "message": "Email settings are not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SMTP_SENDER."
            }

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"]    = sender_email
        msg["To"]      = receiver_email
        msg.set_content(body)

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            return {"status": True, "message": "Email sent successfully"}
        except Exception as e:
            return {"status": False, "message": f"Email could not be sent: {e}"}

    def send_verification_email(self, receiver_email, code):
        return self.send_email(
            receiver_email,
            "CBT Account Verification Code",
            f"Your CBT verification code is: {code}\n\nEnter this code to complete registration."
        )

    def send_password_reset_email(self, receiver_email, code):
        return self.send_email(
            receiver_email,
            "CBT Password Reset Code",
            f"Your CBT password reset code is: {code}\n\nIgnore this email if you did not request a reset."
        )

    # ------------------------------------------------------------------
    # USER MANAGEMENT
    # ------------------------------------------------------------------
    def create_account(self, email, fullname, password, confirm_password, role, user_id):
        if not self.validate_email(email):
            return {"status": False, "message": "Invalid email address"}
        if password != confirm_password:
            return {"status": False, "message": "Password does not match"}
        if role not in ("student", "staff", "admin"):
            return {"status": False, "message": "Role must be student, staff, or admin"}

        try:
            hashed = self.hash_password(password)
            self.mycursor.execute(
                "INSERT INTO users(email, fullname, password, role, id) VALUES(%s,%s,%s,%s,%s)",
                (email, fullname, hashed, role, user_id)
            )
            return {
                "status": True,
                "role": role,
                "message_student": f"Account created successfully. Your matric number is {user_id}",
                "message_staff":   f"Account created successfully. Your staff ID is {user_id}",
                "message_admin":   f"Admin account created successfully. Your admin ID is {user_id}",
            }
        except IntegrityError:
            return {"status": False, "message": "Email or ID already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def login_user(self, email, password):
        try:
            hashed = self.hash_password(password)
            self.mycursor.execute(
                "SELECT * FROM users WHERE email = %s AND password = %s",
                (email, hashed)
            )
            user = self.mycursor.fetchone()
            if user:
                return {"status": True, "message": f"Welcome {user['fullname']}", "data": user}
            return {"status": False, "message": "Invalid email or password"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def reset_password(self, email, new_password, confirm_password):
        if not self.validate_email(email):
            return {"status": False, "message": "Invalid email address"}
        if new_password != confirm_password:
            return {"status": False, "message": "Passwords do not match"}
        if len(new_password) < 6:
            return {"status": False, "message": "Password must be at least 6 characters"}
        try:
            self.mycursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if not self.mycursor.fetchone():
                return {"status": False, "message": "No account found with that email address"}
            self.mycursor.execute(
                "UPDATE users SET password = %s WHERE email = %s",
                (self.hash_password(new_password), email)
            )
            return {"status": True, "message": "Password reset successfully. You can now log in."}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def update_profile(self, user_id, fullname=None, phone=None, department=None):
        fields, values = [], []
        if fullname:
            fields.append("fullname = %s");    values.append(fullname.strip())
        if phone:
            fields.append("phone = %s");       values.append(phone.strip())
        if department:
            fields.append("department = %s");  values.append(department.strip())
        if not fields:
            return {"status": False, "message": "No fields provided to update"}
        values.append(user_id)
        try:
            self.mycursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = %s", values)
            self.mycursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return {"status": True, "message": "Profile updated successfully", "data": self.mycursor.fetchone()}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_user_by_email(self, email):
        try:
            self.mycursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return self.mycursor.fetchone()
        except Exception:
            return None

    def get_all_users(self):
        self.mycursor.execute("SELECT id, email, fullname, role FROM users ORDER BY id ASC")
        return self.mycursor.fetchall()

    # ------------------------------------------------------------------
    # SUBJECT MANAGEMENT
    # ------------------------------------------------------------------
    def add_subject(self, subject_name, subject_code, description=""):
        """Create a new subject."""
        try:
            self.mycursor.execute(
                "INSERT INTO subjects(subject_name, subject_code, description) VALUES(%s, %s, %s)",
                (subject_name.strip(), subject_code.strip().upper(), description.strip() or None)
            )
            return {"status": True, "message": f"Subject '{subject_name}' added successfully"}
        except IntegrityError:
            return {"status": False, "message": "Subject name or code already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_all_subjects(self):
        """Return all subjects ordered by name."""
        try:
            self.mycursor.execute("SELECT * FROM subjects ORDER BY subject_name ASC")
            subjects = self.mycursor.fetchall()
            if not subjects:
                return {"status": False, "message": "No subjects found", "subjects": []}
            return {"status": True, "message": "Subjects fetched successfully", "subjects": subjects}
        except Exception as e:
            return {"status": False, "message": str(e), "subjects": []}

    def get_subject_by_id(self, subject_id):
        """Return a single subject by its ID."""
        try:
            self.mycursor.execute("SELECT * FROM subjects WHERE subject_id = %s", (subject_id,))
            subject = self.mycursor.fetchone()
            if not subject:
                return {"status": False, "message": "Subject not found", "subject": None}
            return {"status": True, "message": "Subject fetched successfully", "subject": subject}
        except Exception as e:
            return {"status": False, "message": str(e), "subject": None}

    def update_subject(self, subject_id, subject_name=None, subject_code=None, description=None):
        """Update one or more fields of a subject."""
        fields, values = [], []
        if subject_name:
            fields.append("subject_name = %s");  values.append(subject_name.strip())
        if subject_code:
            fields.append("subject_code = %s");  values.append(subject_code.strip().upper())
        if description is not None:
            fields.append("description = %s");   values.append(description.strip() or None)
        if not fields:
            return {"status": False, "message": "No fields provided to update"}
        values.append(subject_id)
        try:
            self.mycursor.execute(f"UPDATE subjects SET {', '.join(fields)} WHERE subject_id = %s", values)
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Subject not found"}
            return {"status": True, "message": "Subject updated successfully"}
        except IntegrityError:
            return {"status": False, "message": "Subject name or code already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def delete_subject(self, subject_id):
        """Delete a subject. Questions in the subject will have subject_id set to NULL."""
        try:
            self.mycursor.execute("SELECT subject_name FROM subjects WHERE subject_id = %s", (subject_id,))
            subject = self.mycursor.fetchone()
            if not subject:
                return {"status": False, "message": "Subject not found"}
            self.mycursor.execute("DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
            return {"status": True, "message": f"Subject '{subject['subject_name']}' deleted successfully"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_questions_by_subject(self, subject_id):
        """Return all questions that belong to a given subject."""
        try:
            self.mycursor.execute(
                "SELECT * FROM question WHERE subject_id = %s ORDER BY id ASC",
                (subject_id,)
            )
            questions = self.mycursor.fetchall()
            if not questions:
                return {"status": False, "message": "No questions found for this subject", "questions": []}
            return {"status": True, "message": "Questions fetched successfully", "questions": questions}
        except Exception as e:
            return {"status": False, "message": str(e), "questions": []}

    # ------------------------------------------------------------------
    # QUESTION MANAGEMENT
    # ------------------------------------------------------------------
    def add_question(self, question, option_a, option_b, option_c, option_d, answer, subject_id=None):
        try:
            self.mycursor.execute(
                """INSERT INTO question(subject_id, question, option_a, option_b, option_c, option_d, answer)
                   VALUES(%s, %s, %s, %s, %s, %s, %s)""",
                (subject_id, question, option_a, option_b, option_c, option_d, answer)
            )
            return {"status": True, "message": "Question added successfully"}
        except IntegrityError:
            return {"status": False, "message": "Question already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def generate_all_questions(self):
        try:
            self.mycursor.execute("""
                SELECT q.*, s.subject_name, s.subject_code
                FROM question q
                LEFT JOIN subjects s ON q.subject_id = s.subject_id
                ORDER BY q.id ASC
            """)
            questions = self.mycursor.fetchall()
            if not questions:
                return {"status": False, "message": "No questions available", "questions": []}
            return {"status": True, "message": "Questions fetched successfully", "questions": questions}
        except Exception as e:
            return {"status": False, "message": str(e), "questions": []}

    def generate_question_by_id(self, question_id):
        try:
            self.mycursor.execute("""
                SELECT q.*, s.subject_name, s.subject_code
                FROM question q
                LEFT JOIN subjects s ON q.subject_id = s.subject_id
                WHERE q.id = %s
            """, (question_id,))
            question = self.mycursor.fetchone()
            if not question:
                return {"status": False, "message": "Question not found", "question": None}
            return {"status": True, "message": "Question fetched successfully", "question": question}
        except Exception as e:
            return {"status": False, "message": str(e), "question": None}

    # ------------------------------------------------------------------
    # EXAM MANAGEMENT
    # ------------------------------------------------------------------
    def create_exam(self, exam_title, subject_id, num_questions, duration_minutes, created_by):
        """Create a new configured exam."""
        if not exam_title.strip():
            return {"status": False, "message": "Exam title cannot be empty"}
        if num_questions < 1:
            return {"status": False, "message": "Number of questions must be at least 1"}
        if duration_minutes < 1:
            return {"status": False, "message": "Duration must be at least 1 minute"}

        # Check subject has enough questions
        if subject_id:
            try:
                self.mycursor.execute(
                    "SELECT COUNT(*) AS total FROM question WHERE subject_id = %s",
                    (subject_id,)
                )
                row = self.mycursor.fetchone()
                if row["total"] < num_questions:
                    return {
                        "status": False,
                        "message": f"Subject only has {row['total']} question(s) but you requested {num_questions}"
                    }
            except Exception as e:
                return {"status": False, "message": str(e)}
        else:
            try:
                self.mycursor.execute("SELECT COUNT(*) AS total FROM question")
                row = self.mycursor.fetchone()
                if row["total"] < num_questions:
                    return {
                        "status": False,
                        "message": f"Question pool only has {row['total']} question(s) but you requested {num_questions}"
                    }
            except Exception as e:
                return {"status": False, "message": str(e)}

        try:
            self.mycursor.execute(
                """INSERT INTO exams(exam_title, subject_id, num_questions, duration_minutes, created_by)
                   VALUES(%s, %s, %s, %s, %s)""",
                (exam_title.strip(), subject_id, num_questions, duration_minutes, created_by)
            )
            return {"status": True, "message": f"Exam '{exam_title}' created successfully"}
        except IntegrityError:
            return {"status": False, "message": "An exam with that title already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_all_exams(self):
        """Return all exams with subject and creator details."""
        try:
            self.mycursor.execute("""
                SELECT e.*, s.subject_name, s.subject_code,
                       u.fullname AS created_by_name
                FROM exams e
                LEFT JOIN subjects s ON e.subject_id = s.subject_id
                LEFT JOIN users u ON e.created_by = u.id
                ORDER BY e.created_at DESC
            """)
            exams = self.mycursor.fetchall()
            if not exams:
                return {"status": False, "message": "No exams found", "exams": []}
            return {"status": True, "exams": exams}
        except Exception as e:
            return {"status": False, "message": str(e), "exams": []}

    def get_exam_by_id(self, exam_id):
        """Return a single exam by ID."""
        try:
            self.mycursor.execute("""
                SELECT e.*, s.subject_name, s.subject_code,
                       u.fullname AS created_by_name
                FROM exams e
                LEFT JOIN subjects s ON e.subject_id = s.subject_id
                LEFT JOIN users u ON e.created_by = u.id
                WHERE e.exam_id = %s
            """, (exam_id,))
            exam = self.mycursor.fetchone()
            if not exam:
                return {"status": False, "message": "Exam not found", "exam": None}
            return {"status": True, "exam": exam}
        except Exception as e:
            return {"status": False, "message": str(e), "exam": None}

    def update_exam(self, exam_id, exam_title=None, subject_id=None,
                    num_questions=None, duration_minutes=None):
        """Update one or more fields of an exam."""
        fields, values = [], []
        if exam_title is not None:
            fields.append("exam_title = %s");       values.append(exam_title.strip())
        if subject_id is not None:
            fields.append("subject_id = %s");       values.append(subject_id)
        if num_questions is not None:
            fields.append("num_questions = %s");    values.append(num_questions)
        if duration_minutes is not None:
            fields.append("duration_minutes = %s"); values.append(duration_minutes)
        if not fields:
            return {"status": False, "message": "No fields provided to update"}
        values.append(exam_id)
        try:
            self.mycursor.execute(
                f"UPDATE exams SET {', '.join(fields)} WHERE exam_id = %s", values
            )
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Exam not found"}
            return {"status": True, "message": "Exam updated successfully"}
        except IntegrityError:
            return {"status": False, "message": "An exam with that title already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def delete_exam(self, exam_id):
        """Delete an exam configuration."""
        try:
            self.mycursor.execute("SELECT exam_title FROM exams WHERE exam_id = %s", (exam_id,))
            exam = self.mycursor.fetchone()
            if not exam:
                return {"status": False, "message": "Exam not found"}
            self.mycursor.execute("DELETE FROM exams WHERE exam_id = %s", (exam_id,))
            return {"status": True, "message": f"Exam '{exam['exam_title']}' deleted successfully"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def generate_exams(self, subject_id=None, num_questions=None, duration_minutes=30):
        """Generate a shuffled exam, optionally filtered by subject and capped by num_questions."""
        try:
            if subject_id:
                self.mycursor.execute(
                    "SELECT * FROM question WHERE subject_id = %s", (subject_id,)
                )
            else:
                self.mycursor.execute("SELECT * FROM question")
            questions = self.mycursor.fetchall()
            if not questions:
                return {"status": False, "message": "No questions available for this exam"}
            random.shuffle(questions)
            if num_questions and num_questions < len(questions):
                questions = questions[:num_questions]
            return {"status": True, "question": questions, "time": duration_minutes}
        except Exception as e:
            return {"status": False, "message": str(e)}

    # ------------------------------------------------------------------
    # RESULT MANAGEMENT
    # ------------------------------------------------------------------
    def save_result(self, user, percent, grade, responses, subject_id=None):
        try:
            self.mycursor.execute(
                "INSERT INTO results(id, subject_id, fullname, percent, grade, response) VALUES(%s,%s,%s,%s,%s,%s)",
                (user["id"], subject_id, user["fullname"], percent, grade, ", ".join(responses))
            )
            return {"status": True, "message": "Result saved successfully"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_result(self, user):
        self.mycursor.execute(
            """SELECT r.*, s.subject_name FROM results r
               LEFT JOIN subjects s ON r.subject_id = s.subject_id
               WHERE r.id = %s ORDER BY r.created_at DESC LIMIT 1""",
            (user["id"],)
        )
        return self.mycursor.fetchone()

    def get_all_results(self):
        self.mycursor.execute("""
            SELECT r.*, s.subject_name FROM results r
            LEFT JOIN subjects s ON r.subject_id = s.subject_id
            ORDER BY r.created_at DESC
        """)
        return self.mycursor.fetchall()

    def get_all_results_by_subject(self, subject_id):
        """Return all results for a specific subject."""
        try:
            self.mycursor.execute(
                """SELECT r.*, s.subject_name FROM results r
                   LEFT JOIN subjects s ON r.subject_id = s.subject_id
                   WHERE r.subject_id = %s ORDER BY r.created_at DESC""",
                (subject_id,)
            )
            results = self.mycursor.fetchall()
            if not results:
                return {"status": False, "message": "No results found for this subject", "results": []}
            return {"status": True, "results": results}
        except Exception as e:
            return {"status": False, "message": str(e), "results": []}

    def close_connection(self):
        if self.mycursor:
            self.mycursor.close()
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    app_config = cbtconfig("Taiwo CBT")
    print(app_config.get_schoolname())