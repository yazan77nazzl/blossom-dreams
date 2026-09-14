The same Render error persists after the `.strip()` fix:

`httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol.`

Do NOT make another speculative fix.

Open `app/routers/upload.py` and inspect the exact HTTPX call that raises this exception.

Before that exact call, add a temporary safe diagnostic that logs:

`FINAL_UPLOAD_URL_REPR=<repr of the exact URL variable passed to httpx>`

Also log:

`SUPABASE_URL_REPR=<repr(settings.SUPABASE_URL)>`

and:

`UPLOAD_BUCKET_REPR=<repr(settings.SUPABASE_STORAGE_BUCKET)>`

Do NOT log `SUPABASE_SERVICE_ROLE_KEY`.

Then deploy this diagnostic to Render and reproduce ONE upload.

The purpose is to see the exact string passed to httpx. Do not assume the problem is whitespace, URL construction, or environment configuration until the logged value proves it.

If the final URL is valid (starts with https://), inspect the HTTPX call signature itself and verify that the URL argument is actually the full URL rather than a path or another variable.

Do not change storage provider, bucket, or database.
