# Shamskay Academy - Django LMS

## Project Overview
A full-featured Learning Management System for Shamskay Academy, a secondary school. Built with Django 5.2, using a role-based access control system with admin, staff, student, and parent accounts.

## Tech Stack
- **Backend**: Django 5.2
- **Database**: MySQL (mysqlclient)
- **Frontend**: Bootstrap 5.3, Bootstrap Icons
- **Testing**: pytest, pytest-django
- **PDF**: ReportLab
- **Email**: Django console backend (development)

## Architecture

### Apps Structure
```
accounts/          - Authentication, profiles, registration, password reset
school/            - Core models, admin views, dashboards, reports, fees, events, audit
students/          - Student-facing views (dashboard, results, subjects, tests)
staff/             - Staff dashboard and management views
subjects/          - Class, subject, class-subject, class-teacher management
materials/         - Study material upload and management
assessments/       - Test/exam creation, result entry, term calculations, promotion
```

### Key Models (`school/models.py`)
- `Term` - Academic terms with start/end dates
- `AcademicClass` - Classes like JSS1, JSS2, JSS3, SSS1, SSS2, SSS3
- `Subject` - Subjects with codes (e.g., MTH, ENG)
- `ClassSubject` - Links subjects to classes
- `ClassTeacher` - Assigns teachers to classes
- `Test` / `Exam` - Assessments created by staff
- `TestResult` / `ExamResult` - Individual student results
- `TermResult` - Aggregated term performance per student
- `PromotionDecision` - Promotion/repeat decisions per term
- `GradeBoundary` - Letter grade definitions (A, B, C, etc.) with min/max scores
- `ResultRemark` - Teacher remarks for student results
- `ReportCard` - Formal term summaries with teacher/principal remarks
- `ParentProfile` - Links parent users to student users
- `SchoolEvent` - Calendar events (holidays, exams, meetings, etc.)
- `Fee` / `Payment` - Fee management and payment tracking
- `AuditLog` - System action logging (login/logout/create/update/delete)

### User Roles (`accounts/models.py`)
- `student` - Can view subjects, take tests, view results, report cards
- `staff` - Can create tests/exams, enter results, manage materials, view class results
- `admin` - Full system access, manages all entities
- `parent` - Can view linked children's results and report cards

## Important Design Decisions

### Parent Access
- Admin creates a `ParentProfile` linking a parent user to a student
- Admin sets an invitation code (or it auto-generates `PAR-XXXXXX`)
- Parent visits `/accounts/parent/register/`, enters code, sets username/password
- Parent logs in via standard login, redirected to parent dashboard
- Parent can view linked children's results, term results, and report cards

### Result Entry
- **Single entry**: `/assessments/staff/enter-test-result/` and `/assessments/staff/enter-exam-result/`
- **Bulk table entry**: `/assessments/staff/enter-results/?type=test|exam` - select assessment, enter scores for all students in class

### Delete Confirmation
- All delete actions use a single global Bootstrap modal in `base.html`
- Buttons use `data-bs-target="#deleteModal"`, `data-delete-url`, `data-delete-name`
- JavaScript dynamically sets form action and message

### Grading
- `GradeBoundary` model defines letter grades with min/max scores and remarks
- Not yet automatically applied to result display (future enhancement)

### Audit Logging
- Automatic login/logout logging via Django signals (`school/signals.py`)
- Views should manually log create/update/delete actions (not yet fully implemented everywhere)

## URL Structure

### Public
- `/` - Home page
- `/accounts/login/` - Login
- `/accounts/password_reset/` - Password reset
- `/accounts/role_selection/` - Choose account type

### Student
- `/students/dashboard/` - Student dashboard
- `/students/subjects/` - My subjects
- `/students/results/` - My results
- `/students/term-results/` - Term results
- `/student/report-card/` - Report cards

### Staff
- `/staff/dashboard/` - Staff dashboard
- `/assessments/staff/create-test/` - Create test
- `/assessments/staff/manage-tests/` - Manage tests
- `/assessments/staff/enter-results/` - Enter results (bulk table)

### Admin (panel)
- `/panel/dashboard/` - Admin dashboard
- `/panel/students/` - Manage students
- `/panel/all-results/` - All student results
- `/panel/grade-boundaries/` - Grade boundaries
- `/panel/result-remarks/` - Result remarks
- `/panel/generate-report-cards/` - Generate report cards
- `/panel/parent-profiles/` - Parent profiles
- `/panel/events/` - School events
- `/panel/fees/` - Fees management
- `/panel/payments/` - Payment tracking
- `/panel/audit-logs/` - Audit logs
- `/panel/export/students/` - Export students CSV
- `/panel/export/results/` - Export results CSV

### Parent
- `/parent/dashboard/` - Parent dashboard
- `/parent/child/<student_id>/` - Child detail view

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run dev server
python manage.py runserver

# Run tests
python -m pytest tests/ -v
```

## Current Gaps / Roadmap

### Missing Features
1. **Attendance tracking** - Daily attendance per class/student
2. **Homework/assignments** - Creation, submission, grading
3. **Timetable/schedule** - Class periods and teacher schedules
4. **Library management** - Book catalog, borrowing, returns
5. **Transport management** - Routes and student assignments
6. **Advanced search** - More robust filtering across list pages
7. **Bulk student import** - CSV upload for student registration
8. **Excel exports** - Beyond current CSV exports
9. **REST API** - For mobile apps or integrations
10. **Parent messaging** - Communication between parents and teachers

### Code Quality
- 12 basic tests only; need more coverage for new features
- Some duplicate patterns between `students/` and `assessments/` apps
- Audit logging not fully implemented in all views
- Grading boundaries not yet applied to student-facing result pages

## Conventions

### Templates
- All templates extend `base.html`
- Use Bootstrap 5 classes for layout
- Delete buttons use global modal pattern
- Forms use `novalidate` and show errors inline

### Views
- Admin views: `@login_required` + `@user_passes_test(lambda u: u.is_superuser)`
- Staff views: `@staff_required` decorator
- Student views: `@login_required` + role check
- Parent views: `@login_required` + role check for `ROLE_PARENT`

### CSS
- `static/css/style.css` - Global styles
- `static/css/login.css` - Login/registration pages
- `static/css/home.css` - Home page specific
- Mobile breakpoints: 768px and 576px

### Forms
- Admin forms in `school/forms.py`
- Account forms in `accounts/forms.py`
- Assessment forms in `assessments/forms.py`

## Important Files
- `school/models.py` - All core models
- `school/views.py` - Admin views, parent dashboard, grade boundaries, fees, events
- `school/urls.py` - School app URLs
- `templates/base.html` - Base template with global modal
- `accounts/views.py` - Auth views and parent registration
- `accounts/forms.py` - Registration forms including parent
- `assessments/views.py` - Test/exam creation and result entry
