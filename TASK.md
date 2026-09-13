The website is now broken after the latest changes.

IMPORTANT:
Do NOT revert the latest commit.
Do NOT undo previous working features.
Fix the actual problem causing the page to stay stuck in a loading state.

PROBLEM:
After the latest changes, the website loads but the items/content are no longer displayed.
They appear as if they are loading forever.

The page was working correctly before the latest changes.

Please investigate the issue from end to end:

1. Check the browser/frontend console for JavaScript errors.
2. Check the Network/API requests that are stuck, failing, or returning unexpected responses.
3. Check the backend logs.
4. Check whether the API endpoints used to load the items are returning the correct data.
5. Check whether the frontend is waiting indefinitely for an API response.
6. Check loading state logic, promises, async/await, fetch requests, error handling, and state updates.
7. Check whether the latest changes to app/seed_data.py or any other backend/frontend files affected the item-loading API.
8. Check database initialization/startup and make sure the required data still exists.
9. Check for any API 500/404/400 errors.
10. Check whether a failed request leaves the UI permanently stuck in `loading=true`.

IMPORTANT:
Do not just hide the loading indicator.
Do not add fake/static items.
Do not hardcode data.
Do not change the design just to hide the problem.

Find the ROOT CAUSE and fix it properly.

The booking system that was already working must remain working.

The two locations must remain correct:
- Versailles Center
- Amwaj Center, Jounieh

Do not change the location data unless it is directly causing this loading problem.

Also do not remove or modify unrelated functionality.

After fixing:

1. Run the backend.
2. Test all item/service/product API endpoints.
3. Test the frontend.
4. Confirm the items actually appear.
5. Confirm there are no console errors.
6. Confirm there are no failed API requests.
7. Confirm the loading state finishes correctly.
8. Test the booking flow again.
9. Run the existing tests.

IMPORTANT:
Do NOT commit or push anything yet.

First fix the issue and then tell me:
- What the root cause was.
- Which files you changed.
- What you tested.
- Whether the items now load correctly.