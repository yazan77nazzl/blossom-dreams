Please implement the following updates carefully.

IMPORTANT:
Before making any changes, inspect the existing project structure, booking system, location configuration, database, map implementation, and admin dashboard.

Do not modify anything unrelated to the requirements below.

==================================================
1. SOCIAL MEDIA ICONS
==================================================

Add the business social media icons to the lower/footer section of the website:

- Instagram
- WhatsApp
- TikTok

TikTok official account:
https://www.tiktok.com/@blossomdreams.lb

The TikTok icon must be clickable and open the official Blossom Dreams TikTok profile.

For Instagram and WhatsApp:
- Use the existing official links/configuration already present in the project.
- Do not invent or guess URLs if they are not already configured.
- If they are not configured, create clear configuration placeholders.
- Make all icons responsive and easy to tap on mobile.
- Keep the icons consistent with the existing website design.
- Add subtle hover/tap effects.

==================================================
2. TWO BUSINESS LOCATIONS
==================================================

The business has TWO locations:

1. Versailles Center
2. Amwaj Center, Jounieh

Both locations must be available throughout the booking system.

==================================================
3. VERY IMPORTANT — LOCATION STATUS
==================================================

IMPORTANT:

The **Amwaj Center, Jounieh location is ALREADY CORRECT.**

DO NOT change, move, replace, or modify the Amwaj Center location in any way.

Do NOT change:
- Its coordinates
- Its Google Maps destination
- Its address
- Its map pin
- Its location configuration

The ONLY location that needs to be corrected is:

**Versailles Center**

==================================================
4. VERSAILLES CENTER — CORRECT LOCATION
==================================================

The current Versailles Center location/pin is incorrect and needs to be corrected.

Use this Google Maps link as the reference for the correct Versailles Center location:

https://www.google.com/maps?geocode=FVZlBgId-qQfAg%3D%3D;FeKABgIdjp0fAikjee62lkAfFTHpGFP2BnXpHQ%3D%3D&daddr=Centre+Savoy,+XJJG+7H6,+Sarba&saddr=33.9735896,35.6282820&dirflg=d&ftid=0x151f4096b6ee7923:0x1de97506f65318e9&lucs=,94297699,100795621,94231188,94280568,47071704,94218641,94282134,94286869,100820247,100822504&g_ep=CAISEjI2LjM2LjMuOTczNTQ4ODUxMBgAILq3CypdLDk0Mjk3Njk5LDEwMDc5NTYyMSw5NDIzMTE4OCw5NDI4MDU2OCw0NzA3MTcwNCw5NDIxODY0MSw5NDI4Njg2OSwxMDA4MjAyNDcsMTAwODIyNTA0QgJMQg%3D%3D&skid=0f2ba6b9-e5e3-45ac-902c-c1454b1e5484&g_st=iw

Use this link as the reference when correcting the Versailles Center location.

IMPORTANT:
- This Google Maps reference is for Versailles Center ONLY.
- Correct the Versailles Center location based on this reference.
- Do NOT use the old incorrect Versailles Center pin.
- Do NOT modify the Amwaj Center location.

==================================================
5. LOCATION UI — NO PERMANENT MAP
==================================================

Do NOT keep a large static/embedded map permanently visible on the website.

Instead, provide two clean location options:

- Versailles Center
- Amwaj Center, Jounieh

Each location should be clickable.

The location section should be simple, clean, and consistent with the current website design.

==================================================
6. OPEN GOOGLE MAPS DIRECTLY
==================================================

When the customer clicks a location:

- Open Google Maps directly.
- Do not show a permanent embedded map.
- On mobile, preferably open the Google Maps app when available.
- Otherwise open Google Maps in the browser.

For Versailles Center:
- Open the corrected Versailles Center location based on the Google Maps reference provided above.

For Amwaj Center, Jounieh:
- Keep using the EXISTING correct location and destination.
- DO NOT change its current location.

==================================================
7. BOOKING LOCATION SELECTION
==================================================

Update the booking system so the customer must select a location before selecting/confirming an appointment.

The customer should see:

Location:
- Versailles Center
- Amwaj Center, Jounieh

The selected location must be saved with the booking.

The Admin dashboard must clearly show which location the customer selected.

==================================================
8. LOCATION-SPECIFIC APPOINTMENT AVAILABILITY
==================================================

Available appointment times must be calculated according to the selected location.

Make sure:

- Each location can have its own working hours if configured.
- The selected location determines available appointment times.
- Opening hours are respected.
- Closing hours are respected.
- Service duration is respected.
- Buffer time is respected if configured.
- Already-booked slots are unavailable.
- Blocked/unavailable times are not shown.
- Customers cannot book outside the selected location's working hours.

Do NOT hardcode appointment times.

==================================================
9. FIX THE EXISTING BOOKING ERROR
==================================================

The booking system currently gives an error when the customer tries to complete a booking.

Find the actual root cause and fix it properly.

Test the complete flow:

1. Select a service.
2. Select a location.
3. Select a date.
4. Select an available time.
5. Enter customer information.
6. Submit the booking.
7. Confirm successful booking creation.
8. Confirm the booking is stored in the database.
9. Confirm the booking appears in Admin.
10. Confirm the correct location is saved.

==================================================
10. FIX THE 9:00 AM AVAILABILITY ISSUE
==================================================

There is an existing issue where some days show appointment times starting at 12:00 PM even though the business opening hours are configured to start at 9:00 AM.

Investigate and fix the ROOT CAUSE.

If a location is configured to open at 9:00 AM, appointment slots should be available from 9:00 AM unless they are genuinely unavailable because of:

- Existing booking
- Service duration
- Buffer time
- Blocked time
- Closed day
- Another valid scheduling rule

Do NOT simply modify the frontend to display 9:00 AM.

Check the entire availability system, including:

- Backend
- Frontend
- Database
- Opening hours
- Location schedules
- Date parsing
- Timezone handling
- Service duration
- Buffer times
- Existing bookings
- Availability calculations
- Frontend filtering

Fix the underlying scheduling logic.

==================================================
11. ADMIN DASHBOARD
==================================================

Make sure Admin can see all booking information correctly.

Admin should be able to see:

- Customer name
- Customer phone/contact
- Service
- Location
- Appointment date
- Appointment time
- Booking status
- Booking creation date/time

The location must clearly show either:

Versailles Center

OR

Amwaj Center, Jounieh

New bookings must appear correctly in the Admin dashboard.

==================================================
12. OLD / TEST BOOKING DATA
==================================================

Inspect the database for old test, demo, invalid, duplicate, or corrupted booking records.

If there are clearly old test/demo records that are no longer needed, clean them up safely.

IMPORTANT:

- DO NOT delete legitimate customer bookings.
- DO NOT delete real customer data.
- Only remove records that are clearly test/demo/invalid/duplicate.
- Do not perform a destructive database reset.
- Keep the database consistent.

==================================================
13. FULL BOOKING TESTING
==================================================

After implementing the fixes, perform a complete end-to-end test.

Test VERSAILLES CENTER:

- Location selection
- Correct Versailles Center location
- Correct Google Maps destination
- Available dates
- 9:00 AM availability
- Other appointment times
- Booking creation
- Admin visibility
- Correct location saved with booking

Test AMWAJ CENTER, JOUNIEH:

IMPORTANT:
The existing Amwaj Center location is already correct.

Do NOT modify its location.

Only verify that:
- The existing location still works.
- The existing Google Maps destination still works.
- The location can be selected during booking.
- Appointment availability works correctly.
- Booking creation works.
- Admin visibility works.
- The correct Amwaj location is saved with the booking.

Also test:

- Fully booked time slot
- Duplicate booking attempt
- Invalid booking
- Past date
- Current date
- Future date
- Different services
- Different service durations
- Different working hours
- Mobile layout
- Desktop layout

==================================================
14. DO NOT BREAK EXISTING FUNCTIONALITY
==================================================

Do not redesign the entire website.

Do not modify unrelated sections.

Preserve:

- Existing design
- Existing animations
- Existing functionality
- Bubblegum color #F7A1B3
- Existing correct Amwaj Center location

Only make the required changes.

==================================================
15. FINAL VERIFICATION
==================================================

Do not consider the task complete until you have verified that:

- The booking error is fixed.
- Customers can successfully complete bookings.
- Both locations can be selected.
- Versailles Center has the corrected location.
- Amwaj Center, Jounieh remains unchanged and correct.
- Each location opens the correct Google Maps destination.
- The permanent static map is removed.
- The 9:00 AM availability issue is fixed.
- Appointment times follow the configured working hours.
- Double bookings are prevented.
- The selected location is stored with every booking.
- Admin can see the booking and its location.
- Old test/demo data is safely cleaned if applicable.
- Instagram, WhatsApp, and TikTok icons are displayed.
- TikTok opens:
  https://www.tiktok.com/@blossomdreams.lb
- The Bubblegum color #F7A1B3 is preserved.
- No unrelated functionality is broken.
- The complete booking flow has been tested successfully on mobile and desktop.

Please inspect the existing architecture first, identify the root causes, implement the fixes properly, run the relevant tests, and verify the complete system end-to-end before finishing.