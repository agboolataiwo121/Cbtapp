from random import randint
from cbtconfig import cbtconfig
import threading
import time

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class cbtapp(cbtconfig):
    def __init__(self, school_name):
        super().__init__(school_name)
        self.home()

    # ==================================================================
    # HOME MENU
    # ==================================================================
    def home(self):
        while True:
            print(f"""
            ================================
             Welcome to {self.get_schoolname()}
            ================================
            1. Register
            2. Login
            3. Reset Password
            4. Exit
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.register()
            elif choice == "2": self.login()
            elif choice == "3": self.reset_password_flow()
            elif choice == "4":
                self.close_connection()
                print("Goodbye!")
                exit()
            else:
                print("Invalid choice. Please try again.")

    # ==================================================================
    # SPEECH
    # ==================================================================
    def speak_text(self, text):
        if pyttsx3 is None:
            return
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

    # ==================================================================
    # TIMER
    # ==================================================================
    def exam_countdown_timer(self, total_seconds, timer_state):
        while total_seconds > 0 and not timer_state["submitted"]:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if total_seconds % 60 == 0 or total_seconds <= 10:
                print(f"\n  Time remaining: {minutes:02d}:{seconds:02d}")
            time.sleep(1)
            total_seconds -= 1
        if not timer_state["submitted"]:
            timer_state["time_up"] = True
            print("\n  Time is up! Exam submitted automatically.")

    # ==================================================================
    # REGISTER
    # ==================================================================
    def register(self):
        print("\n--- Register ---")
        email = input("Enter email: ").strip()
        if not self.validate_email(email):
            print("Invalid email address.")
            return

        code   = self.generate_verification_code()
        result = self.send_verification_email(email, code)
        print(result["message"])

        entered = input("Enter verification code: ").strip()
        if entered != code:
            print("Invalid code. Registration cancelled.")
            return

        fullname = input("Enter full name: ").strip()
        if not fullname:
            print("Full name is required.")
            return

        role = input("Enter role (student / staff / admin): ").strip().lower()

        if input("Generate a strong password? yes/no: ").strip().lower() == "yes":
            password         = self.generate_strong_password()
            confirm_password = password
            print(f"Generated password: {password}  — please save this.")
        else:
            password         = input("Enter password: ")
            confirm_password = input("Confirm password: ")

        user_id = randint(100000, 999999)
        result  = self.create_account(email, fullname, password, confirm_password, role, user_id)

        if result["status"]:
            key = f"message_{result['role']}"
            print(result.get(key, "Account created successfully"))
        else:
            print(result["message"])

    # ==================================================================
    # LOGIN
    # ==================================================================
    def login(self):
        print("\n--- Login ---")
        email    = input("Enter email: ").strip()
        password = input("Enter password: ")
        result   = self.login_user(email, password)

        if result["status"]:
            user = result["data"]
            print(result["message"])
            if   user["role"] == "student": self.student_dashboard(user)
            elif user["role"] == "staff":   self.staff_dashboard(user)
            elif user["role"] == "admin":   self.admin_dashboard(user)
            else: print("Unknown user role.")
        else:
            print(result["message"])

    # ==================================================================
    # RESET PASSWORD
    # ==================================================================
    def reset_password_flow(self):
        print("\n--- Reset Password ---")
        email = input("Enter your registered email: ").strip()
        if not self.validate_email(email):
            print("Invalid email address.")
            return
        if not self.get_user_by_email(email):
            print("No account found with that email.")
            return

        code   = self.generate_verification_code()
        result = self.send_password_reset_email(email, code)
        print(result["message"])

        entered = input("Enter reset code: ").strip()
        if entered != code:
            print("Invalid code. Password reset cancelled.")
            return

        new_pw  = input("New password: ")
        confirm = input("Confirm new password: ")
        result  = self.reset_password(email, new_pw, confirm)
        print(result["message"])

    # ==================================================================
    # UPDATE PROFILE
    # ==================================================================
    def update_profile_flow(self, user):
        print("\n--- Update Profile ---")
        print(f"Full name  : {user.get('fullname', '')}")
        print(f"Phone      : {user.get('phone') or 'Not set'}")
        print(f"Department : {user.get('department') or 'Not set'}")
        print("Press Enter to keep the current value.")

        fullname   = input("New full name  : ").strip()
        phone      = input("New phone      : ").strip()
        department = input("New department : ").strip()

        result = self.update_profile(
            user["id"],
            fullname=fullname     or None,
            phone=phone           or None,
            department=department or None
        )
        print(result["message"])
        return result["data"] if result["status"] else user

    # ==================================================================
    # STUDENT DASHBOARD
    # ==================================================================
    def student_dashboard(self, user):
        while True:
            print(f"""
            ================================
             STUDENT — {user['fullname']}
            ================================
            1. Take exam by subject
            2. Take quick exam (all questions)
            3. View my results
            4. View my details
            5. Update profile
            6. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.take_exam_by_subject(user)
            elif choice == "2": self.take_quick_exam(user)
            elif choice == "3": self.view_my_results(user)
            elif choice == "4": self.view_details(user)
            elif choice == "5": user = self.update_profile_flow(user)
            elif choice == "6": break
            else: print("Invalid choice.")

    # ==================================================================
    # TAKE EXAM BY SUBJECT
    # ==================================================================
    def take_exam_by_subject(self, user):
        """Student picks a subject and takes all its questions in 5 minutes."""
        result = self.get_all_subjects()
        if not result["status"]:
            print("No subjects available yet.")
            return

        print("\n--- Available Subjects ---")
        print(f"{'ID':<5} {'Code':<12} {'Name':<30} {'Questions'}")
        print("-" * 60)
        for s in result["subjects"]:
            print(f"{s['subject_id']:<5} {s['subject_code']:<12} "
                  f"{s['subject_name']:<30} {s['question_count']}")

        subject_id = self._get_int_input("\nEnter subject ID: ")
        if subject_id is None:
            return

        check = self.get_subject_by_id(subject_id)
        if not check["status"]:
            print("Subject not found.")
            return

        subject = check["subject"]
        count   = self.get_question_count_by_subject(subject_id)

        if count == 0:
            print(f"No questions available for '{subject['subject_name']}' yet.")
            return

        print(f"\n  Subject  : {subject['subject_name']} ({subject['subject_code']})")
        print(f"  Questions: {count}")
        print(f"  Duration : 5 minutes (fixed)")

        if input("\n  Ready to start? yes/no: ").strip().lower() != "yes":
            print("Exam cancelled.")
            return

        self.take_exams(user, subject_id=subject_id,
                        num_questions=count, duration_minutes=5)

    # ==================================================================
    # TAKE QUICK EXAM (all questions)
    # ==================================================================
    def take_quick_exam(self, user):
        """Take an exam on all available questions in 5 minutes."""
        total = self._total_questions()
        if total == 0:
            print("No questions available yet.")
            return

        print(f"\n--- Quick Exam ---")
        print(f"  Questions: {total} (all available)")
        print(f"  Duration : 5 minutes (fixed)")

        if input("\n  Ready to start? yes/no: ").strip().lower() != "yes":
            print("Exam cancelled.")
            return

        self.take_exams(user, subject_id=None,
                        num_questions=total, duration_minutes=5)

    # ==================================================================
    # STAFF DASHBOARD
    # ==================================================================
    def staff_dashboard(self, user):
        while True:
            print(f"""
            ================================
             STAFF — {user['fullname']}
            ================================
            1. Subject management
            2. Question management
            3. Exam management
            4. View my details
            5. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.subject_menu(user)
            elif choice == "2": self.question_menu()
            elif choice == "3": self.exam_menu(user)
            elif choice == "4": self.view_details(user)
            elif choice == "5": break
            else: print("Invalid choice.")

    # ==================================================================
    # ADMIN DASHBOARD
    # ==================================================================
    def admin_dashboard(self, user):
        while True:
            print(f"""
            ================================
             ADMIN — {user['fullname']}
            ================================
            1. Subject management
            2. Question management
            3. Exam management
            4. View all users
            5. View all results
            6. View my details
            7. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.subject_menu(user)
            elif choice == "2": self.question_menu()
            elif choice == "3": self.exam_menu(user)
            elif choice == "4": self.view_all_users()
            elif choice == "5": self.view_all_results()
            elif choice == "6": self.view_details(user)
            elif choice == "7": break
            else: print("Invalid choice.")

    # ==================================================================
    # SUBJECT MANAGEMENT
    # ==================================================================
    def subject_menu(self, user):
        while True:
            print("""
            --- Subject Management ---
            1. Add subject
            2. View all subjects
            3. View subject by ID
            4. Update subject
            5. Delete subject
            6. Add questions to a subject
            7. View questions in a subject
            8. Edit a question
            9. Delete a question
            10. View results by subject
            11. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1":  self._add_subject()
            elif choice == "2":  self._view_all_subjects()
            elif choice == "3":  self._view_subject_by_id()
            elif choice == "4":  self._update_subject()
            elif choice == "5":  self._delete_subject()
            elif choice == "6":  self._add_questions_to_subject()
            elif choice == "7":  self._view_questions_in_subject()
            elif choice == "8":  self._edit_question()
            elif choice == "9":  self._delete_question()
            elif choice == "10": self._view_results_by_subject()
            elif choice == "11": break
            else: print("Invalid choice.")

    def _add_subject(self):
        print("\n--- Add Subject ---")
        name        = input("Subject name        : ").strip()
        code        = input("Subject code        : ").strip()
        description = input("Description (optional): ").strip()
        result      = self.add_subject(name, code, description)
        print(result["message"])
        if result["status"]:
            print(f"  → You can now add questions to subject ID: {result['subject_id']}")

    def _view_all_subjects(self):
        result = self.get_all_subjects()
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{'ID':<5} {'Code':<12} {'Name':<30} {'Questions':<12} {'Description'}")
        print("-" * 80)
        for s in result["subjects"]:
            desc = (s["description"] or "")[:25]
            print(f"{s['subject_id']:<5} {s['subject_code']:<12} "
                  f"{s['subject_name']:<30} {s['question_count']:<12} {desc}")

    def _view_subject_by_id(self):
        subject_id = self._get_int_input("Enter subject ID: ")
        if subject_id is None:
            return
        result = self.get_subject_by_id(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        s     = result["subject"]
        count = self.get_question_count_by_subject(subject_id)
        print(f"\n  ID          : {s['subject_id']}")
        print(f"  Name        : {s['subject_name']}")
        print(f"  Code        : {s['subject_code']}")
        print(f"  Description : {s['description'] or 'None'}")
        print(f"  Questions   : {count}")
        print(f"  Created     : {s['created_at']}")

    def _update_subject(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID to update: ")
        if subject_id is None:
            return
        check = self.get_subject_by_id(subject_id)
        if not check["status"]:
            print(check["message"])
            return
        s = check["subject"]
        print("Press Enter to keep the current value.")
        name        = input(f"New name [{s['subject_name']}]: ").strip()
        code        = input(f"New code [{s['subject_code']}]: ").strip()
        description = input(f"New description [{s['description'] or ''}]: ").strip()
        result = self.update_subject(
            subject_id,
            subject_name=name        or None,
            subject_code=code        or None,
            description=description  if description != "" else None
        )
        print(result["message"])

    def _delete_subject(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID to delete: ")
        if subject_id is None:
            return
        if input("Are you sure? Questions will be unassigned. yes/no: ").strip().lower() != "yes":
            print("Cancelled.")
            return
        print(self.delete_subject(subject_id)["message"])

    def _add_questions_to_subject(self):
        """
        Add one or multiple questions to a subject interactively.
        After each question the user is asked if they want to add another.
        """
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID to add questions to: ")
        if subject_id is None:
            return

        check = self.get_subject_by_id(subject_id)
        if not check["status"]:
            print("Subject not found.")
            return

        subject = check["subject"]
        print(f"\nAdding questions to: {subject['subject_name']} ({subject['subject_code']})")
        print("Enter question details. Type 'done' as the question to stop.\n")

        added = 0
        while True:
            question = input(f"Question {added + 1}: ").strip()
            if question.lower() == "done" or not question:
                break

            option_a = input("  Option A: ").strip()
            option_b = input("  Option B: ").strip()
            option_c = input("  Option C: ").strip()
            option_d = input("  Option D: ").strip()
            answer   = input("  Correct answer (A/B/C/D): ").strip().upper()

            if answer not in ("A", "B", "C", "D"):
                print("  Invalid answer. Must be A, B, C, or D. Question skipped.")
                continue

            result = self.add_question(
                question, option_a, option_b, option_c, option_d, answer, subject_id
            )
            if result["status"]:
                added += 1
                print(f"  ✓ Question {added} added.\n")
            else:
                print(f"  ✗ {result['message']}\n")

            cont = input("Add another question? yes/no: ").strip().lower()
            if cont != "yes":
                break

        count = self.get_question_count_by_subject(subject_id)
        print(f"\n{added} question(s) added. "
              f"Subject '{subject['subject_name']}' now has {count} question(s) total.")

    def _view_questions_in_subject(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID: ")
        if subject_id is None:
            return
        result = self.get_questions_by_subject(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{len(result['questions'])} question(s) found:\n")
        for q in result["questions"]:
            self._display_question(q)

    def _edit_question(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID to browse questions: ")
        if subject_id is None:
            return
        result = self.get_questions_by_subject(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        for q in result["questions"]:
            self._display_question(q)

        q_id = self._get_int_input("\nEnter question ID to edit: ")
        if q_id is None:
            return
        check = self.generate_question_by_id(q_id)
        if not check["status"]:
            print("Question not found.")
            return
        q = check["question"]
        print("Press Enter to keep the current value.")
        question = input(f"Question [{q['question'][:40]}...]: ").strip() or None
        option_a = input(f"Option A [{q['option_a']}]: ").strip() or None
        option_b = input(f"Option B [{q['option_b']}]: ").strip() or None
        option_c = input(f"Option C [{q['option_c']}]: ").strip() or None
        option_d = input(f"Option D [{q['option_d']}]: ").strip() or None
        answer   = input(f"Answer   [{q['answer']}]: ").strip().upper() or None

        result = self.update_question(
            q_id, question=question, option_a=option_a,
            option_b=option_b, option_c=option_c,
            option_d=option_d, answer=answer
        )
        print(result["message"])

    def _delete_question(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID to browse questions: ")
        if subject_id is None:
            return
        result = self.get_questions_by_subject(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        for q in result["questions"]:
            self._display_question(q)

        q_id = self._get_int_input("\nEnter question ID to delete: ")
        if q_id is None:
            return
        if input("Are you sure? yes/no: ").strip().lower() != "yes":
            print("Cancelled.")
            return
        print(self.delete_question(q_id)["message"])

    def _view_results_by_subject(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID: ")
        if subject_id is None:
            return
        result = self.get_all_results_by_subject(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{'Name':<25} {'Score':<10} {'Grade':<20} {'Date'}")
        print("-" * 70)
        for r in result["results"]:
            print(f"{r['fullname'][:23]:<25} {r['percent']:<10.2f} "
                  f"{r['grade']:<20} {str(r['created_at'])[:19]}")

    # ==================================================================
    # QUESTION MANAGEMENT
    # ==================================================================
    def question_menu(self):
        while True:
            print("""
            --- Question Management ---
            1. Add question (no subject)
            2. View all questions
            3. View question by ID
            4. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._add_question_no_subject()
            elif choice == "2": self.display_all_questions()
            elif choice == "3": self.display_question_by_id()
            elif choice == "4": break
            else: print("Invalid choice.")

    def _add_question_no_subject(self):
        print("\n--- Add Question (No Subject) ---")
        question = input("Question : ").strip()
        option_a = input("Option A : ").strip()
        option_b = input("Option B : ").strip()
        option_c = input("Option C : ").strip()
        option_d = input("Option D : ").strip()
        answer   = input("Answer (A/B/C/D): ").strip().upper()
        result   = self.add_question(
            question, option_a, option_b, option_c, option_d, answer, None
        )
        print(result["message"])

    def display_all_questions(self):
        result = self.generate_all_questions()
        if not result["status"]:
            print(result["message"])
            return
        for q in result["questions"]:
            self._display_question(q)

    def display_question_by_id(self):
        question_id = self._get_int_input("Enter question ID: ")
        if question_id is None:
            return
        result = self.generate_question_by_id(question_id)
        if not result["status"]:
            print(result["message"])
            return
        self._display_question(result["question"])

    # ==================================================================
    # EXAM MANAGEMENT
    # ==================================================================
    def exam_menu(self, user):
        while True:
            print("""
            --- Exam Management ---
            1. Create exam
            2. View all exams
            3. View exam by ID
            4. Update exam
            5. Delete exam
            6. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._create_exam(user)
            elif choice == "2": self._view_all_exams()
            elif choice == "3": self._view_exam_by_id()
            elif choice == "4": self._update_exam()
            elif choice == "5": self._delete_exam()
            elif choice == "6": break
            else: print("Invalid choice.")

    def _create_exam(self, user):
        print("\n--- Create Exam ---")
        exam_title = input("Exam title: ").strip()
        if not exam_title:
            print("Exam title cannot be empty.")
            return

        self._view_all_subjects()
        raw = input("Select subject ID (or Enter for all subjects): ").strip()
        subject_id = int(raw) if raw.isdigit() else None
        if subject_id:
            check = self.get_subject_by_id(subject_id)
            if not check["status"]:
                print("Subject not found. Exam will draw from all questions.")
                subject_id = None

        num_questions = self._get_int_input("Number of questions: ")
        if num_questions is None or num_questions < 1:
            print("Invalid number of questions.")
            return

        duration_minutes = self._get_int_input("Duration in minutes: ")
        if duration_minutes is None or duration_minutes < 1:
            print("Invalid duration.")
            return

        result = self.create_exam(
            exam_title, subject_id, num_questions, duration_minutes, user["id"]
        )
        print(result["message"])

    def _view_all_exams(self):
        result = self.get_all_exams()
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{'ID':<5} {'Title':<30} {'Subject':<20} {'Qs':<5} {'Mins':<6} {'Created By'}")
        print("-" * 80)
        for e in result["exams"]:
            subj = (e["subject_name"] or "All subjects")[:18]
            print(f"{e['exam_id']:<5} {e['exam_title'][:28]:<30} {subj:<20} "
                  f"{e['num_questions']:<5} {e['duration_minutes']:<6} {e['created_by_name']}")

    def _view_exam_by_id(self):
        exam_id = self._get_int_input("Enter exam ID: ")
        if exam_id is None:
            return
        result = self.get_exam_by_id(exam_id)
        if not result["status"]:
            print(result["message"])
            return
        e = result["exam"]
        print(f"\n  ID         : {e['exam_id']}")
        print(f"  Title      : {e['exam_title']}")
        print(f"  Subject    : {e['subject_name'] or 'All subjects'}")
        print(f"  Questions  : {e['num_questions']}")
        print(f"  Duration   : {e['duration_minutes']} minutes")
        print(f"  Created by : {e['created_by_name']}")
        print(f"  Created at : {e['created_at']}")

    def _update_exam(self):
        self._view_all_exams()
        exam_id = self._get_int_input("Enter exam ID to update: ")
        if exam_id is None:
            return
        check = self.get_exam_by_id(exam_id)
        if not check["status"]:
            print(check["message"])
            return
        e = check["exam"]
        print("Press Enter to keep the current value.")
        title  = input(f"Title [{e['exam_title']}]: ").strip() or None
        raw_q  = input(f"Questions [{e['num_questions']}]: ").strip()
        num_q  = int(raw_q) if raw_q.isdigit() else None
        raw_d  = input(f"Duration [{e['duration_minutes']}]: ").strip()
        dur    = int(raw_d) if raw_d.isdigit() else None
        result = self.update_exam(exam_id, exam_title=title,
                                  num_questions=num_q, duration_minutes=dur)
        print(result["message"])

    def _delete_exam(self):
        self._view_all_exams()
        exam_id = self._get_int_input("Enter exam ID to delete: ")
        if exam_id is None:
            return
        if input("Are you sure? yes/no: ").strip().lower() != "yes":
            print("Cancelled.")
            return
        print(self.delete_exam(exam_id)["message"])

    # ==================================================================
    # EXAM ENGINE
    # ==================================================================
    def _normalize_answer(self, ans):
        ans = ans.strip().upper()
        return ans[0] if ans else ""

    def take_exams(self, user, subject_id=None, num_questions=None, duration_minutes=None):
        exam = self.generate_exams(
            subject_id=subject_id,
            num_questions=num_questions,
            duration_minutes=duration_minutes or 30
        )
        if not exam["status"]:
            print(exam["message"])
            return

        questions    = exam["question"]
        responses    = []
        score        = 0
        exam_minutes = exam.get("time", 30)
        timer_state  = {"time_up": False, "submitted": False}
        use_speech   = input("Read questions aloud? yes/no: ").strip().lower() == "yes"

        print(f"\n  {len(questions)} questions | {exam_minutes} minutes | Timer started.\n")

        timer_thread = threading.Thread(
            target=self.exam_countdown_timer,
            args=(exam_minutes * 60, timer_state),
            daemon=True
        )
        timer_thread.start()

        for number, item in enumerate(questions, start=1):
            if timer_state["time_up"]:
                break

            print(f"\nQuestion {number}/{len(questions)}: {item['question']}")
            print(f"  A. {item['option_a']}")
            print(f"  B. {item['option_b']}")
            print(f"  C. {item['option_c']}")
            print(f"  D. {item['option_d']}")

            if use_speech:
                self.speak_text(
                    f"Question {number}. {item['question']}. "
                    f"A. {item['option_a']}. B. {item['option_b']}. "
                    f"C. {item['option_c']}. D. {item['option_d']}."
                )

            response = input("Your answer (A/B/C/D): ").strip()

            if timer_state["time_up"]:
                print("  Time expired. This answer will not be scored.")
                break

            responses.append(response)
            if self._normalize_answer(response) == self._normalize_answer(item["answer"]):
                score += 1
                print("  ✓ Correct!")
            else:
                print(f"  ✗ Wrong. Correct answer: {item['answer']}")

        timer_state["submitted"] = True

        total   = len(questions)
        percent = (score / total * 100) if total > 0 else 0
        grade   = self.calculate_grade(percent)

        print(f"\n  ========================")
        print(f"  EXAM RESULT")
        print(f"  ========================")
        print(f"  Name  : {user['fullname']}")
        print(f"  Score : {score}/{total} ({percent:.2f}%)")
        print(f"  Grade : {grade}")
        print(f"  ========================")

        result = self.save_result(user, percent, grade, responses, subject_id=subject_id)
        print(result["message"])

    def calculate_grade(self, percent):
        if 70 <= percent <= 100: return "A — Excellent"
        if 60 <= percent < 70:  return "B — Good"
        if 50 <= percent < 60:  return "C — Average"
        if 40 <= percent < 50:  return "D — Below Average"
        return "F — Failed"

    # ==================================================================
    # VIEW HELPERS
    # ==================================================================
    def view_my_results(self, user):
        results = self.get_all_results_by_user(user["id"])
        if not results:
            print("No results yet. Please take an exam first.")
            return
        print(f"\n{'Subject':<25} {'Score':<10} {'Grade':<22} {'Date'}")
        print("-" * 75)
        for r in results:
            subj = (r.get("subject_name") or "General")[:23]
            print(f"{subj:<25} {r['percent']:<10.2f} {r['grade']:<22} "
                  f"{str(r['created_at'])[:19]}")

    def view_all_users(self):
        users = self.get_all_users()
        if not users:
            print("No users found.")
            return
        print(f"\n{'ID':<10} {'Name':<25} {'Email':<35} {'Role'}")
        print("-" * 80)
        for u in users:
            print(f"{u['id']:<10} {u['fullname'][:23]:<25} "
                  f"{u['email']:<35} {u['role']}")

    def view_all_results(self):
        results = self.get_all_results()
        if not results:
            print("No results found.")
            return
        print(f"\n{'Name':<25} {'Subject':<20} {'Score':<10} {'Grade':<22} {'Date'}")
        print("-" * 90)
        for r in results:
            subj = (r.get("subject_name") or "General")[:18]
            print(f"{r['fullname'][:23]:<25} {subj:<20} {r['percent']:<10.2f} "
                  f"{r['grade']:<22} {str(r['created_at'])[:19]}")

    def view_details(self, user):
        print("\n--- Your Details ---")
        skip = {"password"}
        for key, value in user.items():
            if key in skip:
                continue
            print(f"  {key.replace('_', ' ').title()}: "
                  f"{value if value is not None else 'Not set'}")

    def _display_question(self, question):
        subj = question.get("subject_name") or "No subject"
        print(f"\n  [ID: {question['id']}]  Subject: {subj}")
        print(f"  Q: {question['question']}")
        print(f"     A. {question['option_a']}")
        print(f"     B. {question['option_b']}")
        print(f"     C. {question['option_c']}")
        print(f"     D. {question['option_d']}")
        print(f"     Answer: {question['answer']}")

    # ==================================================================
    # GET INT INPUT
    # ==================================================================
    def _get_int_input(self, prompt):
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Please enter a valid number.")
            return None


if __name__ == "__main__":
    cbtapp("Taiwo CBT")