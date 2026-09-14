The Render traceback confirms:

`httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol.`

This happens inside `_store_supabase` when making the HTTP request.

The diagnostic log we added is NOT appearing before the exception, so inspect the code directly.

Open `app/routers/upload.py` and find the exact line that calls `httpx` (`client.post`, `client.put`, or equivalent).

Trace the variable used as the request URL backwards until you reach `settings.SUPABASE_URL`.

I want you to verify the exact construction.

The final Storage upload URL MUST be constructed as:

`{SUPABASE_URL}/storage/v1/object/{bucket}/{filename}`

where:

`SUPABASE_URL = https://jhfldeoquxqejwyeohhw.supabase.co`

Do not use `/rest/v1/`.
Do not use `/public/` in the upload API URL.
Do not strip the protocol.
Do not use a relative URL.
Do not hardcode the complete URL.

Also inspect whether the code is accidentally passing only a path such as:

`/storage/v1/object/...`

to httpx instead of the complete absolute URL.

Fix the exact construction bug and run a direct test of `_store_supabase` or `/api/upload`.

Do not change the bucket or storage provider.
