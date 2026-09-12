# Production process definition (Render / Heroku-style platforms).
# The app binds 0.0.0.0 and reads PORT from the platform's environment.
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}