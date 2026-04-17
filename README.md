# Radoki IM System

A Django-based training and management system built with Django 5.2.

## Features

- User account management and authentication
- Course management and resource distribution
- Payment processing and receipts
- Attendance tracking
- Dashboard with analytics
- Certificate generation
- User referral and rewards system

## Tech Stack

- **Backend**: Django 5.2
- **Database**: PostgreSQL (psycopg2)
- **Frontend**: Bootstrap 5 with Django Crispy Forms
- **PDF Generation**: ReportLab
- **Environment Management**: django-environ

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd radoki_im_system
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Update database credentials and other settings

5. **Run migrations**

   ```bash
   python manage.py migrate
   ```

6. **Create superuser**

   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

Access the application at `http://localhost:8000`

## Project Structure

```
radoki_im_system/
├── accounts/          # User authentication and profiles
├── courses/          # Course management
├── assignments/      # Assignment management
├── payments/         # Payment processing
├── attendance/       # Attendance tracking
├── dashboard/        # Analytics and dashboards
├── core/            # Core functionality
├── media/           # User uploads (media files, receipts)
├── static/          # Static files (CSS, JS)
└── radoki/          # Project settings
```

## Database

This project uses **PostgreSQL** as the primary database.

### For Production Deployment:

- Use a managed PostgreSQL service (AWS RDS, DigitalOcean, Heroku Postgres, etc.)
- Connection details should be stored in environment variables (`.env` file)
- Never commit `.env` to version control

### For Local Development:

- Install PostgreSQL locally
- Update `.env` with your database credentials
- Run migrations to set up tables

### Backing Up & Restoring Database:

```bash
# Backup
pg_dump -U username dbname > backup.sql

# Restore
psql -U username dbname < backup.sql
```

## Configuration

All sensitive configuration is stored in environment variables (`.env`):

- Database credentials
- Secret keys
- Debug mode
- Allowed hosts

Make sure to set these before running the application.

## Running Tests

```bash
python manage.py test
```

## Deployment

For production deployment:

1. Set `DEBUG = False` in settings
2. Configure `ALLOWED_HOSTS`
3. Use a production WSGI server (Gunicorn, uWSGI)
4. Set up static files collection
5. Configure a reverse proxy (Nginx)

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License

[Specify your license here]

## Support

For issues or questions, please contact the development team.
