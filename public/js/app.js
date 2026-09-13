// Blossom Dreams - Public Front-End Application
import { apiFetch, showToast, formatPrice, formatDuration, formatDatePretty, escapeHtml } from "./api.js";
import { bookingWizard } from "./booking.js";

class BlossomApp {
  constructor() {
    this.settings = null;
    this.categories = [];
    this.services = [];
    this.offers = [];
    this.gallery = [];
    this.activeCategorySlug = "all";
    this.searchQuery = "";
    this.countdownTimer = null;
  }

  async init() {
    try {
      this.setupIntersectionObserver();
      await this.loadInitialData();
      bookingWizard.init(this.services, this.settings);
      this.bindEvents();
      this.render();
      this.startOfferCountdowns();
    } catch (e) {
      console.error("Initialization error:", e);
      this.forceRevealAll();
      showToast("Unable to load salon details. Please refresh the page.", "error");
    }
  }

  forceRevealAll() {
    document.querySelectorAll('.reveal-on-scroll:not(.is-revealed)').forEach(el => el.classList.add('is-revealed'));
  }

  setupIntersectionObserver() {
    if (!('IntersectionObserver' in window)) {
      // No observer support: never hide the content.
      document.querySelectorAll('.reveal-on-scroll').forEach(el => el.classList.add('is-revealed'));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.12,
      rootMargin: "0px 0px -40px 0px"
    });

    document.querySelectorAll('.reveal-on-scroll').forEach(el => observer.observe(el));
    this.scrollObserver = observer;
  }

  observeNewElements() {
    const els = document.querySelectorAll('.reveal-on-scroll:not(.is-revealed)');
    if (!this.scrollObserver) {
      // No IntersectionObserver support: keep everything visible.
      els.forEach(el => el.classList.add('is-revealed'));
      return;
    }
    els.forEach(el => this.scrollObserver.observe(el));
  }

  async loadInitialData() {
    const [settings, categories, services, offers, gallery] = await Promise.all([
      apiFetch("/api/settings").catch(() => null),
      apiFetch("/api/categories").catch(() => []),
      apiFetch("/api/services").catch(() => []),
      apiFetch("/api/offers").catch(() => []),
      apiFetch("/api/gallery").catch(() => []),
    ]);

    this.settings = settings;
    this.categories = categories;
    this.services = services;
    this.offers = offers;
    this.gallery = gallery;
  }

  bindEvents() {
    // Mobile navigation drawer toggle
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    const mobileDrawer = document.getElementById("mobile-drawer");
    const closeDrawerBtn = document.getElementById("close-drawer-btn");
    const drawerOverlay = document.getElementById("drawer-overlay");

    if (mobileMenuBtn && mobileDrawer) {
      mobileMenuBtn.addEventListener("click", () => {
        mobileDrawer.classList.remove("translate-x-full");
        document.body.style.overflow = "hidden";
      });
      const closeDrawer = () => {
        mobileDrawer.classList.add("translate-x-full");
        document.body.style.overflow = "";
      };
      if (closeDrawerBtn) closeDrawerBtn.addEventListener("click", closeDrawer);
      if (drawerOverlay) drawerOverlay.addEventListener("click", closeDrawer);
      document.querySelectorAll(".drawer-nav-link").forEach(l => l.addEventListener("click", closeDrawer));
    }

    // Global "Book Now" buttons
    document.querySelectorAll(".btn-open-booking").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const serviceId = btn.dataset.serviceId || null;
        bookingWizard.open(serviceId);
      });
    });

    // Service Search Input with debounce
    const searchInput = document.getElementById("services-search-input");
    if (searchInput) {
      let debounceTimeout;
      searchInput.addEventListener("input", (e) => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
          this.searchQuery = e.target.value.toLowerCase().trim();
          this.renderServicesList();
        }, 180);
      });
    }

    // Booking Lookup / Verify Modal
    const lookupBtn = document.getElementById("btn-lookup-booking");
    if (lookupBtn) {
      lookupBtn.addEventListener("click", (e) => {
        e.preventDefault();
        this.openLookupModal();
      });
    }

    // Gallery Lightbox
    this.bindGalleryEvents();
  }

  render() {
    this.renderSettingsAndBranding();
    this.renderOffers();
    this.renderCategoryPills();
    this.renderServicesList();
    this.renderGallery();
    setTimeout(() => this.observeNewElements(), 100);
  }

  renderSettingsAndBranding() {
    if (!this.settings) return;
    const s = this.settings;

    // Announcement text
    const banner = document.getElementById("announcement-banner-text");
    if (banner && s.announcement_text) {
      banner.innerText = s.announcement_text;
    }

    // Salon branding
    document.querySelectorAll(".salon-brand-name").forEach(el => el.innerText = s.salon_name);
    document.querySelectorAll(".salon-brand-tagline").forEach(el => el.innerText = s.tagline);
    document.querySelectorAll(".salon-phone-text").forEach(el => el.innerText = s.phone);
    document.querySelectorAll(".salon-address-text").forEach(el => el.innerText = s.address);
    document.querySelectorAll(".salon-hours-text").forEach(el => el.innerText = s.opening_hours_text);

    // WhatsApp Links
    const rawWa = (s.whatsapp_number || "+96170882194").replace(/[^0-9]/g, "");
    const waUrl = `https://wa.me/${rawWa}?text=${encodeURIComponent("Hello Blossom Dreams! 🌸 I would like to inquire about booking a salon appointment.")}`;
    document.querySelectorAll(".salon-whatsapp-link").forEach(el => {
      el.href = waUrl;
    });

    // Instagram Links
    const igUrl = s.instagram_url || "https://www.instagram.com/blossomdreams.lb/";
    document.querySelectorAll(".salon-instagram-link").forEach(el => {
      el.href = igUrl;
    });
  }

  // --- Real-time Countdown Timer for Offers ---
  startOfferCountdowns() {
    const updateCountdowns = () => {
      const now = new Date().getTime();
      document.querySelectorAll(".offer-countdown-tag").forEach(el => {
        const endDateStr = el.dataset.endDate;
        if (!endDateStr) return;
        const target = new Date(`${endDateStr}T23:59:59`).getTime();
        const diff = target - now;

        if (diff <= 0) {
          el.innerText = "Ending today";
          return;
        }

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (days > 1) {
          el.innerText = `⏱ ${days}d ${hours}h left`;
        } else {
          el.innerText = `⏱ ${hours}h ${mins}m left`;
        }
      });
    };

    updateCountdowns();
    this.countdownTimer = setInterval(updateCountdowns, 60000);
  }

  // --- Special Offers Section ---
  renderOffers() {
    const container = document.getElementById("offers-container");
    if (!container) return;

    if (!this.offers || this.offers.length === 0) {
      container.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-400">
          <span class="text-3xl block mb-2">🌸</span>
          <p class="text-sm font-serif italic">Check back soon for our signature seasonal pampering packages.</p>
        </div>
      `;
      return;
    }

    const symbol = this.settings?.currency_symbol || "$";
    let html = "";

    this.offers.forEach((off, idx) => {
      html += `
        <div class="luxury-card flex flex-col group border border-pink-200/70 reveal-on-scroll delay-${(idx % 4) * 100}">
          <!-- Discount badge & Countdown -->
          <div class="absolute top-3 left-3 z-10 flex flex-col gap-1.5 items-start">
            <span class="badge-discount">
              <span>✦</span>
              <span>${off.discount_percent}% OFF</span>
            </span>
          </div>

          <div class="absolute top-3 right-3 z-10">
            <span class="countdown-pill offer-countdown-tag" data-end-date="${off.end_date}">
              ⏱ Limited Time
            </span>
          </div>

          <!-- Offer Image with smooth zoom -->
          <div class="relative h-56 sm:h-60 overflow-hidden bg-pink-100">
            <img src="${off.image_url || '/static/images/offer_glow_duo.jpg'}" alt="${escapeHtml(off.title)}"
              class="w-full h-full object-cover group-hover:scale-108 transition duration-700 ease-out" />
            <div class="absolute inset-0 bg-gradient-to-t from-black/65 via-transparent to-transparent"></div>
            
            <div class="absolute bottom-3 left-4 right-4 text-white">
              <span class="text-[9px] uppercase tracking-[0.2em] font-bold text-pink-300">Exclusive Atelier Bundle</span>
              <h4 class="text-base font-serif font-bold leading-tight drop-shadow-sm mt-0.5">${escapeHtml(off.title)}</h4>
            </div>
          </div>

          <!-- Offer Body -->
          <div class="p-5 flex-1 flex flex-col justify-between">
            <p class="text-xs text-slate-600 line-clamp-2 leading-relaxed mb-4 font-normal">
              ${escapeHtml(off.description || '')}
            </p>

            <div class="pt-3.5 border-t border-pink-100/80 flex items-center justify-between">
              <div>
                <span class="text-[10px] text-slate-400 line-through block leading-tight">${formatPrice(off.original_price, symbol)}</span>
                <span class="text-xl font-bold text-pink-700 font-serif leading-none">${formatPrice(off.discounted_price, symbol)}</span>
              </div>
              <button data-service-id="${off.service_id || ''}" class="btn-primary px-4 py-2.5 rounded-xl text-xs font-bold btn-book-offer flex items-center gap-1.5 shadow-md">
                <span>Claim Offer</span>
                <span>✦</span>
              </button>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Bind offer booking triggers
    container.querySelectorAll(".btn-book-offer").forEach(btn => {
      btn.addEventListener("click", () => {
        const srvId = btn.dataset.serviceId;
        bookingWizard.open(srvId ? parseInt(srvId) : null);
      });
    });
  }

  // --- Category Tabs Filter ---
  renderCategoryPills() {
    const container = document.getElementById("categories-pills-container");
    if (!container) return;

    let html = `
      <button data-slug="all" class="category-pill-btn px-5 py-2.5 rounded-full text-xs font-bold transition whitespace-nowrap ${this.activeCategorySlug === 'all' ? 'bg-[#EE6A95] text-white shadow-md shadow-pink-600/30' : 'bg-white text-slate-700 hover:bg-pink-50 border border-pink-100/90'}">
        ✨ All Treatments
      </button>
    `;

    this.categories.forEach(cat => {
      const isActive = this.activeCategorySlug === cat.slug;
      html += `
        <button data-slug="${cat.slug}" class="category-pill-btn px-5 py-2.5 rounded-full text-xs font-bold transition whitespace-nowrap ${isActive ? 'bg-[#EE6A95] text-white shadow-md shadow-pink-600/30' : 'bg-white text-slate-700 hover:bg-pink-50 border border-pink-100/90'}">
          ${escapeHtml(cat.name)}
        </button>
      `;
    });

    container.innerHTML = html;

    container.querySelectorAll(".category-pill-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        this.activeCategorySlug = btn.dataset.slug;
        this.renderCategoryPills();
        this.renderServicesList();
      });
    });
  }

  // --- Services Catalog List ---
  renderServicesList() {
    const container = document.getElementById("services-grid-container");
    if (!container) return;

    const symbol = this.settings?.currency_symbol || "$";

    let filtered = this.services.filter(s => {
      const matchCat = this.activeCategorySlug === "all" || 
        (this.categories.find(c => c.slug === this.activeCategorySlug)?.id === s.category_id);
      
      const matchSearch = !this.searchQuery || 
        s.name.toLowerCase().includes(this.searchQuery) || 
        (s.description && s.description.toLowerCase().includes(this.searchQuery)) ||
        (s.category_name && s.category_name.toLowerCase().includes(this.searchQuery));

      return matchCat && matchSearch;
    });

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="col-span-full py-16 text-center text-slate-400">
          <span class="text-4xl block mb-2">🌸</span>
          <p class="text-sm font-bold text-slate-700">No treatments match your search.</p>
          <p class="text-xs text-slate-400 mt-1">Try another keyword or browse all categories.</p>
        </div>
      `;
      return;
    }

    let html = "";
    filtered.forEach((s, idx) => {
      const displayPrice = s.discount_price || s.price;
      html += `
        <div class="luxury-card flex flex-col group border border-pink-100/80 reveal-on-scroll delay-${(idx % 4) * 100}">
          <!-- Treatment Image with Overlay & Zoom -->
          <div class="relative h-52 overflow-hidden bg-pink-50">
            <img src="${s.image_url || '/static/images/nails_manicure.jpg'}" alt="${escapeHtml(s.name)}"
              class="w-full h-full object-cover group-hover:scale-108 transition duration-700 ease-out" />
            
            <div class="absolute top-3 left-3 flex flex-col gap-1.5 z-10">
              ${s.discount_percent ? `<span class="badge-discount">${s.discount_percent}% OFF</span>` : ''}
              ${s.is_featured ? `<span class="badge-featured">★ Signature</span>` : ''}
            </div>

            <div class="absolute bottom-3 right-3 bg-white/95 backdrop-blur-md px-3 py-1 rounded-full text-[11px] font-bold text-slate-700 shadow-sm border border-pink-100 flex items-center gap-1.5">
              <span>⏱</span>
              <span>${formatDuration(s.duration_minutes)}</span>
            </div>
          </div>

          <!-- Content Body -->
          <div class="p-5 flex-1 flex flex-col justify-between">
            <div>
              <span class="text-[10px] font-bold text-pink-700 uppercase tracking-widest block mb-1">
                ${escapeHtml(s.category_name || 'Bespoke Care')}
              </span>
              <h4 class="text-base font-serif font-bold text-gray-900 group-hover:text-pink-700 transition">
                ${escapeHtml(s.name)}
              </h4>
              <p class="text-xs text-slate-500 mt-2 line-clamp-2 leading-relaxed font-normal">
                ${escapeHtml(s.description || '')}
              </p>
            </div>

            <!-- Price & Action -->
            <div class="pt-4 mt-3 border-t border-pink-100/80 flex items-center justify-between">
              <div>
                <span class="text-[10px] text-slate-400 uppercase tracking-wider font-semibold block">Investment</span>
                <div class="flex items-baseline gap-1.5">
                  <span class="text-xl font-bold text-gray-900 font-serif leading-none">${formatPrice(displayPrice, symbol)}</span>
                  ${s.discount_price ? `<span class="text-xs text-slate-400 line-through">${formatPrice(s.price, symbol)}</span>` : ''}
                </div>
              </div>
              <button data-id="${s.id}" class="btn-primary px-4 py-2.5 rounded-xl text-xs font-bold btn-book-service flex items-center gap-1.5 shadow-sm">
                <span>Book</span>
                <span>→</span>
              </button>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Bind Book triggers
    container.querySelectorAll(".btn-book-service").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        bookingWizard.open(id);
      });
    });

    this.observeNewElements();
  }

  // --- Visual Gallery ---
  renderGallery() {
    const container = document.getElementById("gallery-grid-container");
    if (!container) return;

    if (!this.gallery || this.gallery.length === 0) {
      container.innerHTML = `<div class="col-span-full text-center py-8 text-slate-400 text-xs">Portfolio updating...</div>`;
      return;
    }

    let html = "";
    this.gallery.forEach((g, idx) => {
      html += `
        <div data-index="${idx}" class="gallery-item-card relative h-56 sm:h-64 rounded-3xl overflow-hidden cursor-pointer group shadow-sm border border-pink-100/60 reveal-on-scroll delay-${(idx % 4) * 100}">
          <img src="${g.image_url}" alt="${escapeHtml(g.title || 'Salon Gallery')}"
            class="w-full h-full object-cover group-hover:scale-110 transition duration-700 ease-out" />
          <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition duration-300 flex flex-col justify-end p-4 text-white">
            <span class="text-[9px] text-pink-300 font-bold uppercase tracking-wider">${escapeHtml(g.category || 'Atelier')}</span>
            <h5 class="text-sm font-serif font-bold leading-tight drop-shadow-sm">${escapeHtml(g.title || '')}</h5>
            <p class="text-[11px] text-slate-200 line-clamp-1 mt-0.5 font-normal">${escapeHtml(g.caption || '')}</p>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
    this.observeNewElements();
  }

  bindGalleryEvents() {
    const container = document.getElementById("gallery-grid-container");
    if (!container) return;

    container.addEventListener("click", (e) => {
      const card = e.target.closest(".gallery-item-card");
      if (!card) return;
      const idx = parseInt(card.dataset.index);
      const item = this.gallery[idx];
      if (item) this.openLightbox(item);
    });
  }

  openLightbox(item) {
    let lb = document.getElementById("gallery-lightbox-modal");
    if (!lb) {
      lb = document.createElement("div");
      lb.id = "gallery-lightbox-modal";
      lb.className = "fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md";
      document.body.appendChild(lb);
    }

    lb.innerHTML = `
      <div class="relative max-w-2xl w-full bg-white rounded-3xl overflow-hidden shadow-2xl modal-content-anim">
        <button id="close-lightbox-btn" class="absolute top-4 right-4 z-10 w-9 h-9 rounded-full bg-black/60 text-white hover:bg-black flex items-center justify-center transition">
          ✕
        </button>
        <div class="max-h-[70vh] bg-black flex items-center justify-center">
          <img src="${item.image_url}" alt="${escapeHtml(item.title || '')}" class="max-h-[70vh] w-full object-contain" />
        </div>
        <div class="p-6 bg-white">
          <span class="text-[10px] uppercase tracking-wider text-pink-700 font-bold">${escapeHtml(item.category || 'Atelier')}</span>
          <h4 class="text-lg font-serif font-bold text-gray-900 mt-0.5">${escapeHtml(item.title || '')}</h4>
          <p class="text-xs text-slate-600 mt-1 leading-relaxed">${escapeHtml(item.caption || '')}</p>
        </div>
      </div>
    `;

    lb.classList.remove("hidden");
    document.body.style.overflow = "hidden";

    const close = () => {
      lb.classList.add("hidden");
      document.body.style.overflow = "";
    };

    lb.querySelector("#close-lightbox-btn").addEventListener("click", close);
    lb.addEventListener("click", (e) => {
      if (e.target === lb) close();
    });
  }

  // --- Client Appointment Lookup Modal ---
  openLookupModal() {
    let modal = document.getElementById("lookup-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "lookup-modal";
      modal.className = "fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay";
      modal.innerHTML = `
        <div class="relative w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-pink-100">
          <div class="flex items-center justify-between pb-3 border-b border-pink-100">
            <div>
              <h4 class="text-base font-serif font-bold text-gray-900">Check Booking Status</h4>
              <p class="text-[11px] text-pink-700 font-medium">Verify your confirmed salon reservation</p>
            </div>
            <button id="close-lookup-btn" class="w-8 h-8 rounded-full bg-pink-50 text-gray-500 hover:text-gray-800 flex items-center justify-center">✕</button>
          </div>
          <div class="py-4">
            <p class="text-xs text-slate-500 mb-3">Enter your 5-digit booking code (e.g. BD-84920):</p>
            <div class="flex gap-2">
              <input type="text" id="lookup-code-input" placeholder="BD-XXXXX" class="flex-1 text-xs uppercase px-3.5 py-2.5 rounded-xl border border-pink-200 focus:outline-none focus:ring-2 focus:ring-pink-500 font-mono text-center font-bold text-base" />
              <button id="lookup-search-btn" class="btn-primary px-5 py-2.5 rounded-xl text-xs font-bold">Search</button>
            </div>
            <div id="lookup-result-box" class="mt-4 hidden"></div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      modal.querySelector("#close-lookup-btn").addEventListener("click", () => {
        modal.classList.add("hidden");
      });
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
      });

      modal.querySelector("#lookup-search-btn").addEventListener("click", async () => {
        const code = modal.querySelector("#lookup-code-input").value.trim();
        const resBox = modal.querySelector("#lookup-result-box");
        if (!code) {
          showToast("Please enter a booking code", "error");
          return;
        }

        resBox.classList.remove("hidden");
        resBox.innerHTML = `<div class="text-center py-4 text-xs text-pink-600">Verifying code...</div>`;

        try {
          const b = await apiFetch(`/api/bookings/verify/${code}`);
          const symbol = this.settings?.currency_symbol || "$";
          resBox.innerHTML = `
            <div class="ticket-receipt p-5 shadow-xs text-xs space-y-2">
              <div class="flex justify-between items-center pb-2 border-b border-pink-100">
                <span class="font-mono font-bold text-pink-700 text-sm">${b.booking_code}</span>
                <span class="capitalize px-2.5 py-0.5 rounded-full text-[10px] font-bold ${b.status === 'confirmed' ? 'bg-emerald-100 text-emerald-800' : 'bg-pink-100 text-pink-800'}">${b.status}</span>
              </div>
              <div class="space-y-1 pt-1">
                <div>Treatment: <strong class="text-slate-900">${escapeHtml(b.service_name)}</strong></div>
                <div>Date: <strong class="text-slate-800">${formatDatePretty(b.appointment_date)}</strong></div>
                <div>Time: <strong class="text-pink-700">${b.appointment_time}</strong> (${formatDuration(b.duration_minutes)})</div>
                <div>Guest: <strong class="text-slate-800">${escapeHtml(b.customer_name)}</strong></div>
                <div>Total: <strong class="text-pink-700">${formatPrice(b.price, symbol)}</strong></div>
              </div>
            </div>
          `;
        } catch (err) {
          resBox.innerHTML = `
            <div class="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-xs text-center font-medium">
              No booking found with this code. Please check and try again.
            </div>
          `;
        }
      });
    }

    modal.classList.remove("hidden");
    document.getElementById("lookup-code-input").focus();
  }
}

// Instantiate on DOM load
document.addEventListener("DOMContentLoaded", () => {
  const app = new BlossomApp();
  app.init();
});

// Sticky header refinement on scroll
const siteHeader = document.querySelector(".site-header");
if (siteHeader) {
  const updateHeaderShadow = () => siteHeader.classList.toggle("scrolled", window.scrollY > 24);
  window.addEventListener("scroll", updateHeaderShadow, { passive: true });
  updateHeaderShadow();
}
