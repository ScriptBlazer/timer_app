# Timer Tracking App - Complete Setup & Testing Guide

## What Has Been Built

A fully functional timer tracking web application with the following features:

### Core Functionality
✅ User authentication (register, login, logout)
✅ Customer management (create, view, edit, delete)
✅ Project management (create, view, edit, delete, mark complete)
✅ Timer management (create, view, delete)
✅ Timer start/stop with live updates (updates every second)
✅ Session notes (add when stopping timer, edit later)
✅ Session management (view, edit notes, delete)
✅ Automatic duration calculations (HH:MM:SS format)
✅ Automatic cost calculations (duration × hourly rate)
✅ Permission system (users can only see their own data)

### Technical Implementation
- Django 4.2.7 backend
- SQLite database
- Django templates for frontend
- Vanilla JavaScript for AJAX and live timers
- Clean, functional CSS styling
- RESTful URL structure
- Proper data relationships with cascade deletes

## File Structure

```
timer_app/
├── manage.py                          # Django management script
├── requirements.txt                   # Python dependencies
├── README.md                          # Main documentation
├── SETUP_GUIDE.md                     # This file
├── start.sh                           # Quick start script
├── .gitignore                         # Git ignore rules
├── db.sqlite3                         # Database (created after setup)
├── venv/                              # Virtual environment (created after setup)
├── config/                            # Django project settings
│   ├── __init__.py
│   ├── settings.py                    # Project settings
│   ├── urls.py                        # Main URL configuration
│   ├── wsgi.py                        # WSGI configuration
│   └── asgi.py                        # ASGI configuration
└── timer_app/                         # Main application
    ├── __init__.py
    ├── models.py                      # Database models
    ├── views.py                       # View logic (all CRUD + AJAX)
    ├── forms.py                       # Form definitions
    ├── urls.py                        # URL routing
    ├── admin.py                       # Admin configuration
    ├── migrations/                    # Database migrations
    │   └── 0001_initial.py
    ├── templatetags/                  # Custom template filters
    │   ├── __init__.py
    │   └── timer_filters.py           # Duration and currency formatters
    └── templates/timer_app/           # HTML templates
        ├── base.html                  # Base template with navbar and styling
        ├── login.html                 # Login page
        ├── register.html              # Registration page
        ├── customer_list.html         # List all customers
        ├── customer_detail.html       # Customer detail with projects
        ├── customer_form.html         # Add/edit customer
        ├── customer_confirm_delete.html
        ├── project_form.html          # Add/edit project
        ├── project_detail.html        # Project detail with timers (+ AJAX)
        ├── project_confirm_delete.html
        ├── project_confirm_complete.html
        ├── timer_form.html            # Add timer
        ├── timer_detail.html          # Timer detail with sessions (+ AJAX)
        ├── timer_confirm_delete.html
        └── session_confirm_delete.html
```

## Setup Instructions

### Option 1: Quick Start (Recommended)

```bash
chmod +x start.sh
./start.sh
```

### Option 2: Manual Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```

2. **Activate virtual environment:**
   ```bash
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start server:**
   ```bash
   python manage.py runserver
   ```

7. **Open browser:**
   - Go to: http://127.0.0.1:8000/

## Testing the Application

### 1. User Registration & Login
1. Go to http://127.0.0.1:8000/
2. Click "Register here"
3. Create an account with username, email, and password
4. You'll be automatically logged in and redirected to the customer list

### 2. Create a Customer
1. Click "Add Customer" button
2. Enter a name (e.g., "Acme Corp")
3. Click "Save"
4. You should see the customer detail page

### 3. Create a Project
1. On the customer detail page, click "Add Project"
2. Enter a project name (e.g., "Website Redesign")
3. Click "Save"
4. You should see the project detail page

### 4. Create a Timer
1. On the project detail page, click "Add Timer"
2. Enter a task name (e.g., "Frontend Development")
3. Enter a price per hour (e.g., 75.00)
4. Click "Save"
5. You should see the project detail page with your new timer

### 5. Start and Stop a Timer
1. Click the green "Start" button on a timer
2. The timer should immediately show "RUNNING" status
3. Watch the "Current Session" column - it should update every second
4. Click the red "Stop" button
5. A modal should appear asking for a note
6. Type what you worked on (e.g., "Implemented login page")
7. Click "Save"
8. The timer should now show "STOPPED" status
9. Notice the "Total Time" and "Total Cost" have been updated

### 6. View Sessions
1. Click "Sessions" button on a timer
2. You should see all sessions with:
   - Start and end times
   - Duration in HH:MM:SS format
   - Cost calculated from duration × hourly rate
   - Your note
3. Try clicking "Edit" on a note to change it
4. Try starting and stopping the timer multiple times to create more sessions

### 7. Test Completed Projects
1. Go back to a project detail page
2. Click "Mark Complete"
3. Confirm the action
4. Notice the "Start" buttons are now gone
5. Try to start a timer - it should be prevented

### 8. Test Data Isolation
1. Logout
2. Register a new account
3. Login with the new account
4. You should see an empty customer list
5. The previous account's data should not be visible

### 9. Test Calculations
1. Create a timer with $100/hour rate
2. Start it, wait a minute, then stop it
3. Check that the cost is approximately $1.67 (1 minute ÷ 60 minutes × $100)
4. The duration should show as 00:01:00 (or close to it)

### 10. Test Cascading Deletes
1. Create a customer with projects, timers, and sessions
2. Delete the customer
3. All related data should be deleted automatically

## URL Reference

```
/                                  → Home (redirects to /customers/ if logged in)
/login/                           → Login page
/register/                        → Registration page
/logout/                          → Logout (redirects to login)

/customers/                       → List all customers
/customers/add/                   → Add new customer
/customers/<id>/                  → Customer detail (shows projects)
/customers/<id>/edit/             → Edit customer
/customers/<id>/delete/           → Delete customer

/projects/add/?customer=<id>      → Add new project
/projects/<id>/                   → Project detail (shows timers)
/projects/<id>/edit/              → Edit project
/projects/<id>/delete/            → Delete project
/projects/<id>/complete/          → Mark project as completed

/timers/add/?project=<id>         → Add new timer
/timers/<id>/                     → Timer detail (shows sessions)
/timers/<id>/delete/              → Delete timer
/timers/<id>/start/               → Start timer (AJAX)
/timers/<id>/stop/                → Stop timer (AJAX)

/sessions/<id>/note/              → Update session note (AJAX)
/sessions/<id>/delete/            → Delete session
```

## Admin Interface

Access at http://127.0.0.1:8000/admin/ using superuser credentials.

You can view and manage all data through the admin interface.

## Troubleshooting

### Server won't start
- Make sure virtual environment is activated
- Make sure Django is installed: `pip list | grep Django`
- Run migrations: `python manage.py migrate`

### Cannot login
- Make sure you registered an account
- Try creating a superuser: `python manage.py createsuperuser`

### Timer not updating
- Make sure JavaScript is enabled in your browser
- Check browser console for errors (F12 → Console tab)

### Database errors
- Delete db.sqlite3 and re-run: `python manage.py migrate`

### Permission errors
- Make sure you're logged in
- Try accessing only your own data

## Key Features Implemented

### Business Logic
- ✅ Users can only see their own data
- ✅ Cannot start timer on completed project
- ✅ Cannot start already-running timer
- ✅ Cannot stop already-stopped timer
- ✅ Only one active session per timer at a time
- ✅ Cascade deletes (delete customer → deletes all related data)

### UI/UX Features
- ✅ Live timer display (updates every second)
- ✅ AJAX for start/stop (no page reload)
- ✅ Modal for adding session notes
- ✅ Success/error messages for all actions
- ✅ Breadcrumb navigation
- ✅ Clean, functional design
- ✅ Status badges (running/stopped, active/completed)
- ✅ Formatted durations (HH:MM:SS)
- ✅ Formatted currency ($XX.XX)

### Data Integrity
- ✅ Required fields validated
- ✅ Foreign key relationships
- ✅ Cascade deletes
- ✅ Timestamps on all records
- ✅ Decimal precision for money

## Success Criteria ✅

All success criteria from the MVP requirements have been met:

✅ A user can register and login
✅ A user can add customers, projects, and timers
✅ A user can start and stop timers
✅ Timer duration is tracked accurately
✅ Notes can be added when stopping timers
✅ All calculations (duration, cost, totals) are correct
✅ The live timer updates every second while running
✅ All CRUD operations work without errors
✅ Users can only see their own data
✅ The app works in modern browsers without breaking

## Next Steps (Beyond MVP)

If you want to extend this app, consider:
- Export to PDF or Excel
- Charts and graphs for time tracking
- Invoice generation
- Filtering and search
- Team features
- Mobile app
- API for integrations
- Recurring timers
- Time rounding options
- Bulk operations

## Support

For issues or questions, refer to the README.md or check Django documentation at https://docs.djangoproject.com/

