// Interactive 6-Step Luxury Booking Wizard for Blossom Dreams
import { apiFetch, showToast, formatPrice, formatDuration, formatDatePretty, formatTimeDisplay, escapeHtml } from "./api.js";

class BookingWizard {
  constructor() {
    this.modal = null;
    this.services = [];
    this.offers = [];
    this.settings = null;
    this.locations = [];
    this.state = {
      step: 1, // 1: Services & Offers, 2: Location, 3: Date, 4: Time, 5: Details, 6: Confirmation
      selectedServiceIds: [], // array of service ids
      selectedOfferIds: [],   // array of offer ids
      selectedLocation: null,
      selectedDate: null,
      selectedTime: null,
      availableSlots: [],
      isLoadingSlots: false,
      slotsReason: null,
      customerName: "",
      customerPhone: "",
      customerEmail: "",
      customerNotes: "",
      confirmedBooking: null,
      totalDuration: 0,
      totalPrice: 0
    };
  }

  init(services, settings, locations = [], offers = []) {
    this.services = services;
    this.offers = offers || [];
    this.settings = settings;
    this.locations = locations || [];
    this.renderModalContainer();
  }

  renderModalContainer() {
    if (document.getElementById("booking-modal")) return;

    const modal = document.createElement("div");
    modal.id = "booking-modal";
    modal.className = "fixed inset-0 z-50 flex items-end sm:items-center justify-center hidden";
    modal.innerHTML = `
      <div id="booking-modal-overlay" class="fixed inset-0 modal-overlay transition-opacity"></div>
      <div class="booking-sheet relative w-full max-w-xl bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden z-10 modal-content-anim max-h-[92vh] flex flex-col border border-pink-100/80">
        
        <!-- Header -->
        <div class="px-4 sm:px-6 py-3.5 sm:py-4.5 border-b border-pink-100 flex items-center justify-between bg-gradient-to-r from-[#FDEDE8] via-white to-[#F6D9D0]">
          <div class="flex items-center gap-3">
            <span class="w-9 h-9 rounded-xl bg-pink-100 text-pink-700 flex items-center justify-center text-lg shadow-xs">🌸</span>
            <div>
              <h3 class="text-base font-serif font-bold text-gray-900 leading-tight">Private Appointment Reservation</h3>
              <p class="text-[10px] text-pink-700 font-bold tracking-widest uppercase mt-0.5">Blossom Dreams • Jounieh</p>
            </div>
          </div>
          <button id="close-booking-modal" class="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 flex items-center justify-center transition">
            ✕
          </button>
        </div>

        <!-- 6-Step Progress Bar & Indicators -->
        <div class="px-6 pt-3.5 pb-2.5 bg-pink-50/40 border-b border-pink-100/60">
          <div class="flex items-center justify-between text-[11px] font-bold text-slate-400 mb-2">
            <span id="step-lbl-1" class="step-indicator active">1. Service</span>
            <span id="step-lbl-2" class="step-indicator">2. Location</span>
            <span id="step-lbl-3" class="step-indicator">3. Date</span>
            <span id="step-lbl-4" class="step-indicator">4. Time</span>
            <span id="step-lbl-5" class="step-indicator">5. Details</span>
            <span id="step-lbl-6" class="step-indicator">6. Confirm</span>
          </div>
          <div class="booking-progress-track">
            <div id="booking-progress-bar" class="booking-progress-fill" style="width: 17%;"></div>
          </div>
        </div>

        <!-- Scrollable Wizard Body -->
        <div id="wizard-step-content" class="p-6 overflow-y-auto flex-1">
          <!-- Dynamically populated -->
        </div>

        <!-- Sticky Footer Controls -->
        <div id="wizard-footer" class="wizard-footer-safe px-4 sm:px-6 py-4 border-t border-pink-100 bg-slate-50/90 flex items-center justify-between gap-2">
          <!-- Controls -->
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    this.modal = modal;

    document.getElementById("close-booking-modal").addEventListener("click", () => this.close());
    document.getElementById("booking-modal-overlay").addEventListener("click", () => this.close());
  }

  open(preSelectedServiceId = null, preSelectedOfferId = null) {
    if (!this.modal) this.renderModalContainer();

    // Reset state for a fresh booking
    this.state.step = 1;
    this.state.selectedLocation = null;
    this.state.selectedTime = null;
    this.state.availableSlots = [];
    this.state.confirmedBooking = null;
    this.state.selectedServiceIds = [];
    this.state.selectedOfferIds = [];
    this.state.totalDuration = 0;
    this.state.totalPrice = 0;

    // Set today as initial date
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    this.state.selectedDate = `${yyyy}-${mm}-${dd}`;

    // Pre-select the service the user clicked "Book" on (if any)
    if (preSelectedServiceId) {
      const match = this.services.find(s => s.id === parseInt(preSelectedServiceId));
      if (match) {
        this.state.selectedServiceIds.push(match.id);
        // recompute aggregates
        this._recalcTotals();
      }
    }
    // Pre-select the offer the user clicked "Claim Offer" on (if any)
    if (preSelectedOfferId) {
      const match = this.offers.find(o => o.id === parseInt(preSelectedOfferId));
      if (match) {
        this.state.selectedOfferIds.push(match.id);
        this._recalcTotals();
      }
    }

    this.modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
    this.renderCurrentStep();
  }

  _recalcTotals() {
    let dur = 0, price = 0;
    const symbol = this.settings?.currency_symbol || "$";
    this.state.selectedServiceIds.forEach(id => {
      const s = this.services.find(sv => sv.id === id);
      if (s) {
        dur += s.duration_minutes || 0;
        const p = s.discount_price && s.discount_price > 0 ? s.discount_price : s.price;
        price += p;
      }
    });
    // Offers may have their own price/duration; include if present
    this.state.selectedOfferIds.forEach(id => {
      const o = this.offers.find(of => of.id === id);
      if (o) {
        // Assume offer has discounted_price and possibly duration_minutes
        if (o.duration_minutes) dur += o.duration_minutes;
        price += o.discounted_price || 0;
      }
    });
    this.state.totalDuration = dur;
    this.state.totalPrice = price;
  }

  close() {
    if (!this.modal) return;
    this.modal.classList.add("hidden");
    document.body.style.overflow = "";
  }

  updateProgress() {
    const progressMap = { 1: "17%", 2: "34%", 3: "50%", 4: "67%", 5: "84%", 6: "100%" };
    const bar = document.getElementById("booking-progress-bar");
    if (bar) {
      bar.style.width = progressMap[this.state.step] || "17%";
      if (this.state.step === 6) bar.classList.add("complete");
    }

    for (let i = 1; i <= 6; i++) {
      const lbl = document.getElementById(`step-lbl-${i}`);
      if (!lbl) continue;
      if (i < this.state.step) {
        lbl.className = "text-emerald-700 font-bold";
      } else if (i === this.state.step) {
        lbl.className = "text-pink-700 font-extrabold";
      } else {
        lbl.className = "text-slate-400 font-medium";
      }
    }
  }

  renderCurrentStep() {
    this.updateProgress();
    const content = document.getElementById("wizard-step-content");
    const footer = document.getElementById("wizard-footer");
    if (!content || !footer) return;

    content.className = "p-6 overflow-y-auto flex-1 step-slide-in";

    if (this.state.step === 1) this.renderStep1(content, footer);
    else if (this.state.step === 2) this.renderStep2(content, footer);
    else if (this.state.step === 3) this.renderStep3(content, footer);
    else if (this.state.step === 4) this.renderStep4(content, footer);
    else if (this.state.step === 5) this.renderStep5(content, footer);
    else if (this.state.step === 6) this.renderStep6(content, footer);
  }

  // --- STEP 1: SELECT SERVICES & OFFERS ---
  renderStep1(content, footer) {
    const symbol = this.settings?.currency_symbol || "$";
    let html = `
      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 1 — Choose Services & Offers</h4>
        <p class="text-xs text-slate-500 mt-0.5">Select one or more items. You can combine services and offers.</p>
      </div>

      <div class="mb-3.5">
        <input type="text" id="wizard-service-search" placeholder="Search treatment or offer..."
          class="w-full text-xs px-4 py-2.5 rounded-xl border border-pink-200 focus:outline-none focus:ring-2 focus:ring-pink-500 bg-pink-50/20" />
      </div>

      <div id="wizard-services-list" class="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
    `;

    // Services
    if (this.services && this.services.length) {
      html += `<div class="mb-3"><h5 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Services</h5></div>`;
      this.services.forEach(s => {
        const isSelected = this.state.selectedServiceIds.includes(s.id);
        const displayPrice = s.discount_price || s.price;
        html += `
          <div data-type="service" data-id="${s.id}" class="wizard-item p-3.5 rounded-2xl border cursor-pointer transition flex items-center justify-between ${isSelected ? 'border-pink-600 bg-pink-50/70 ring-2 ring-pink-500/20' : 'border-pink-100 hover:border-pink-300 hover:bg-pink-50/30'}">
            <div class="flex items-center gap-3">
              <input type="checkbox" class="w-4 h-4 accent-pink-600" ${isSelected ? 'checked' : ''} />
              <div class="w-12 h-12 rounded-xl bg-pink-100 overflow-hidden flex-shrink-0 border border-pink-200/80">
                <img src="${s.image_url || ''}" alt="${escapeHtml(s.name)}" class="w-full h-full object-cover" />
              </div>
              <div>
                <h5 class="text-sm font-bold text-gray-900">${escapeHtml(s.name)}</h5>
                <div class="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                  <span>⏱ ${formatDuration(s.duration_minutes)}</span>
                  <span>•</span>
                  <span class="text-pink-700 font-semibold">${escapeHtml(s.category_name || '')}</span>
                </div>
              </div>
            </div>
            <div class="text-right">
              <div class="text-sm font-bold text-pink-700">${formatPrice(displayPrice, symbol)}</div>
              ${s.discount_price ? `<div class="text-[10px] text-slate-400 line-through">${formatPrice(s.price, symbol)}</div>` : ''}
            </div>
          </div>
        `;
      });
    }

    // Offers
    if (this.offers && this.offers.length) {
      html += `<div class="mb-3 mt-4"><h5 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Offers & Packages</h5></div>`;
      this.offers.forEach(o => {
        const isSelected = this.state.selectedOfferIds.includes(o.id);
        const displayPrice = o.discounted_price || o.original_price;
        const hasDiscount = o.discounted_price && o.original_price && o.discounted_price < o.original_price;
        html += `
          <div data-type="offer" data-id="${o.id}" class="wizard-item p-3.5 rounded-2xl border cursor-pointer transition flex items-center justify-between ${isSelected ? 'border-pink-600 bg-pink-50/70 ring-2 ring-pink-500/20' : 'border-pink-100 hover:border-pink-300 hover:bg-pink-50/30'}">
            <div class="flex items-center gap-3">
              <input type="checkbox" class="w-4 h-4 accent-pink-600" ${isSelected ? 'checked' : ''} />
              <div class="w-12 h-12 rounded-xl bg-emerald-100 overflow-hidden flex-shrink-0 border border-emerald-200/80">
                <img src="${o.image_url || ''}" alt="${escapeHtml(o.name)}" class="w-full h-full object-cover" />
              </div>
              <div>
                <h5 class="text-sm font-bold text-gray-900">${escapeHtml(o.name)}</h5>
                <div class="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                  <span>⏱ ${formatDuration(o.duration_minutes)}</span>
                  <span>•</span>
                  <span class="text-emerald-700 font-semibold">${escapeHtml(o.category_name || 'Offer')}</span>
                </div>
              </div>
            </div>
            <div class="text-right">
              <div class="text-sm font-bold text-emerald-700">${formatPrice(displayPrice, symbol)}</div>
              ${hasDiscount ? `<div class="text-[10px] text-slate-400 line-through">${formatPrice(o.original_price, symbol)}</div>` : ''}
            </div>
          </div>
        `;
      });
    }

    html += `</div>`;
    content.innerHTML = html;

    // Search filter (works for both services and offers)
    const searchInput = document.getElementById("wizard-service-search");
    searchInput.addEventListener("input", (e) => {
      const term = e.target.value.toLowerCase().trim();
      document.querySelectorAll(".wizard-item").forEach(item => {
        const id = parseInt(item.dataset.id);
        const type = item.dataset.type;
        const list = type === 'service' ? this.services : this.offers;
        const obj = list.find(x => x.id === id);
        if (!obj) return;
        const match = obj.name.toLowerCase().includes(term) || (obj.description && obj.description.toLowerCase().includes(term));
        item.style.display = match ? "flex" : "none";
      });
    });

    // Checkbox handling
    document.querySelectorAll(".wizard-item").forEach(item => {
      const checkbox = item.querySelector('input[type="checkbox"]');
      const id = parseInt(item.dataset.id);
      const type = item.dataset.type;

      // Click on whole row toggles checkbox
      item.addEventListener("click", (e) => {
        if (e.target === checkbox) return; // let native checkbox handle
        checkbox.checked = !checkbox.checked;
        this.toggleSelection(type, id);
      });
      checkbox.addEventListener("change", () => {
        this.toggleSelection(type, id);
      });
    });

    // Footer with continue button enabled only when at least one selected
    const hasSelection = this.state.selectedServiceIds.length > 0 || this.state.selectedOfferIds.length > 0;
    footer.innerHTML = `
      <div class="text-xs text-slate-500 font-medium mb-2">Select at least one service or offer to proceed</div>
      <button id="step1-next-btn" ${hasSelection ? '' : 'disabled'} class="btn-primary ${hasSelection ? '' : 'opacity-50 cursor-not-allowed'} px-6 py-2.5 rounded-xl text-xs font-bold">
        Continue →
      </button>
    `;

    if (hasSelection) {
      document.getElementById("step1-next-btn").addEventListener("click", () => {
        this.state.step = 2;
        this.renderCurrentStep();
      });
    }
  }

  // Helper: toggle selection and recompute totals
  toggleSelection(type, id) {
    if (type === 'service') {
      const idx = this.state.selectedServiceIds.indexOf(id);
      if (idx === -1) this.state.selectedServiceIds.push(id);
      else this.state.selectedServiceIds.splice(idx, 1);
    } else if (type === 'offer') {
      const idx = this.state.selectedOfferIds.indexOf(id);
      if (idx === -1) this.state.selectedOfferIds.push(id);
      else this.state.selectedOfferIds.splice(idx, 1);
    }
    this.recalcTotals();
    this.renderCurrentStep(); // re-render to update checkboxes and totals
  }

  recalcTotals() {
    let totalPrice = 0;
    let totalDuration = 0;
    // services
    this.state.selectedServiceIds.forEach(id => {
      const s = this.services.find(x => x.id === id);
      if (s) {
        totalPrice += s.discount_price || s.price;
        totalDuration += s.duration_minutes;
      }
    });
    // offers
    this.state.selectedOfferIds.forEach(id => {
      const o = this.offers.find(x => x.id === id);
      if (o) {
        totalPrice += o.discounted_price || o.original_price;
        totalDuration += o.duration_minutes;
      }
    });
    this.state.totalPrice = totalPrice;
    this.state.totalDuration = totalDuration;
  }

  // --- STEP 2: SELECT LOCATION ---
  renderStep2(content, footer) {
    if (!this.locations || this.locations.length === 0) {
      this.state.step = 3;
      this.renderCurrentStep();
      return;
    }

    const symbol = this.settings?.currency_symbol || "$";
    const totalPrice = this.state.totalPrice;
    const totalDuration = this.state.totalDuration;

    // Build recap list
    let recapHtml = '';
    this.state.selectedServiceIds.forEach(id => {
      const s = this.services.find(x => x.id === id);
      if (s) {
        const p = s.discount_price || s.price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(s.name)}</span><span class="font-semibold">${formatDuration(s.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });
    this.state.selectedOfferIds.forEach(id => {
      const o = this.offers.find(x => x.id === id);
      if (o) {
        const p = o.discounted_price || o.original_price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(o.name)}</span><span class="font-semibold">${formatDuration(o.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });

    let html = `
      <!-- Selection Recap -->
      <div class="mb-5 p-3 rounded-2xl bg-pink-50/70 border border-pink-200">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Your Selection</div>
        ${recapHtml}
        <div class="border-t border-pink-200 mt-2 pt-2 flex justify-between text-sm font-bold">
          <span>Total</span>
          <span>${formatDuration(totalDuration)} • ${formatPrice(totalPrice, symbol)}</span>
        </div>
        <button id="wizard-change-service-btn" class="text-[11px] text-pink-700 hover:text-pink-900 font-bold underline mt-2 block text-center">Change Services / Offers</button>
      </div>

      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 2 — Choose Your Location</h4>
        <p class="text-xs text-slate-500 mt-0.5">Select the boutique you would like to visit</p>
      </div>

      <div class="space-y-3">
    `;

    this.locations.forEach(loc => {
      const isSelected = this.state.selectedLocation?.id === loc.id;
      html += `
        <div data-location-id="${loc.id}" class="wizard-location-item p-4 rounded-2xl border cursor-pointer transition flex items-start gap-3.5 ${isSelected ? 'border-pink-600 bg-pink-50/70 ring-2 ring-pink-500/20' : 'border-pink-100 hover:border-pink-300 hover:bg-pink-50/30'}">
          <span class="w-11 h-11 rounded-2xl bg-pink-100 text-pink-700 flex items-center justify-center text-lg flex-shrink-0">📍</span>
          <div class="min-w-0">
            <h5 class="text-sm font-bold text-gray-900">${escapeHtml(loc.name)}</h5>
            ${loc.address ? `<p class="text-[11px] text-slate-500 mt-0.5 leading-relaxed">${escapeHtml(loc.address)}</p>` : ''}
            ${loc.google_maps_url ? `<a href="${escapeHtml(loc.google_maps_url)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 mt-1.5 text-[11px] text-pink-700 font-bold hover:text-pink-900 underline" title="Open in Google Maps">Open in Maps ↗</a>` : ''}
          </div>
          <span class="ml-auto w-5 h-5 rounded-full border-2 ${isSelected ? 'border-pink-600 bg-pink-600' : 'border-pink-200'} flex items-center justify-center flex-shrink-0">${isSelected ? '<span class="text-white text-[10px]">✓</span>' : ''}</span>
        </div>
      `;
    });

    html += `
      </div>

      <p class="text-[11px] text-slate-400 mt-4 flex items-center gap-1.5">📍 Tap a location to open it on Google Maps, then select it for your appointment.</p>
    `;

    content.innerHTML = html;

    document.getElementById("wizard-change-service-btn").addEventListener("click", () => {
      this.state.step = 1;
      this.renderCurrentStep();
    });

    document.querySelectorAll(".wizard-location-item").forEach(item => {
      item.addEventListener("click", (e) => {
        if (e.target.closest("a")) return; // let the map link open normally
        const id = parseInt(item.dataset.locationId);
        this.state.selectedLocation = this.locations.find(loc => loc.id === id);
        document.querySelectorAll(".wizard-location-item").forEach(x => {
          x.classList.remove("border-pink-600", "bg-pink-50/70", "ring-2", "ring-pink-500/20");
          const dot = x.querySelector("span.ml-auto");
          if (dot) { dot.classList.remove("border-pink-600", "bg-pink-600"); dot.innerHTML = ""; }
        });
        item.classList.add("border-pink-600", "bg-pink-50/70", "ring-2", "ring-pink-500/20");
        const dot = item.querySelector("span.ml-auto");
        if (dot) { dot.classList.add("border-pink-600", "bg-pink-600"); dot.innerHTML = '<span class="text-white text-[10px]">✓</span>'; }
        // Enable next button
        const nextBtn = document.getElementById("step2-next-btn");
        if (nextBtn) { nextBtn.disabled = false; nextBtn.classList.remove("opacity-50", "cursor-not-allowed"); }
      });
    });

    // Footer with disabled next until location selected
    const locSelected = !!this.state.selectedLocation;
    footer.innerHTML = `
      <button id="step2-next-btn" ${locSelected ? '' : 'disabled'} class="btn-primary ${locSelected ? '' : 'opacity-50 cursor-not-allowed'} px-6 py-2.5 rounded-xl text-xs font-bold">
        Next: Choose Date →
      </button>
    `;

    // Always attach listener; it will check for selected location
    document.getElementById("step2-next-btn").addEventListener("click", () => {
      if (!this.state.selectedLocation) return;
      this.state.step = 3;
      this.renderCurrentStep();
    });
  }

  // --- STEP 3: SELECT DATE ---
  renderStep3(content, footer) {
    const loc = this.state.selectedLocation;
    const symbol = this.settings?.currency_symbol || "$";
    const totalDuration = this.state.totalDuration;
    const totalPrice = this.state.totalPrice;

    // Build recap list
    let recapHtml = '';
    this.state.selectedServiceIds.forEach(id => {
      const s = this.services.find(x => x.id === id);
      if (s) {
        const p = s.discount_price || s.price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(s.name)}</span><span class="font-semibold">${formatDuration(s.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });
    this.state.selectedOfferIds.forEach(id => {
      const o = this.offers.find(x => x.id === id);
      if (o) {
        const p = o.discounted_price || o.original_price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(o.name)}</span><span class="font-semibold">${formatDuration(o.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });

    let html = `
      <!-- Selection Recap -->
      <div class="mb-5 p-3 rounded-2xl bg-pink-50/70 border border-pink-200">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Your Selection</div>
        ${recapHtml}
        <div class="border-t border-pink-200 mt-2 pt-2 flex justify-between text-sm font-bold">
          <span>Total</span>
          <span>${formatDuration(totalDuration)} • ${formatPrice(totalPrice, symbol)}${loc ? ` • 📍 ${escapeHtml(loc.name)}` : ''}</span>
        </div>
        <button id="wizard-change-service-btn" class="text-[11px] text-pink-700 hover:text-pink-900 font-bold underline mt-2 block text-center">Change Services / Offers</button>
      </div>

      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 3 — Select Appointment Date</h4>
        <p class="text-xs text-slate-500 mt-0.5">Choose your preferred salon visiting day</p>
      </div>

      <!-- 14-Day Quick Selector Strip -->
      <div class="mb-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-bold uppercase tracking-wider text-slate-700">Upcoming 14 Days</span>
          <span class="text-xs font-bold text-pink-700 font-mono" id="wizard-date-preview">${formatDatePretty(this.state.selectedDate)}</span>
        </div>

        <div id="date-scroll-strip" class="flex gap-2.5 overflow-x-auto pb-2 scrollbar-none">
    `;

    const now = new Date();
    for (let i = 0; i < 14; i++) {
      const d = new Date();
      d.setDate(now.getDate() + i);
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const dateStr = `${yyyy}-${mm}-${dd}`;
      const dayName = d.toLocaleDateString("en-US", { weekday: "short" });
      const dayNum = d.getDate();
      const isSelected = this.state.selectedDate === dateStr;
      const isSunday = d.getDay() === 0;

      html += `
        <button data-date="${dateStr}" ${isSunday ? 'disabled aria-disabled="true" title="Salon closed on Sundays"' : ''} class="cal-date-btn flex-shrink-0 w-15 py-3 rounded-2xl flex flex-col items-center justify-center text-center ${isSelected ? 'selected' : 'bg-white'} ${isSunday ? 'opacity-40 cursor-not-allowed' : ''}">
          <span class="text-[10px] uppercase font-bold ${isSelected ? 'text-pink-100' : 'text-slate-400'}">${dayName}</span>
          <span class="text-sm font-extrabold mt-0.5 ${isSelected ? 'text-white' : 'text-gray-900'}">${dayNum}</span>
          ${isSunday ? '<span class="text-[8px] text-rose-500 font-bold mt-0.5">Closed</span>' : ''}
        </button>
      `;
    }

    html += `
        </div>
      </div>

      <!-- Calendar input -->
      <div class="p-4 rounded-2xl bg-white border border-pink-100 flex items-center justify-between">
        <div class="text-xs text-slate-600 font-medium">Or pick any specific date:</div>
        <input type="date" id="wizard-date-input" value="${this.state.selectedDate}" min="${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}"
          class="text-xs px-3 py-1.5 rounded-xl border border-pink-200 text-slate-800 bg-pink-50/30 font-semibold" />
      </div>
    `;

    content.innerHTML = html;

    // Listeners
    document.getElementById("wizard-change-service-btn").addEventListener("click", () => {
      this.state.step = 1;
      this.renderCurrentStep();
    });

    document.querySelectorAll(".cal-date-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const d = btn.dataset.date;
        this.state.selectedDate = d;
        this.state.selectedTime = null;
        document.querySelectorAll(".cal-date-btn").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        document.getElementById("wizard-date-input").value = d;
        document.getElementById("wizard-date-preview").innerText = formatDatePretty(d);
      });
    });

    document.getElementById("wizard-date-input").addEventListener("change", (e) => {
      this.state.selectedDate = e.target.value;
      this.state.selectedTime = null;
      document.querySelectorAll(".cal-date-btn").forEach(b => {
        b.classList.toggle("selected", b.dataset.date === e.target.value);
      });
      document.getElementById("wizard-date-preview").innerText = formatDatePretty(e.target.value);
    });

    // Footer
    footer.innerHTML = `
      <button id="step3-back-btn" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        ← Back
      </button>
      <button id="step3-next-btn" class="btn-primary px-6 py-2.5 rounded-xl text-xs font-bold">
        Next: Choose Time →
      </button>
    `;

    document.getElementById("step3-back-btn").addEventListener("click", () => {
      this.state.step = 2;
      this.renderCurrentStep();
    });

    document.getElementById("step3-next-btn").addEventListener("click", () => {
      this.state.selectedTime = null;
      this.state.step = 4;
      this.renderCurrentStep();
    });
  }

  // --- STEP 4: SELECT TIME SLOT ---
  async renderStep4(content, footer) {
    const loc = this.state.selectedLocation;
    const dateStr = this.state.selectedDate;
    const totalDuration = this.state.totalDuration;
    const totalPrice = this.state.totalPrice;
    const symbol = this.settings?.currency_symbol || "$";

    // Build recap list
    let recapHtml = '';
    this.state.selectedServiceIds.forEach(id => {
      const s = this.services.find(x => x.id === id);
      if (s) {
        const p = s.discount_price || s.price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(s.name)}</span><span class="font-semibold">${formatDuration(s.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });
    this.state.selectedOfferIds.forEach(id => {
      const o = this.offers.find(x => x.id === id);
      if (o) {
        const p = o.discounted_price || o.original_price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(o.name)}</span><span class="font-semibold">${formatDuration(o.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });

    let html = `
      <!-- Selection Recap -->
      <div class="mb-5 p-3 rounded-2xl bg-pink-50/70 border border-pink-200">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Your Selection</div>
        ${recapHtml}
        <div class="border-t border-pink-200 mt-2 pt-2 flex justify-between text-sm font-bold">
          <span>Total</span>
          <span>${formatDuration(totalDuration)} • ${formatPrice(totalPrice, symbol)}${loc ? ` • 📍 ${escapeHtml(loc.name)}` : ''}</span>
        </div>
        <button id="wizard-back-to-date" class="text-[11px] text-pink-700 hover:text-pink-900 font-bold underline mt-2 block text-center">Change Date</button>
      </div>

      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 4 — Select Available Time</h4>
        <p class="text-xs text-slate-500 mt-0.5">Calculated in real-time to avoid any scheduling conflicts</p>
      </div>

      <!-- Time Slots Container -->
      <div id="wizard-time-slots-wrapper">
        <div class="py-12 text-center text-pink-600">
          <span class="animate-spin inline-block text-2xl mb-2">🌸</span>
          <p class="text-xs font-medium">Checking live atelier calendar...</p>
        </div>
      </div>
    `;

    content.innerHTML = html;

    document.getElementById("wizard-back-to-date").addEventListener("click", () => {
      this.state.selectedTime = null;
      this.state.step = 3;
      this.renderCurrentStep();
    });

    footer.innerHTML = `
      <button id="step4-back-btn" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        ← Back
      </button>
      <button id="step4-next-btn" disabled class="btn-primary opacity-50 px-6 py-2.5 rounded-xl text-xs font-bold cursor-not-allowed">
        Next: Guest Details →
      </button>
    `;

    document.getElementById("step4-back-btn").addEventListener("click", () => {
      this.state.step = 3;
      this.renderCurrentStep();
    });

    document.getElementById("step4-next-btn").addEventListener("click", () => {
      if (this.state.selectedTime) {
        this.state.step = 5;
        this.renderCurrentStep();
      }
    });

    await this.fetchAndRenderGroupedSlots();
  }

  async fetchAndRenderGroupedSlots() {
    const wrapper = document.getElementById("wizard-time-slots-wrapper");
    if (!wrapper) return;

    try {
      let url = `/api/availability/slots?date=${this.state.selectedDate}&duration=${this.state.totalDuration}`;
      if (this.state.selectedLocation) {
        url += `&location_id=${this.state.selectedLocation.id}`;
      }

      const data = await apiFetch(url);
      this.state.availableSlots = data.slots || [];

      if (!data.available || this.state.availableSlots.length === 0) {
        const reason = data.reason || "All appointments are fully booked for this date. Please choose another day.";
        wrapper.innerHTML = `
          <div class="p-6 rounded-2xl bg-amber-50/80 border border-amber-200 text-center">
            <span class="text-3xl block mb-2">📅</span>
            <p class="text-xs font-bold text-amber-900 mb-1">${escapeHtml(reason)}</p>
            <button id="btn-pick-diff-date" class="mt-3 btn-secondary px-4 py-2 rounded-xl text-xs font-bold">
              Choose Another Date
            </button>
          </div>
        `;
        document.getElementById("btn-pick-diff-date").addEventListener("click", () => {
          this.state.step = 3;
          this.renderCurrentStep();
        });
        return;
      }

      // Group slots into Morning (before 12:00), Afternoon (12:00 - 16:30), Evening (after 16:30)
      const morning = [];
      const afternoon = [];
      const evening = [];

      this.state.availableSlots.forEach(slot => {
        const hour = parseInt(slot.split(":")[0]);
        const min = parseInt(slot.split(":")[1]);
        const total = hour * 60 + min;

        if (total < 12 * 60) morning.push(slot);
        else if (total < 16 * 60 + 30) afternoon.push(slot);
        else evening.push(slot);
      });

      let html = `<div class="space-y-4 max-h-[300px] overflow-y-auto pr-1">`;

      if (morning.length > 0) {
        html += `
          <div>
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">🌅 Morning Slots</span>
            <div class="grid grid-cols-3 sm:grid-cols-4 gap-2">
              ${morning.map(s => this.renderSlotButton(s)).join('')}
            </div>
          </div>
        `;
      }

      if (afternoon.length > 0) {
        html += `
          <div>
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">☀️ Afternoon Slots</span>
            <div class="grid grid-cols-3 sm:grid-cols-4 gap-2">
              ${afternoon.map(s => this.renderSlotButton(s)).join('')}
            </div>
          </div>
        `;
      }

      if (evening.length > 0) {
        html += `
          <div>
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">🌆 Evening Slots</span>
            <div class="grid grid-cols-3 sm:grid-cols-4 gap-2">
              ${evening.map(s => this.renderSlotButton(s)).join('')}
            </div>
          </div>
        `;
      }

      html += `</div>`;
      wrapper.innerHTML = html;

      // Slot clicks
      wrapper.querySelectorAll(".slot-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          wrapper.querySelectorAll(".slot-btn").forEach(b => b.classList.remove("selected"));
          btn.classList.add("selected");
          this.state.selectedTime = btn.dataset.time;

          const nextBtn = document.getElementById("step4-next-btn");
          if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.classList.remove("opacity-50", "cursor-not-allowed");
          }
        });
      });

    } catch (err) {
      wrapper.innerHTML = `
        <div class="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-2xl text-center">
          Failed to load availability slots. Please try again.
        </div>
      `;
    }
  }

  renderSlotButton(slot) {
    const isSelected = this.state.selectedTime === slot;
    return `
      <button data-time="${slot}" class="slot-btn py-2.5 px-2 rounded-xl text-xs font-bold text-slate-800 ${isSelected ? 'selected' : ''}">
        ${formatTimeDisplay(slot)}
      </button>
    `;
  }

  // --- STEP 5: GUEST INFORMATION ---
  renderStep5(content, footer) {
    const loc = this.state.selectedLocation;
    const symbol = this.settings?.currency_symbol || "$";
    const totalDuration = this.state.totalDuration;
    const totalPrice = this.state.totalPrice;

    // Build recap list
    let recapHtml = '';
    this.state.selectedServiceIds.forEach(id => {
      const s = this.services.find(x => x.id === id);
      if (s) {
        const p = s.discount_price || s.price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(s.name)}</span><span class="font-semibold">${formatDuration(s.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });
    this.state.selectedOfferIds.forEach(id => {
      const o = this.offers.find(x => x.id === id);
      if (o) {
        const p = o.discounted_price || o.original_price;
        recapHtml += `<div class="flex justify-between text-xs"><span>${escapeHtml(o.name)}</span><span class="font-semibold">${formatDuration(o.duration_minutes)} • ${formatPrice(p, symbol)}</span></div>`;
      }
    });

    let html = `
      <!-- Complete Recap Card -->
      <div class="mb-5 p-4 rounded-2xl bg-gradient-to-br from-[#FDEDE8] to-[#F6D9D0] border border-pink-200 shadow-xs">
        <h5 class="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Appointment Summary</h5>
        <div class="space-y-1.5 text-xs">
          ${recapHtml}
          <div class="border-t border-pink-200 mt-1 pt-1 flex justify-between text-sm font-bold">
            <span>Total</span>
            <span>${formatDuration(totalDuration)} • ${formatPrice(totalPrice, symbol)}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-slate-500">Location:</span>
            <strong class="text-pink-700">${loc ? escapeHtml(loc.name) : escapeHtml(this.settings?.address || 'Amwaj Center, Jounieh, Lebanon')}</strong>
          </div>
          <div class="flex justify-between">
            <span class="text-slate-500">Schedule:</span>
            <strong class="text-pink-700">${formatDatePretty(this.state.selectedDate)} at ${formatTimeDisplay(this.state.selectedTime)}</strong>
          </div>
        </div>
      </div>

      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 5 — Guest Contact Details</h4>
        <p class="text-xs text-slate-500 mt-0.5">Please provide your details so we can confirm your reservation</p>
      </div>

      <form id="wizard-details-form" class="space-y-3.5 text-xs">
        <div>
          <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">
            Full Name <span class="text-rose-600">*</span>
          </label>
          <input type="text" id="cust-name" required placeholder="e.g. Maya Haddad" value="${escapeHtml(this.state.customerName)}"
            class="w-full px-4 py-2.5 rounded-xl border border-pink-200 focus:outline-none focus:ring-2 focus:ring-pink-500 bg-white" />
        </div>

        <div>
          <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">
            Phone / WhatsApp Number <span class="text-rose-600">*</span>
          </label>
          <input type="tel" id="cust-phone" required placeholder="e.g. +961 70 123 456" value="${escapeHtml(this.state.customerPhone)}"
            class="w-full px-4 py-2.5 rounded-xl border border-pink-200 focus:outline-none focus:ring-2 focus:ring-pink-500 bg-white" />
          <span class="text-[10px] text-slate-400 mt-1 block">We will send immediate appointment confirmation via WhatsApp.</span>
        </div>

        <div>
          <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">
            Email Address <span class="text-slate-400 font-normal">(Optional)</span>
          </label>
          <input type="email" id="cust-email" placeholder="e.g. maya@example.com" value="${escapeHtml(this.state.customerEmail)}"
            class="w-full px-4 py-2.5 rounded-xl border border-pink-200 focus:outline-none focus:ring-2 focus:ring-pink-500 bg-white" />
        </div>

        <div>
          <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">
            Special Requests / Notes <span class="text-slate-400 font-normal">(Optional)</span>
          </label>
          <textarea id="cust-notes" rows="2" placeholder="e.g. Sensitive cuticles, bridal occasion..."
            class="w-full px-4 py-2 rounded-xl border border-pink-200 focus:outline-none focus:ring-2 focus:ring-pink-500 bg-white">${escapeHtml(this.state.customerNotes)}</textarea>
        </div>

        <div class="flex items-start gap-2">
          <input type="checkbox" id="cust-consent" required
            class="mt-1 w-4 h-4 text-pink-600 border-pink-300 rounded focus:ring-pink-500" />
          <label for="cust-consent" class="text-xs text-slate-600">
            I agree to the <a href="/terms.html" class="underline text-pink-600 hover:text-pink-800">Terms & Conditions</a> and <a href="/privacy.html" class="underline text-pink-600 hover:text-pink-800">Privacy Policy</a>.
          </label>
        </div>
      </form>
    `;

    content.innerHTML = html;

    footer.innerHTML = `
      <button id="step5-back-btn" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        ← Back
      </button>
      <button id="step5-submit-btn" class="btn-primary px-6 py-2.5 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md">
        <span>Confirm & Reserve Slot</span>
        <span>✦</span>
      </button>
    `;

    document.getElementById("step5-back-btn").addEventListener("click", () => {
      this.state.step = 4;
      this.renderCurrentStep();
    });

    const detailsForm = document.getElementById("wizard-details-form");
    detailsForm.addEventListener("submit", (e) => {
      e.preventDefault();
      this.submitBooking();
    });

    document.getElementById("step5-submit-btn").addEventListener("click", () => {
      this.submitBooking();
    });
  }

  async submitBooking() {
    const submitBtn = document.getElementById("step5-submit-btn");
    if (!submitBtn || submitBtn.disabled) {
      return;
    }

    const nameInput = document.getElementById("cust-name");
    const phoneInput = document.getElementById("cust-phone");
    const emailInput = document.getElementById("cust-email");
    const notesInput = document.getElementById("cust-notes");

    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    const email = emailInput ? emailInput.value.trim() : "";
    const notes = notesInput ? notesInput.value.trim() : "";

    if (!name || name.length < 2) {
      showToast("Please enter a valid full name (at least 2 characters).", "error");
      nameInput.focus();
      return;
    }
    if (!phone || phone.replace(/[^0-9]/g, "").length < 5) {
      showToast("Please enter a valid phone number (at least 5 digits).", "error");
      phoneInput.focus();
      return;
    }

    this.state.customerName = name;
    this.state.customerPhone = phone;
    this.state.customerEmail = email;
    this.state.customerNotes = notes;

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>Reserving Slot...</span> <span class="animate-spin">🌸</span>`;

    try {
      const payload = {
        service_ids: this.state.selectedServiceIds,
        offer_ids: this.state.selectedOfferIds,
        location_id: this.state.selectedLocation ? this.state.selectedLocation.id : null,
        customer_name: name,
        customer_phone: phone,
        customer_email: email || null,
        notes: notes || null,
        appointment_date: this.state.selectedDate,
        appointment_time: this.state.selectedTime
      };

      const booking = await apiFetch("/api/bookings", {
        method: "POST",
        body: payload
      });

      this.state.confirmedBooking = booking;
      this.state.step = 6;
      showToast("Appointment successfully confirmed!", "success");
      this.renderCurrentStep();
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Confirm & Reserve Slot</span> <span>✦</span>`;

      if (err.status === 409) {
        showToast("Slot conflict: That time was just booked. Please pick another slot.", "error");
        this.state.step = 4;
        this.renderCurrentStep();
      } else {
        showToast(err.message || "Failed to complete booking. Please try again.", "error");
      }
    }
  }

  // --- STEP 6: CONFIRMATION & CELEBRATION ---
  renderStep6(content, footer) {
    const b = this.state.confirmedBooking;
    const symbol = this.settings?.currency_symbol || "$";
    const waNumber = (this.settings?.whatsapp_number || "+96170882194").replace(/[^0-9]/g, "");
    const locationLabel = b.location_name || (this.state.selectedLocation?.name || null);

    const waMessage = encodeURIComponent(
      `Hello Blossom Dreams! 🌸\nI just booked an appointment online:\n\n` +
      `• Code: ${b.booking_code}\n` +
      `• Service: ${b.service_name}\n` +
      (locationLabel ? `• Location: ${locationLabel}\n` : ``) +
      `• Date: ${formatDatePretty(b.appointment_date)}\n` +
      `• Time: ${formatTimeDisplay(b.appointment_time)}\n` +
      `• Client: ${b.customer_name}\n\n` +
      `Looking forward to visiting your atelier!`
    );
    const waUrl = `https://wa.me/${waNumber}?text=${waMessage}`;

    let html = `
      <div class="text-center py-2">
        <!-- Blossom Checkmark Celebration -->
        <div class="w-18 h-18 rounded-full bg-gradient-to-tr from-pink-500 to-rose-600 text-white flex items-center justify-center text-3xl mx-auto mb-3 shadow-xl shadow-pink-600/30 animate-blossom-success">
          ✓
        </div>
        <h4 class="text-2xl font-serif font-extrabold text-gray-900">Appointment Reserved!</h4>
        <p class="text-xs text-slate-500 mt-1">We look forward to pampering you at Blossom Dreams.</p>

        <!-- Ticket Receipt Card -->
        <div class="ticket-receipt mt-5 p-6 shadow-sm text-left">
          <div class="flex items-center justify-between pb-3 border-b border-pink-100">
            <div>
              <span class="text-[9px] text-slate-400 uppercase font-extrabold tracking-widest">Booking Code</span>
              <div class="text-lg font-bold text-pink-700 font-mono flex items-center gap-2">
                <span>${b.booking_code}</span>
                <button id="btn-copy-code" class="text-[10px] text-slate-400 hover:text-slate-700 bg-slate-100 px-2 py-0.5 rounded font-sans" title="Copy code">Copy</button>
              </div>
            </div>
            <div class="text-right">
              <span class="text-[9px] text-slate-400 uppercase font-extrabold tracking-widest">Status</span>
              <div><span class="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase tracking-wide">Confirmed</span></div>
            </div>
          </div>

          <div class="py-4 space-y-2 text-xs border-b border-pink-100">
            <div class="flex justify-between">
              <span class="text-slate-500">Treatment:</span>
              <strong class="text-gray-900">${escapeHtml(b.service_name)}</strong>
            </div>
            ${locationLabel ? `
            <div class="flex justify-between">
              <span class="text-slate-500">Location:</span>
              <strong class="text-pink-700">${escapeHtml(locationLabel)}</strong>
            </div>` : ''}
            <div class="flex justify-between">
              <span class="text-slate-500">Date:</span>
              <strong class="text-slate-800">${formatDatePretty(b.appointment_date)}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Time:</span>
              <strong class="text-pink-700">${formatTimeDisplay(b.appointment_time)} (${formatDuration(b.duration_minutes)})</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Guest:</span>
              <span class="font-medium text-slate-800">${escapeHtml(b.customer_name)}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Total:</span>
              <strong class="text-pink-800 font-serif text-sm">${formatPrice(b.price, symbol)}</strong>
            </div>
          </div>

          <div class="pt-3 text-[11px] text-slate-500 flex items-center gap-2">
            <span>📍</span>
            <span>${escapeHtml(locationLabel || this.settings?.address || 'Amwaj Center, Jounieh, Lebanon')}</span>
          </div>
        </div>

        <!-- WhatsApp Notify CTA -->
        <div class="mt-5">
          <a href="${waUrl}" target="_blank" rel="noopener noreferrer"
            class="w-full inline-flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-2xl bg-[#25D366] hover:bg-[#20bd5a] text-white text-xs font-bold shadow-lg shadow-emerald-500/25 transition transform active:scale-95">
            <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.095 3.2 5.076 4.487.709.306 1.262.489 1.694.626.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg>
            <span>Notify Atelier on WhatsApp</span>
          </a>
        </div>
      </div>
    `;

    content.innerHTML = html;

    // Copy code button
    const copyBtn = document.getElementById("btn-copy-code");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(b.booking_code);
        copyBtn.innerText = "Copied!";
        setTimeout(() => copyBtn.innerText = "Copy", 2000);
      });
    }

    footer.innerHTML = `
      <button id="step6-book-another" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        Book Another Treatment
      </button>
      <button id="step6-done-btn" class="btn-primary px-7 py-2.5 rounded-xl text-xs font-bold">
        Done
      </button>
    `;

    document.getElementById("step6-book-another").addEventListener("click", () => {
      this.open();
    });

    document.getElementById("step6-done-btn").addEventListener("click", () => {
      this.close();
    });
  }
}

export const bookingWizard = new BookingWizard();
