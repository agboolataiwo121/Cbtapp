from random import randint
from cbtconfig import cbtconfig
import threading
import time


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
            1. Student
            2. Staff
            3. Exit
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1":    self.student_portal()
            elif choice == "2":    self.staff_portal()
            elif choice == "3":
                self.close_connection()
                print("Goodbye!")
                exit()
            elif choice.lower() == "admin":
                self.admin_portal()
            else:
                print("Invalid choice.")

    # ==================================================================
    # PORTALS
    # ==================================================================
    def student_portal(self):
        while True:
            print("""
            --- Student ---
            1. Register
            2. Login
            3. Reset Password
            4. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._register("student")
            elif choice == "2": self._login("student")
            elif choice == "3": self._reset_password()
            elif choice == "4": break
            else: print("Invalid choice.")

    def staff_portal(self):
        while True:
            print("""
            --- Staff ---
            1. Login
            2. Reset Password
            3. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._login("staff")
            elif choice == "2": self._reset_password()
            elif choice == "3": break
            else: print("Invalid choice.")

    def admin_portal(self):
        while True:
            print("""
            --- Admin ---
            1. Login
            2. Reset Password
            3. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._login("admin")
            elif choice == "2": self._reset_password()
            elif choice == "3": break
            else: print("Invalid choice.")

    # ==================================================================
    # SHARED REGISTER / LOGIN / RESET
    # ==================================================================
    def _register(self, role):
        labels = {"student": "Student", "staff": "Staff", "admin": "Admin"}
        print(f"\n--- {labels[role]} Registration ---")

        # Admin requires secret key
        if role == "admin":
            if input("Enter admin secret key: ").strip() != "ACADEMIQ_ADMIN_2025":
                print("Invalid secret key. Registration denied.")
                return

        email = input("Email address    : ").strip()
        if not self.validate_email(email):
            print("Invalid email address.")
            return

        code   = self.generate_verification_code()
        result = self.send_verification_email(email, code)
        print(result["message"])
        if not result["status"]:
            print(f"[DEV] Code: {code}")

        if input("Enter verification code: ").strip() != code:
            print("Wrong code. Registration cancelled.")
            return

        fullname   = input("Full name        : ").strip()
        department = input("Department       : ").strip()
        phone      = input("Phone number     : ").strip()

        if input("Generate strong password? yes/no: ").strip().lower() == "yes":
            password = confirm = self.generate_strong_password()
            print(f"Generated password: {password}  — save this now!")
        else:
            password = input("Password         : ")
            confirm  = input("Confirm password : ")

        user_id = randint(100000, 999999)
        result  = self.create_account(
            email, fullname, password, confirm, role, user_id,
            phone=phone, department=department
        )
        if result["status"]:
            key = f"message_{role}"
            print(result.get(key, "Registration successful"))
        else:
            print(result["message"])

    def _login(self, role):
        labels = {"student": "Student", "staff": "Staff", "admin": "Admin"}
        print(f"\n--- {labels[role]} Login ---")
        email    = input("Email   : ").strip()
        password = input("Password: ")
        result   = self.login_user(email, password, expected_role=role)
        if not result["status"]:
            print(result["message"])
            return
        user = result["data"]
        print(result["message"])
        if   role == "student": self.student_dashboard(user)
        elif role == "staff":   self.staff_dashboard(user)
        elif role == "admin":   self.admin_dashboard(user)

    def _reset_password(self):
        print("\n--- Reset Password ---")
        email = input("Registered email: ").strip()
        if not self.validate_email(email):
            print("Invalid email.")
            return
        if not self.get_user_by_email(email):
            print("No account found with that email.")
            return

        code   = self.generate_verification_code()
        result = self.send_password_reset_email(email, code)
        print(result["message"])
        if not result["status"]:
            print(f"[DEV] Code: {code}")

        if input("Enter reset code    : ").strip() != code:
            print("Wrong code. Cancelled.")
            return

        new_pw  = input("New password       : ")
        confirm = input("Confirm password   : ")
        result  = self.reset_password(email, new_pw, confirm)
        print(result["message"])

    # ==================================================================
    # STUDENT DASHBOARD
    # ==================================================================
    def student_dashboard(self, user):
        while True:
            user = self._refresh_user(user)
            print(f"""
            ================================
             {user['fullname']}  [{user['id']}]
             Role: Student
            ================================
            1. My Courses
            2. Browse & Enroll in Courses
            3. Study Lessons
            4. Take Exam
            5. My Results
            6. My Profile
            7. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._my_courses(user)
            elif choice == "2": self._browse_courses(user)
            elif choice == "3": self._study_lessons(user)
            elif choice == "4": self._take_exam(user)
            elif choice == "5": self._my_results(user)
            elif choice == "6": self._view_profile(user)
            elif choice == "7": break
            else: print("Invalid choice.")
        print("Logged out.")

    # ------------------------------------------------------------------
    # Student — My Courses
    # ------------------------------------------------------------------
    def _my_courses(self, user):
        enrollments = self.get_student_enrollments(user["id"])
        if not enrollments:
            print("\n  You are not enrolled in any courses yet.")
            print("  Go to 'Browse & Enroll' to get started.")
            return

        while True:
            print(f"\n  --- My Courses ---")
            print(f"  {'#':<4} {'Title':<30} {'Duration':<14} {'Status'}")
            print("  " + "-" * 60)
            for i, e in enumerate(enrollments, 1):
                print(f"  {i:<4} {e['title'][:28]:<30} "
                      f"{(e['duration'] or 'N/A'):<14} {e['status']}")
            print("""
  1. Drop a course
  2. Mark course as completed
  3. Back
            """)
            choice = input("  Enter choice: ").strip()
            if   choice == "1":
                self._drop_course(user, enrollments)
                enrollments = self.get_student_enrollments(user["id"])
            elif choice == "2":
                self._complete_course(user, enrollments)
                enrollments = self.get_student_enrollments(user["id"])
            elif choice == "3":
                break
            else:
                print("  Invalid choice.")

    def _drop_course(self, user, enrollments):
        n = self._get_int("  Course # to drop: ")
        if n is None or n < 1 or n > len(enrollments):
            print("  Invalid selection.")
            return
        e = enrollments[n - 1]
        if e["status"] == "dropped":
            print("  Already dropped.")
            return
        if input(f"  Drop '{e['title']}'? yes/no: ").strip().lower() == "yes":
            print(" ", self.update_enrollment_status(
                user["id"], e["course_id"], "dropped")["message"])

    def _complete_course(self, user, enrollments):
        n = self._get_int("  Course # to mark complete: ")
        if n is None or n < 1 or n > len(enrollments):
            print("  Invalid selection.")
            return
        e = enrollments[n - 1]
        if e["status"] == "completed":
            print("  Already completed.")
            return
        if input(f"  Mark '{e['title']}' as completed? yes/no: ").strip().lower() == "yes":
            print(" ", self.update_enrollment_status(
                user["id"], e["course_id"], "completed")["message"])

    # ------------------------------------------------------------------
    # Student — Browse & Enroll
    # ------------------------------------------------------------------
    def _browse_courses(self, user):
        result = self.get_all_courses()
        if not result["status"]:
            print("  No courses available yet.")
            return

        print("\n  --- Available Courses ---")
        print(f"  {'ID':<5} {'Title':<30} {'Duration':<14} {'Subjects':<10} {'Students'}")
        print("  " + "-" * 70)
        for c in result["courses"]:
            print(f"  {c['course_id']:<5} {c['title'][:28]:<30} "
                  f"{(c['duration'] or 'N/A'):<14} {c['subject_count']:<10} "
                  f"{c['enrolled_count']}")

        course_id = self._get_int("\n  Enter course ID to view (0 to go back): ")
        if not course_id or course_id == 0:
            return

        check = self.get_course_by_id(course_id)
        if not check["status"]:
            print("  Course not found.")
            return

        c = check["course"]
        print(f"\n  Title      : {c['title']}")
        print(f"  Description: {c['description'] or 'No description'}")
        print(f"  Duration   : {c['duration'] or 'Not specified'}")
        print(f"  Created by : {c['created_by_name']}")
        if c["subjects"]:
            print("\n  Subjects:")
            for s in c["subjects"]:
                print(f"    - {s['subject_name']} ({s['subject_code']})")

        existing = self.get_enrollment(user["id"], course_id)
        if existing:
            print(f"\n  You are '{existing['status']}' in this course.")
            if existing["status"] == "dropped":
                if input("  Re-enroll? yes/no: ").strip().lower() == "yes":
                    print(" ", self.update_enrollment_status(
                        user["id"], course_id, "enrolled")["message"])
        else:
            if input("\n  Enroll in this course? yes/no: ").strip().lower() == "yes":
                print(" ", self.enroll_student(user["id"], course_id)["message"])

    # ------------------------------------------------------------------
    # Student — Study Lessons
    # ------------------------------------------------------------------
    def _study_lessons(self, user):
        """Student picks any subject directly and reads its lessons."""
        result = self.get_all_subjects()
        if not result["status"]:
            print("  No subjects available.")
            return

        print("\n  --- Study Lessons ---")
        print(f"  {'ID':<5} {'Code':<12} {'Name':<30} {'Lessons'}")
        print("  " + "-" * 60)
        for s in result["subjects"]:
            print(f"  {s['subject_id']:<5} {s['subject_code']:<12} "
                  f"{s['subject_name']:<30} {s['lesson_count']}")

        subject_id = self._get_int("\n  Enter subject ID: ")
        if subject_id is None:
            return

        check = self.get_subject_by_id(subject_id)
        if not check["status"]:
            print("  Subject not found.")
            return

        lessons_result = self.get_lessons_by_subject(subject_id)
        if not lessons_result["status"]:
            print(f"  No lessons available for "
                  f"'{check['subject']['subject_name']}' yet.")
            return

        lessons = lessons_result["lessons"]
        print(f"\n  Lessons for {check['subject']['subject_name']}:")
        print(f"  {'#':<4} {'Week':<6} {'Topic':<25} {'Title'}")
        print("  " + "-" * 60)
        for i, l in enumerate(lessons, 1):
            print(f"  {i:<4} {l['week']:<6} "
                  f"{(l['topic'] or 'General')[:23]:<25} {l['title']}")

        n = self._get_int("\n  Enter lesson # to read (0 to go back): ")
        if n is None or n == 0:
            return
        if n < 1 or n > len(lessons):
            print("  Invalid selection.")
            return

        self._show_lesson(lessons[n - 1])

    def _show_lesson(self, lesson):
        w = 60
        print(f"\n  {'=' * w}")
        print(f"  {lesson['title'].center(w)}")
        print(f"  {'=' * w}")
        subj = lesson.get('subject_name', '')
        if subj:
            print(f"  Subject : {subj}")
        print(f"  Week    : {lesson['week']}"
              + (f"  |  Topic: {lesson['topic']}" if lesson['topic'] else ""))
        print(f"  Author  : {lesson.get('created_by_name', 'N/A')}")
        print(f"  {'-' * w}")
        print()
        for line in lesson["content"].split("\n"):
            print(f"  {line}")
        print(f"\n  {'=' * w}")
        input("\n  Press Enter to continue...")

    # ------------------------------------------------------------------
    # Student — Take Exam
    # ------------------------------------------------------------------
    def _take_exam(self, user):
        result = self.get_all_subjects()
        if not result["status"]:
            print("  No subjects available.")
            return

        print("\n  --- Take Exam ---")
        print(f"  {'ID':<5} {'Code':<12} {'Name':<30} {'Questions'}")
        print("  " + "-" * 60)
        for s in result["subjects"]:
            print(f"  {s['subject_id']:<5} {s['subject_code']:<12} "
                  f"{s['subject_name']:<30} {s['question_count']}")

        subject_id = self._get_int("\n  Enter subject ID: ")
        if subject_id is None:
            return

        check = self.get_subject_by_id(subject_id)
        if not check["status"]:
            print("  Subject not found.")
            return

        subject = check["subject"]
        count   = self.get_question_count(subject_id)
        if count == 0:
            print(f"  No questions for '{subject['subject_name']}' yet.")
            return

        print(f"\n  Subject  : {subject['subject_name']} ({subject['subject_code']})")
        print(f"  Questions: {count}")
        print(f"  Duration : 5 minutes (fixed)")

        if input("\n  Ready to start? yes/no: ").strip().lower() != "yes":
            print("  Exam cancelled.")
            return

        self._run_exam(user, subject_id, count)

    def _run_exam(self, user, subject_id, count):
        result = self.generate_exam_questions(subject_id, count)
        if not result["status"]:
            print(f"  {result['message']}")
            return

        questions   = result["questions"]
        score       = 0
        timer_state = {"time_up": False, "submitted": False}

        print(f"\n  {len(questions)} questions | 5 minutes | Timer started.\n")

        timer = threading.Thread(
            target=self._countdown,
            args=(5 * 60, timer_state),
            daemon=True
        )
        timer.start()

        for number, q in enumerate(questions, 1):
            if timer_state["time_up"]:
                break

            print(f"\n  Question {number}/{len(questions)}: {q['question']}")
            print(f"    A. {q['option_a']}")
            print(f"    B. {q['option_b']}")
            print(f"    C. {q['option_c']}")
            print(f"    D. {q['option_d']}")

            ans = input("  Your answer (A/B/C/D): ").strip().upper()

            if timer_state["time_up"]:
                print("  Time expired — answer not scored.")
                break

            if ans and ans[0] in ("A", "B", "C", "D"):
                if ans[0] == q["answer"]:
                    score += 1
                    print("  Correct!")
                else:
                    print(f"  Wrong. Correct answer: {q['answer']}")
            else:
                print("  Invalid input — skipped.")

        timer_state["submitted"] = True
        total   = len(questions)
        percent = round(score / total * 100, 2) if total > 0 else 0
        grade   = self._calculate_grade(percent)

        print(f"\n  {'=' * 40}")
        print(f"  RESULT")
        print(f"  {'=' * 40}")
        print(f"  Name   : {user['fullname']}")
        print(f"  Subject: {self.get_subject_by_id(subject_id)['subject']['subject_name']}")
        print(f"  Score  : {score}/{total} ({percent}%)")
        print(f"  Grade  : {grade}")
        print(f"  {'=' * 40}")

        res = self.save_result(user["id"], subject_id, user["fullname"], score, total)
        print(f"  {res['message']}")

    def _countdown(self, total_seconds, timer_state):
        while total_seconds > 0 and not timer_state["submitted"]:
            mins = total_seconds // 60
            secs = total_seconds % 60
            if total_seconds % 60 == 0 or total_seconds <= 10:
                print(f"\n  Time remaining: {mins:02d}:{secs:02d}")
            time.sleep(1)
            total_seconds -= 1
        if not timer_state["submitted"]:
            timer_state["time_up"] = True
            print("\n  Time is up! Exam auto-submitted.")

    # ------------------------------------------------------------------
    # Student — My Results
    # ------------------------------------------------------------------
    def _my_results(self, user):
        results = self.get_results_by_student(user["id"])
        if not results:
            print("\n  No results yet. Take an exam first.")
            return
        print(f"\n  --- My Results ---")
        print(f"  {'Subject':<25} {'Score':<10} {'Percent':<10} {'Grade':<6} {'Date'}")
        print("  " + "-" * 70)
        for r in results:
            print(f"  {r['subject_name'][:23]:<25} "
                  f"{r['score']}/{r['total']:<8} "
                  f"{r['percent']:<10.2f} "
                  f"{r['grade']:<6} "
                  f"{str(r['created_at'])[:19]}")

    # ==================================================================
    # STAFF DASHBOARD
    # ==================================================================
    def staff_dashboard(self, user):
        while True:
            print(f"""
            ================================
             {user['fullname']}  [{user['id']}]
             Role: Staff
            ================================
            1. Course Management
            2. Subject Management
            3. Lesson Management
            4. Question Management
            5. View Results
            6. My Profile
            7. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._course_menu(user)
            elif choice == "2": self._subject_menu(user)
            elif choice == "3": self._lesson_menu(user)
            elif choice == "4": self._question_menu(user)
            elif choice == "5": self._view_results_menu()
            elif choice == "6": self._view_profile(user)
            elif choice == "7": break
            else: print("Invalid choice.")
        print("Logged out.")

    # ==================================================================
    # ADMIN DASHBOARD
    # ==================================================================
    def admin_dashboard(self, user):
        while True:
            print(f"""
            ================================
             {user['fullname']}  [{user['id']}]
             Role: Admin
            ================================
            1.  Course Management
            2.  Subject Management
            3.  Lesson Management
            4.  Question Management
            5.  View Results
            6.  Staff Management
            7.  View All Users
            8.  View All Enrollments
            9.  My Profile
            10. Log out
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1":  self._course_menu(user)
            elif choice == "2":  self._subject_menu(user)
            elif choice == "3":  self._lesson_menu(user)
            elif choice == "4":  self._question_menu(user)
            elif choice == "5":  self._view_results_menu()
            elif choice == "6":  self._staff_management(user)
            elif choice == "7":  self._view_all_users()
            elif choice == "8":  self._view_all_enrollments()
            elif choice == "9":  self._view_profile(user)
            elif choice == "10": break
            else: print("Invalid choice.")
        print("Logged out.")

    # ==================================================================
    # COURSE MANAGEMENT
    # ==================================================================
    def _course_menu(self, user):
        while True:
            print("""
            --- Course Management ---
            1. Create course
            2. View all courses
            3. View course details
            4. Update course
            5. Delete course
            6. Assign subject to course
            7. Remove subject from course
            8. View course enrollments
            9. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._create_course(user)
            elif choice == "2": self._list_courses()
            elif choice == "3": self._view_course()
            elif choice == "4": self._update_course()
            elif choice == "5": self._delete_course()
            elif choice == "6": self._assign_subject()
            elif choice == "7": self._remove_subject()
            elif choice == "8": self._course_enrollments()
            elif choice == "9": break
            else: print("Invalid choice.")

    def _create_course(self, user):
        print("\n--- Create Course ---")
        title       = input("Course title      : ").strip()
        description = input("Description       : ").strip()
        duration    = input("Duration          : ").strip()

        subject_ids = []
        s_result = self.get_all_subjects()
        if s_result["status"]:
            self._print_subjects(s_result["subjects"])
            raw = input("Assign subject IDs (comma-separated, Enter to skip): ").strip()
            if raw:
                for part in raw.split(","):
                    p = part.strip()
                    if p.isdigit():
                        subject_ids.append(int(p))

        result = self.create_course(title, description, duration,
                                    user["id"], subject_ids or None)
        print(result["message"])

    def _list_courses(self):
        result = self.get_all_courses()
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{'ID':<5} {'Title':<30} {'Duration':<14} {'Subjects':<10} "
              f"{'Enrolled':<10} {'Created By'}")
        print("-" * 85)
        for c in result["courses"]:
            print(f"{c['course_id']:<5} {c['title'][:28]:<30} "
                  f"{(c['duration'] or 'N/A'):<14} {c['subject_count']:<10} "
                  f"{c['enrolled_count']:<10} {c['created_by_name']}")

    def _view_course(self):
        self._list_courses()
        cid = self._get_int("Enter course ID: ")
        if cid is None:
            return
        result = self.get_course_by_id(cid)
        if not result["status"]:
            print(result["message"])
            return
        c = result["course"]
        print(f"\n  ID          : {c['course_id']}")
        print(f"  Title       : {c['title']}")
        print(f"  Description : {c['description'] or 'None'}")
        print(f"  Duration    : {c['duration'] or 'Not set'}")
        print(f"  Created by  : {c['created_by_name']}")
        print(f"  Created at  : {str(c['created_at'])[:19]}")
        if c["subjects"]:
            print("\n  Assigned Subjects:")
            for s in c["subjects"]:
                print(f"    [{s['subject_id']}] {s['subject_name']} ({s['subject_code']})")
        else:
            print("\n  No subjects assigned.")
        enrollments = self.get_course_enrollments(c["course_id"])
        print(f"\n  Enrolled students: {len(enrollments)}")

    def _update_course(self):
        self._list_courses()
        cid = self._get_int("Enter course ID to update: ")
        if cid is None:
            return
        check = self.get_course_by_id(cid)
        if not check["status"]:
            print(check["message"])
            return
        c = check["course"]
        print("Press Enter to keep current value.")
        title = input(f"Title [{c['title']}]: ").strip() or None
        desc  = input(f"Description [{c['description'] or ''}]: ").strip()
        dur   = input(f"Duration [{c['duration'] or ''}]: ").strip()
        result = self.update_course(
            cid, title=title,
            description=desc if desc != "" else None,
            duration=dur if dur != "" else None
        )
        print(result["message"])

    def _delete_course(self):
        self._list_courses()
        cid = self._get_int("Enter course ID to delete: ")
        if cid is None:
            return
        if input("Delete course and all enrollments? yes/no: ").strip().lower() != "yes":
            print("Cancelled.")
            return
        print(self.delete_course(cid)["message"])

    def _assign_subject(self):
        self._list_courses()
        cid = self._get_int("Enter course ID: ")
        if cid is None:
            return
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID to assign: ")
        if sid is None:
            return
        print(self.assign_subject_to_course(cid, sid)["message"])

    def _remove_subject(self):
        self._list_courses()
        cid = self._get_int("Enter course ID: ")
        if cid is None:
            return
        check = self.get_course_by_id(cid)
        if not check["status"] or not check["course"]["subjects"]:
            print("No subjects assigned to this course.")
            return
        for s in check["course"]["subjects"]:
            print(f"  [{s['subject_id']}] {s['subject_name']}")
        sid = self._get_int("Enter subject ID to remove: ")
        if sid is None:
            return
        print(self.remove_subject_from_course(cid, sid)["message"])

    def _course_enrollments(self):
        self._list_courses()
        cid = self._get_int("Enter course ID: ")
        if cid is None:
            return
        rows = self.get_course_enrollments(cid)
        if not rows:
            print("No students enrolled.")
            return
        print(f"\n{'Name':<25} {'Email':<30} {'Status':<12} {'Enrolled At'}")
        print("-" * 80)
        for e in rows:
            print(f"{e['fullname'][:23]:<25} {e['email']:<30} "
                  f"{e['status']:<12} {str(e['enrolled_at'])[:19]}")

    def _view_all_enrollments(self):
        result = self.get_all_courses()
        if not result["status"]:
            print("No courses.")
            return
        found = False
        print(f"\n{'Course':<30} {'Student':<25} {'Status':<12} {'Enrolled At'}")
        print("-" * 85)
        for c in result["courses"]:
            for e in self.get_course_enrollments(c["course_id"]):
                print(f"{c['title'][:28]:<30} {e['fullname'][:23]:<25} "
                      f"{e['status']:<12} {str(e['enrolled_at'])[:19]}")
                found = True
        if not found:
            print("No enrollments yet.")

    # ==================================================================
    # SUBJECT MANAGEMENT
    # ==================================================================
    def _subject_menu(self, user):
        while True:
            print("""
            --- Subject Management ---
            1. Add subject
            2. View all subjects
            3. Update subject
            4. Delete subject
            5. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._add_subject()
            elif choice == "2": self._print_subjects(
                self.get_all_subjects().get("subjects", []))
            elif choice == "3": self._update_subject()
            elif choice == "4": self._delete_subject()
            elif choice == "5": break
            else: print("Invalid choice.")

    def _add_subject(self):
        print("\n--- Add Subject ---")
        name = input("Subject name : ").strip()
        code = input("Subject code : ").strip()
        desc = input("Description  : ").strip()
        result = self.add_subject(name, code, desc)
        print(result["message"])

    def _update_subject(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID to update: ")
        if sid is None:
            return
        check = self.get_subject_by_id(sid)
        if not check["status"]:
            print(check["message"])
            return
        s = check["subject"]
        print("Press Enter to keep current value.")
        name = input(f"Name [{s['subject_name']}]: ").strip() or None
        code = input(f"Code [{s['subject_code']}]: ").strip() or None
        desc = input(f"Desc [{s['description'] or ''}]: ").strip()
        result = self.update_subject(
            sid, subject_name=name, subject_code=code,
            description=desc if desc != "" else None
        )
        print(result["message"])

    def _delete_subject(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID to delete: ")
        if sid is None:
            return
        if input("Delete subject and ALL its questions, lessons and results? yes/no: "
                 ).strip().lower() != "yes":
            print("Cancelled.")
            return
        print(self.delete_subject(sid)["message"])

    # ==================================================================
    # QUESTION MANAGEMENT
    # ==================================================================
    def _question_menu(self, user):
        while True:
            print("""
            --- Question Management ---
            1. Add questions to a subject
            2. View questions by subject
            3. Edit a question
            4. Delete a question
            5. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._add_questions()
            elif choice == "2": self._view_questions()
            elif choice == "3": self._edit_question()
            elif choice == "4": self._delete_question()
            elif choice == "5": break
            else: print("Invalid choice.")

    def _add_questions(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID: ")
        if sid is None:
            return
        check = self.get_subject_by_id(sid)
        if not check["status"]:
            print("Subject not found.")
            return

        subj  = check["subject"]
        added = 0
        print(f"\nAdding questions to: {subj['subject_name']}")
        print("Type 'done' as the question text to stop.\n")

        while True:
            q_text = input(f"Question {added + 1}: ").strip()
            if q_text.lower() == "done" or not q_text:
                break

            opt_a = input("  Option A: ").strip()
            opt_b = input("  Option B: ").strip()
            opt_c = input("  Option C: ").strip()
            opt_d = input("  Option D: ").strip()
            ans   = input("  Answer (A/B/C/D): ").strip().upper()

            # Validate all fields are filled
            if not all([opt_a, opt_b, opt_c, opt_d]):
                print("  All four options are required. Question skipped.\n")
                continue

            if ans not in ("A", "B", "C", "D"):
                print("  Answer must be A, B, C, or D. Question skipped.\n")
                continue

            result = self.add_question(sid, q_text, opt_a, opt_b, opt_c, opt_d, ans)
            if result["status"]:
                added += 1
                print(f"  Saved! ({added} question(s) added so far)\n")
                # Only ask to continue if save succeeded
                if input("  Add another? yes/no: ").strip().lower() != "yes":
                    break
            else:
                print(f"  Error: {result['message']}\n")
                if input("  Try again with a different question? yes/no: ").strip().lower() != "yes":
                    break

        count = self.get_question_count(sid)
        print(f"\n{added} question(s) added. "
              f"'{subj['subject_name']}' now has {count} question(s) total.")

    def _view_questions(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID: ")
        if sid is None:
            return
        result = self.get_questions_by_subject(sid)
        if not result["status"]:
            print(result["message"])
            return
        questions = result["questions"]
        total     = len(questions)
        page_size = 10
        page      = 0

        while True:
            start = page * page_size
            end   = min(start + page_size, total)
            print(f"\n  Showing {start + 1}–{end} of {total} question(s):\n")
            for q in questions[start:end]:
                self._print_question(q)

            if end >= total:
                print("\n  (End of questions)")
                break

            nav = input("\n  [N]ext page / [Q]uit viewing: ").strip().lower()
            if nav == "n":
                page += 1
            else:
                break

    def _edit_question(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID to browse: ")
        if sid is None:
            return
        result = self.get_questions_by_subject(sid)
        if not result["status"]:
            print(result["message"])
            return

        # Show a compact list so IDs are visible without scrolling
        questions = result["questions"]
        print(f"\n  {'ID':<6} {'Question (first 60 chars)'}")
        print("  " + "-" * 70)
        for q in questions:
            print(f"  {q['id']:<6} {q['question'][:68]}")

        qid = self._get_int("\nEnter question ID to edit: ")
        if qid is None:
            return
        check = self.get_question_by_id(qid)
        if not check["status"]:
            print("Question not found.")
            return
        q = check["question"]

        # Show full question before editing
        self._print_question(q)
        print("\nPress Enter to keep the current value.")

        question = input(f"Question: ").strip() or None
        opt_a    = input(f"Option A [{q['option_a']}]: ").strip() or None
        opt_b    = input(f"Option B [{q['option_b']}]: ").strip() or None
        opt_c    = input(f"Option C [{q['option_c']}]: ").strip() or None
        opt_d    = input(f"Option D [{q['option_d']}]: ").strip() or None

        ans_raw  = input(f"Answer [{q['answer']}] (A/B/C/D, Enter to keep): ").strip().upper()
        # Validate answer if provided
        if ans_raw and ans_raw not in ("A", "B", "C", "D"):
            print("Invalid answer. Must be A, B, C, or D. Answer not changed.")
            ans_raw = None
        ans = ans_raw or None

        result = self.update_question(qid, question=question, option_a=opt_a,
                                      option_b=opt_b, option_c=opt_c,
                                      option_d=opt_d, answer=ans)
        print(result["message"])

    def _delete_question(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID to browse: ")
        if sid is None:
            return
        result = self.get_questions_by_subject(sid)
        if not result["status"]:
            print(result["message"])
            return

        # Compact list showing ID and first 60 chars
        questions = result["questions"]
        print(f"\n  {'ID':<6} {'Question (first 60 chars)'}")
        print("  " + "-" * 70)
        for q in questions:
            print(f"  {q['id']:<6} {q['question'][:68]}")

        qid = self._get_int("\nEnter question ID to delete: ")
        if qid is None:
            return

        # Show full question so staff confirms they have the right one
        check = self.get_question_by_id(qid)
        if not check["status"]:
            print("Question not found.")
            return
        self._print_question(check["question"])

        if input("\nDelete this question? yes/no: ").strip().lower() != "yes":
            print("Cancelled.")
            return
        print(self.delete_question(qid)["message"])

    # ==================================================================
    # LESSON MANAGEMENT
    # ==================================================================
    def _lesson_menu(self, user):
        while True:
            print("""
            --- Lesson Management ---
            1. Add lesson
            2. View lessons by subject
            3. Update lesson
            4. Delete lesson
            5. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._add_lesson(user)
            elif choice == "2": self._view_lessons()
            elif choice == "3": self._update_lesson()
            elif choice == "4": self._delete_lesson()
            elif choice == "5": break
            else: print("Invalid choice.")

    def _add_lesson(self, user):
        print("\n--- Add Lesson ---")
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID: ")
        if sid is None:
            return
        check = self.get_subject_by_id(sid)
        if not check["status"]:
            print("Subject not found.")
            return

        print(f"\nAdding lesson to: {check['subject']['subject_name']}")
        title = input("Lesson title     : ").strip()
        raw_w = input("Week number      : ").strip()
        week  = int(raw_w) if raw_w.isdigit() and int(raw_w) >= 1 else 1
        topic = input("Topic (optional) : ").strip()
        print("Enter lesson content. Type 'END' on a new line to finish:")

        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)

        content = "\n".join(lines)
        result  = self.add_lesson(sid, title, week, topic, content, user["id"])
        print(result["message"])

    def _view_lessons(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID: ")
        if sid is None:
            return
        result = self.get_lessons_by_subject(sid)
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{'ID':<5} {'Week':<6} {'Topic':<25} {'Title':<35} {'By'}")
        print("-" * 80)
        for l in result["lessons"]:
            print(f"{l['lesson_id']:<5} {l['week']:<6} "
                  f"{(l['topic'] or 'General')[:23]:<25} "
                  f"{l['title'][:33]:<35} {l['created_by_name']}")

        if input("\nRead a lesson? yes/no: ").strip().lower() == "yes":
            lid = self._get_int("Enter lesson ID: ")
            if lid is None:
                return
            r = self.get_lesson_by_id(lid)
            if r["status"]:
                self._show_lesson(r["lesson"])
            else:
                print(r["message"])

    def _update_lesson(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID to browse: ")
        if sid is None:
            return
        result = self.get_lessons_by_subject(sid)
        if not result["status"]:
            print(result["message"])
            return
        for l in result["lessons"]:
            print(f"  [{l['lesson_id']}] Week {l['week']} — {l['title']}")

        lid = self._get_int("Enter lesson ID to update: ")
        if lid is None:
            return
        check = self.get_lesson_by_id(lid)
        if not check["status"]:
            print("Lesson not found.")
            return
        l = check["lesson"]
        print("Press Enter to keep current value.")
        title   = input(f"Title [{l['title']}]: ").strip() or None
        raw_w   = input(f"Week [{l['week']}]: ").strip()
        week    = int(raw_w) if raw_w.isdigit() and int(raw_w) >= 1 else None
        topic   = input(f"Topic [{l['topic'] or ''}]: ").strip()
        content = None
        if input("Update content? yes/no: ").strip().lower() == "yes":
            print("Enter new content. Type 'END' to finish:")
            lines = []
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                lines.append(line)
            content = "\n".join(lines) if lines else None

        result = self.update_lesson(
            lid, title=title, week=week,
            topic=topic if topic != "" else None,
            content=content
        )
        print(result["message"])

    def _delete_lesson(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID to browse: ")
        if sid is None:
            return
        result = self.get_lessons_by_subject(sid)
        if not result["status"]:
            print(result["message"])
            return
        for l in result["lessons"]:
            print(f"  [{l['lesson_id']}] Week {l['week']} — {l['title']}")
        lid = self._get_int("Enter lesson ID to delete: ")
        if lid is None:
            return
        if input("Are you sure? yes/no: ").strip().lower() != "yes":
            print("Cancelled.")
            return
        print(self.delete_lesson(lid)["message"])

    # ==================================================================
    # RESULTS
    # ==================================================================
    def _view_results_menu(self):
        while True:
            print("""
            --- View Results ---
            1. Results by subject
            2. All results
            3. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._results_by_subject()
            elif choice == "2": self._all_results()
            elif choice == "3": break
            else: print("Invalid choice.")

    def _results_by_subject(self):
        self._print_subjects(self.get_all_subjects().get("subjects", []))
        sid = self._get_int("Enter subject ID: ")
        if sid is None:
            return
        result = self.get_results_by_subject(sid)
        if not result["status"]:
            print(result["message"])
            return
        print(f"\n{'Name':<25} {'Score':<10} {'Percent':<10} {'Grade':<6} {'Date'}")
        print("-" * 70)
        for r in result["results"]:
            print(f"{r['fullname'][:23]:<25} "
                  f"{r['score']}/{r['total']:<8} "
                  f"{r['percent']:<10.2f} "
                  f"{r['grade']:<6} "
                  f"{str(r['created_at'])[:19]}")

    def _all_results(self):
        results = self.get_all_results()
        if not results:
            print("No results found.")
            return
        print(f"\n{'Name':<25} {'Subject':<22} {'Score':<10} {'Percent':<10} "
              f"{'Grade':<6} {'Date'}")
        print("-" * 90)
        for r in results:
            print(f"{r['fullname'][:23]:<25} "
                  f"{r['subject_name'][:20]:<22} "
                  f"{r['score']}/{r['total']:<8} "
                  f"{r['percent']:<10.2f} "
                  f"{r['grade']:<6} "
                  f"{str(r['created_at'])[:19]}")

    # ==================================================================
    # STAFF MANAGEMENT (admin only)
    # ==================================================================
    def _staff_management(self, admin):
        while True:
            print("""
            --- Staff Management ---
            1. Create staff account
            2. View all staff
            3. Reset staff password
            4. Delete staff account
            5. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": self._admin_create_staff(admin)
            elif choice == "2": self._view_all_staff()
            elif choice == "3": self._admin_reset_staff_password()
            elif choice == "4": self._admin_delete_staff()
            elif choice == "5": break
            else: print("Invalid choice.")

    def _admin_create_staff(self, admin):
        print("\n--- Create Staff Account ---")
        fullname   = input("Full name    : ").strip()
        if not fullname:
            print("Full name is required.")
            return
        email      = input("Email        : ").strip()
        if not self.validate_email(email):
            print("Invalid email address.")
            return
        phone      = input("Phone        : ").strip()
        department = input("Department   : ").strip()

        # Admin sets the initial password
        if input("Generate strong password? yes/no: ").strip().lower() == "yes":
            password = self.generate_strong_password()
            confirm  = password
            print(f"\n  Generated password: {password}")
            print("  Share this with the staff member securely.\n")
        else:
            password = input("Set password : ")
            confirm  = input("Confirm      : ")

        user_id = randint(100000, 899999)
        result  = self.create_account(
            email, fullname, password, confirm, "staff", user_id,
            phone=phone, department=department
        )
        if result["status"]:
            print(f"\n  Staff account created successfully!")
            print(f"  Name      : {fullname}")
            print(f"  Email     : {email}")
            print(f"  Staff ID  : {user_id}")
            print(f"  Department: {department or 'Not set'}")
            print(f"\n  Share the email and password with the staff member.")
        else:
            print(result["message"])

    def _view_all_staff(self):
        users = self.get_all_users()
        staff = [u for u in users if u["role"] == "staff"]
        if not staff:
            print("\n  No staff accounts found.")
            return
        print(f"\n  {'ID':<10} {'Name':<25} {'Email':<30} {'Department'}")
        print("  " + "-" * 80)
        for u in staff:
            print(f"  {u['id']:<10} {u['fullname'][:23]:<25} "
                  f"{u['email']:<30} {u['department'] or 'Not set'}")

    def _admin_reset_staff_password(self):
        self._view_all_staff()
        email = input("\nEnter staff email to reset password: ").strip()
        user  = self.get_user_by_email(email)
        if not user:
            print("No account found with that email.")
            return
        if user["role"] != "staff":
            print("That account is not a staff account.")
            return

        if input("Generate strong password? yes/no: ").strip().lower() == "yes":
            new_pw  = self.generate_strong_password()
            confirm = new_pw
            print(f"\n  New password: {new_pw}")
            print("  Share this with the staff member securely.\n")
        else:
            new_pw  = input("New password : ")
            confirm = input("Confirm      : ")

        result = self.reset_password(email, new_pw, confirm)
        print(result["message"])

    def _admin_delete_staff(self):
        self._view_all_staff()
        email = input("\nEnter staff email to delete: ").strip()
        user  = self.get_user_by_email(email)
        if not user:
            print("No account found with that email.")
            return
        if user["role"] != "staff":
            print("That account is not a staff account.")
            return
        print(f"\n  Name : {user['fullname']}")
        print(f"  Email: {user['email']}")
        if input("\n  Delete this staff account? yes/no: ").strip().lower() != "yes":
            print("  Cancelled.")
            return
        result = self.delete_user(user["id"])
        print(result["message"])

    # ==================================================================
    # ADMIN — VIEW ALL USERS
    # ==================================================================
    def _view_all_users(self):
        users = self.get_all_users()
        if not users:
            print("No users found.")
            return
        print(f"\n{'ID':<10} {'Name':<25} {'Email':<30} {'Role':<10} {'Dept'}")
        print("-" * 90)
        for u in users:
            print(f"{u['id']:<10} {u['fullname'][:23]:<25} "
                  f"{u['email']:<30} {u['role']:<10} "
                  f"{u['department'] or 'N/A'}")

    # ==================================================================
    # PROFILE
    # ==================================================================
    def _view_profile(self, user):
        while True:
            print(f"""
            --- Profile ---
            Name      : {user['fullname']}
            ID        : {user['id']}
            Email     : {user['email']}
            Role      : {user['role']}
            Phone     : {user.get('phone') or 'Not set'}
            Department: {user.get('department') or 'Not set'}

            1. Update profile
            2. Back
            """)
            choice = input("Enter choice: ").strip()
            if   choice == "1": user = self._update_profile(user)
            elif choice == "2": break
            else: print("Invalid choice.")

    def _update_profile(self, user):
        print("\n--- Update Profile --- (Press Enter to keep current value)")
        fullname   = input(f"Full name [{user['fullname']}]: ").strip() or None
        phone      = input(f"Phone [{user.get('phone') or ''}]: ").strip() or None
        department = input(f"Department [{user.get('department') or ''}]: ").strip() or None
        result     = self.update_profile(user["id"], fullname, phone, department)
        print(result["message"])
        return result["data"] if result["status"] else user

    # ==================================================================
    # HELPERS
    # ==================================================================
    def _refresh_user(self, user):
        self.mycursor.execute("SELECT * FROM users WHERE id=%s", (user["id"],))
        fresh = self.mycursor.fetchone()
        return fresh if fresh else user

    def _print_subjects(self, subjects):
        if not subjects:
            print("No subjects found.")
            return
        print(f"\n{'ID':<5} {'Code':<12} {'Name':<30} {'Questions':<12} {'Lessons'}")
        print("-" * 70)
        for s in subjects:
            print(f"{s['subject_id']:<5} {s['subject_code']:<12} "
                  f"{s['subject_name']:<30} "
                  f"{s.get('question_count', 0):<12} "
                  f"{s.get('lesson_count', 0)}")

    def _print_question(self, q):
        print(f"\n  [ID: {q['id']}]  {q['question']}")
        print(f"    A. {q['option_a']}")
        print(f"    B. {q['option_b']}")
        print(f"    C. {q['option_c']}")
        print(f"    D. {q['option_d']}")
        print(f"    Answer: {q['answer']}")

    def _get_int(self, prompt):
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Please enter a valid number.")
            return None


if __name__ == "__main__":
    cbtapp("AcademIQ")