The upload error on Render is now:

`Could not reach the image storage service: Request URL is missing an 'http://' or 'https://' protocol.`

The Render environment variable `SUPABASE_URL` is configured as:

`https://jhfldeoquxqejwyeohhw.supabase.co`

The Supabase `uploads` bucket exists and is Public.

Please inspect the actual code in `app/routers/upload.py` and `app/config.py` and determine why the HTTP request URL is being constructed without the `http://` or `https://` protocol.

Check:

* How `SUPABASE_URL` is loaded from environment variables.
* Whether the code accidentally strips `https://`.
* Whether `.strip()`, URL parsing, or string concatenation is corrupting the URL.
* How the Storage upload URL is constructed.
* Whether Render is actually passing the expected environment variable to the running process.

Add safe logging that shows the URL structure being used (but NEVER log `SUPABASE_SERVICE_ROLE_KEY` or any secret).

Do not switch to local storage.
Do not create another bucket.
Do not hardcode the Supabase URL.
Do not expose secrets.

Fix the root cause and test `/api/upload` again on Render.
