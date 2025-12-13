# KonnectAble

Social platform for differently abled people — Django project.

Quick start

1. Create a virtualenv and install requirements.

```bash
python -m venv .env
.env\\Scripts\\activate
python -m pip install -r requirements.txt
```

2. Run migrations and start server:

```bash
.env\\Scripts\\python.exe manage.py migrate
.env\\Scripts\\python.exe manage.py runserver
```

Notes

- Do not commit `.env` or `db.sqlite3`.
- Add a GitHub remote and push: `git remote add origin <url>` then `git push -u origin main`.