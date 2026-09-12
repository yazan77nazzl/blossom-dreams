// Interactive 5-Step Luxury Booking Wizard for Blossom Dreams
import { apiFetch, showToast, formatPrice, formatDuration, formatDatePretty, escapeHtml } from "./api.js";

class BookingWizard {
  constructor() {
    this.modal = null;
    this.services = [];
    this.settings = null;
    this.state = {
      step: 1, // 1: Service, 2: Date, 3: Time, 4: Details, 5: Confirmation
      selectedService: null,
      selectedDate: null,
      selectedTime: null,
      availableSlots: [],
      isLoadingSlots: false,
      slotsReason: null,
      customerName: "",
      customerPhone: "",
      customerEmail: "",
      customerNotes: "",
      confirmedBooking: null
    };
  }

  init(services, settings) {
    this.services = services;
    this.settings = settings;
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
              <p class="text-[10px] text-pink-700 font-bold tracking-widest uppercase mt-0.5">Blossom Dreams • Verdun Atelier</p>
            </div>
          </div>
          <button id="close-booking-modal" class="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 flex items-center justify-center transition">
            ✕
          </button>
        </div>

        <!-- 5-Step Progress Bar & Indicators -->
        <div class="px-6 pt-3.5 pb-2.5 bg-pink-50/40 border-b border-pink-100/60">
          <div class="flex items-center justify-between text-[11px] font-bold text-slate-400 mb-2">
            <span id="step-lbl-1" class="step-indicator active">1. Service</span>
            <span id="step-lbl-2" class="step-indicator">2. Date</span>
            <span id="step-lbl-3" class="step-indicator">3. Time</span>
            <span id="step-lbl-4" class="step-indicator">4. Details</span>
            <span id="step-lbl-5" class="step-indicator">5. Confirmation</span>
          </div>
          <div class="booking-progress-track">
            <div id="booking-progress-bar" class="booking-progress-fill" style="width: 20%;"></div>
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

  open(preSelectedServiceId = null) {
    if (!this.modal) this.renderModalContainer();

    this.state.step = 1;
    this.state.selectedTime = null;
    this.state.availableSlots = [];
    this.state.confirmedBooking = null;

    // Set today as initial date
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    this.state.selectedDate = `${yyyy}-${mm}-${dd}`;

    if (preSelectedServiceId) {
      const match = this.services.find(s => s.id === parseInt(preSelectedServiceId));
      if (match) {
        this.state.selectedService = match;
        this.state.step = 2; // Jump directly to date
      }
    } else {
      this.state.selectedService = null;
    }

    this.modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
    this.renderCurrentStep();
  }

  close() {
    if (!this.modal) return;
    this.modal.classList.add("hidden");
    document.body.style.overflow = "";
  }

  updateProgress() {
    const progressMap = { 1: "20%", 2: "40%", 3: "60%", 4: "80%", 5: "100%" };
    const bar = document.getElementById("booking-progress-bar");
    if (bar) bar.style.width = progressMap[this.state.step] || "20%";

    for (let i = 1; i <= 5; i++) {
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
  }

  // --- STEP 1: SELECT TREATMENT ---
  renderStep1(content, footer) {
    const symbol = this.settings?.currency_symbol || "$";
    let html = `
      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 1 — Choose a Treatment</h4>
        <p class="text-xs text-slate-500 mt-0.5">Select from our signature luxury salon menu</p>
      </div>

      <div class="mb-3.5">
        <input type="text" id="wizard-service-search" placeholder="Search treatment (e.g., Russian manicure, BIAB, Volume Lashes...)"
          class="w-full text-xs px-4 py-2.5 rounded-xl border border-pink-200 focus:outline-none focus:ring-2 focus:ring-pink-500 bg-pink-50/20" />
      </div>

      <div id="wizard-services-list" class="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
    `;

    this.services.forEach(s => {
      const isSelected = this.state.selectedService?.id === s.id;
      const displayPrice = s.discount_price || s.price;
      html += `
        <div data-id="${s.id}" class="wizard-service-item p-3.5 rounded-2xl border cursor-pointer transition flex items-center justify-between ${isSelected ? 'border-pink-600 bg-pink-50/70 ring-2 ring-pink-500/20' : 'border-pink-100 hover:border-pink-300 hover:bg-pink-50/30'}">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-xl bg-pink-100 overflow-hidden flex-shrink-0 border border-pink-200/80">
              <img src="${s.image_url || '/static/images/nails_manicure.jpg'}" alt="${escapeHtml(s.name)}" class="w-full h-full object-cover" />
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

    html += `</div>`;
    content.innerHTML = html;

    // Search filter
    const searchInput = document.getElementById("wizard-service-search");
    searchInput.addEventListener("input", (e) => {
      const term = e.target.value.toLowerCase().trim();
      document.querySelectorAll(".wizard-service-item").forEach(item => {
        const id = parseInt(item.dataset.id);
        const s = this.services.find(srv => srv.id === id);
        if (!s) return;
        const match = s.name.toLowerCase().includes(term) || (s.description && s.description.toLowerCase().includes(term));
        item.style.display = match ? "flex" : "none";
      });
    });

    // Selection
    document.querySelectorAll(".wizard-service-item").forEach(item => {
      item.addEventListener("click", () => {
        const id = parseInt(item.dataset.id);
        this.state.selectedService = this.services.find(s => s.id === id);
        this.state.step = 2;
        this.renderCurrentStep();
      });
    });

    // Footer
    footer.innerHTML = `
      <div class="text-xs text-slate-500 font-medium">Select any service to proceed</div>
      <button id="step1-next-btn" ${this.state.selectedService ? '' : 'disabled'} class="btn-primary ${this.state.selectedService ? '' : 'opacity-50 cursor-not-allowed'} px-6 py-2.5 rounded-xl text-xs font-bold">
        Continue →
      </button>
    `;

    if (this.state.selectedService) {
      document.getElementById("step1-next-btn").addEventListener("click", () => {
        this.state.step = 2;
        this.renderCurrentStep();
      });
    }
  }

  // --- STEP 2: SELECT DATE ---
  renderStep2(content, footer) {
    const s = this.state.selectedService;
    const symbol = this.settings?.currency_symbol || "$";
    const price = s.discount_price || s.price;

    let html = `
      <!-- Service Recap Pill -->
      <div class="mb-5 p-3 rounded-2xl bg-pink-50/70 border border-pink-200 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-xl">✨</span>
          <div>
            <h5 class="text-xs font-bold text-gray-900">${escapeHtml(s.name)}</h5>
            <p class="text-[11px] text-pink-700 font-semibold">${formatDuration(s.duration_minutes)} • ${formatPrice(price, symbol)}</p>
          </div>
        </div>
        <button id="wizard-change-service-btn" class="text-[11px] text-pink-700 hover:text-pink-900 font-bold underline">
          Change
        </button>
      </div>

      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 2 — Select Appointment Date</h4>
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
        <button data-date="${dateStr}" class="cal-date-btn flex-shrink-0 w-15 py-3 rounded-2xl flex flex-col items-center justify-center text-center ${isSelected ? 'selected' : 'bg-white'} ${isSunday ? 'opacity-40' : ''}">
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
        <input type="date" id="wizard-date-input" value="${this.state.selectedDate}" min="${new Date().toISOString().split('T')[0]}"
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
        document.querySelectorAll(".cal-date-btn").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        document.getElementById("wizard-date-input").value = d;
        document.getElementById("wizard-date-preview").innerText = formatDatePretty(d);
      });
    });

    document.getElementById("wizard-date-input").addEventListener("change", (e) => {
      this.state.selectedDate = e.target.value;
      document.querySelectorAll(".cal-date-btn").forEach(b => {
        b.classList.toggle("selected", b.dataset.date === e.target.value);
      });
      document.getElementById("wizard-date-preview").innerText = formatDatePretty(e.target.value);
    });

    // Footer
    footer.innerHTML = `
      <button id="step2-back-btn" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        ← Back
      </button>
      <button id="step2-next-btn" class="btn-primary px-6 py-2.5 rounded-xl text-xs font-bold">
        Next: Choose Time →
      </button>
    `;

    document.getElementById("step2-back-btn").addEventListener("click", () => {
      this.state.step = 1;
      this.renderCurrentStep();
    });

    document.getElementById("step2-next-btn").addEventListener("click", () => {
      this.state.step = 3;
      this.renderCurrentStep();
    });
  }

  // --- STEP 3: SELECT TIME SLOT ---
  async renderStep3(content, footer) {
    const s = this.state.selectedService;
    const dateStr = this.state.selectedDate;

    let html = `
      <!-- Date & Service Pill -->
      <div class="mb-5 p-3 rounded-2xl bg-pink-50/70 border border-pink-200 flex items-center justify-between">
        <div>
          <div class="text-xs font-bold text-gray-900">${escapeHtml(s.name)}</div>
          <div class="text-[11px] text-pink-700 font-semibold font-mono">${formatDatePretty(dateStr)} • ${formatDuration(s.duration_minutes)}</div>
        </div>
        <button id="wizard-back-to-date" class="text-[11px] text-pink-700 hover:text-pink-900 font-bold underline">
          Change Date
        </button>
      </div>

      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 3 — Select Available Time</h4>
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
      this.state.step = 2;
      this.renderCurrentStep();
    });

    footer.innerHTML = `
      <button id="step3-back-btn" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        ← Back
      </button>
      <button id="step3-next-btn" disabled class="btn-primary opacity-50 px-6 py-2.5 rounded-xl text-xs font-bold cursor-not-allowed">
        Next: Guest Details →
      </button>
    `;

    document.getElementById("step3-back-btn").addEventListener("click", () => {
      this.state.step = 2;
      this.renderCurrentStep();
    });

    document.getElementById("step3-next-btn").addEventListener("click", () => {
      if (this.state.selectedTime) {
        this.state.step = 4;
        this.renderCurrentStep();
      }
    });

    await this.fetchAndRenderGroupedSlots();
  }

  async fetchAndRenderGroupedSlots() {
    const wrapper = document.getElementById("wizard-time-slots-wrapper");
    if (!wrapper) return;

    try {
      const data = await apiFetch(`/api/availability/slots?date=${this.state.selectedDate}&service_id=${this.state.selectedService.id}`);
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
          this.state.step = 2;
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

          const nextBtn = document.getElementById("step3-next-btn");
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
        ${slot}
      </button>
    `;
  }

  // --- STEP 4: GUEST INFORMATION ---
  renderStep4(content, footer) {
    const s = this.state.selectedService;
    const symbol = this.settings?.currency_symbol || "$";
    const price = s.discount_price || s.price;

    let html = `
      <!-- Complete Recap Card -->
      <div class="mb-5 p-4 rounded-2xl bg-gradient-to-br from-[#FDEDE8] to-[#F6D9D0] border border-pink-200 shadow-xs">
        <h5 class="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Appointment Summary</h5>
        <div class="space-y-1.5 text-xs">
          <div class="flex justify-between">
            <span class="text-slate-500">Service:</span>
            <strong class="text-gray-900">${escapeHtml(s.name)}</strong>
          </div>
          <div class="flex justify-between">
            <span class="text-slate-500">Schedule:</span>
            <strong class="text-pink-700">${formatDatePretty(this.state.selectedDate)} at ${this.state.selectedTime}</strong>
          </div>
          <div class="flex justify-between">
            <span class="text-slate-500">Duration & Investment:</span>
            <strong class="text-pink-800">${formatDuration(s.duration_minutes)} • ${formatPrice(price, symbol)}</strong>
          </div>
        </div>
      </div>

      <div class="mb-4">
        <h4 class="text-base font-serif font-bold text-gray-900">Step 4 — Guest Contact Details</h4>
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
      </form>
    `;

    content.innerHTML = html;

    footer.innerHTML = `
      <button id="step4-back-btn" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        ← Back
      </button>
      <button id="step4-submit-btn" class="btn-primary px-6 py-2.5 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md">
        <span>Confirm & Reserve Slot</span>
        <span>✦</span>
      </button>
    `;

    document.getElementById("step4-back-btn").addEventListener("click", () => {
      this.state.step = 3;
      this.renderCurrentStep();
    });

    document.getElementById("step4-submit-btn").addEventListener("click", () => {
      this.submitBooking();
    });
  }

  async submitBooking() {
    const nameInput = document.getElementById("cust-name");
    const phoneInput = document.getElementById("cust-phone");
    const emailInput = document.getElementById("cust-email");
    const notesInput = document.getElementById("cust-notes");

    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    const email = emailInput ? emailInput.value.trim() : "";
    const notes = notesInput ? notesInput.value.trim() : "";

    if (!name) {
      showToast("Please enter your full name.", "error");
      nameInput.focus();
      return;
    }
    if (!phone) {
      showToast("Please enter your phone number.", "error");
      phoneInput.focus();
      return;
    }

    this.state.customerName = name;
    this.state.customerPhone = phone;
    this.state.customerEmail = email;
    this.state.customerNotes = notes;

    const submitBtn = document.getElementById("step4-submit-btn");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>Reserving Slot...</span> <span class="animate-spin">🌸</span>`;

    try {
      const payload = {
        service_id: this.state.selectedService.id,
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
      this.state.step = 5;
      showToast("Appointment successfully confirmed!", "success");
      this.renderCurrentStep();
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Confirm & Reserve Slot</span> <span>✦</span>`;

      if (err.status === 409) {
        showToast("Slot conflict: That time was just booked. Please pick another slot.", "error");
        this.state.step = 3;
        this.renderCurrentStep();
      } else {
        showToast(err.message || "Failed to complete booking. Please try again.", "error");
      }
    }
  }

  // --- STEP 5: CONFIRMATION & CELEBRATION ---
  renderStep5(content, footer) {
    const b = this.state.confirmedBooking;
    const symbol = this.settings?.currency_symbol || "$";
    const waNumber = (this.settings?.whatsapp_number || "+96170882194").replace(/[^0-9]/g, "");

    const waMessage = encodeURIComponent(
      `Hello Blossom Dreams! 🌸\nI just booked an appointment online:\n\n` +
      `• Code: ${b.booking_code}\n` +
      `• Service: ${b.service_name}\n` +
      `• Date: ${formatDatePretty(b.appointment_date)}\n` +
      `• Time: ${b.appointment_time}\n` +
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
            <div class="flex justify-between">
              <span class="text-slate-500">Date:</span>
              <strong class="text-slate-800">${formatDatePretty(b.appointment_date)}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Time:</span>
              <strong class="text-pink-700">${b.appointment_time} (${formatDuration(b.duration_minutes)})</strong>
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
            <span>${escapeHtml(this.settings?.address || 'Verdun, Beirut, Lebanon')}</span>
          </div>
        </div>

        <!-- WhatsApp Notify CTA -->
        <div class="mt-5">
          <a href="${waUrl}" target="_blank" rel="noopener noreferrer"
            class="w-full inline-flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-2xl bg-[#25D366] hover:bg-[#20bd5a] text-white text-xs font-bold shadow-lg shadow-emerald-500/25 transition transform active:scale-95">
            <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/></svg>
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
      <button id="step5-book-another" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold">
        Book Another Treatment
      </button>
      <button id="step5-done-btn" class="btn-primary px-7 py-2.5 rounded-xl text-xs font-bold">
        Done
      </button>
    `;

    document.getElementById("step5-book-another").addEventListener("click", () => {
      this.open();
    });

    document.getElementById("step5-done-btn").addEventListener("click", () => {
      this.close();
    });
  }
}

export const bookingWizard = new BookingWizard();
