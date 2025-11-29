# Timer Tracking App - MVP

A simple Django-based timer tracking application for tracking time spent on tasks across different customers and projects.

## Quick Start

**The fastest way to get started:**

```bash
./start.sh
```

This script will:
1. Create a virtual environment (if needed)
2. Install all dependencies
3. Run database migrations
4. Start the development server

Then open your browser to: **http://127.0.0.1:8000/**

## Features

- **User Authentication**: Register, login, and logout functionality
- **Customer Management**: Create and manage clients
- **Project Management**: Organize work by projects under customers
- **Timer Tracking**: Track time spent on specific tasks with live timer display
- **Session Notes**: Add notes describing work done during each timer session
- **Cost Calculation**: Automatically calculate costs based on hourly rates
- **Project Status**: Mark projects as completed to prevent further timing

## Installation

1. **Install Python** (3.8 or higher recommended)

2. **Set up environment variables**:
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and set your SECRET_KEY
   # Generate a new secret key with:
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser** (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

7. **Access the application**:
   - Open your browser and go to: http://127.0.0.1:8000/
   - Register a new account or login

## Usage

### Basic Workflow

1. **Register/Login**: Create an account or login
2. **Add a Customer**: Create a client you work for
3. **Add a Project**: Create a project under that customer
4. **Add a Timer**: Create a timer with a task name and hourly rate
5. **Start Timer**: Click "Start" to begin tracking time
6. **Stop Timer**: Click "Stop" when done, then add a note about what you worked on
7. **View Sessions**: See all your timer sessions with durations and costs

### Key Features

- **Live Timer Display**: When a timer is running, it updates every second
- **Automatic Cost Calculation**: Costs are calculated automatically based on duration and hourly rate
- **Session Notes**: Add notes when stopping timers to document your work
- **Project Completion**: Mark projects as complete to prevent accidental time tracking
- **Data Isolation**: Each user can only see their own data

## Project Structure

```
timer_app/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── db.sqlite3               # Database (created after migration)
├── config/                  # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── timer_app/               # Main application
    ├── models.py            # Database models
    ├── views.py             # View logic
    ├── forms.py             # Form definitions
    ├── urls.py              # URL routing
    ├── admin.py             # Admin configuration
    ├── templatetags/        # Custom template filters
    │   └── timer_filters.py
    └── templates/           # HTML templates
        └── timer_app/
```

## Database Models

- **Customer**: Clients you work for
- **Project**: Projects under each customer (can be active or completed)
- **Timer**: Tasks/activities within projects (with hourly rate)
- **TimerSession**: Individual time tracking sessions (start, end, note)

## Admin Interface

Access the Django admin at http://127.0.0.1:8000/admin/ using your superuser credentials.

## Development

This is an MVP (Minimum Viable Product) focused on core functionality. The design is intentionally simple and functional.

## Notes

- Uses SQLite database (suitable for single-user or small team use)
- All times are stored in UTC
- The app uses Django's built-in authentication system
- AJAX is used for timer start/stop operations for a smooth user experience

## Environment Variables

The application uses a `.env` file for configuration. Key variables:

- `SECRET_KEY` - Django secret key (generate a new one for production!)
- `DEBUG` - Set to `True` for development, `False` for production
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DATABASE_NAME` - SQLite database filename

## Security Note

For production use, you should:
1. Generate a new SECRET_KEY and add it to .env
2. Set DEBUG=False in .env
3. Configure ALLOWED_HOSTS properly in .env
4. Use a production-grade database (PostgreSQL, MySQL)
5. Set up proper static file serving
6. Use HTTPS
7. Never commit your .env file to git!

