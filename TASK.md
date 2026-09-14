The Render logs show:

GET /api/health → 200 OK

but image uploads consistently show:

POST /api/upload → 502 Bad Gateway

Supabase Storage bucket `uploads` exists and is Public. The same upload works locally.

Please investigate `/api/upload` and identify the exact exception/error occurring when the backend attempts to upload to Supabase Storage on Render.

Check the actual exception handling and logging in `app/routers/upload.py` and the Supabase Storage client.

Do not change storage back to local.
Do not create a new bucket.
Do not change the Supabase bucket name.
Do not hide the underlying exception.

Add/fix useful server-side logging if necessary so the exact Supabase error is visible in Render logs, then fix the root cause.

After fixing, test POST `/api/upload` on Render and confirm it returns 200/201 instead of 502.
