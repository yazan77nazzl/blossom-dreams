FULL PROJECT UPDATE — IMPORTANT

Please inspect the existing project before making changes.

The project already has several working parts, so DO NOT rewrite or break functionality that is currently working.

The booking submission/API is now working correctly after the previous fixes. Preserve that working functionality.

Implement ALL requirements below and test everything before considering the task complete.

==================================================
1. BRAND COLOR
==================================================

Use the Bubblegum color throughout the website where the existing burgundy/wine color was previously used:

#F7A1B3

Keep the design elegant and consistent.

Do not redesign the entire website.

==================================================
2. HERO / OPENING IMAGE
==================================================

The main image shown when the website opens should:

- NOT have a visible frame/border around it.
- NOT look like it is inside a card.
- Appear clearly in the center of the screen.
- Be large and high quality.
- Have a smooth entrance animation when the page first loads.
- The image should be clearly visible.
- Keep the existing visual style and avoid unnecessary borders.

Do not crop the image in a way that makes it unclear.

==================================================
3. HERO TEXT
==================================================

Replace:

"Verdum Atelier"

with:

"+22 years of experience"

Remove the previous text/statistics:

"100% Hygiene & Sterilization"
"4.9 ★ Client Reviews"
"2000+ Happy Clients"

Also remove:

"Russian Cuticle Care"

and:

"Flawless 4-Week Retention"

Do not show these texts anywhere in the relevant hero/service section.

Also remove the five-star symbol that was displayed next to:

"+22 years of experience"

==================================================
4. SOCIAL MEDIA ICONS
==================================================

Add social media icons for:

- Instagram
- WhatsApp
- TikTok

Place them in the existing lower/footer social section.

TikTok official profile:

https://www.tiktok.com/@blossomdreams.lb

The TikTok icon must open the official TikTok profile.

For Instagram and WhatsApp:
- Use the existing configured official links/contact information.
- Do not invent a phone number or URL.
- Keep the icons responsive.
- Make them easy to tap on mobile.

==================================================
5. WHATSAPP ICON — IMPORTANT
==================================================

The current WhatsApp icon is WRONG.

Replace it with a real recognizable WhatsApp brand icon.

DO NOT use:
- 💬 emoji
- Generic chat icon
- Generic message icon
- MessageCircle
- Random speech bubble
- Fake CSS WhatsApp logo

Use a proper WhatsApp brand SVG/icon.

If the project already uses an icon library that supports brand icons, use the correct WhatsApp icon from that library.

The icon should clearly look like the official WhatsApp logo with the recognizable phone handset inside the WhatsApp bubble.

The WhatsApp icon must be clickable.

Use the WhatsApp business contact already configured in the project.

Do not invent a new phone number.

On mobile, open WhatsApp when possible.

On desktop, open WhatsApp Web/the appropriate WhatsApp link.

==================================================
6. TWO BUSINESS LOCATIONS
==================================================

The business has TWO locations:

1. Versailles Center
2. Amwaj Center, Jounieh

Customers must be able to choose between these two locations.

==================================================
7. IMPORTANT — AMWAJ LOCATION
==================================================

The existing:

"Amwaj Center, Jounieh"

location is CORRECT.

DO NOT modify it.

Do NOT change:
- Coordinates
- Map pin
- Google Maps destination
- Address
- Location configuration

Keep the existing Amwaj Center location exactly as it currently works.

==================================================
8. VERSAILLES CENTER LOCATION
==================================================

The Versailles Center location previously needed correction.

Use this Google Maps reference for Versailles Center:

https://www.google.com/maps?geocode=FVZlBgId-qQfAg%3D%3D;FeKABgIdjp0fAikjee62lkAfFTHpGFP2BnXpHQ%3D%3D&daddr=Centre+Savoy,+XJJG+7H6,+Sarba&saddr=33.9735896,35.6282820&dirflg=d&ftid=0x151f4096b6ee7923:0x1de97506f65318e9&lucs=,94297699,100795621,94231188,94280568,47071704,94218641,94282134,94286869,100820247,100822504&g_ep=CAISEjI2LjM2LjMuOTczNTQ4ODUxMBgAILq3CypdLDk0Mjk3Njk5LDEwMDc5NTYyMSw5NDIzMTE4OCw5NDI4MDU2OCw0NzA3MTcwNCw5NDIxODY0MSw5NDI4MjEzNCw5NDI4Njg2OSwxMDA4MjAyNDcsMTAwODIyNTA0QgJMQg%3D%3D&skid=0f2ba6b9-e5e3-45ac-902c-c1454b1e5484&g_st=iw

This reference is for:

VERSAILLES CENTER ONLY.

Correct Versailles Center based on this reference.

DO NOT modify Amwaj Center.

==================================================
9. LOCATION UI
==================================================

Do NOT keep a large permanent static map visible on the website.

Instead show two location options:

- Versailles Center
- Amwaj Center, Jounieh

When the customer clicks a location:

Open Google Maps directly.

Do not require a permanent embedded map.

For Versailles Center:
Use the corrected Versailles location.

For Amwaj Center:
Keep the existing correct Google Maps destination.

==================================================
10. BOOKING LOCATION SELECTION
==================================================

The customer must select a location when making a booking.

Options:

- Versailles Center
- Amwaj Center, Jounieh

The selected location must be saved with the booking.

Admin must see the selected location.

==================================================
11. BOOKING SYSTEM — PRESERVE WORKING API
==================================================

The HTTP 500 booking problem was already fixed.

DO NOT break the working booking creation API.

A booking must successfully:

- Submit
- Validate
- Save to PostgreSQL/Neon
- Return a successful response
- Appear in Admin
- Store service
- Store location
- Store date
- Store time
- Store customer information

Do not rewrite working booking creation unnecessarily.

==================================================
12. APPOINTMENT AVAILABILITY — MAJOR FIX
==================================================

There is still an availability problem.

Some future days do not show morning appointments.

Some days start at:
- 11:00 AM
- 2:00 PM
- 4:00 PM

even though the business may open in the morning.

This must be fixed properly.

DO NOT hardcode appointment times.

DO NOT simply force 9:00 AM to appear.

Find the actual root cause.

==================================================
13. WORKING HOURS
==================================================

Available appointment times must be generated from the actual configured working hours.

If a location opens at:

9:00 AM

then valid appointments should start from 9:00 AM, subject to:

- Service duration
- Appointment interval
- Buffer if configured
- Existing bookings
- Blocked periods
- Closing time

If the location opens at another time, use that configured time.

Do NOT use fixed values.

==================================================
14. REMOVE BREAKS COMPLETELY
==================================================

Remove the entire Breaks functionality.

I do NOT want a Breaks system anymore.

Remove from Admin:

- Breaks section
- Add Break
- Edit Break
- Delete Break
- Break configuration
- Break time selectors
- Break-related fields
- Break-related buttons
- Break-related UI

Remove backend/API break functionality if it is no longer needed.

Do not leave broken references.

IMPORTANT:

After removing Breaks, availability must still work correctly using:

- Opening hours
- Closing hours
- Service duration
- Appointment interval
- Existing bookings
- Other legitimate scheduling restrictions

Do not replace Breaks with hardcoded unavailable periods.

==================================================
15. AVAILABILITY DATABASE AUDIT
==================================================

Inspect the REAL production Neon/PostgreSQL data.

Do not rely only on local SQLite.

For BOTH:

Versailles Center
Amwaj Center, Jounieh

Inspect every day of the week.

Check:

- Opening time
- Closing time
- Location schedule
- Special dates
- Schedule overrides
- Blocked dates
- Existing bookings
- Any unexpected restrictions

Find out why some future dates only show afternoon slots.

If the database has incorrect schedule values, fix the data/configuration.

If the backend calculation is wrong, fix the backend.

If the frontend filters out valid morning slots, fix the frontend.

Do not add special cases for individual dates.

==================================================
16. TIMEZONE
==================================================

The business timezone is:

Asia/Beirut

Use this consistently.

Do not allow UTC conversion to shift opening hours.

If the business opens at:

9:00 AM

the customer must see:

9:00 AM

not a shifted time.

Date/day calculations must also use the Lebanon local calendar date.

==================================================
17. SERVICE DURATION
==================================================

Available slots must respect service duration.

Example:

60-minute service:

9:00 AM → 10:00 AM

The next appointment must respect the configured interval/buffer.

Never show a slot that would extend beyond closing time.

==================================================
18. EXISTING BOOKINGS
==================================================

Existing confirmed bookings must block their exact time.

Prevent double booking.

This must be enforced on the backend/database level, not only by hiding the slot in the frontend.

==================================================
19. TIME DISPLAY — 12-HOUR FORMAT
==================================================

Change the DISPLAY format to a 12-hour clock.

Use:

9:00 AM
10:00 AM
11:30 AM
12:00 PM
1:00 PM
2:00 PM
4:00 PM
7:00 PM

Do NOT display:

09:00
10:00
11:30
12:00
13:00
14:00
16:00
19:00

Apply this to:

- Booking calendar
- Available appointment slots
- Selected time
- Booking confirmation
- Booking summary
- Customer booking details
- Admin dashboard
- Admin booking details
- Calendar

IMPORTANT:

Keep the internal database/API time representation unchanged if it is already working.

Only change the DISPLAY format.

Correct conversion:

12:00 AM = midnight
9:00 AM = morning
12:00 PM = noon
1:00 PM = afternoon

==================================================
20. ADMIN — BOOKINGS & CALENDAR
==================================================

In:

"Bookings & Calendar"

Admin must see:

- Customer name
- Phone/contact
- Service
- Location
- Date
- Appointment time
- Booking status
- Created date/time

Display appointment times in 12-hour format.

==================================================
21. DELETE BOOKING FROM ADMIN
==================================================

Add a:

"Delete Booking"

action for every booking.

When Admin clicks Delete:

1. Show a confirmation dialog.
2. Explain that the booking will be permanently deleted.
3. Require confirmation.
4. Delete the selected booking from the database.
5. Remove it from the Admin list/calendar.
6. Make the appointment slot available again.

Confirmation:

"Are you sure you want to permanently delete this booking?"

Buttons:

"Cancel"
"Delete Booking"

==================================================
22. DELETE BOOKING — BACKEND
==================================================

Do NOT implement deletion only in the frontend.

Create/fix the proper backend delete endpoint.

Use the booking's unique database ID.

The backend must:

- Verify the booking exists.
- Delete ONLY the selected booking.
- Handle related records safely.
- Return success/error correctly.

Do NOT delete:
- Customer
- Service
- Location
- Other bookings
- Unrelated data

==================================================
23. AVAILABILITY AFTER BOOKING DELETION
==================================================

If Admin deletes a booking at:

10:00 AM

then that time should become available again, assuming:

- Location is open
- Service can fit
- No other booking blocks it

Do not cache deleted bookings.

==================================================
24. PRODUCT DELETE ERROR
==================================================

There is currently an error when Admin tries to delete a product.

Find the actual root cause.

Trace:

Admin UI
→ Delete request
→ API
→ Backend
→ Database
→ Foreign keys/relationships

Check whether the product is referenced by:

- Services
- Bookings
- Orders
- Categories
- Images
- Other database records

Handle relationships safely.

Do NOT blindly delete unrelated records.

If safe deletion is possible, delete correctly.

If the product cannot safely be deleted because of existing dependencies, show a clear Admin error explaining why.

Do not hide the error.

==================================================
25. PRODUCT DELETE TEST
==================================================

After fixing:

1. Create a test product.
2. Delete it from Admin.
3. Verify successful response.
4. Verify it disappears from the product list.
5. Verify it is actually removed from the database.
6. Verify no unrelated records were deleted.

==================================================
26. OLD / TEST BOOKING DATA
==================================================

Inspect the production database.

If there are clearly test/demo/invalid/duplicate bookings, clean them safely.

DO NOT delete real customer bookings.

DO NOT reset the production database.

Only remove records that are clearly test/demo/invalid.

==================================================
27. ADMIN SAFETY
==================================================

Deleting a booking must only delete that booking.

Deleting a product must only affect the intended product and safe dependent records.

Do not delete:

- Customers
- Locations
- Services
- Other bookings
- Other products
- Real customer data

==================================================
28. FULL TESTING
==================================================

Run the complete test suite.

Then test against PostgreSQL/Neon.

Test both locations.

Test at least 14–30 future dates.

For each date verify:

- Day of week
- Location
- Opening time
- Closing time
- First available appointment
- Morning slots
- Afternoon slots
- Existing bookings
- Service duration
- Appointment interval
- Timezone
- 12-hour display

Specifically investigate dates that previously started at:

11:00 AM
2:00 PM
4:00 PM

Do NOT consider the issue fixed unless you know WHY those times were appearing.

==================================================
29. END-TO-END BOOKING TEST
==================================================

Test:

1. Select service.
2. Select location.
3. Select future date.
4. Verify available times.
5. Select morning appointment.
6. Submit booking.
7. Confirm successful response.
8. Confirm database record.
9. Confirm Admin record.
10. Confirm correct location.
11. Confirm correct date/time.
12. Delete the test booking from Admin.
13. Confirm it disappears.
14. Confirm its time becomes available again.

==================================================
30. MOBILE AND DESKTOP
==================================================

Test the website on:

- Mobile
- Desktop

Verify:

- Booking
- Calendar
- Location selection
- Social icons
- WhatsApp
- TikTok
- Instagram
- Admin
- Delete booking
- Delete product
- 12-hour time format

==================================================
31. FINAL ACCEPTANCE CRITERIA
==================================================

Do NOT consider this task complete until:

- Booking creation works.
- No HTTP 500 occurs during normal booking.
- Appointment availability follows real working hours.
- Morning slots are not incorrectly hidden.
- Future dates work correctly.
- Both locations work independently.
- Amwaj Center location remains unchanged and correct.
- Versailles Center uses the corrected location.
- Static map is removed.
- Locations open Google Maps directly.
- Breaks are completely removed.
- Product deletion works.
- Admin can delete individual bookings.
- Deleted booking times become available again.
- Double bookings are prevented.
- Asia/Beirut timezone works correctly.
- All appointment times display in 12-hour format.
- WhatsApp uses the REAL recognizable WhatsApp icon.
- WhatsApp link works.
- TikTok link works.
- Instagram link works.
- Bubblegum #F7A1B3 is used.
- Hero image has no visible frame and has a smooth opening animation.
- Removed texts remain removed.
- No real customer data is deleted.
- All relevant tests pass.

IMPORTANT:

Do not use hacks.
Do not hardcode appointment times.
Do not hide errors.
Do not fake the WhatsApp icon.
Do not modify Amwaj Center's correct location.
Do not break the working booking API.

Inspect the actual code, database, API, and production configuration, identify the root causes, implement proper fixes, and perform full end-to-end testing before declaring the task complete.