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
        self.conn          = None
        self.mycursor      = None
        self.create_database()
        self.connect_database()
        self.create_tables()

    # ------------------------------------------------------------------
    # DATABASE SETUP
    # ------------------------------------------------------------------
    def create_database(self):
        try:
            tmp = sql.connect(host="127.0.0.1", port=3306, user="root", password="")
            cur = tmp.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {self.database_name}")
            tmp.commit()
            cur.close()
            tmp.close()
            print(f"Database '{self.database_name}' is ready")
        except Error as e:
            print(f"Database could not be created: {e}")
            raise

    def connect_database(self):
        try:
            self.conn = sql.connect(
                host="127.0.0.1", port=3306,
                user="root", password="",
                database=self.database_name
            )
            self.conn.autocommit = True
            self.mycursor = self.conn.cursor(dictionary=True)
            print("Database connected successfully")
        except Error as e:
            print(f"Database refused to connect: {e}")
            raise

    def create_tables(self):
        stmts = []

        stmts.append("""
            CREATE TABLE IF NOT EXISTS users (
                id         INT PRIMARY KEY,
                email      VARCHAR(100) UNIQUE NOT NULL,
                fullname   VARCHAR(100) NOT NULL,
                password   VARCHAR(160) NOT NULL,
                role       ENUM('student','staff','admin') NOT NULL,
                phone      VARCHAR(20)  DEFAULT NULL,
                department VARCHAR(100) DEFAULT NULL
            ) ENGINE=InnoDB
        """)

        stmts.append("""
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id   INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL UNIQUE,
                subject_code VARCHAR(20)  NOT NULL UNIQUE,
                description  TEXT DEFAULT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)

        stmts.append("""
            CREATE TABLE IF NOT EXISTS question (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                subject_id INT NOT NULL,
                question   TEXT NOT NULL,
                option_a   VARCHAR(255) NOT NULL,
                option_b   VARCHAR(255) NOT NULL,
                option_c   VARCHAR(255) NOT NULL,
                option_d   VARCHAR(255) NOT NULL,
                answer     ENUM('A','B','C','D') NOT NULL,
                CONSTRAINT fk_question_subject
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """)

        stmts.append("""
            CREATE TABLE IF NOT EXISTS results (
                result_id  INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                fullname   VARCHAR(100) NOT NULL,
                score      INT NOT NULL DEFAULT 0,
                total      INT NOT NULL DEFAULT 0,
                percent    FLOAT NOT NULL DEFAULT 0,
                grade      VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_results_student
                    FOREIGN KEY (student_id) REFERENCES users(id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_results_subject
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """)

        stmts.append("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id   INT AUTO_INCREMENT PRIMARY KEY,
                title       VARCHAR(150) NOT NULL UNIQUE,
                description TEXT DEFAULT NULL,
                duration    VARCHAR(50)  DEFAULT NULL,
                created_by  INT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_course_creator
                    FOREIGN KEY (created_by) REFERENCES users(id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """)

        stmts.append("""
            CREATE TABLE IF NOT EXISTS course_subjects (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                course_id  INT NOT NULL,
                subject_id INT NOT NULL,
                UNIQUE KEY uq_cs (course_id, subject_id),
                CONSTRAINT fk_cs_course
                    FOREIGN KEY (course_id) REFERENCES courses(course_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_cs_subject
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """)

        stmts.append("""
            CREATE TABLE IF NOT EXISTS enrollments (
                enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id    INT NOT NULL,
                course_id     INT NOT NULL,
                status        ENUM('enrolled','completed','dropped') NOT NULL DEFAULT 'enrolled',
                enrolled_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_enrollment (student_id, course_id),
                CONSTRAINT fk_enroll_student
                    FOREIGN KEY (student_id) REFERENCES users(id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_enroll_course
                    FOREIGN KEY (course_id) REFERENCES courses(course_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """)

        stmts.append("""
            CREATE TABLE IF NOT EXISTS lessons (
                lesson_id   INT AUTO_INCREMENT PRIMARY KEY,
                subject_id  INT NOT NULL,
                title       VARCHAR(150) NOT NULL,
                week        INT NOT NULL DEFAULT 1,
                topic       VARCHAR(150) DEFAULT NULL,
                content     LONGTEXT NOT NULL,
                created_by  INT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_lesson_subject
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_lesson_creator
                    FOREIGN KEY (created_by) REFERENCES users(id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB
        """)

        for stmt in stmts:
            self.mycursor.execute(stmt)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def get_schoolname(self):
        return self.__school_name

    def validate_email(self, email):
        return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None

    def hash_password(self, password):
        salt = os.urandom(32)
        key  = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
        return (salt + key).hex()

    def check_password(self, stored_hex, provided):
        try:
            if len(stored_hex) == 64:
                return secrets.compare_digest(
                    stored_hex, hashlib.sha256(provided.encode()).hexdigest()
                )
            b    = bytes.fromhex(stored_hex)
            salt = b[:32]
            key  = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt, 260_000)
            return secrets.compare_digest(b[32:], key)
        except Exception:
            return False

    def generate_verification_code(self, length=6):
        return "".join(str(secrets.randbelow(10)) for _ in range(length))

    def generate_strong_password(self, length=12):
        if length < 8:
            length = 8
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        chars = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*()"),
        ]
        chars.extend(secrets.choice(all_chars) for _ in range(length - 4))
        secrets.SystemRandom().shuffle(chars)
        return "".join(chars)

    # ------------------------------------------------------------------
    # EMAIL
    # ------------------------------------------------------------------
    def send_email(self, receiver_email, subject, body):
        smtp_host     = "smtp.gmail.com"
        smtp_port     = 465
        smtp_user     = "agboolataiwo385@gmail.com"
        smtp_password = "vwhapkhxnrgmwlsr"
        sender_email  = "agboolataiwo385@gmail.com"

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"]    = sender_email
        msg["To"]      = receiver_email
        msg.set_content(body)

        try:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            return {"status": True, "message": "Email sent successfully"}
        except Exception as e:
            return {"status": False, "message": f"Email failed: {e}"}

    def send_verification_email(self, receiver_email, code):
        return self.send_email(
            receiver_email,
            f"{self.get_schoolname()} — Verification Code",
            f"Your verification code is: {code}\n\nEnter this to complete registration."
        )

    def send_password_reset_email(self, receiver_email, code):
        return self.send_email(
            receiver_email,
            f"{self.get_schoolname()} — Password Reset",
            f"Your password reset code is: {code}\n\nIgnore if you did not request this."
        )

    # ------------------------------------------------------------------
    # USER MANAGEMENT
    # ------------------------------------------------------------------
    def create_account(self, email, fullname, password, confirm_password,
                       role, user_id, phone=None, department=None):
        if not self.validate_email(email):
            return {"status": False, "message": "Invalid email address"}
        if not fullname.strip():
            return {"status": False, "message": "Full name is required"}
        if password != confirm_password:
            return {"status": False, "message": "Passwords do not match"}
        if len(password) < 6:
            return {"status": False, "message": "Password must be at least 6 characters"}
        if role not in ("student", "staff", "admin"):
            return {"status": False, "message": "Invalid role"}
        try:
            hashed = self.hash_password(password)
            self.mycursor.execute(
                """INSERT INTO users(id, email, fullname, password, role, phone, department)
                   VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (user_id, email.strip(), fullname.strip(), hashed, role,
                 phone.strip() if phone else None,
                 department.strip() if department else None)
            )
            return {
                "status": True,
                "role": role,
                "message_student": f"Registration successful! Your matric number is {user_id}",
                "message_staff":   f"Registration successful! Your staff ID is {user_id}",
                "message_admin":   f"Admin account created! Your admin ID is {user_id}",
            }
        except IntegrityError:
            return {"status": False, "message": "Email or ID already exists. Try again."}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def login_user(self, email, password, expected_role=None):
        try:
            self.mycursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = self.mycursor.fetchone()
            if not user or not self.check_password(user["password"], password):
                return {"status": False, "message": "Invalid email or password"}
            if expected_role and user["role"] != expected_role:
                return {
                    "status": False,
                    "message": f"This account is not registered as {expected_role}. "
                               f"Please use the correct portal."
                }
            # Upgrade legacy SHA-256 hash
            if len(user["password"]) == 64:
                self.mycursor.execute(
                    "UPDATE users SET password=%s WHERE id=%s",
                    (self.hash_password(password), user["id"])
                )
            return {"status": True, "message": f"Welcome, {user['fullname']}!", "data": user}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def reset_password(self, email, new_password, confirm_password):
        if new_password != confirm_password:
            return {"status": False, "message": "Passwords do not match"}
        if len(new_password) < 6:
            return {"status": False, "message": "Password must be at least 6 characters"}
        try:
            self.mycursor.execute("SELECT id FROM users WHERE email=%s", (email,))
            if not self.mycursor.fetchone():
                return {"status": False, "message": "No account found with that email"}
            self.mycursor.execute(
                "UPDATE users SET password=%s WHERE email=%s",
                (self.hash_password(new_password), email)
            )
            return {"status": True, "message": "Password reset successfully. Please log in."}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def update_profile(self, user_id, fullname=None, phone=None, department=None):
        fields, values = [], []
        if fullname:   fields.append("fullname = %s");   values.append(fullname.strip())
        if phone:      fields.append("phone = %s");      values.append(phone.strip())
        if department: fields.append("department = %s"); values.append(department.strip())
        if not fields:
            return {"status": False, "message": "Nothing to update"}
        values.append(user_id)
        try:
            self.mycursor.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id=%s", values
            )
            self.mycursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            return {"status": True, "message": "Profile updated",
                    "data": self.mycursor.fetchone()}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def delete_user(self, user_id):
        try:
            self.mycursor.execute(
                "SELECT fullname, role FROM users WHERE id=%s", (user_id,)
            )
            user = self.mycursor.fetchone()
            if not user:
                return {"status": False, "message": "User not found"}
            self.mycursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
            return {"status": True,
                    "message": f"Account for '{user['fullname']}' deleted successfully"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_user_by_email(self, email):
        try:
            self.mycursor.execute("SELECT * FROM users WHERE email=%s", (email,))
            return self.mycursor.fetchone()
        except Exception:
            return None

    def get_all_users(self):
        try:
            self.mycursor.execute(
                "SELECT id, email, fullname, role, phone, department "
                "FROM users ORDER BY role, fullname ASC"
            )
            return self.mycursor.fetchall()
        except Exception:
            return []

    # ------------------------------------------------------------------
    # SUBJECT MANAGEMENT
    # ------------------------------------------------------------------
    def add_subject(self, subject_name, subject_code, description=""):
        try:
            self.mycursor.execute(
                "INSERT INTO subjects(subject_name, subject_code, description) VALUES(%s,%s,%s)",
                (subject_name.strip(), subject_code.strip().upper(),
                 description.strip() or None)
            )
            subject_id = self.mycursor.lastrowid
            return {"status": True, "subject_id": subject_id,
                    "message": f"Subject '{subject_name}' added (ID: {subject_id})"}
        except IntegrityError:
            return {"status": False, "message": "Subject name or code already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_all_subjects(self):
        try:
            self.mycursor.execute("""
                SELECT s.*,
                       COUNT(DISTINCT q.id)  AS question_count,
                       COUNT(DISTINCT l.lesson_id) AS lesson_count
                FROM subjects s
                LEFT JOIN question q ON q.subject_id = s.subject_id
                LEFT JOIN lessons  l ON l.subject_id = s.subject_id
                GROUP BY s.subject_id
                ORDER BY s.subject_name ASC
            """)
            subjects = self.mycursor.fetchall()
            if not subjects:
                return {"status": False, "message": "No subjects found", "subjects": []}
            return {"status": True, "subjects": subjects}
        except Exception as e:
            return {"status": False, "message": str(e), "subjects": []}

    def get_subject_by_id(self, subject_id):
        try:
            self.mycursor.execute(
                "SELECT * FROM subjects WHERE subject_id=%s", (subject_id,)
            )
            s = self.mycursor.fetchone()
            if not s:
                return {"status": False, "message": "Subject not found", "subject": None}
            return {"status": True, "subject": s}
        except Exception as e:
            return {"status": False, "message": str(e), "subject": None}

    def update_subject(self, subject_id, subject_name=None, subject_code=None,
                       description=None):
        fields, values = [], []
        if subject_name: fields.append("subject_name=%s"); values.append(subject_name.strip())
        if subject_code: fields.append("subject_code=%s"); values.append(subject_code.strip().upper())
        if description is not None:
            fields.append("description=%s"); values.append(description.strip() or None)
        if not fields:
            return {"status": False, "message": "Nothing to update"}
        values.append(subject_id)
        try:
            self.mycursor.execute(
                f"UPDATE subjects SET {', '.join(fields)} WHERE subject_id=%s", values
            )
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Subject not found"}
            return {"status": True, "message": "Subject updated"}
        except IntegrityError:
            return {"status": False, "message": "Subject name or code already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def delete_subject(self, subject_id):
        try:
            self.mycursor.execute(
                "SELECT subject_name FROM subjects WHERE subject_id=%s", (subject_id,)
            )
            s = self.mycursor.fetchone()
            if not s:
                return {"status": False, "message": "Subject not found"}
            self.mycursor.execute(
                "DELETE FROM subjects WHERE subject_id=%s", (subject_id,)
            )
            return {"status": True,
                    "message": f"Subject '{s['subject_name']}' and all its data deleted"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    # ------------------------------------------------------------------
    # QUESTION MANAGEMENT
    # ------------------------------------------------------------------
    def add_question(self, subject_id, question, option_a, option_b,
                     option_c, option_d, answer):
        answer = answer.strip().upper()
        if answer not in ("A", "B", "C", "D"):
            return {"status": False, "message": "Answer must be A, B, C, or D"}
        try:
            self.mycursor.execute(
                """INSERT INTO question(subject_id, question, option_a, option_b,
                                       option_c, option_d, answer)
                   VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (subject_id, question.strip(), option_a.strip(), option_b.strip(),
                 option_c.strip(), option_d.strip(), answer)
            )
            return {"status": True, "message": "Question added successfully"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_questions_by_subject(self, subject_id):
        try:
            self.mycursor.execute(
                "SELECT * FROM question WHERE subject_id=%s ORDER BY id ASC",
                (subject_id,)
            )
            qs = self.mycursor.fetchall()
            if not qs:
                return {"status": False, "message": "No questions for this subject",
                        "questions": []}
            return {"status": True, "questions": qs}
        except Exception as e:
            return {"status": False, "message": str(e), "questions": []}

    def get_question_count(self, subject_id):
        self.mycursor.execute(
            "SELECT COUNT(*) AS c FROM question WHERE subject_id=%s", (subject_id,)
        )
        return self.mycursor.fetchone()["c"]

    def update_question(self, question_id, question=None, option_a=None,
                        option_b=None, option_c=None, option_d=None, answer=None):
        fields, values = [], []
        if question is not None and question.strip():
            fields.append("question=%s");  values.append(question.strip())
        if option_a is not None and option_a.strip():
            fields.append("option_a=%s");  values.append(option_a.strip())
        if option_b is not None and option_b.strip():
            fields.append("option_b=%s");  values.append(option_b.strip())
        if option_c is not None and option_c.strip():
            fields.append("option_c=%s");  values.append(option_c.strip())
        if option_d is not None and option_d.strip():
            fields.append("option_d=%s");  values.append(option_d.strip())
        if answer is not None and answer.strip():
            a = answer.strip().upper()
            if a not in ("A", "B", "C", "D"):
                return {"status": False, "message": "Answer must be A, B, C, or D"}
            fields.append("answer=%s"); values.append(a)
        if not fields:
            return {"status": False, "message": "Nothing to update — no valid fields provided"}
        values.append(question_id)
        try:
            self.mycursor.execute(
                f"UPDATE question SET {', '.join(fields)} WHERE id=%s", values
            )
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Question not found"}
            return {"status": True, "message": "Question updated successfully"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def delete_question(self, question_id):
        try:
            self.mycursor.execute("SELECT id FROM question WHERE id=%s", (question_id,))
            if not self.mycursor.fetchone():
                return {"status": False, "message": "Question not found"}
            self.mycursor.execute("DELETE FROM question WHERE id=%s", (question_id,))
            return {"status": True, "message": "Question deleted"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_question_by_id(self, question_id):
        try:
            self.mycursor.execute("SELECT * FROM question WHERE id=%s", (question_id,))
            q = self.mycursor.fetchone()
            if not q:
                return {"status": False, "message": "Question not found", "question": None}
            return {"status": True, "question": q}
        except Exception as e:
            return {"status": False, "message": str(e), "question": None}

    # ------------------------------------------------------------------
    # EXAM ENGINE
    # ------------------------------------------------------------------
    def generate_exam_questions(self, subject_id, count=None):
        """Fetch and shuffle questions for a subject."""
        try:
            self.mycursor.execute(
                "SELECT * FROM question WHERE subject_id=%s", (subject_id,)
            )
            qs = self.mycursor.fetchall()
            if not qs:
                return {"status": False, "message": "No questions available for this subject"}
            random.shuffle(qs)
            if count and count < len(qs):
                qs = qs[:count]
            return {"status": True, "questions": qs}
        except Exception as e:
            return {"status": False, "message": str(e)}

    # ------------------------------------------------------------------
    # RESULT MANAGEMENT
    # ------------------------------------------------------------------
    def save_result(self, student_id, subject_id, fullname, score, total):
        percent = round((score / total * 100), 2) if total > 0 else 0
        grade   = self._calculate_grade(percent)
        try:
            self.mycursor.execute(
                """INSERT INTO results(student_id, subject_id, fullname,
                                      score, total, percent, grade)
                   VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (student_id, subject_id, fullname, score, total, percent, grade)
            )
            return {"status": True, "message": "Result saved",
                    "percent": percent, "grade": grade}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def _calculate_grade(self, percent):
        if percent >= 70: return "A"
        if percent >= 60: return "B"
        if percent >= 50: return "C"
        if percent >= 40: return "D"
        return "F"

    def get_results_by_student(self, student_id):
        try:
            self.mycursor.execute("""
                SELECT r.*, s.subject_name, s.subject_code
                FROM results r
                JOIN subjects s ON r.subject_id = s.subject_id
                WHERE r.student_id=%s
                ORDER BY r.created_at DESC
            """, (student_id,))
            return self.mycursor.fetchall()
        except Exception:
            return []

    def get_results_by_subject(self, subject_id):
        try:
            self.mycursor.execute("""
                SELECT r.*, s.subject_name
                FROM results r
                JOIN subjects s ON r.subject_id = s.subject_id
                WHERE r.subject_id=%s
                ORDER BY r.percent DESC, r.created_at DESC
            """, (subject_id,))
            rows = self.mycursor.fetchall()
            if not rows:
                return {"status": False, "message": "No results for this subject", "results": []}
            return {"status": True, "results": rows}
        except Exception as e:
            return {"status": False, "message": str(e), "results": []}

    def get_all_results(self):
        try:
            self.mycursor.execute("""
                SELECT r.*, s.subject_name, s.subject_code
                FROM results r
                JOIN subjects s ON r.subject_id = s.subject_id
                ORDER BY r.created_at DESC
            """)
            return self.mycursor.fetchall()
        except Exception:
            return []

    # ------------------------------------------------------------------
    # COURSE MANAGEMENT
    # ------------------------------------------------------------------
    def create_course(self, title, description, duration, created_by, subject_ids=None):
        if not title.strip():
            return {"status": False, "message": "Course title cannot be empty"}
        try:
            self.mycursor.execute(
                """INSERT INTO courses(title, description, duration, created_by)
                   VALUES(%s,%s,%s,%s)""",
                (title.strip(), description.strip() or None,
                 duration.strip() or None, created_by)
            )
            course_id = self.mycursor.lastrowid
            if subject_ids:
                for sid in subject_ids:
                    try:
                        self.mycursor.execute(
                            "INSERT INTO course_subjects(course_id, subject_id) VALUES(%s,%s)",
                            (course_id, sid)
                        )
                    except IntegrityError:
                        pass
            return {"status": True, "course_id": course_id,
                    "message": f"Course '{title}' created (ID: {course_id})"}
        except IntegrityError:
            return {"status": False, "message": "A course with that title already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_all_courses(self):
        try:
            self.mycursor.execute("""
                SELECT c.*, u.fullname AS created_by_name,
                       COUNT(DISTINCT cs.subject_id) AS subject_count,
                       COUNT(DISTINCT e.student_id)  AS enrolled_count
                FROM courses c
                LEFT JOIN users u ON c.created_by = u.id
                LEFT JOIN course_subjects cs ON cs.course_id = c.course_id
                LEFT JOIN enrollments e ON e.course_id = c.course_id
                                       AND e.status = 'enrolled'
                GROUP BY c.course_id
                ORDER BY c.created_at DESC
            """)
            rows = self.mycursor.fetchall()
            if not rows:
                return {"status": False, "message": "No courses found", "courses": []}
            return {"status": True, "courses": rows}
        except Exception as e:
            return {"status": False, "message": str(e), "courses": []}

    def get_course_by_id(self, course_id):
        try:
            self.mycursor.execute("""
                SELECT c.*, u.fullname AS created_by_name
                FROM courses c
                LEFT JOIN users u ON c.created_by = u.id
                WHERE c.course_id=%s
            """, (course_id,))
            course = self.mycursor.fetchone()
            if not course:
                return {"status": False, "message": "Course not found", "course": None}
            self.mycursor.execute("""
                SELECT s.subject_id, s.subject_name, s.subject_code
                FROM course_subjects cs
                JOIN subjects s ON cs.subject_id = s.subject_id
                WHERE cs.course_id=%s ORDER BY s.subject_name
            """, (course_id,))
            course["subjects"] = self.mycursor.fetchall()
            return {"status": True, "course": course}
        except Exception as e:
            return {"status": False, "message": str(e), "course": None}

    def update_course(self, course_id, title=None, description=None, duration=None):
        fields, values = [], []
        if title:
            fields.append("title=%s"); values.append(title.strip())
        if description is not None:
            fields.append("description=%s"); values.append(description.strip() or None)
        if duration is not None:
            fields.append("duration=%s"); values.append(duration.strip() or None)
        if not fields:
            return {"status": False, "message": "Nothing to update"}
        values.append(course_id)
        try:
            self.mycursor.execute(
                f"UPDATE courses SET {', '.join(fields)} WHERE course_id=%s", values
            )
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Course not found"}
            return {"status": True, "message": "Course updated"}
        except IntegrityError:
            return {"status": False, "message": "A course with that title already exists"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def delete_course(self, course_id):
        try:
            self.mycursor.execute(
                "SELECT title FROM courses WHERE course_id=%s", (course_id,)
            )
            c = self.mycursor.fetchone()
            if not c:
                return {"status": False, "message": "Course not found"}
            self.mycursor.execute("DELETE FROM courses WHERE course_id=%s", (course_id,))
            return {"status": True, "message": f"Course '{c['title']}' deleted"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def assign_subject_to_course(self, course_id, subject_id):
        try:
            self.mycursor.execute(
                "INSERT INTO course_subjects(course_id, subject_id) VALUES(%s,%s)",
                (course_id, subject_id)
            )
            return {"status": True, "message": "Subject assigned to course"}
        except IntegrityError:
            return {"status": False, "message": "Subject already in this course"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def remove_subject_from_course(self, course_id, subject_id):
        try:
            self.mycursor.execute(
                "DELETE FROM course_subjects WHERE course_id=%s AND subject_id=%s",
                (course_id, subject_id)
            )
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Subject not in this course"}
            return {"status": True, "message": "Subject removed from course"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    # ------------------------------------------------------------------
    # ENROLLMENT MANAGEMENT
    # ------------------------------------------------------------------
    def enroll_student(self, student_id, course_id):
        try:
            self.mycursor.execute(
                "SELECT course_id FROM courses WHERE course_id=%s", (course_id,)
            )
            if not self.mycursor.fetchone():
                return {"status": False, "message": "Course not found"}
            self.mycursor.execute(
                "INSERT INTO enrollments(student_id, course_id) VALUES(%s,%s)",
                (student_id, course_id)
            )
            return {"status": True, "message": "Enrolled successfully"}
        except IntegrityError:
            return {"status": False, "message": "Already enrolled in this course"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def update_enrollment_status(self, student_id, course_id, status):
        if status not in ("enrolled", "completed", "dropped"):
            return {"status": False, "message": "Invalid status"}
        try:
            self.mycursor.execute(
                "UPDATE enrollments SET status=%s WHERE student_id=%s AND course_id=%s",
                (status, student_id, course_id)
            )
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Enrollment not found"}
            return {"status": True, "message": f"Status updated to '{status}'"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_student_enrollments(self, student_id):
        try:
            self.mycursor.execute("""
                SELECT e.*, c.title, c.description, c.duration,
                       u.fullname AS created_by_name
                FROM enrollments e
                JOIN courses c ON e.course_id = c.course_id
                LEFT JOIN users u ON c.created_by = u.id
                WHERE e.student_id=%s
                ORDER BY e.enrolled_at DESC
            """, (student_id,))
            return self.mycursor.fetchall()
        except Exception:
            return []

    def get_course_enrollments(self, course_id):
        try:
            self.mycursor.execute("""
                SELECT e.*, u.fullname, u.email, u.department
                FROM enrollments e
                JOIN users u ON e.student_id = u.id
                WHERE e.course_id=%s
                ORDER BY e.enrolled_at DESC
            """, (course_id,))
            return self.mycursor.fetchall()
        except Exception:
            return []

    def get_enrollment(self, student_id, course_id):
        try:
            self.mycursor.execute(
                "SELECT * FROM enrollments WHERE student_id=%s AND course_id=%s",
                (student_id, course_id)
            )
            return self.mycursor.fetchone()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # LESSON MANAGEMENT
    # ------------------------------------------------------------------
    def add_lesson(self, subject_id, title, week, topic, content, created_by):
        if not title.strip():
            return {"status": False, "message": "Lesson title cannot be empty"}
        if not content.strip():
            return {"status": False, "message": "Lesson content cannot be empty"}
        if week < 1:
            return {"status": False, "message": "Week must be 1 or greater"}
        try:
            self.mycursor.execute(
                """INSERT INTO lessons(subject_id, title, week, topic, content, created_by)
                   VALUES(%s,%s,%s,%s,%s,%s)""",
                (subject_id, title.strip(), week,
                 topic.strip() or None, content.strip(), created_by)
            )
            return {"status": True, "lesson_id": self.mycursor.lastrowid,
                    "message": f"Lesson '{title}' added"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def get_lessons_by_subject(self, subject_id):
        try:
            self.mycursor.execute("""
                SELECT l.*, u.fullname AS created_by_name
                FROM lessons l
                LEFT JOIN users u ON l.created_by = u.id
                WHERE l.subject_id=%s
                ORDER BY l.week ASC, l.lesson_id ASC
            """, (subject_id,))
            rows = self.mycursor.fetchall()
            if not rows:
                return {"status": False, "message": "No lessons for this subject",
                        "lessons": []}
            return {"status": True, "lessons": rows}
        except Exception as e:
            return {"status": False, "message": str(e), "lessons": []}

    def get_lesson_by_id(self, lesson_id):
        try:
            self.mycursor.execute("""
                SELECT l.*, s.subject_name, s.subject_code,
                       u.fullname AS created_by_name
                FROM lessons l
                LEFT JOIN subjects s ON l.subject_id = s.subject_id
                LEFT JOIN users u ON l.created_by = u.id
                WHERE l.lesson_id=%s
            """, (lesson_id,))
            l = self.mycursor.fetchone()
            if not l:
                return {"status": False, "message": "Lesson not found", "lesson": None}
            return {"status": True, "lesson": l}
        except Exception as e:
            return {"status": False, "message": str(e), "lesson": None}

    def update_lesson(self, lesson_id, title=None, week=None, topic=None, content=None):
        fields, values = [], []
        if title:           fields.append("title=%s");   values.append(title.strip())
        if week is not None and week >= 1:
            fields.append("week=%s");    values.append(week)
        if topic is not None:
            fields.append("topic=%s");   values.append(topic.strip() or None)
        if content:         fields.append("content=%s"); values.append(content.strip())
        if not fields:
            return {"status": False, "message": "Nothing to update"}
        values.append(lesson_id)
        try:
            self.mycursor.execute(
                f"UPDATE lessons SET {', '.join(fields)} WHERE lesson_id=%s", values
            )
            if self.mycursor.rowcount == 0:
                return {"status": False, "message": "Lesson not found"}
            return {"status": True, "message": "Lesson updated"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def delete_lesson(self, lesson_id):
        try:
            self.mycursor.execute(
                "SELECT title FROM lessons WHERE lesson_id=%s", (lesson_id,)
            )
            l = self.mycursor.fetchone()
            if not l:
                return {"status": False, "message": "Lesson not found"}
            self.mycursor.execute("DELETE FROM lessons WHERE lesson_id=%s", (lesson_id,))
            return {"status": True, "message": f"Lesson '{l['title']}' deleted"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def close_connection(self):
        if self.mycursor:
            self.mycursor.close()
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    cfg = cbtconfig("AcademIQ")
    print(cfg.get_schoolname())