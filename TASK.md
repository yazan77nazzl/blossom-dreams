The Render upload error is now:

`Could not reach the image storage service: [Errno -2] Name or service not known`

The expected Supabase project URL is:

`https://jhfldeoquxqejwyeohhw.supabase.co`

The `uploads` bucket exists and uploads work locally.

Do NOT make more code changes yet.

First diagnose the actual runtime configuration on Render:

1. Log the parsed SUPABASE_URL safely (protocol + hostname only, never secrets).
2. Log the final Supabase Storage upload URL hostname and path, without logging the service role key.
3. Verify that the hostname is exactly `jhfldeoquxqejwyeohhw.supabase.co`.
4. Check for whitespace, quotes, duplicate `SUPABASE_URL=`, `/rest/v1/`, or any other malformed value coming from the Render environment variable.
5. Do not auto-correct or modify the URL yet; show the actual parsed hostname in Render logs.
6. Do not expose `SUPABASE_SERVICE_ROLE_KEY`.

After adding only the necessary safe diagnostic logging, tell me exactly what hostname the running Render process is using.
