The Render deployment still returns:

`Could not reach the image storage service: Request URL is missing an 'http://' or 'https://' protocol.`

Local diagnostics show the expected URL is correct:

`https://jhfldeoquxqejwyeohhw.supabase.co`

Do NOT add another URL fallback and do NOT make more speculative fixes.

Trace the exact value passed as the URL argument to `httpx.AsyncClient().put()` (or the actual HTTP request used by `_store_supabase`) at runtime.

I need you to identify the exact final request URL immediately before the HTTP request is executed.

Log ONLY:

* the final URL with the service-role secret completely removed
* its `repr()`
* the hostname
* the protocol

Do not log any secret values.

Then inspect how that final URL is constructed in `app/routers/upload.py`.

The important question is:
Why does httpx report that the request URL has no http:// or https:// protocol if SUPABASE_URL itself is correct?

Do not modify the code until you identify the exact malformed value.

After identifying the cause, fix only the root cause and test `/api/upload`.
