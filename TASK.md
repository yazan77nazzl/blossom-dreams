I have a problem in my Admin page:

`Supabase storage is not configured (missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).`

Whenever I add an image or edit/replace an image from the Admin panel, I get this error.

I want you to fix this **properly and permanently**, not hide the error or add a temporary fallback.

Please:

1. Inspect the entire project and find every usage of:

   * `SUPABASE_URL`
   * `SUPABASE_SERVICE_ROLE_KEY`
   * `createClient`
   * `supabase.storage`
   * `.upload()`
   * Any code responsible for uploading, replacing, or deleting images.

2. Identify the exact reason why the Supabase environment variables are missing or not being loaded on the server.

3. Check which framework/environment the project uses (Next.js, Vite, etc.) and use the correct environment-variable setup for that framework.

4. Fix the Supabase server/admin client so it runs only on the server and **never exposes the service-role/secret key to the browser or client-side code**.

5. If the project currently uses `SUPABASE_SERVICE_ROLE_KEY`, check whether the current Supabase Secret Key should be used instead. Do not change the architecture unnecessarily.

6. Inspect the Supabase Storage bucket used by the application and make sure the bucket name in the code matches the configured bucket.

7. Verify and fix all image operations:

   * Uploading a new image
   * Editing an existing image
   * Replacing an old image
   * Deleting an image

   They should all use the correct server-side Supabase client.

8. Inspect `.env`, `.env.local`, `.env.example`, and configuration files. Do not print, expose, or commit any existing secrets.

9. If production deployment is missing environment variables, tell me exactly which variable names I need to add to the hosting platform, but never ask me to send you the secret values.

10. Add proper environment-variable validation so missing configuration produces a clear developer error instead of failing during image upload.

11. Do not randomly change Supabase Storage policies, RLS, or database permissions. First understand the existing architecture and preserve security.

12. Search the entire project for other code paths that could cause the same Supabase configuration problem and fix them too.

13. Run the available tests, lint, typecheck, and build commands if applicable, and fix any issues caused by your changes.

Most importantly: **do the actual code changes in the project. Do not just explain what I should do.**

At the end, give me:

* The root cause of the problem
* The files you changed
* The required environment variable names
* Any Supabase Storage configuration required
* The final deployment steps
* Confirmation that Admin image upload/edit/delete works correctly
