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
            print("""
            =============================
             Welcome to Taiwo CBT System
            =============================
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
                print("Goodbye")
                exit()
            else:
                print("Invalid choice. Please try again.")

    # ==================================================================
    # SPEECH
    # ==================================================================
    def speak_text(self, text):
        if pyttsx3 is None:
            print("Text-to-speech not available. Install: pip install pyttsx3")
            return
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as error:
            print(f"Text-to-speech error: {error}")

    # ==================================================================
    # TIMER
    # ==================================================================
    def exam_countdown_timer(self, total_seconds, timer_state):
        while total_seconds > 0 and not timer_state["submitted"]:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if total_seconds % 60 == 0 or total_seconds <= 10:
                print(f"\nTime remaining: {minutes:02d}:{seconds:02d}")
            time.sleep(1)
            total_seconds -= 1
        if not timer_state["submitted"]:
            timer_state["time_up"] = True
            print("\nTime is up. Exam submitted automatically.")

    # ==================================================================
    # REGISTER
    # ==================================================================
    def register(self):
        print("\n--- Register ---")
        email = input("Enter email: ").strip()
        if not self.validate_email(email):
            print("Invalid email address")
            return

        code = self.generate_verification_code()
        result = self.send_verification_email(email, code)
        print(result["message"])
        if not result["status"]:
            print(f"[DEV] Verification code: {code}")

        if input("Enter verification code: ").strip() != code:
            print("Invalid code. Registration cancelled.")
            return

        fullname = input("Enter full name: ").strip()
        role     = input("Enter role (student / staff / admin): ").strip().lower()

        if input("Generate a strong password? yes/no: ").strip().lower() == "yes":
            password = self.generate_strong_password()
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
            else: print("Unknown user role")
        else:
            print(result["message"])

    # ==================================================================
    # RESET PASSWORD
    # ==================================================================
    def reset_password_flow(self):
        print("\n--- Reset Password ---")
        email = input("Enter your registered email: ").strip()
        if not self.validate_email(email):
            print("Invalid email address")
            return
        if not self.get_user_by_email(email):
            print("No account found with that email.")
            return

        code   = self.generate_verification_code()
        result = self.send_password_reset_email(email, code)
        print(result["message"])
        if not result["status"]:
            print(f"[DEV] Reset code: {code}")

        if input("Enter reset code: ").strip() != code:
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
        print("Press Enter to keep the current value.")
        print(f"Full name   : {user.get('fullname', '')}")
        print(f"Phone       : {user.get('phone') or 'Not set'}")
        print(f"Department  : {user.get('department') or 'Not set'}")

        fullname   = input("New full name (Enter to skip): ").strip()
        phone      = input("New phone (Enter to skip): ").strip()
        department = input("New department (Enter to skip): ").strip()

        result = self.update_profile(
            user["id"],
            fullname=fullname   or None,
            phone=phone         or None,
            department=department or None
        )
        print(result["message"])
        return result["data"] if result["status"] else user

    # ==================================================================
    # EXAM MANAGEMENT MENU  (staff & admin)
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

        # Exam title
        exam_title = input("Exam title: ").strip()
        if not exam_title:
            print("Exam title cannot be empty.")
            return

        # Select subject
        subjects_result = self.get_all_subjects()
        subject_id = None
        if subjects_result["status"]:
            self._view_all_subjects()
            raw = input("Select subject ID (or Enter for all subjects): ").strip()
            if raw.isdigit():
                subject_id = int(raw)
                check = self.get_subject_by_id(subject_id)
                if not check["status"]:
                    print("Subject not found. Exam will draw from all subjects.")
                    subject_id = None
                else:
                    print(f"Subject selected: {check['subject']['subject_name']}")
        else:
            print("No subjects found. Exam will draw from all questions.")

        # Number of questions
        num_questions = self._get_int_input("Number of questions: ")
        if num_questions is None or num_questions < 1:
            print("Invalid number of questions.")
            return

        # Duration
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
        print(f"\nID         : {e['exam_id']}")
        print(f"Title      : {e['exam_title']}")
        print(f"Subject    : {e['subject_name'] or 'All subjects'}")
        print(f"Questions  : {e['num_questions']}")
        print(f"Duration   : {e['duration_minutes']} minutes")
        print(f"Created by : {e['created_by_name']}")
        print(f"Created at : {e['created_at']}")

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

        title = input(f"Title [{e['exam_title']}]: ").strip() or None

        # Subject
        self._view_all_subjects()
        raw = input(f"Subject ID [{e['subject_id'] or 'All'}] (Enter to keep, 0 for all): ").strip()
        if raw == "0":
            subject_id = None
        elif raw.isdigit():
            subject_id = int(raw)
        else:
            subject_id = None if raw == "" else e["subject_id"]

        raw_q = input(f"Number of questions [{e['num_questions']}]: ").strip()
        num_questions = int(raw_q) if raw_q.isdigit() else None

        raw_d = input(f"Duration in minutes [{e['duration_minutes']}]: ").strip()
        duration = int(raw_d) if raw_d.isdigit() else None

        result = self.update_exam(exam_id, exam_title=title, subject_id=subject_id,
                                  num_questions=num_questions, duration_minutes=duration)
        print(result["message"])

    def _delete_exam(self):
        self._view_all_exams()
        exam_id = self._get_int_input("Enter exam ID to delete: ")
        if exam_id is None:
            return
        if input("Are you sure? yes/no: ").strip().lower() != "yes":
            print("Cancelled.")
            return
        result = self.delete_exam(exam_id)
        print(result["message"])

    # ==================================================================
    # SUBJECT MANAGEMENT UI  (shared by staff & admin)
    # ==================================================================
    def subject_menu(self):
        while True:
            print("""
            --- Subject Management ---
            1.  Add subject
            2.  View all subjects
            3.  View subject by ID
            4.  Update subject
            5.  Delete subject
            6.  Add question to subject
            7.  View questions by subject
            8.  View results by subject
            9.  Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._add_subject()
            elif choice == "2": self._view_all_subjects()
            elif choice == "3": self._view_subject_by_id()
            elif choice == "4": self._update_subject()
            elif choice == "5": self._delete_subject()
            elif choice == "6": self._add_question_to_subject()
            elif choice == "7": self._view_questions_by_subject()
            elif choice == "8": self._view_results_by_subject()
            elif choice == "9": break
            else: print("Invalid choice.")

    def _add_subject(self):
        name        = input("Subject name: ").strip()
        code        = input("Subject code (e.g. MTH101): ").strip()
        description = input("Description (optional, Enter to skip): ").strip()
        result      = self.add_subject(name, code, description)
        print(result["message"])

    def _add_question_to_subject(self):
        """Add a question and assign it to a chosen subject in one step."""
        subjects_result = self.get_all_subjects()
        if not subjects_result["status"]:
            print("No subjects exist yet. Please add a subject first.")
            return

        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID to add question to: ")
        if subject_id is None:
            return

        check = self.get_subject_by_id(subject_id)
        if not check["status"]:
            print("Subject not found.")
            return

        print(f"\nAdding question to: {check['subject']['subject_name']} ({check['subject']['subject_code']})")
        question = input("Question: ").strip()
        option_a = input("Option A: ").strip()
        option_b = input("Option B: ").strip()
        option_c = input("Option C: ").strip()
        option_d = input("Option D: ").strip()
        answer   = input("Answer (A / B / C / D or full text): ").strip()

        result = self.add_question(question, option_a, option_b, option_c, option_d, answer, subject_id)
        print(result["message"])

    def _view_all_subjects(self):
        result = self.get_all_subjects()
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{'ID':<5} {'Code':<12} {'Name':<30} {'Description'}")
        print("-" * 70)
        for s in result["subjects"]:
            desc = (s["description"] or "")[:30]
            print(f"{s['subject_id']:<5} {s['subject_code']:<12} {s['subject_name']:<30} {desc}")

    def _view_subject_by_id(self):
        subject_id = self._get_int_input("Enter subject ID: ")
        if subject_id is None:
            return
        result = self.get_subject_by_id(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        s = result["subject"]
        print(f"\nID          : {s['subject_id']}")
        print(f"Name        : {s['subject_name']}")
        print(f"Code        : {s['subject_code']}")
        print(f"Description : {s['description'] or 'None'}")
        print(f"Created     : {s['created_at']}")

    def _update_subject(self):
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
        subject_id = self._get_int_input("Enter subject ID to delete: ")
        if subject_id is None:
            return
        confirm = input("Are you sure? This cannot be undone. yes/no: ").strip().lower()
        if confirm != "yes":
            print("Deletion cancelled.")
            return
        result = self.delete_subject(subject_id)
        print(result["message"])

    def _view_questions_by_subject(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID: ")
        if subject_id is None:
            return
        result = self.get_questions_by_subject(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        for q in result["questions"]:
            self._display_question(q)

    def _view_results_by_subject(self):
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID: ")
        if subject_id is None:
            return
        result = self.get_all_results_by_subject(subject_id)
        if not result["status"]:
            print(result["message"])
            return
        for r in result["results"]:
            print("\n" + "-" * 40)
            for key, value in r.items():
                if key == "response":
                    continue
                print(f"{key.replace('_', ' ').title()}: {value}")

    # ==================================================================
    # DASHBOARDS
    # ==================================================================
    def question_menu(self):
        """Dedicated question management submenu for staff and admin."""
        while True:
            print("""
            --- Question Management ---
            1. Add question (no subject)
            2. Add question to a subject
            3. View all questions
            4. View question by ID
            5. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.create_question(force_no_subject=True)
            elif choice == "2": self._add_question_to_subject()
            elif choice == "3": self.display_all_questions()
            elif choice == "4": self.display_question_by_id()
            elif choice == "5": break
            else: print("Invalid choice.")

    def staff_dashboard(self, user):
        while True:
            print("""
            STAFF DASHBOARD
            1. Exam management
            2. Question management
            3. Subject management
            4. View my details
            5. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.exam_menu(user)
            elif choice == "2": self.question_menu()
            elif choice == "3": self.subject_menu()
            elif choice == "4": self.view_details(user)
            elif choice == "5": break
            else: print("Invalid choice.")

    def admin_dashboard(self, user):
        while True:
            print("""
            ADMIN DASHBOARD
            1. Exam management
            2. Question management
            3. Subject management
            4. View all users
            5. View all results
            6. View my details
            7. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.exam_menu(user)
            elif choice == "2": self.question_menu()
            elif choice == "3": self.subject_menu()
            elif choice == "4": self.view_all_users()
            elif choice == "5": self.view_all_results()
            elif choice == "6": self.view_details(user)
            elif choice == "7": break
            else: print("Invalid choice.")

    def student_dashboard(self, user):
        while True:
            print("""
            STUDENT DASHBOARD
            1. Take exam (configured)
            2. Take exam by subject
            3. View result
            4. View my details
            5. Update profile
            6. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self.take_exam_from_config(user)
            elif choice == "2": self.take_exam_by_subject(user)
            elif choice == "3": self.view_result(user)
            elif choice == "4": self.view_details(user)
            elif choice == "5": user = self.update_profile_flow(user)
            elif choice == "6": break
            else: print("Invalid choice.")

    def take_exam_from_config(self, user):
        """Let a student pick a configured exam and sit it with its settings."""
        result = self.get_all_exams()
        if not result["status"]:
            print("No exams available at the moment.")
            return
        self._view_all_exams()
        exam_id = self._get_int_input("Enter exam ID to attempt: ")
        if exam_id is None:
            return
        check = self.get_exam_by_id(exam_id)
        if not check["status"]:
            print(check["message"])
            return
        exam_config = check["exam"]
        print(f"\nExam     : {exam_config['exam_title']}")
        print(f"Subject  : {exam_config['subject_name'] or 'All subjects'}")
        print(f"Questions: {exam_config['num_questions']}")
        print(f"Duration : {exam_config['duration_minutes']} minutes")
        if input("\nReady to start? yes/no: ").strip().lower() != "yes":
            print("Exam cancelled.")
            return
        self.take_exams(
            user,
            subject_id=exam_config["subject_id"],
            num_questions=exam_config["num_questions"],
            duration_minutes=exam_config["duration_minutes"]
        )

    # ==================================================================
    # QUESTION HELPERS
    # ==================================================================
    def create_question(self, force_no_subject=False):
        """Create a question. Pass force_no_subject=True to skip subject selection."""
        print("\n--- Add Question ---")
        subject_id = None

        if not force_no_subject:
            subjects_result = self.get_all_subjects()
            if subjects_result["status"]:
                print("Available subjects (press Enter to leave unassigned):")
                self._view_all_subjects()
                raw = input("Assign to subject ID (or Enter to skip): ").strip()
                if raw.isdigit():
                    subject_id = int(raw)
                    if not self.get_subject_by_id(subject_id)["status"]:
                        print("Subject not found. Saving without a subject.")
                        subject_id = None
            else:
                print("No subjects yet — saving without a subject.")

        question = input("Enter question: ").strip()
        option_a = input("Option A: ").strip()
        option_b = input("Option B: ").strip()
        option_c = input("Option C: ").strip()
        option_d = input("Option D: ").strip()
        answer   = input("Correct answer (A / B / C / D or full text): ").strip()

        result = self.add_question(question, option_a, option_b, option_c, option_d, answer, subject_id)
        print(result["message"])

    def _display_question(self, question):
        subj = question.get("subject_name") or "No subject"
        print(f"\n[ID: {question['id']}]  Subject: {subj}")
        print(f"Q: {question['question']}")
        print(f"   A. {question['option_a']}")
        print(f"   B. {question['option_b']}")
        print(f"   C. {question['option_c']}")
        print(f"   D. {question['option_d']}")
        print(f"   Answer: {question['answer']}")

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
    # EXAM
    # ==================================================================
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
        use_speech   = input("Read questions aloud? yes/no: ").strip().lower()

        print(f"\n{len(questions)} questions | {exam_minutes} minutes | Timer started.")

        timer_thread = threading.Thread(
            target=self.exam_countdown_timer,
            args=(exam_minutes * 60, timer_state),
            daemon=True
        )
        timer_thread.start()

        for number, item in enumerate(questions, start=1):
            if timer_state["time_up"]:
                break

            print(f"\nQuestion {number}: {item['question']}")
            print(f"A. {item['option_a']}")
            print(f"B. {item['option_b']}")
            print(f"C. {item['option_c']}")
            print(f"D. {item['option_d']}")

            if use_speech == "yes":
                self.speak_text(
                    f"Question {number}. {item['question']}. "
                    f"A. {item['option_a']}. B. {item['option_b']}. "
                    f"C. {item['option_c']}. D. {item['option_d']}."
                )

            response = input("Your answer: ").strip()

            if timer_state["time_up"]:
                print("Answer received after time expired and will not be marked.")
                break

            responses.append(response)
            if response.lower() == item["answer"].lower().strip():
                score += 1
                print("Correct")
            else:
                print("Wrong")

        timer_state["submitted"] = True
        percent = (score / len(questions)) * 100
        grade   = self.calculate_grade(percent)

        print(f"\nName : {user['fullname']}")
        print(f"Score: {percent:.2f}%")
        print(f"Grade: {grade}")

        result = self.save_result(user, percent, grade, responses, subject_id=subject_id)
        print(result["message"])

    def take_exam_by_subject(self, user):
        """Let a student choose a subject then sit an exam on that subject only."""
        subjects_result = self.get_all_subjects()
        if not subjects_result["status"]:
            print(subjects_result["message"])
            return
        self._view_all_subjects()
        subject_id = self._get_int_input("Enter subject ID for the exam: ")
        if subject_id is None:
            return
        check = self.get_subject_by_id(subject_id)
        if not check["status"]:
            print(check["message"])
            return
        print(f"\nStarting exam: {check['subject']['subject_name']}")
        self.take_exams(user, subject_id=subject_id)

    def calculate_grade(self, percent):
        if 70 <= percent <= 100: return "Grade A"
        if 60 <= percent < 70:  return "Grade B"
        if 50 <= percent < 60:  return "Grade C"
        if 40 <= percent < 50:  return "Grade D"
        return "You failed. You can do better"

    # ==================================================================
    # VIEW HELPERS
    # ==================================================================
    def view_result(self, user):
        result = self.get_result(user)
        if not result:
            print("No result yet. Kindly take the exam.")
            return
        print("\n--- Latest Result ---")
        skip = {"response"}
        for key, value in result.items():
            if key in skip:
                continue
            print(f"{key.replace('_',' ').title()}: {value}")

    def view_all_users(self):
        users = self.get_all_users()
        if not users:
            print("No users found")
            return
        for user in users:
            print("\nUser Details")
            for key, value in user.items():
                print(f"  {key}: {value}")

    def view_all_results(self):
        results = self.get_all_results()
        if not results:
            print("No results found")
            return
        for result in results:
            print("\n" + "-" * 40)
            for key, value in result.items():
                if key == "response":
                    continue
                print(f"  {key.replace('_',' ').title()}: {value}")

    def view_details(self, user):
        print("\n--- Your Details ---")
        skip = {"password"}
        for key, value in user.items():
            if key in skip:
                continue
            print(f"{key.replace('_',' ').title()}: {value if value is not None else 'Not set'}")

    # ==================================================================
    # UTILITY
    # ==================================================================
    def _get_int_input(self, prompt):
        """Prompt for an integer. Returns None if input is invalid."""
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Please enter a valid number.")
            return None


if __name__ == "__main__":
    cbtapp("Taiwo CBT")