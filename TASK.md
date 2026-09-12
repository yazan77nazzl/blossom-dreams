I want you to implement the following changes in the existing Blossom Dreams project.

IMPORTANT:
- Work on the local project first.
- Do NOT push to GitHub yet.
- Do NOT break the current production deployment.
- Do not change the database schema or API unless it is genuinely necessary.
- After making the changes, run all tests and fix any failures before considering the task complete.

1. BOOKING SYSTEM — FULL AUDIT AND TESTING

I need a thorough review of the entire booking system, including frontend, backend, API, database, availability logic, and Admin dashboard.

Do not just run the existing tests. Inspect the actual booking flow and add/fix automated tests where necessary.

Test and verify:

- Service selection.
- Date selection.
- Available time slots.
- Preventing selection of unavailable slots.
- Preventing double bookings for the same appointment.
- Two simultaneous booking requests for the same slot (race conditions).
- Validation of all customer information.
- Invalid/malformed API requests.
- Creating and saving bookings correctly in PostgreSQL.
- Booking appearing correctly in the Admin dashboard.
- Admin booking status changes.
- Refreshing the page during the booking process.
- Browser back/forward behavior.
- Repeated form submission.
- Availability updating correctly after a booking.
- Timezone/date/time handling.
- Past dates and invalid dates.
- Booking outside business hours.
- Booking a slot that has already been taken.
- API-level protection against creating invalid bookings directly.
- Authentication and authorization for Admin APIs.
- Normal users must not be able to access Admin functionality.
- Database errors and API error handling.
- Any edge cases you discover during your review.

Pay special attention to preventing double-booking and race conditions. The booking system must be reliable in production.

Run the complete test suite, including:

python -m pytest -v

If additional tests are needed, create them.

2. HERO IMAGE — OVAL FRAME

The main hero image at the beginning of the website currently has the wrong frame shape.

Change it to an elegant oval shape rather than a circle.

Requirements:
- Clearly oval, not circular.
- Responsive on desktop and mobile.
- No image distortion.
- Use appropriate object-fit/object-position.
- Keep the current visual style and layout.
- Make it look premium and elegant.
- Do not break the hero section.

3. SCROLL ANIMATIONS

The website items/cards/sections currently appear static.

I want elements to animate when they enter the viewport while scrolling.

Requirements:
- Fade in.
- Smooth movement from LEFT → RIGHT.
- Premium, subtle animation.
- Not exaggerated or distracting.
- Elements should animate when they enter the viewport rather than all animating immediately on page load.
- Add a subtle stagger effect to consecutive items where appropriate.
- Use IntersectionObserver or another performant solution.
- Avoid unnecessary repeated animations on every scroll.
- Respect `prefers-reduced-motion` for accessibility.
- Make sure the animations work properly on both desktop and mobile.

4. FINAL VERIFICATION

Before finishing:

- Inspect all affected files.
- Run the full test suite.
- Verify the application starts successfully.
- Verify the booking system still works.
- Verify the Admin dashboard still works.
- Verify PostgreSQL integration.
- Verify the hero image on responsive layouts.
- Verify the scroll animations.
- Make sure no secrets or `.env` files are added to Git.
- Do NOT run `git push`.

At the end, give me a clear report containing:

1. What was fixed.
2. What was changed.
3. Which files were modified.
4. All tests that were run and their results.
5. Any manual tests I should perform before pushing to GitHub.
6. Any remaining risks or issues.

Do not consider the task complete just because the CSS was changed. I specifically want a serious audit and regression test of the booking system.