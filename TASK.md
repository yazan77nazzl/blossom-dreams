### New Task — Fix Multi-Service Selection

The booking flow must support **true multi-select** for Services and Offers.

#### Flow

When the user clicks:

**Our Bespoke Menu → Signature Treatments → Book**

open:

**Step 1 — Choose Services & Offers**

NOT Location.

The clicked service should be pre-selected, but the user must be able to select **unlimited additional services**.

Example:

☑ Service A
☑ Service B
☑ Service C
☑ Service D

Selecting a new service must **never remove previous selections**. Clicking a selected item should remove only that item.

#### Selection

Support all combinations:

* Multiple Services
* Multiple Offers
* Services + Offers
* Offers only

Use independent checkboxes and true multi-select behavior, **not radio/single-select logic**.

`selectedServiceIds` and `selectedOfferIds` must remain arrays and must only add/remove the clicked ID. Never replace the array with a single ID.

#### UI

Keep the selection summary updated with:

* Selected items
* Total price
* Total duration
* Checkbox state
* Selected card styling

#### Final Flow

**Book → Services & Offers → Continue → Location → Date → Time → Guest Details → Confirmation**

Location must never appear before Step 1 is completed.

#### Implementation

Inspect the **actual current code** in `public/js/booking.js` and find the real source of the single-select behavior, including `open()`, `renderStep1()`, event handlers, and selection state.

**Do not just provide code for manual copy/paste. Apply the fix directly to the repository.**

Then verify:

1. Book opens Step 1.
2. Clicked service is pre-selected.
3. Multiple services stay selected simultaneously.
4. Multiple offers work the same way.
5. Removing one item does not affect others.
6. Selections persist through all booking steps.
7. Price and duration recalculate correctly.
8. Location appears only after Continue.
9. Final booking contains all selected services/offers.

After completing the task, report the files changed and confirm the multi-select flow was tested.