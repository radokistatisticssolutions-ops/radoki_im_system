# Setting Up Project on a New Computer

Follow these steps to continue development on a different machine:

## Prerequisites

Install on your new computer:

- **Python 3.10+** - https://www.python.org/
- **PostgreSQL** - https://www.postgresql.org/download/
- **Git** - https://git-scm.com/

## Step 1: Clone the Repository

```bash
git clone <your-github-repository-url>
cd radoki_im_system
```

## Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Setup PostgreSQL Database

**Option A: Local PostgreSQL (Development)**

```bash
# Create database (using pgAdmin or psql)
# Windows (Command Prompt):
psql -U postgres
# Then in psql:
CREATE DATABASE radoki_db;
```

**Option B: Connect to Existing Database**

- If you have database backups, restore them:
  ```bash
  psql -U postgres radoki_db < backup.sql
  ```

## Step 5: Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your local settings:
# - Update DATABASE_URL with your PostgreSQL credentials
# - Update EMAIL credentials if needed
# - Keep SECRET_KEY as is (or generate a new one for production)
```

**Windows Command Prompt:**

```cmd
copy .env.example .env
# Then edit .env with your favorite editor
```

## Step 6: Run Database Migrations

```bash
python manage.py migrate
```

If this is your first time setting up:

```bash
# Create a superuser account
python manage.py createsuperuser
# Follow the prompts to create admin account
```

## Step 7: Collect Static Files (if needed)

```bash
python manage.py collectstatic --noinput
```

## Step 8: Run Development Server

```bash
python manage.py runserver
```

Access the application at: **http://localhost:8000**

Admin panel at: **http://localhost:8000/admin**

---

## Backing Up & Restoring Database

### Backup Database

```bash
pg_dump -U postgres radoki_db > backup.sql
```

Keep `backup.sql` in a safe location (NOT in git repository).

### Restore Database

```bash
psql -U postgres radoki_db < backup.sql
```

---

## If You Already Have Backup Files

```bash
# Place backup files in a safe location
# Create empty database:
psql -U postgres
CREATE DATABASE radoki_db;

# Restore from backup:
psql -U postgres radoki_db < path/to/backup.sql

# Run migrations to update schema:
python manage.py migrate
```

---

## Troubleshooting

### Issue: "Database does not exist"

```bash
# Create it:
psql -U postgres
CREATE DATABASE radoki_db;
```

### Issue: "Connection refused" (PostgreSQL)

- Make sure PostgreSQL service is running
- Update DATABASE_URL in .env with correct credentials

### Issue: "Port 5432 already in use"

- Either stop the conflicting process or update DATABASE_URL to use a different port

### Issue: "ModuleNotFoundError"

```bash
# Make sure virtual environment is activated
# Then reinstall dependencies:
pip install -r requirements.txt
```

### Issue: "Migrations not applied"

```bash
# Check migration status:
python manage.py showmigrations

# Apply all migrations:
python manage.py migrate
```

---

## Quick Reference Commands

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Run server
python manage.py runserver

# Run tests
python manage.py test

# Create migrations (after model changes)
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# PostgreSQL commands
psql -U postgres  # Connect to PostgreSQL
psql -l  # List all databases
```

---

## Important Security Notes

⚠️ **NEVER commit these files to GitHub:**

- `.env` - Always use `.env.example` as template
- `db.sqlite3` or database files
- `.claude/` folder
- `__pycache__/` folders

✅ **Always included:**

- `.env.example` - Safe template
- `requirements.txt` - Dependencies
- Migration files - Database schema

---

## Sync Changes with Team

```bash
# Before starting work:
git pull origin main

# After making changes:
git add .
git commit -m "Your commit message"
git push origin main
```

---

For more details, see the main [README.md](README.md)
