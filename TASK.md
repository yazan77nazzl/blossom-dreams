The Supabase Storage upload is now failing with:

`Image storage failed (HTTP 401).`

The environment variables are configured in Render and the deployment succeeds.

Please investigate and fix this properly.

Important context:

* The project currently uses `SUPABASE_URL`
* The project currently uses `SUPABASE_SERVICE_ROLE_KEY`
* I configured `SUPABASE_SERVICE_ROLE_KEY` in Render using the new Supabase Secret Key (`sb_secret_...`)
* Storage bucket is `uploads`
* The previous missing-environment-variable error is fixed.
* The current failure is specifically HTTP 401 from Supabase Storage.

Please:

1. Inspect the exact code responsible for the Storage upload.
2. Check how the Supabase Storage HTTP request is authenticated.
3. Verify whether the code expects the legacy `service_role` JWT key or the new `sb_secret_...` Secret Key.
4. Update the implementation to correctly authenticate with the current Supabase API/Storage authentication mechanism.
5. If the current code uses `Authorization: Bearer ...`, verify that this is actually correct for the key type being used.
6. Prefer the official Supabase server-side client/library if appropriate instead of manually constructing HTTP requests with `httpx`, unless there is a good reason to keep the existing implementation.
7. Keep all secret credentials strictly server-side.
8. Do NOT ask me to expose or paste any secret key.
9. Verify that the Storage bucket name and Supabase project URL are correct.
10. Test the upload flow after making the change.
11. Also verify image replacement and deletion.
12. Run all existing tests, lint/typecheck/build if available.
13. Make the actual code changes in the project.

Do not just explain the issue. Diagnose the 401 and implement the correct fix.
