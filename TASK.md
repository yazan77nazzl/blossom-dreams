URGENT: Render deployment is failing during application startup.

The exact production error is:

psycopg.ProgrammingError:
only '%s', '%b', '%t' are allowed as placeholders, got '%0'

The traceback points to:

app/seed_data.py line 111

Specifically this query:

UPDATE locations SET google_maps_url = ?
WHERE slug = 'versailles'
  AND (
    google_maps_url IS NULL
    OR google_maps_url = ''
    OR google_maps_url LIKE '%0x151f4096b6ee7923%'
  )

The project uses SQLite locally and PostgreSQL/Neon in production.

The problem is that PostgreSQL/psycopg does NOT use SQLite's `?` parameter placeholder. It uses `%s`.

Also, the Google Maps URL contains `%` characters, so make sure the URL is passed as a bound parameter and is NOT interpolated directly into the SQL string.

FIX THE ROOT CAUSE PROPERLY.

Requirements:

1. Make the seed_database() location update compatible with PostgreSQL/psycopg.
2. Preserve SQLite compatibility if the project supports both databases.
3. Do NOT hardcode or directly interpolate the Google Maps URL into the SQL query.
4. Use the project's existing database abstraction/helper if it already handles database-specific placeholders.
5. Make sure LIKE parameters are also handled correctly for PostgreSQL.
6. Do not modify the correct Amwaj Center location.
7. Do not change any other booking functionality.
8. Do not remove the Versailles location update; fix it correctly.
9. Run the relevant tests.
10. Test application startup using PostgreSQL/psycopg, because SQLite alone will NOT catch this bug.
11. Run the exact production startup command:
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   and verify that the application starts without an exception.

IMPORTANT:
Do not make random changes.
Do not change the Google Maps URL to avoid the error.
The correct fix is to make the SQL/database parameter handling compatible with PostgreSQL while preserving SQLite support.

After fixing it, verify:
- seed_database() completes successfully
- FastAPI startup completes
- No "Application startup failed" error
- Render can start the service successfully
- Existing booking functionality remains intact