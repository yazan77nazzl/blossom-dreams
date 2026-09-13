URGENT: The booking system is STILL BROKEN and needs a complete root-cause fix, not a frontend workaround.

Current problems:

1. When I submit a booking, I get:
   "Request failed with status 500"

2. The available appointment times are WRONG.
   On some days they start at 4:00 PM.
   On other days they start at 11:00 AM.
   The business working hours are configured differently, so the system is clearly not calculating availability correctly.

3. The WhatsApp icon is incorrect. I want the REAL WhatsApp icon.

Please stop and fully audit the booking system before making changes.

==================================================
1. FIX THE HTTP 500 BOOKING ERROR
==================================================

Find the exact backend/API/database error causing:

"Request failed with status 500"

Do NOT simply catch the error or hide it from the frontend.

Trace the complete request:

Frontend booking form
→ API request
→ backend booking endpoint
→ validation
→ availability check
→ database
→ booking creation
→ response

Find the actual exception/root cause and fix it.

Check:
- API endpoint
- Request payload
- Validation
- Required fields
- Location ID
- Service ID
- Date format
- Time format
- Timezone conversion
- Database schema
- Database constraints
- Foreign keys
- Booking creation logic
- Availability logic

After fixing it, actually create a test booking and verify that:
- The API returns success.
- The booking is saved in the database.
- The booking appears in Admin.
- The selected service, location, date, and time are stored correctly.

Do NOT consider the task complete if the API still returns HTTP 500.

==================================================
2. COMPLETELY FIX APPOINTMENT AVAILABILITY
==================================================

The appointment times are currently completely inconsistent.

Some days start at 4:00 PM.
Some days start at 11:00 AM.
The system must NOT randomly choose or infer these times.

The available appointment times MUST be generated directly from the configured working hours.

For example:

If a location/day is configured:

Opening time: 9:00 AM
Closing time: 6:00 PM

Then available slots must be generated starting from 9:00 AM according to the service duration and configured interval/buffer.

Do NOT hardcode:
- 11:00 AM
- 12:00 PM
- 4:00 PM
or any other start time.

The system must read the actual working-hours configuration from the database/configuration.

==================================================
3. CHECK WORKING HOURS LOGIC
==================================================

Audit the entire working-hours implementation.

Check:

- Day of week mapping
- Opening time
- Closing time
- Location-specific working hours
- Service duration
- Appointment interval
- Buffer time
- Break times
- Blocked times
- Existing bookings
- Current date/time
- Timezone
- UTC conversion
- Local time conversion
- Date parsing
- Frontend filtering
- Backend filtering

Make sure the day of the week is calculated correctly.

For example:
If Monday is configured as 9:00 AM–6:00 PM,
Monday appointments must be generated from 9:00 AM to 6:00 PM according to the booking rules.

Do NOT shift the start time because of timezone conversion.

==================================================
4. IMPORTANT TIMEZONE REQUIREMENT
==================================================

The business operates in Lebanon.

Make sure the booking system consistently uses the correct Lebanon timezone:

Asia/Beirut

Do not accidentally convert business opening hours to UTC and then display them as local time.

Opening hours such as 9:00 AM must remain 9:00 AM for the customer.

Check the entire flow:
Database → Backend → API → Frontend.

Dates and appointment times must represent the same local business time everywhere.

==================================================
5. LOCATION-SPECIFIC AVAILABILITY
==================================================

The business has TWO locations:

1. Versailles Center
2. Amwaj Center, Jounieh

The customer selects a location before choosing an appointment.

The selected location must determine the correct working hours and available appointments.

IMPORTANT:

Amwaj Center, Jounieh is already correct.

DO NOT change its existing location/coordinates/Google Maps destination.

Versailles Center is the location that previously needed correction.

Do not break either location while fixing availability.

==================================================
6. SERVICE DURATION
==================================================

Make sure appointment slots respect the selected service duration.

Example:

If the service takes 60 minutes, a 9:00 AM booking occupies:
9:00 AM → 10:00 AM

The next appointment must respect the configured interval/buffer.

Never offer a time that would cause the appointment to extend beyond the location's closing time.

==================================================
7. EXISTING BOOKINGS
==================================================

Existing confirmed bookings must block their corresponding time slots.

Prevent double booking.

Two customers must never be able to successfully book the exact same unavailable appointment.

This must be enforced on the backend/database level, not only by hiding the slot in the frontend.

==================================================
8. ADMIN
==================================================

Every successful booking must appear correctly in Admin.

Admin must see:

- Customer name
- Customer phone
- Service
- Location
- Appointment date
- Appointment time
- Booking status
- Created date/time

The appointment time displayed in Admin must match the time selected by the customer.

==================================================
9. OLD / TEST DATA
==================================================

Inspect existing booking records.

If there are clearly test/demo/invalid/duplicate records causing availability problems, clean them safely.

DO NOT delete real customer bookings.

DO NOT reset the entire database.

Only remove data that is clearly test/demo/invalid.

==================================================
10. WHATSAPP ICON
==================================================

The current WhatsApp icon is incorrect.

Replace it with the REAL WhatsApp icon/logo.

Use the official WhatsApp recognizable icon, not a generic chat/message icon.

Requirements:
- Clearly recognizable as WhatsApp.
- Correct WhatsApp logo styling.
- Clickable.
- Opens the configured business WhatsApp contact.
- Works correctly on mobile and desktop.
- Keep the existing website styling and Bubblegum color #F7A1B3 where appropriate.

Do not replace WhatsApp with a generic speech bubble icon.

==================================================
11. FULL END-TO-END TESTING
==================================================

After making the fixes, test the system thoroughly.

Test multiple days with different configured working hours.

For each day:

1. Select location.
2. Select service.
3. Select date.
4. Verify the first available appointment matches the configured opening time.
5. Verify all valid appointment slots appear.
6. Select an appointment.
7. Submit booking.
8. Verify HTTP response is successful.
9. Verify database record.
10. Verify Admin record.
11. Verify selected time is correct.
12. Verify selected location is correct.

Specifically test days where the system currently incorrectly starts at:
- 4:00 PM
- 11:00 AM

Find out WHY those days are wrong and fix the underlying cause.

Do not manually add special cases for those days.

==================================================
12. FINAL REQUIREMENT
==================================================

Do NOT tell me the task is complete just because the UI looks correct.

The task is complete ONLY when:

- HTTP 500 booking error is fixed.
- A real booking can be successfully submitted.
- Booking is stored in the database.
- Booking appears in Admin.
- Appointment times are generated from the actual configured working hours.
- No random 11 AM / 4 PM start times occur.
- Timezone handling is correct.
- Service duration works.
- Buffers work.
- Existing bookings block unavailable times.
- Double bookings are prevented.
- Both locations work correctly.
- Amwaj Center's existing correct location remains unchanged.
- Versailles Center remains correctly configured.
- WhatsApp uses the real WhatsApp icon.
- Mobile and desktop booking flows work.

IMPORTANT:
Inspect the actual code and logs, identify the root cause of every issue, fix it properly, and run end-to-end tests before finishing.
Do not use frontend hacks or hardcoded appointment times to hide the problem.