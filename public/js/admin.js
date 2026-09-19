// Blossom Dreams - Admin Dashboard Controller & Analytics
import { apiFetch, showToast, formatPrice, formatDuration, formatDatePretty, formatTimeDisplay, escapeHtml, setAuthToken, clearAuthToken, getAuthToken, getCurrentUser } from "./api.js";

function formatDateTimePretty(dtStr) {
  if (!dtStr) return "";
  const [datePart, timePart = ""] = String(dtStr).split(" ");
  const prettyDate = formatDatePretty(datePart);
  return timePart ? `${prettyDate} ${timePart.slice(0, 5)}` : prettyDate;
}

class AdminApp {
  constructor() {
    this.token = getAuthToken();
    this.currentUser = getCurrentUser();
    this.currentTab = "overview";
    this.services = [];
    this.categories = [];
    this.offers = [];
    this.bookings = [];
    this.settings = null;
    this.locations = [];
    this.calCurrentDate = new Date();
  }

  async init() {
    this.bindGlobalEvents();
    if (this.token) {
      try {
        await this.verifyAndLoadDashboard();
      } catch (e) {
        this.showLoginView();
      }
    } else {
      this.showLoginView();
    }
    this._autoRefreshTimer = setInterval(() => {
      if (this.currentTab === "bookings" && this.token) {
        this.renderBookingsTab().catch(() => {});
      }
    }, 30000);
  }

  showLoginView() {
    if (this._autoRefreshTimer) {
      clearInterval(this._autoRefreshTimer);
      this._autoRefreshTimer = null;
    }
    document.getElementById("admin-login-view").classList.remove("hidden");
    document.getElementById("admin-dashboard-view").classList.add("hidden");
  }

  showDashboardView() {
    document.getElementById("admin-login-view").classList.add("hidden");
    document.getElementById("admin-dashboard-view").classList.remove("hidden");
    if (this.currentUser) {
      document.getElementById("admin-user-display").innerText = this.currentUser.full_name || this.currentUser.username;
    }
  }

  async verifyAndLoadDashboard() {
    try {
      const user = await apiFetch("/api/auth/me");
      this.currentUser = user;
      this.showDashboardView();
      await this.loadAllData();
      this.renderCurrentTab();
      this.updatePendingBadge();
      this.showPendingNotification();
    } catch (e) {
      clearAuthToken();
      this.showLoginView();
    }
  }

  async loadAllData() {
    const [settings, categories, services, offers, bookings, locations, subcategories] = await Promise.all([
      apiFetch("/api/settings").catch(() => null),
      apiFetch("/api/categories?include_inactive=true").catch(() => []),
      apiFetch("/api/services?include_inactive=true").catch(() => []),
      apiFetch("/api/offers?include_inactive=true").catch(() => []),
      apiFetch("/api/bookings").catch(() => []),
      apiFetch("/api/locations").catch(() => []),
      apiFetch("/api/subcategories?include_inactive=true").catch(() => [])
    ]);

    this.settings = settings;
    this.categories = categories;
    this.services = services;
    this.offers = offers;
    this.bookings = bookings;
    this.locations = locations;
    this.subcategories = subcategories || [];
  }

  bindGlobalEvents() {
    // 1. Login Form Submit
    const loginForm = document.getElementById("admin-login-form");
    if (loginForm) {
      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const usernameInput = document.getElementById("login-username").value.trim();
        const passwordInput = document.getElementById("login-password").value;
        const errorBox = document.getElementById("login-error-msg");
        const submitBtn = document.getElementById("btn-submit-login");

        errorBox.classList.add("hidden");
        submitBtn.disabled = true;
        submitBtn.innerText = "Signing in...";

        try {
          const res = await apiFetch("/api/auth/login", {
            method: "POST",
            body: { username: usernameInput, password: passwordInput }
          });

          this.token = res.access_token;
          this.currentUser = res.user;
          setAuthToken(res.access_token, res.user);

          showToast("Welcome back, " + res.user.full_name, "success");
          await this.verifyAndLoadDashboard();
        } catch (err) {
          errorBox.innerText = err.message || "Invalid credentials.";
          errorBox.classList.remove("hidden");
        } finally {
          submitBtn.disabled = false;
          submitBtn.innerText = "Sign In to Executive Suite →";
        }
      });
    }

    // 2. Logout Button
    const logoutBtn = document.getElementById("admin-logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", () => {
        clearAuthToken();
        this.token = null;
        this.currentUser = null;
        this.showLoginView();
        showToast("Logged out successfully.", "info");
      });
    }

    // 3. Tab Buttons
    document.querySelectorAll(".admin-tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        this.switchTab(tab);
      });
    });

    // Mobile Sidebar Toggle (slide-in drawer + backdrop)
    const mobileToggle = document.getElementById("admin-mobile-toggle");
    const sidebar = document.getElementById("admin-sidebar");
    let mobileSidebarOpen = false;
    const closeMobileSidebar = () => {
      if (!mobileSidebarOpen || !sidebar) return;
      mobileSidebarOpen = false;
      sidebar.classList.add("hidden");
      sidebar.classList.remove("fixed", "inset-y-0", "left-0", "z-[60]", "shadow-2xl");
      const backdrop = document.getElementById("admin-mobile-backdrop");
      if (backdrop) backdrop.remove();
      document.body.style.overflow = "";
      mobileToggle?.setAttribute("aria-expanded", "false");
    };
    if (mobileToggle && sidebar) {
      mobileToggle.setAttribute("aria-expanded", "false");
      mobileToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        if (mobileSidebarOpen) {
          closeMobileSidebar();
          return;
        }
        mobileSidebarOpen = true;
        sidebar.classList.remove("hidden");
        sidebar.classList.add("fixed", "inset-y-0", "left-0", "z-[60]", "shadow-2xl");
        const backdrop = document.createElement("div");
        backdrop.id = "admin-mobile-backdrop";
        backdrop.className = "fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-[55] md:hidden transition-opacity";
        backdrop.addEventListener("click", closeMobileSidebar);
        document.body.appendChild(backdrop);
        document.body.style.overflow = "hidden";
        mobileToggle.setAttribute("aria-expanded", "true");
      });
    }
    this.closeMobileSidebar = closeMobileSidebar;
    document.querySelectorAll(".admin-tab-btn").forEach(btn =>
      btn.addEventListener("click", () => this.closeMobileSidebar())
    );

    // Quick Manual Booking button
    

    // Booking Filters
    const bDate = document.getElementById("filter-booking-date");
    const bStatus = document.getElementById("filter-booking-status");
    const bSearch = document.getElementById("filter-booking-search");
    const bReset = document.getElementById("btn-reset-booking-filters");

    const refreshBookings = () => this.renderBookingsTable();
    if (bDate) bDate.addEventListener("change", refreshBookings);
    if (bStatus) bStatus.addEventListener("change", refreshBookings);
    if (bSearch) bSearch.addEventListener("input", refreshBookings);
    if (bReset) {
      bReset.addEventListener("click", () => {
        bDate.value = "";
        bStatus.value = "";
        bSearch.value = "";
        refreshBookings();
      });
    }

    // Table vs Calendar Toggle
    const btnTable = document.getElementById("btn-view-table");
    const btnCal = document.getElementById("btn-view-calendar");
    if (btnTable && btnCal) {
      btnTable.addEventListener("click", () => {
        btnTable.className = "px-3.5 py-1.5 text-xs font-bold rounded-lg bg-white shadow-xs text-slate-800 transition";
        btnCal.className = "px-3.5 py-1.5 text-xs font-bold rounded-lg text-slate-500 hover:text-slate-800 transition";
        document.getElementById("bookings-table-view").classList.remove("hidden");
        document.getElementById("bookings-calendar-view").classList.add("hidden");
      });
      btnCal.addEventListener("click", () => {
        btnCal.className = "px-3.5 py-1.5 text-xs font-bold rounded-lg bg-white shadow-xs text-slate-800 transition";
        btnTable.className = "px-3.5 py-1.5 text-xs font-bold rounded-lg text-slate-500 hover:text-slate-800 transition";
        document.getElementById("bookings-table-view").classList.add("hidden");
        document.getElementById("bookings-calendar-view").classList.remove("hidden");
        this.renderCalendar();
      });
    }

    // Calendar navigation
    const calPrev = document.getElementById("cal-prev-month");
    const calNext = document.getElementById("cal-next-month");
    const calToday = document.getElementById("cal-today-btn");
    if (calPrev) calPrev.addEventListener("click", () => {
      this.calCurrentDate.setMonth(this.calCurrentDate.getMonth() - 1);
      this.renderCalendar();
    });
    if (calNext) calNext.addEventListener("click", () => {
      this.calCurrentDate.setMonth(this.calCurrentDate.getMonth() + 1);
      this.renderCalendar();
    });
    if (calToday) calToday.addEventListener("click", () => {
      this.calCurrentDate = new Date();
      this.renderCalendar();
    });

    // Add Modals Buttons
    document.getElementById("btn-add-service-modal").addEventListener("click", () => {
      this.openServiceModal();
    });
    document.getElementById("btn-add-offer-modal").addEventListener("click", () => {
      this.openOfferModal();
    });
    document.getElementById("btn-add-closed-modal").addEventListener("click", () => {
      this.openAddClosedDateModal();
    });
    document.getElementById("btn-add-gallery-modal").addEventListener("click", () => {
      this.openAddGalleryModal();
    });

    // Forms
    const setForm = document.getElementById("admin-settings-form");
    if (setForm) {
      setForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.saveSettings();
      });
    }

    const pwdForm = document.getElementById("admin-password-form");
    if (pwdForm) {
      pwdForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.changePassword();
      });
    }
  }

  switchTab(tabName) {
    this.currentTab = tabName;
    document.querySelectorAll(".admin-tab-btn").forEach(b => {
      if (b.dataset.tab === tabName) {
        b.className = "admin-tab-btn w-full px-3.5 py-2.5 rounded-xl flex items-center gap-3 transition active bg-pink-50 text-pink-800 font-bold border border-pink-100";
      } else {
        b.className = "admin-tab-btn w-full px-3.5 py-2.5 rounded-xl flex items-center gap-3 transition hover:bg-slate-50 text-slate-600";
      }
    });

    const titles = {
      overview: "Dashboard Overview & Analytics",
      bookings: "Bookings & Calendar",
      calendar: "Manual Calendar",
      services: "Services & Treatments",
      categories: "Manage Service Categories",
      offers: "Special Offers",
      availability: "Hours & Availability",
      gallery: "Gallery Portfolio",
      settings: "Salon Settings"
    };
    document.getElementById("admin-page-title").innerText = titles[tabName] || "Dashboard";

    document.querySelectorAll(".admin-tab-pane").forEach(pane => {
      pane.classList.add("hidden");
    });
    const activePane = document.getElementById(`tab-${tabName}`);
    if (activePane) activePane.classList.remove("hidden");

    this.renderCurrentTab();
  }

  renderCurrentTab() {
    if (this.currentTab === "overview") this.renderOverview();
    else if (this.currentTab === "bookings") this.renderBookingsTab();
    else if (this.currentTab === "calendar") this.renderCalendarTab();
    else if (this.currentTab === "services") this.renderServicesTab();
    else if (this.currentTab === "categories") this.renderCategoriesTab();
    else if (this.currentTab === "offers") this.renderOffersTab();
    else if (this.currentTab === "availability") this.renderAvailabilityTab();
    else if (this.currentTab === "gallery") this.renderGalleryTab();
    else if (this.currentTab === "subcategories") this.renderSubcategoriesTab();
    else if (this.currentTab === "settings") this.renderSettingsTab();
  }

  // --- 1. OVERVIEW & CHARTS ---
  async renderOverview() {
    try {
      const stats = await apiFetch("/api/bookings/stats/overview");
      const symbol = this.settings?.currency_symbol || "$";

      document.getElementById("stat-today-bookings").innerText = stats.today_appointments_count;
      document.getElementById("stat-upcoming-bookings").innerText = stats.upcoming_appointments_count;
      document.getElementById("stat-active-services").innerText = stats.total_active_services;
      document.getElementById("stat-total-revenue").innerText = formatPrice(stats.estimated_revenue, symbol);

      // Render Weekly Trend Chart (SVG)
      this.renderWeeklyTrendChart();

      // Render Category Breakdown Bars
      this.renderCategoryDistribution();

      // Render Today's Agenda Feed
      const agendaContainer = document.getElementById("today-agenda-container");
      if (!stats.today_appointments || stats.today_appointments.length === 0) {
        agendaContainer.innerHTML = `
          <div class="py-10 text-center text-slate-400 text-xs">
            <span class="text-3xl block mb-2">🌸</span>
            <p class="font-serif italic">No appointments scheduled for today yet.</p>
          </div>
        `;
        return;
      }

      let html = `
        <table class="w-full text-left text-xs text-slate-600">
          <thead class="bg-slate-50 text-slate-400 uppercase font-semibold text-[10px] tracking-wider">
            <tr>
              <th class="py-2.5 px-3">Time</th>
              <th class="py-2.5 px-3">Code</th>
              <th class="py-2.5 px-3">Guest</th>
              <th class="py-2.5 px-3">Service</th>
              <th class="py-2.5 px-3">Status</th>
              <th class="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
      `;

      stats.today_appointments.forEach(b => {
        html += `
          <tr class="hover:bg-slate-50/80 transition">
            <td class="py-3 px-3 font-bold text-pink-700 font-mono">${formatTimeDisplay(b.appointment_time)}</td>
            <td class="py-3 px-3 font-mono text-slate-500 font-bold">${b.booking_code}</td>
            <td class="py-3 px-3">
              <div class="font-bold text-slate-900">${escapeHtml(b.customer_name)}</div>
              <div class="text-[10px] text-slate-400 font-mono">${escapeHtml(b.customer_phone)}</div>
            </td>
            <td class="py-3 px-3 font-medium text-slate-800">${escapeHtml(b.service_name)}</td>
            <td class="py-3 px-3">${this.getStatusBadge(b.status)}</td>
            <td class="py-3 px-3 text-right space-x-1">
              ${b.status === 'pending' ? `<button data-id="${b.id}" data-status="confirmed" class="btn-quick-status px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-800 text-[10px] font-bold">Confirm</button>` : ''}
              ${b.status === 'confirmed' ? `<button data-id="${b.id}" data-status="completed" class="btn-quick-status px-2.5 py-1 rounded-lg bg-indigo-100 text-indigo-800 text-[10px] font-bold">Complete</button>` : ''}
              <button data-id="${b.id}" class="btn-view-booking-detail px-2 py-1 rounded-lg bg-slate-100 text-slate-600 text-[10px] font-bold">Details</button>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      agendaContainer.innerHTML = html;

      this.bindBookingActionButtons(agendaContainer);
    } catch (e) {
      console.error(e);
    }
  }

  renderWeeklyTrendChart() {
    const container = document.getElementById("chart-weekly-bookings-container");
    if (!container) return;

    // Aggregate counts for the next 7 days
    const days = [];
    const counts = [];
    const now = new Date();

    for (let i = 0; i < 7; i++) {
      const d = new Date();
      d.setDate(now.getDate() + i);
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const dateStr = `${yyyy}-${mm}-${dd}`;
      const dayLabel = d.toLocaleDateString("en-US", { weekday: "short" });

      const count = this.bookings.filter(b => b.appointment_date === dateStr && b.status !== 'cancelled').length;
      days.push(dayLabel);
      counts.push(count);
    }

    const maxCount = Math.max(...counts, 4);

    let svgHtml = `
      <div class="w-full flex items-end justify-between gap-3 h-36 pt-4">
    `;

    counts.forEach((c, idx) => {
      const heightPercent = Math.round((c / maxCount) * 100);
      const isToday = idx === 0;
      svgHtml += `
        <div class="flex-1 flex flex-col items-center gap-1.5 group">
          <span class="text-[10px] font-mono font-bold text-slate-600 opacity-0 group-hover:opacity-100 transition">${c}</span>
          <div class="w-full max-w-[36px] rounded-t-xl transition duration-500 ${isToday ? 'bg-gradient-to-t from-[#EE6A95] to-[#F7A1B3]' : 'bg-pink-100 group-hover:bg-pink-300'}" style="height: ${Math.max(heightPercent, 12)}%;"></div>
          <span class="text-[10px] font-bold uppercase tracking-wider ${isToday ? 'text-pink-700' : 'text-slate-400'}">${days[idx]}</span>
        </div>
      `;
    });

    svgHtml += `</div>`;
    container.innerHTML = svgHtml;
  }

  renderCategoryDistribution() {
    const container = document.getElementById("category-distribution-container");
    if (!container) return;

    const catCounts = {};
    this.services.forEach(s => {
      const cat = s.category_name || "Other";
      catCounts[cat] = (catCounts[cat] || 0) + 1;
    });

    const total = this.services.length || 1;
    let html = "";

    Object.entries(catCounts).slice(0, 4).forEach(([cat, count]) => {
      const pct = Math.round((count / total) * 100);
      html += `
        <div>
          <div class="flex justify-between items-center mb-1">
            <span class="font-bold text-slate-700">${escapeHtml(cat)}</span>
            <span class="font-mono text-slate-400 font-semibold">${count} (${pct}%)</span>
          </div>
          <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div class="bg-gradient-to-r from-pink-500 to-rose-600 h-full rounded-full" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // --- 2. BOOKINGS TAB ---
  async renderBookingsTab() {
    this.bookings = await apiFetch("/api/bookings");
    this.updatePendingBadge();
    this.renderBookingsTable();
  }

  renderBookingsTable() {
    const tbody = document.getElementById("bookings-table-body");
    if (!tbody) return;

    const dateVal = document.getElementById("filter-booking-date")?.value;
    const statusVal = document.getElementById("filter-booking-status")?.value;
    const searchVal = document.getElementById("filter-booking-search")?.value.toLowerCase().trim();
    const symbol = this.settings?.currency_symbol || "$";

    let filtered = this.bookings.filter(b => {
      if (dateVal && b.appointment_date !== dateVal) return false;
      if (statusVal && b.status !== statusVal) return false;
      if (searchVal) {
        const matchName = b.customer_name.toLowerCase().includes(searchVal);
        const matchPhone = b.customer_phone.toLowerCase().includes(searchVal);
        const matchCode = b.booking_code.toLowerCase().includes(searchVal);
        const matchService = b.service_name && b.service_name.toLowerCase().includes(searchVal);
        const matchLocation = b.location_name && b.location_name.toLowerCase().includes(searchVal);
        if (!matchName && !matchPhone && !matchCode && !matchService && !matchLocation) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="py-10 text-center text-slate-400 text-xs">
            No bookings found matching current filters.
          </td>
        </tr>
      `;
      return;
    }

    let html = "";
    filtered.forEach(b => {
      html += `
        <tr class="hover:bg-slate-50/80 transition">
          <td class="py-3.5 px-4 font-mono font-bold text-slate-700">${b.booking_code}</td>
          <td class="py-3.5 px-4">
            <div class="font-bold text-slate-800">${formatDatePretty(b.appointment_date)}</div>
            <div class="text-[11px] font-mono text-pink-700 font-bold">${formatTimeDisplay(b.appointment_time)} (${formatDuration(b.duration_minutes)})</div>
          </td>
          <td class="py-3.5 px-4">
            <div class="font-bold text-slate-900">${escapeHtml(b.customer_name)}</div>
            <div class="text-[11px] text-slate-500 font-mono">${escapeHtml(b.customer_phone)}</div>
          </td>
          <td class="py-3.5 px-4 font-semibold text-slate-800">${escapeHtml(b.service_name)}</td>
          <td class="py-3.5 px-4">
            <span class="inline-block max-w-[9rem] truncate align-middle text-slate-600" title="${escapeHtml(b.location_name || "")}">${escapeHtml(b.location_name || "—")}</span>
          </td>
          <td class="py-3.5 px-4 font-bold text-pink-800">${formatPrice(b.price, symbol)}</td>
          <td class="py-3.5 px-4">
            <select data-id="${b.id}" class="select-change-status text-xs font-semibold py-1 px-2.5 rounded-xl border border-slate-200 bg-white shadow-2xs">
              <option value="pending" ${b.status === 'pending' ? 'selected' : ''}>Pending</option>
              <option value="confirmed" ${b.status === 'confirmed' ? 'selected' : ''}>Confirmed</option>
              <option value="completed" ${b.status === 'completed' ? 'selected' : ''}>Completed</option>
              <option value="cancelled" ${b.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
              <option value="no_show" ${b.status === 'no_show' ? 'selected' : ''}>No Show</option>
            </select>
          </td>
          <td class="py-3.5 px-4 text-[11px] text-slate-500 font-mono">${formatDateTimePretty(b.created_at)}</td>
          <td class="py-3.5 px-4 text-right space-x-2">
            <button data-id="${b.id}" class="btn-view-booking-detail text-pink-700 hover:text-pink-900 font-bold text-xs">
              View
            </button>
            <button data-id="${b.id}" class="btn-cancel-booking text-amber-600 hover:text-amber-800 font-bold text-xs">
              Cancel
            </button>
            <button data-id="${b.id}" class="btn-delete-booking text-rose-600 hover:text-rose-800 font-bold text-xs">
              Delete
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
    this.bindBookingActionButtons(tbody);
  }

  bindBookingActionButtons(container) {
    container.querySelectorAll(".select-change-status").forEach(sel => {
      sel.addEventListener("change", async () => {
        const id = parseInt(sel.dataset.id);
        const newStatus = sel.value;
        try {
          await apiFetch(`/api/bookings/${id}/status`, {
            method: "PATCH",
            body: { status: newStatus }
          });
          showToast(`Status updated to ${newStatus}`);
          await this.loadAllData();
          this.renderCurrentTab();
        } catch (e) {
          showToast(e.message, "error");
        }
      });
    });

    container.querySelectorAll(".btn-quick-status").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = parseInt(btn.dataset.id);
        const newStatus = btn.dataset.status;
        try {
          await apiFetch(`/api/bookings/${id}/status`, {
            method: "PATCH",
            body: { status: newStatus }
          });
          showToast(`Booking marked as ${newStatus}`);
          await this.loadAllData();
          this.renderCurrentTab();
        } catch (e) {
          showToast(e.message, "error");
        }
      });
    });

    container.querySelectorAll(".btn-view-booking-detail").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const b = this.bookings.find(item => item.id === id);
        if (b) this.openBookingDetailModal(b);
      });
    });

    container.querySelectorAll(".btn-cancel-booking").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const b = this.bookings.find(item => item.id === id);
        this.showConfirmDialog("Cancel Appointment", `Are you sure you want to cancel booking ${b ? b.booking_code : "#" + id}? It will keep the slot blocked until you delete or clear it.`, async () => {
          try {
            await apiFetch(`/api/bookings/${id}/status`, {
              method: "PATCH",
              body: { status: "cancelled" }
            });
            showToast("Booking cancelled.");
            await this.loadAllData();
            this.renderCurrentTab();
          } catch (e) {
            showToast(e.message, "error");
          }
        });
      });
    });

    container.querySelectorAll(".btn-delete-booking").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const b = this.bookings.find(item => item.id === id);
        if (b) this.confirmPermanentDeleteBooking(b);
      });
    });
  }

  confirmPermanentDeleteBooking(b) {
    const root = document.getElementById("admin-modal-root");
    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-sm bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="text-center mb-4">
            <span class="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center text-xl mx-auto mb-2">🗑</span>
            <h4 class="font-serif font-bold text-slate-900 text-base">Delete Booking</h4>
            <p class="text-xs text-slate-500 mt-1">Are you sure you want to permanently delete this booking?</p>
            <p class="text-[10px] text-slate-400 mt-2 font-mono">${escapeHtml(b.booking_code)} — ${formatDatePretty(b.appointment_date)} at ${formatTimeDisplay(b.appointment_time)}</p>
          </div>
          <div class="flex gap-3 pt-2">
            <button id="confirm-cancel-btn" class="btn-secondary flex-1 py-2.5 rounded-xl text-xs font-bold">Cancel</button>
            <button id="confirm-delete-btn" class="bg-rose-600 hover:bg-rose-700 text-white flex-1 py-2.5 rounded-xl text-xs font-bold shadow-sm">Delete Booking</button>
          </div>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#confirm-cancel-btn").addEventListener("click", close);
    root.querySelector("#confirm-delete-btn").addEventListener("click", async () => {
      close();
      try {
        await apiFetch(`/api/bookings/${b.id}`, { method: "DELETE" });
        showToast(`Booking ${b.booking_code} permanently deleted.`);
        await this.loadAllData();
        this.renderCurrentTab();
      } catch (e) {
        showToast(e.message, "error");
      }
    });
  }

  getStatusBadge(status) {
    const map = {
      pending: "bg-amber-100 text-amber-800",
      confirmed: "bg-emerald-100 text-emerald-800",
      completed: "bg-indigo-100 text-indigo-800",
      cancelled: "bg-rose-100 text-rose-800",
      no_show: "bg-slate-100 text-slate-800"
    };
    const cls = map[status] || "bg-slate-100 text-slate-800";
    return `<span class="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${cls}">${status.replace('_', ' ')}</span>`;
  }

  // --- Calendar Grid Renderer ---
  renderCalendar() {
    const grid = document.getElementById("admin-calendar-grid");
    const monthLbl = document.getElementById("cal-current-month-lbl");
    if (!grid || !monthLbl) return;

    const year = this.calCurrentDate.getFullYear();
    const month = this.calCurrentDate.getMonth();

    monthLbl.innerText = new Date(year, month, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });

    const firstDayIndex = new Date(year, month, 1).getDay();
    const totalDays = new Date(year, month + 1, 0).getDate();

    let html = "";
    const daysHeaders = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    daysHeaders.forEach(dh => {
      html += `<div class="text-center text-[10px] font-extrabold text-slate-400 py-1 uppercase tracking-wider">${dh}</div>`;
    });

    for (let i = 0; i < firstDayIndex; i++) {
      html += `<div class="h-22 bg-slate-50/50 rounded-xl border border-slate-100"></div>`;
    }

    const todayStr = new Date().toISOString().split('T')[0];

    for (let day = 1; day <= totalDays; day++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const isToday = dateStr === todayStr;
      const dayBookings = this.bookings.filter(b => b.appointment_date === dateStr && b.status !== 'cancelled');

      html += `
        <div data-date="${dateStr}" class="cal-day-cell h-24 p-2 bg-white rounded-xl border ${isToday ? 'border-pink-500 ring-2 ring-pink-500/20' : 'border-slate-200'} hover:border-pink-400 cursor-pointer flex flex-col justify-between transition group shadow-2xs">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold ${isToday ? 'text-pink-700' : 'text-slate-800'}">${day}</span>
            ${dayBookings.length > 0 ? `<span class="w-4.5 h-4.5 rounded-full bg-pink-600 text-white flex items-center justify-center text-[9px] font-bold shadow-xs">${dayBookings.length}</span>` : ''}
          </div>
          <div class="space-y-0.5 overflow-hidden">
            ${dayBookings.slice(0, 2).map(b => `
              <div class="text-[9px] font-semibold bg-pink-50 text-pink-900 px-1.5 py-0.5 rounded truncate">
                ${formatTimeDisplay(b.appointment_time)} ${escapeHtml(b.customer_name)}
              </div>
            `).join('')}
            ${dayBookings.length > 2 ? `<div class="text-[8px] text-slate-400 font-bold">+${dayBookings.length - 2} more</div>` : ''}
          </div>
        </div>
      `;
    }

    grid.innerHTML = html;

    grid.querySelectorAll(".cal-day-cell").forEach(cell => {
      cell.addEventListener("click", () => {
        const d = cell.dataset.date;
        document.getElementById("filter-booking-date").value = d;
        document.getElementById("btn-view-table").click();
      });
    });
  }

  // --- 3. SERVICES TAB ---
  async renderServicesTab() {
    this.services = await apiFetch("/api/services?include_inactive=true");
    this.categories = await apiFetch("/api/categories?include_inactive=true");
    const container = document.getElementById("admin-services-table-container");
    if (!container) return;

    const symbol = this.settings?.currency_symbol || "$";

    let html = `
      <table class="w-full text-left text-xs text-slate-600">
        <thead class="bg-slate-50 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-200">
          <tr>
            <th class="py-3 px-4">Service</th>
            <th class="py-3 px-4">Category</th>
            <th class="py-3 px-4">Nail Subcategory</th>
            <th class="py-3 px-4">Duration</th>
            <th class="py-3 px-4">Price</th>
            <th class="py-3 px-4">Discount</th>
            <th class="py-3 px-4">Active</th>
            <th class="py-3 px-4">Featured</th>
            <th class="py-3 px-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
    `;

    this.services.forEach(s => {
      const nailSubcatName = s.nail_subcategory_name ? escapeHtml(s.nail_subcategory_name) : '<span class="text-slate-300">—</span>';
      html += `
        <tr class="hover:bg-slate-50/80 transition">
          <td class="py-3 px-4">
            <div class="flex items-center gap-3">
              <div class="w-11 h-11 rounded-xl bg-pink-100 overflow-hidden flex-shrink-0 border border-pink-200/80">
                <img src="${s.image_url || ''}" alt="${escapeHtml(s.name)}" class="w-full h-full object-cover" />
              </div>
              <div>
                <div class="font-bold text-slate-900">${escapeHtml(s.name)}</div>
                <div class="text-[10px] text-slate-400 line-clamp-1">${escapeHtml(s.description || '')}</div>
              </div>
            </div>
          </td>
          <td class="py-3 px-4 font-bold text-pink-800">${escapeHtml(s.category_name || '')}</td>
          <td class="py-3 px-4 text-slate-700">${nailSubcatName}</td>
          <td class="py-3 px-4 font-mono font-medium">${formatDuration(s.duration_minutes)}</td>
          <td class="py-3 px-4 font-bold text-slate-900">${formatPrice(s.price, symbol)}</td>
          <td class="py-3 px-4">
            ${s.discount_price ? `<span class="text-pink-700 font-bold">${formatPrice(s.discount_price, symbol)}</span> (${s.discount_percent}% off)` : '<span class="text-slate-300">—</span>'}
          </td>
          <td class="py-3 px-4">
            <button data-id="${s.id}" data-active="${s.is_active ? '1' : '0'}" class="btn-toggle-service-active px-2.5 py-0.5 rounded-full text-[10px] font-bold ${s.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'}">
              ${s.is_active ? 'Active' : 'Hidden'}
            </button>
          </td>
          <td class="py-3 px-4">
            <button data-id="${s.id}" data-featured="${s.is_featured ? '1' : '0'}" class="btn-toggle-service-featured px-2.5 py-0.5 rounded-full text-[10px] font-bold ${s.is_featured ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-400'}">
              ${s.is_featured ? '★ Yes' : 'No'}
            </button>
          </td>
          <td class="py-3 px-4 text-right space-x-2">
            <button data-id="${s.id}" class="btn-edit-service text-pink-700 hover:text-pink-900 font-bold">Edit</button>
            <button data-id="${s.id}" class="btn-delete-service text-rose-600 hover:text-rose-800 font-bold">Delete</button>
          </td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;

    // Bindings
    container.querySelectorAll(".btn-edit-service").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const s = this.services.find(item => item.id === id);
        if (s) this.openServiceModal(s);
      });
    });

    container.querySelectorAll(".btn-delete-service").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        this.showConfirmDialog("Delete Service", "Are you sure you want to permanently delete this service?", async () => {
          try {
            await apiFetch(`/api/services/${id}`, { method: "DELETE" });
            showToast("Service deleted.");
            this.renderServicesTab();
          } catch (e) {
            showToast(e.message, "error");
          }
        });
      });
    });

    container.querySelectorAll(".btn-toggle-service-active").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = parseInt(btn.dataset.id);
        const current = btn.dataset.active === '1';
        try {
          await apiFetch(`/api/services/${id}`, {
            method: "PUT",
            body: { is_active: !current }
          });
          showToast("Service visibility updated.");
          this.renderServicesTab();
        } catch (e) {
          showToast(e.message, "error");
        }
      });
    });

    container.querySelectorAll(".btn-toggle-service-featured").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = parseInt(btn.dataset.id);
        const current = btn.dataset.featured === '1';
        try {
          await apiFetch(`/api/services/${id}`, {
            method: "PUT",
            body: { is_featured: !current }
          });
          showToast("Featured status updated.");
          this.renderServicesTab();
        } catch (e) {
          showToast(e.message, "error");
        }
      });
    });
  }

  

  // --- SUBCATEGORIES MANAGEMENT (GENERIC) ---
  async renderSubcategoriesTab() {
    const container = document.getElementById("tab-subcategories");
    if (!container) return;

    const subcategories = this.subcategories || [];

    let html = `
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-serif font-bold text-slate-900 text-base">Subcategories</h3>
          <button id="btn-add-subcategory" class="px-4 py-2 text-xs font-bold rounded-xl bg-pink-600 text-white hover:bg-pink-700 transition flex items-center gap-2">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            Add Subcategory
          </button>
        </div>
        <div id="subcategories-grid" class="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
    `;

    if (subcategories.length === 0) {
      html += `
        <div class="col-span-full py-12 text-center text-slate-400 text-xs font-serif italic border-2 border-dashed border-slate-200 rounded-2xl">
          No subcategories created yet. Click "Add Subcategory" to create your first one.
        </div>
      </div>
      `;
    } else {
      subcategories.forEach(sc => {
        const cat = this.categories.find(c => c.id === sc.category_id);
        const catName = cat ? cat.name : "Unknown";
        html += `
          <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:shadow-sm transition">
            <div class="flex items-start justify-between mb-3">
              <div>
                <h4 class="font-bold text-slate-800 text-sm">${escapeHtml(sc.name)}</h4>
                <p class="text-[10px] text-slate-400 font-medium mt-0.5">Category: ${escapeHtml(catName)}</p>
                <p class="text-[10px] text-slate-400 font-medium mt-0.5">ID: ${sc.id}</p>
              </div>
              <div class="flex items-center gap-1.5">
                <button data-id="${sc.id}" class="btn-edit-subcat p-1.5 rounded-lg text-slate-400 hover:text-pink-700 hover:bg-pink-50 transition" title="Edit">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button data-id="${sc.id}" class="btn-delete-subcat p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition" title="Delete">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>
            <div class="text-[10px] text-slate-500 font-medium uppercase tracking-wider">${escapeHtml(sc.slug)}</div>
            ${sc.description ? '<div class="mt-2 text-xs text-slate-600 line-clamp-2">' + escapeHtml(sc.description) + '</div>' : ''}
          </div>
        `;
      });
      html += `
        </div>
      </div>
      `;
    }

    container.innerHTML = html;

    document.getElementById("btn-add-subcategory")?.addEventListener("click", () => this.openSubcategoryModal());
    container.querySelectorAll(".btn-edit-subcat").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const sc = subcategories.find(item => item.id === id);
        if (sc) this.openSubcategoryModal(sc);
      });
    });
    container.querySelectorAll(".btn-delete-subcat").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        this.showConfirmDialog("Delete Subcategory", "Are you sure you want to delete this subcategory? This action cannot be undone.", async () => {
          try {
            await apiFetch(`/api/subcategories/${id}`, { method: "DELETE" });
            showToast("Subcategory deleted.");
            this.subcategories = await apiFetch("/api/subcategories");
            this.renderSubcategoriesTab();
          } catch (e) {
            showToast(e.message, "error");
          }
        });
      });
    });
  }

  // --- CATEGORIES MANAGEMENT ---
  async renderCategoriesTab() {
    this.categories = await apiFetch("/api/categories?include_inactive=true");
    const container = document.getElementById("categories-container");
    if (!container) return;

    let html = `
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-serif font-bold text-slate-900 text-base">Service Categories</h3>
          <button id="btn-add-category" class="px-4 py-2 text-xs font-bold rounded-xl bg-pink-600 text-white hover:bg-pink-700 transition flex items-center gap-2">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            Add Category
          </button>
        </div>
        <div id="categories-grid" class="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
    `;

    if (this.categories.length === 0) {
      html += `
        <div class="col-span-full py-12 text-center text-slate-400 text-xs font-serif italic border-2 border-dashed border-slate-200 rounded-2xl">
          No categories created yet. Click "Add Category" to create your first one.
        </div>
      </div>
      `;
    } else {
      this.categories.forEach(cat => {
        const iconMap = {
          'sparkles': '✨', 'hand': '💅', 'eye': '👁️', 'heart': '❤️',
          'star': '⭐', 'flower': '🌸', 'leaf': '🍃', 'gem': '💎',
          'crown': '👑', 'magic': '🪄', 'scissors': '✂️', 'brush': '🖌️'
        };
        const icon = iconMap[cat.icon] || '✨';
        html += `
          <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:shadow-sm transition">
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-3">
                <span class="text-2xl">${icon}</span>
                <div>
                  <h4 class="font-bold text-slate-800 text-sm">${escapeHtml(cat.name)}</h4>
                  <p class="text-[10px] text-slate-400 font-medium mt-0.5">ID: ${cat.id}</p>
                </div>
              </div>
              <div class="flex items-center gap-1.5">
                <button data-id="${cat.id}" class="btn-edit-category p-1.5 rounded-lg text-slate-400 hover:text-pink-700 hover:bg-pink-50 transition" title="Edit">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button data-id="${cat.id}" class="btn-delete-category p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition" title="Delete">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>
            <div class="text-[10px] text-slate-500 font-medium uppercase tracking-wider">${escapeHtml(cat.slug)}</div>
            <div class="flex items-center gap-2 mt-2">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${cat.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'}">
                ${cat.is_active ? 'Active' : 'Inactive'}
              </span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-pink-100 text-pink-700">Order: ${cat.display_order || 0}</span>
            </div>
            ${cat.description ? '<div class="mt-2 text-xs text-slate-600 line-clamp-2">' + escapeHtml(cat.description) + '</div>' : ''}
          </div>
        `;
      });
      html += `
        </div>
      </div>
      `;
    }

    container.innerHTML = html;

    document.getElementById("btn-add-category")?.addEventListener("click", () => this.openCategoryModal());
    container.querySelectorAll(".btn-edit-category").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const cat = this.categories.find(item => item.id === id);
        if (cat) this.openCategoryModal(cat);
      });
    });
    container.querySelectorAll(".btn-delete-category").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        this.showConfirmDialog("Delete Category", "Are you sure you want to delete this category? Services in this category will become uncategorized. This action cannot be undone.", async () => {
          try {
            await apiFetch(`/api/categories/${id}`, { method: "DELETE" });
            showToast("Category deleted.");
            this.categories = await apiFetch("/api/categories?include_inactive=true");
            this.renderCategoriesTab();
            if (this.currentTab === "services") this.renderServicesTab();
          } catch (e) {
            showToast(e.message, "error");
          }
        });
      });
    });
  }

  openCategoryModal(existing = null) {
    const root = document.getElementById("admin-modal-root");
    const isEdit = !!existing;

    const iconOptions = [
      { value: "sparkles", label: "✨ Sparkles" },
      { value: "hand", label: "💅 Hand" },
      { value: "eye", label: "👁️ Eye" },
      { value: "heart", label: "❤️ Heart" },
      { value: "star", label: "⭐ Star" },
      { value: "flower", label: "🌸 Flower" },
      { value: "leaf", label: "🍃 Leaf" },
      { value: "gem", label: "💎 Gem" },
      { value: "crown", label: "👑 Crown" },
      { value: "magic", label: "🪄 Magic" },
      { value: "scissors", label: "✂️ Scissors" },
      { value: "brush", label: "🖌️ Brush" }
    ];

    let iconOptionsHtml = iconOptions.map(opt => `
      <option value="${opt.value}" ${existing && existing.icon === opt.value ? "selected" : ""}>${opt.label}</option>
    `).join("");

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-lg bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-lg">${isEdit ? "Edit Category" : "Add New Category"}</h4>
            <button id="close-cat-modal" class="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition">
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>

          <form id="category-form" class="space-y-4 pt-4">
            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Category Name</label>
              <input type="text" id="cat-name" value="${escapeHtml(existing?.name || "")}" required class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs" placeholder="e.g., Nails, Lashes, Facials" />
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Slug (URL-friendly)</label>
              <input type="text" id="cat-slug" value="${escapeHtml(existing?.slug || "")}" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs font-mono" placeholder="auto-generated from name" />
              <p class="text-[10px] text-slate-400 mt-1">Leave empty to auto-generate from name</p>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Description</label>
              <textarea id="cat-desc" rows="2" class="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs">${escapeHtml(existing?.description || "")}</textarea>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Display Order</label>
                <input type="number" id="cat-order" value="${existing?.display_order || 0}" min="0" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs font-mono" />
              </div>
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Icon</label>
                <select id="cat-icon" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs">
                  ${iconOptionsHtml}
                </select>
              </div>
            </div>

            <div class="flex items-center gap-6 pt-2">
              <label class="flex items-center gap-2 font-bold text-slate-700">
                <input type="checkbox" id="cat-active" ${existing ? (existing.is_active ? "checked" : "") : "checked"} class="w-4 h-4 text-pink-600 rounded" />
                <span>Active (show on public menu)</span>
              </label>
            </div>

            <div class="pt-4 border-t border-slate-100 flex justify-end gap-2">
              <button type="button" id="cancel-cat-btn" class="btn-secondary px-4 py-2 rounded-xl">Cancel</button>
              <button type="submit" class="btn-primary px-5 py-2 rounded-xl font-bold">
                ${isEdit ? "Save Changes" : "Create Category"}
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-cat-modal").addEventListener("click", close);
    root.querySelector("#cancel-cat-btn").addEventListener("click", close);

    // Auto-generate slug from name
    const nameInput = root.querySelector("#cat-name");
    const slugInput = root.querySelector("#cat-slug");
    nameInput.addEventListener("input", () => {
      if (!slugInput.dataset.manuallyEdited) {
        slugInput.value = nameInput.value.toLowerCase().trim().replace(/[\\s\\W-]+/g, "-").replace(/^-+|-+$/g, "");
      }
    });
    slugInput.addEventListener("input", () => {
      slugInput.dataset.manuallyEdited = "true";
    });

    root.querySelector("#category-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        name: root.querySelector("#cat-name").value.trim(),
        slug: root.querySelector("#cat-slug").value.trim() || undefined,
        description: root.querySelector("#cat-desc").value.trim() || undefined,
        display_order: parseInt(root.querySelector("#cat-order").value) || 0,
        icon: root.querySelector("#cat-icon").value,
        is_active: root.querySelector("#cat-active").checked
      };

      if (!payload.name) {
        showToast("Category name is required.", "error");
        return;
      }

      try {
        if (isEdit) {
          await apiFetch(`/api/categories/${existing.id}`, { method: "PUT", body: payload });
          showToast("Category updated!");
        } else {
          await apiFetch("/api/categories", { method: "POST", body: payload });
          showToast("Category created!");
        }
        close();
        this.categories = await apiFetch("/api/categories?include_inactive=true");
        this.renderCategoriesTab();
        if (this.currentTab === "services") this.renderServicesTab();
      } catch (err) {
        showToast(err.message || "Failed to save category", "error");
      }
    });
  }

// --- 4. OFFERS TAB ---
  async renderOffersTab() {
    this.offers = await apiFetch("/api/offers?include_inactive=true");
    const container = document.getElementById("admin-offers-table-container");
    if (!container) return;

    const symbol = this.settings?.currency_symbol || "$";

    let html = `
      <table class="w-full text-left text-xs text-slate-600">
        <thead class="bg-slate-50 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-200">
          <tr>
            <th class="py-3 px-4">Offer</th>
            <th class="py-3 px-4">Linked Service</th>
            <th class="py-3 px-4">Original Price</th>
            <th class="py-3 px-4">Discounted Price</th>
            <th class="py-3 px-4">Validity Range</th>
            <th class="py-3 px-4">Status</th>
            <th class="py-3 px-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
    `;

    this.offers.forEach(o => {
      html += `
        <tr class="hover:bg-slate-50/80 transition">
          <td class="py-3 px-4">
            <div class="font-bold text-slate-900">${escapeHtml(o.title)}</div>
            <div class="text-[10px] text-slate-400 line-clamp-1">${escapeHtml(o.description || '')}</div>
          </td>
          <td class="py-3 px-4 font-bold text-slate-700">${escapeHtml(o.service_name || 'Package')}</td>
          <td class="py-3 px-4 text-slate-400 line-through">${formatPrice(o.original_price, symbol)}</td>
          <td class="py-3 px-4 font-bold text-pink-700 font-serif text-sm">${formatPrice(o.discounted_price, symbol)} (${o.discount_percent}% off)</td>
          <td class="py-3 px-4 font-mono text-[11px]">${o.start_date} to ${o.end_date}</td>
          <td class="py-3 px-4">
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold ${o.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'}">
              ${o.is_active ? 'Active' : 'Inactive'}
            </span>
          </td>
          <td class="py-3 px-4 text-right space-x-2">
            <button data-id="${o.id}" class="btn-edit-offer text-pink-700 hover:text-pink-900 font-bold">Edit</button>
            <button data-id="${o.id}" class="btn-delete-offer text-rose-600 hover:text-rose-800 font-bold">Delete</button>
          </td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;

    container.querySelectorAll(".btn-edit-offer").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const o = this.offers.find(item => item.id === id);
        if (o) this.openOfferModal(o);
      });
    });

    container.querySelectorAll(".btn-delete-offer").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        this.showConfirmDialog("Delete Offer", "Are you sure you want to delete this special offer?", async () => {
          try {
            await apiFetch(`/api/offers/${id}`, { method: "DELETE" });
            showToast("Offer deleted.");
            this.renderOffersTab();
          } catch (e) {
            showToast(e.message, "error");
          }
        });
      });
    });
  }

  // --- 5. AVAILABILITY & HOURS TAB ---
  async renderAvailabilityTab() {
    const locSelect = document.getElementById("avail-location-select");
    if (locSelect && !locSelect._bound) {
      locSelect._bound = true;
      locSelect.innerHTML = `<option value="">All Locations (Global)</option>` +
        (this.locations || []).map(l => `<option value="${l.id}">${escapeHtml(l.name)}</option>`).join('');
      locSelect.value = this._selectedAvailLocId ?? "";
      locSelect.addEventListener("change", () => {
        this._selectedAvailLocId = locSelect.value || null;
        this.renderAvailabilityTab();
      });
    }
    const locationId = locSelect?.value || null;
    const qs = locationId ? `?location_id=${locationId}` : "";
    const config = await apiFetch(`/api/availability/config${qs}`);
    const bufferInput = document.getElementById("avail-buffer-input");
    if (bufferInput) bufferInput.value = config.schedule?.[0]?.buffer_minutes ?? 0;
    const bufferByDay = {};
    (config.schedule || []).forEach(d => { bufferByDay[d.day_of_week] = d.buffer_minutes ?? 0; });

    const saveBufferBtn = document.getElementById("btn-save-buffer");
    if (saveBufferBtn && !saveBufferBtn._bound) {
      saveBufferBtn._bound = true;
      saveBufferBtn.addEventListener("click", async () => {
        const val = parseInt(document.getElementById("avail-buffer-input").value) || 0;
        const locId = locSelect?.value || null;
        const q = locId ? `?location_id=${locId}` : "";
        try {
          await apiFetch(`/api/availability/config${q}`, { method: "PUT", body: { buffer_minutes: val } });
          showToast("Buffer saved.");
        } catch (e) {
          showToast(e.message, "error");
        }
      });
    }

    // 1. Weekly Schedule List
    const schedContainer = document.getElementById("admin-schedule-list");
    let schedHtml = "";
    config.schedule.forEach(s => {
      schedHtml += `
        <div class="p-3.5 rounded-2xl border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white shadow-2xs">
          <div class="flex items-center gap-3 w-36">
            <input type="checkbox" id="sched-open-${s.day_of_week}" ${s.is_open ? 'checked' : ''} class="w-4 h-4 rounded text-pink-600 focus:ring-pink-500" />
            <label for="sched-open-${s.day_of_week}" class="text-xs font-bold text-slate-800">${s.day_name}</label>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-400">Open:</span>
            <input type="time" id="sched-open-time-${s.day_of_week}" value="${s.open_time}" class="text-xs px-2.5 py-1 rounded-xl border border-slate-200 font-mono font-semibold" />
            <span class="text-xs text-slate-400">Close:</span>
            <input type="time" id="sched-close-time-${s.day_of_week}" value="${s.close_time}" class="text-xs px-2.5 py-1 rounded-xl border border-slate-200 font-mono font-semibold" />
            <span class="text-xs text-slate-400">Slot:</span>
            <select id="sched-interval-${s.day_of_week}" class="text-xs px-2 py-1.5 rounded-xl border border-slate-200 font-semibold bg-white">
              <option value="15" ${s.slot_interval_minutes === 15 ? 'selected' : ''}>15 min</option>
              <option value="30" ${s.slot_interval_minutes === 30 ? 'selected' : ''}>30 min</option>
              <option value="45" ${s.slot_interval_minutes === 45 ? 'selected' : ''}>45 min</option>
              <option value="60" ${s.slot_interval_minutes === 60 ? 'selected' : ''}>60 min</option>
            </select>
          </div>
          <button data-day="${s.day_of_week}" data-name="${s.day_name}" class="btn-save-day-sched btn-secondary px-3.5 py-1.5 rounded-xl text-xs font-bold">
            Save
          </button>
        </div>
      `;
    });
    schedContainer.innerHTML = schedHtml;

    schedContainer.querySelectorAll(".btn-save-day-sched").forEach(btn => {
      btn.addEventListener("click", async () => {
        const day = parseInt(btn.dataset.day);
        const name = btn.dataset.name;
        const isOpen = document.getElementById(`sched-open-${day}`).checked;
        const openTime = document.getElementById(`sched-open-time-${day}`).value;
        const closeTime = document.getElementById(`sched-close-time-${day}`).value;
        const slotInterval = parseInt(document.getElementById(`sched-interval-${day}`).value, 10);

        try {
          await apiFetch(`/api/availability/schedule/${day}${locSelect?.value ? `?location_id=${locSelect.value}` : ""}`, {
            method: "PUT",
            body: {
              day_of_week: day,
              day_name: name,
              is_open: isOpen,
              open_time: openTime,
              close_time: closeTime,
              slot_interval_minutes: slotInterval,
              buffer_minutes: bufferByDay[day] ?? 0
            }
          });
          showToast(`Saved schedule for ${name}`);
        } catch (e) {
          showToast(e.message, "error");
        }
      });
    });

    // 2. Closed Dates List
    const closedContainer = document.getElementById("admin-closed-dates-list");
    if (config.closed_dates.length === 0) {
      closedContainer.innerHTML = `<div class="text-slate-400 py-2">No specific holidays or closed dates set.</div>`;
    } else {
      closedContainer.innerHTML = config.closed_dates.map(c => `
        <div class="p-2.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-between">
          <div>
            <strong class="text-rose-900 font-mono">${c.closed_date}:</strong>
            <span class="text-rose-700 ml-1">${escapeHtml(c.reason)}</span>
          </div>
          <button data-id="${c.id}" class="btn-delete-closed-date text-rose-600 hover:text-rose-800 font-bold text-xs">✕</button>
        </div>
      `).join('');

      closedContainer.querySelectorAll(".btn-delete-closed-date").forEach(btn => {
        btn.addEventListener("click", async () => {
          const id = parseInt(btn.dataset.id);
          try {
            await apiFetch(`/api/availability/closed-dates/${id}`, { method: "DELETE" });
            showToast("Closed date removed.");
            this.renderAvailabilityTab();
          } catch (e) {
            showToast(e.message, "error");
          }
        });
      });
    }
  }

  // --- 6. GALLERY TAB ---
  async renderGalleryTab() {
    const images = await apiFetch("/api/gallery");
    const container = document.getElementById("admin-gallery-grid");
    if (!container) return;

    if (images.length === 0) {
      container.innerHTML = `<div class="col-span-full py-12 text-center text-slate-400 text-xs font-serif italic">No portfolio photos uploaded yet.</div>`;
      return;
    }

    let html = "";
    images.forEach(img => {
      html += `
        <div class="group relative rounded-2xl overflow-hidden border border-slate-200 shadow-xs bg-white">
          <div class="h-44 bg-slate-100 overflow-hidden">
            <img src="${img.image_url}" alt="${escapeHtml(img.title || '')}" class="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
          </div>
          <div class="p-3.5">
            <div class="text-[10px] text-pink-700 font-bold uppercase tracking-wider">${escapeHtml(img.category)}</div>
            <div class="font-bold text-slate-800 text-xs truncate">${escapeHtml(img.title || 'Atelier Shot')}</div>
            <div class="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-100">
              <span class="text-[10px] text-slate-400 font-semibold">${img.is_featured ? '★ Featured' : ''}</span>
              <div class="flex items-center gap-2">
                <button data-id="${img.id}" class="btn-edit-gallery-img text-pink-700 hover:text-pink-900 text-xs font-bold">Edit</button>
                <button data-id="${img.id}" class="btn-delete-gallery-img text-rose-600 hover:text-rose-800 text-xs font-bold">Delete</button>
              </div>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    container.querySelectorAll(".btn-delete-gallery-img").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        this.showConfirmDialog("Delete Photo", "Are you sure you want to remove this image from the portfolio?", async () => {
          try {
            await apiFetch(`/api/gallery/${id}`, { method: "DELETE" });
            showToast("Photo removed.");
            this.renderGalleryTab();
          } catch (e) {
            showToast(e.message, "error");
          }
        });
      });
    });

    container.querySelectorAll(".btn-edit-gallery-img").forEach(btn => {
      btn.addEventListener("click", () => {
        const image = images.find(item => item.id === parseInt(btn.dataset.id));
        if (image) this.openGalleryEditModal(image);
      });
    });
  }

  

  // --- GENERIC SUBCATEGORY MODAL ---
  openSubcategoryModal(existing = null) {
    const isEdit = !!existing;
    const root = document.getElementById("admin-modal-root");
    // Build category options for the subcategory's parent category
    let catOptions = this.categories.map(c => `
      <option value="${c.id}" ${existing && existing.category_id === c.id ? "selected" : ""}>${escapeHtml(c.name)}</option>
    `).join("");

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-base">${isEdit ? "Edit Subcategory" : "Add Subcategory"}</h4>
            <button id="close-subcat-modal" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 hover:text-slate-800">✕</button>
          </div>

          <form id="subcategory-form" class="py-4 space-y-3.5 text-xs">
            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Category *</label>
              <select id="subcat-category" required class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-pink-500 font-semibold">
                ${catOptions}
              </select>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Name *</label>
              <input type="text" id="subcat-name" required value="${escapeHtml(existing?.name || "")}" placeholder="e.g. Classic Manicure"
                class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-pink-500 font-semibold" />
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Slug</label>
              <input type="text" id="subcat-slug" value="${escapeHtml(existing?.slug || "")}" placeholder="e.g. classic-manicure"
                class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-pink-500 font-semibold" />
              <p class="text-[10px] text-slate-400 mt-1">URL-friendly identifier (lowercase, hyphens only)</p>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Description</label>
              <textarea id="subcat-description" rows="2" class="w-full px-3.5 py-2 rounded-xl border border-slate-200">${escapeHtml(existing?.description || "")}</textarea>
            </div>

            <div class="flex items-center gap-3 pt-2">
              <label class="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                <input type="checkbox" id="subcat-active" ${existing?.is_active ? "checked" : "checked"}>
                <span class="text-sm">Active</span>
              </label>
            </div>

            <div class="flex gap-2 pt-4 border-t border-slate-100">
              <button type="button" id="cancel-subcat-btn" class="flex-1 py-2.5 text-center text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition">Cancel</button>
              <button type="submit" class="flex-1 py-2.5 text-center text-xs font-bold bg-pink-600 hover:bg-pink-700 text-white rounded-xl transition">${isEdit ? "Save Changes" : "Create Subcategory"}</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-subcat-modal").addEventListener("click", close);
    root.querySelector("#cancel-subcat-btn").addEventListener("click", close);

    // Auto-generate slug from name while typing
    const nameEl = root.querySelector("#subcat-name");
    const slugEl = root.querySelector("#subcat-slug");
    nameEl.addEventListener("input", () => {
      const raw = nameEl.value.trim().toLowerCase();
      slugEl.value = raw.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    });

    root.querySelector("#subcategory-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        category_id: parseInt(root.querySelector("#subcat-category").value),
        name: root.querySelector("#subcat-name").value.trim(),
        slug: root.querySelector("#subcat-slug").value.trim().toLowerCase(),
        description: root.querySelector("#subcat-description").value.trim(),
        is_active: root.querySelector("#subcat-active").checked
      };

      try {
        if (isEdit) {
          await apiFetch(`/api/subcategories/${existing.id}`, { method: "PUT", body: payload });
          showToast("Subcategory updated!");
        } else {
          await apiFetch("/api/subcategories", { method: "POST", body: payload });
          showToast("Subcategory created!");
        }
        close();
        this.subcategories = await apiFetch("/api/subcategories");
        this.renderSubcategoriesTab();
        if (this.currentTab === "services") this.renderServicesTab();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

openGalleryEditModal(image) {
    const root = document.getElementById("admin-modal-root");
    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-base">Edit Portfolio Photo</h4>
            <button id="close-gallery-edit" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">✕</button>
          </div>
          <form id="gallery-edit-form" class="py-4 space-y-3 text-xs">
            <div>
              <label class="block font-bold text-slate-700 mb-1">Image URL</label>
              <input id="edit-gallery-url" required value="${escapeHtml(image.image_url || '')}" class="w-full px-3 py-2 rounded-xl border border-slate-200" />
            </div>
            <div>
              <label class="block font-bold text-slate-700 mb-1">Title</label>
              <input id="edit-gallery-title" value="${escapeHtml(image.title || '')}" class="w-full px-3 py-2 rounded-xl border border-slate-200" />
            </div>
            <div>
              <label class="block font-bold text-slate-700 mb-1">Category</label>
              <input id="edit-gallery-category" value="${escapeHtml(image.category || 'All')}" class="w-full px-3 py-2 rounded-xl border border-slate-200" />
            </div>
            <div>
              <label class="block font-bold text-slate-700 mb-1">Caption</label>
              <textarea id="edit-gallery-caption" rows="2" class="w-full px-3 py-2 rounded-xl border border-slate-200">${escapeHtml(image.caption || '')}</textarea>
            </div>
            <label class="flex items-center gap-2 font-bold text-slate-700">
              <input id="edit-gallery-featured" type="checkbox" ${image.is_featured ? 'checked' : ''} class="w-4 h-4 text-pink-600 rounded" />
              <span>Featured</span>
            </label>
            <div class="pt-3 border-t border-slate-100 flex justify-end gap-2">
              <button type="button" id="cancel-gallery-edit" class="btn-secondary px-4 py-2 rounded-xl">Cancel</button>
              <button type="submit" class="btn-primary px-4 py-2 rounded-xl font-bold">Save Changes</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-gallery-edit").addEventListener("click", close);
    root.querySelector("#cancel-gallery-edit").addEventListener("click", close);
    root.querySelector("#gallery-edit-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await apiFetch(`/api/gallery/${image.id}`, {
          method: "PUT",
          body: {
            image_url: root.querySelector("#edit-gallery-url").value.trim(),
            title: root.querySelector("#edit-gallery-title").value.trim(),
            category: root.querySelector("#edit-gallery-category").value.trim() || "All",
            caption: root.querySelector("#edit-gallery-caption").value.trim(),
            is_featured: root.querySelector("#edit-gallery-featured").checked
          }
        });
        showToast("Portfolio photo updated.");
        close();
        this.renderGalleryTab();
      } catch (error) {
        showToast(error.message || "Could not update photo.", "error");
      }
    });
  }

  // --- 7. SETTINGS TAB ---
  renderSettingsTab() {
    if (!this.settings) return;
    const s = this.settings;

    document.getElementById("set-salon-name").value = s.salon_name || "";
    document.getElementById("set-currency").value = s.currency_symbol || "$";
    document.getElementById("set-tagline").value = s.tagline || "";
    document.getElementById("set-description").value = s.description || "";
    document.getElementById("set-phone").value = s.phone || "";
    document.getElementById("set-whatsapp").value = s.whatsapp_number || "";
    document.getElementById("set-instagram").value = s.instagram_url || "";
    document.getElementById("set-tiktok").value = s.tiktok_url || "";
    document.getElementById("set-address").value = s.address || "";
    document.getElementById("set-hours").value = s.opening_hours_text || "";
    document.getElementById("set-announcement").value = s.announcement_text || "";
document.getElementById("set-homepage-welcome").value = s.homepage_welcome_text || "";
  }

  async saveSettings() {
    const payload = {
      salon_name: document.getElementById("set-salon-name").value.trim(),
      currency_symbol: document.getElementById("set-currency").value.trim(),
      tagline: document.getElementById("set-tagline").value.trim(),
      description: document.getElementById("set-description").value.trim(),
      phone: document.getElementById("set-phone").value.trim(),
      whatsapp_number: document.getElementById("set-whatsapp").value.trim(),
      instagram_url: document.getElementById("set-instagram").value.trim(),
      tiktok_url: document.getElementById("set-tiktok").value.trim(),
      address: document.getElementById("set-address").value.trim(),
      opening_hours_text: document.getElementById("set-hours").value.trim(),
      announcement_text: document.getElementById("set-announcement").value.trim(),
      homepage_welcome_text: document.getElementById("set-homepage-welcome").value.trim()
    };

    try {
      this.settings = await apiFetch("/api/settings", {
        method: "PUT",
        body: payload
      });
      showToast("Salon settings saved successfully!");
    } catch (e) {
      showToast(e.message, "error");
    }
  }

  async changePassword() {
    const oldP = document.getElementById("pwd-old").value;
    const newP = document.getElementById("pwd-new").value;
    const confP = document.getElementById("pwd-confirm").value;

    if (newP !== confP) {
      showToast("New passwords do not match.", "error");
      return;
    }
    if (newP.length < 6) {
      showToast("Password must be at least 6 characters.", "error");
      return;
    }

    try {
      await apiFetch("/api/auth/change-password", {
        method: "POST",
        body: { old_password: oldP, new_password: newP }
      });
      showToast("Admin password changed!");
      document.getElementById("admin-password-form").reset();
    } catch (e) {
      showToast(e.message, "error");
    }
  }

  // --- CUSTOM BRANDED CONFIRMATION DIALOG ---
  showConfirmDialog(title, message, onConfirm) {
    const root = document.getElementById("admin-modal-root");
    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-sm bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="text-center mb-4">
            <span class="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center text-xl mx-auto mb-2">⚠️</span>
            <h4 class="font-serif font-bold text-slate-900 text-base">${escapeHtml(title)}</h4>
            <p class="text-xs text-slate-500 mt-1">${escapeHtml(message)}</p>
          </div>
          <div class="flex gap-3 pt-2">
            <button id="confirm-cancel-btn" class="btn-secondary flex-1 py-2.5 rounded-xl text-xs font-bold">No, Cancel</button>
            <button id="confirm-ok-btn" class="bg-rose-600 hover:bg-rose-700 text-white flex-1 py-2.5 rounded-xl text-xs font-bold shadow-sm">Yes, Proceed</button>
          </div>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#confirm-cancel-btn").addEventListener("click", close);
    root.querySelector("#confirm-ok-btn").addEventListener("click", () => {
      close();
      onConfirm();
    });
  }

  // --- SERVICE MODAL ---
  openServiceModal(existing = null) {
    const root = document.getElementById("admin-modal-root");
    const isEdit = !!existing;

    let catOptions = this.categories.map(c => `
      <option value="${c.id}" ${existing && existing.category_id === c.id ? "selected" : ""}>
      <option value="${c.id}" ${existing && existing.category_id === c.id ? 'selected' : ''}>${escapeHtml(c.name)}</option>
    `).join('');

    // Build generic subcategory options (all)
    let subcatOptionsAll = '<option value="">-- Select Subcategory (optional) --</option>' + (this.subcategories || []).map(sc => `
      <option value="${sc.id}" data-category="${sc.category_id}" ${existing && existing.subcategory_id === sc.id ? 'selected' : ''}>${escapeHtml(sc.name)}</option>
    `).join('');

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-lg bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-base">${isEdit ? 'Edit Treatment' : 'Add New Treatment'}</h4>
            <button id="close-srv-modal" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 hover:text-slate-800">✕</button>
          </div>

          <form id="service-form" class="py-4 space-y-3.5 text-xs">
            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Treatment Name *</label>
              <input type="text" id="srv-name" required value="${escapeHtml(existing?.name || '')}" placeholder="e.g. Russian Manicure"
                class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-pink-500 font-semibold" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Category *</label>
                <select id="srv-category" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold">
                  ${catOptions}
                </select>
              </div>
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Duration (minutes) *</label>
                <input type="number" id="srv-duration" required min="10" step="5" value="${existing?.duration_minutes || 60}"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
              </div>
            </div>

            <!-- Subcategory (optional) -->
            <div id="subcategory-field" class="grid grid-cols-2 gap-3">
              <div class="col-span-2">
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Subcategory (optional)</label>
                <select id="srv-subcategory" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold">
                  ${subcatOptionsAll}
                </select>
                <p class="text-xs text-slate-500 mt-1">Optional: Choose a subcategory for this treatment</p>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Regular Price ($) *</label>
                <input type="number" id="srv-price" required step="0.5" min="0" value="${existing?.price || 35}"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
              </div>
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Discount Price ($) <span class="text-slate-400 font-normal">Optional</span></label>
                <input type="number" id="srv-discount" step="0.5" min="0" value="${existing?.discount_price || ''}" placeholder="None"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
              </div>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Description</label>
              <textarea id="srv-desc" rows="2" class="w-full px-3.5 py-2 rounded-xl border border-slate-200">${escapeHtml(existing?.description || '')}</textarea>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Photo (Upload or URL)</label>
              <div class="flex gap-2">
                <input type="text" id="srv-image" value="${escapeHtml(existing?.image_url || '')}" placeholder="/static/images/... or https://"
                  class="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-xs" />
                <label class="btn-secondary px-3.5 py-2 rounded-xl cursor-pointer text-xs font-bold flex items-center gap-1">
                  <span>Upload</span>
                  <input type="file" id="srv-file-input" accept="image/*" class="hidden" />
                </label>
              </div>
            </div>

            <div class="flex items-center gap-6 pt-2">
              <label class="flex items-center gap-2 font-bold text-slate-700">
                <input type="checkbox" id="srv-active" ${existing ? (existing.is_active ? 'checked' : '') : 'checked'} class="w-4 h-4 text-pink-600 rounded" />
                <span>Active on Public Menu</span>
              </label>
              <label class="flex items-center gap-2 font-bold text-slate-700">
                <input type="checkbox" id="srv-featured" ${existing && existing.is_featured ? 'checked' : ''} class="w-4 h-4 text-pink-600 rounded" />
                <span>Featured Signature</span>
              </label>
            </div>

            <div class="pt-4 border-t border-slate-100 flex justify-end gap-2">
              <button type="button" id="cancel-srv-btn" class="btn-secondary px-4 py-2 rounded-xl">Cancel</button>
              <button type="submit" class="btn-primary px-5 py-2 rounded-xl font-bold">
                ${isEdit ? 'Save Changes' : 'Create Treatment'}
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-srv-modal").addEventListener("click", close);
    root.querySelector("#cancel-srv-btn").addEventListener("click", close);

    // Filter subcategory options based on selected category
    const categorySelect = root.querySelector("#srv-category");
    const subcatSelect = root.querySelector("#srv-subcategory");
    if (categorySelect && subcatSelect) {
      const filterOptions = () => {
        const selectedCatId = parseInt(categorySelect.value);
        Array.from(subcatSelect.options).forEach(opt => {
          if (opt.value === "") return; // keep placeholder
          const catId = parseInt(opt.dataset.category);
          opt.style.display = catId === selectedCatId ? "" : "none";
        });
        // Reset selection if current not matching
        const currentVal = subcatSelect.value;
        if (currentVal) {
          const currentOpt = subcatSelect.querySelector(`option[value="${currentVal}"]`);
          if (currentOpt && currentOpt.style.display === "none") {
            subcatSelect.value = "";
          }
        }
      };
      categorySelect.addEventListener("change", filterOptions);
      // Initial filter
      filterOptions();
    }

    const fileInput = root.querySelector("#srv-file-input");
    fileInput.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("file", file);
      try {
        const uploadRes = await apiFetch("/api/upload", { method: "POST", body: formData });
        root.querySelector("#srv-image").value = uploadRes.url;
        showToast("Photo uploaded successfully!");
      } catch (err) {
        showToast(err.message || "Failed to upload", "error");
      }
    });

    root.querySelector("#service-form").addEventListener("submit", async (e) => {
      console.log("SERVICE FORM SUBMIT FIRED");
      e.preventDefault();
      const discVal = root.querySelector("#srv-discount").value;
      const payload = {
        category_id: parseInt(root.querySelector("#srv-category").value),
        name: root.querySelector("#srv-name").value.trim(),
        duration_minutes: parseInt(root.querySelector("#srv-duration").value),
        price: parseFloat(root.querySelector("#srv-price").value),
        discount_price: discVal && parseFloat(discVal) > 0 ? parseFloat(discVal) : 0,
        description: root.querySelector("#srv-desc").value.trim(),
        image_url: root.querySelector("#srv-image").value.trim(),
        is_active: root.querySelector("#srv-active").checked,
        is_featured: root.querySelector("#srv-featured").checked,
        subcategory_id: root.querySelector("#srv-subcategory")?.value ? parseInt(root.querySelector("#srv-subcategory").value) : null
      };

      console.log("SENDING POST /api/services", payload);
      try {
        if (isEdit) {
          await apiFetch(`/api/services/${existing.id}`, { method: "PUT", body: payload });
          showToast("Treatment updated!");
        } else {
          await apiFetch("/api/services", { method: "POST", body: payload });
          showToast("New treatment added!");
        }
        close();
        await this.loadAllData();
        this.renderServicesTab();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // --- SPECIAL OFFER MODAL ---
  openOfferModal(existing = null) {
    const root = document.getElementById("admin-modal-root");
    const isEdit = !!existing;

    let srvOptions = `<option value="">No linked service (Atelier Bundle)</option>` + this.services.map(s => `
      <option value="${s.id}" ${existing && existing.service_id === s.id ? 'selected' : ''}>${escapeHtml(s.name)}</option>
    `).join('');

    const todayStr = new Date().toISOString().split('T')[0];

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-lg bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-base">${isEdit ? 'Edit Special Offer' : 'Create Special Offer'}</h4>
            <button id="close-off-modal" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 hover:text-slate-800">✕</button>
          </div>

          <form id="offer-form" class="py-4 space-y-3.5 text-xs">
            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Offer Title *</label>
              <input type="text" id="off-title" required value="${escapeHtml(existing?.title || '')}" placeholder="e.g. Blossom Glow Duo"
                class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-pink-500 font-semibold" />
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Linked Service</label>
              <select id="off-service" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold">
                ${srvOptions}
              </select>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Duration (minutes) *</label>
              <input type="number" id="off-duration" required min="5" step="5" value="${existing?.duration_minutes || 60}"
                class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Original Price ($) *</label>
                <input type="number" id="off-orig-price" required step="0.5" min="0" value="${existing?.original_price || 100}"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
              </div>
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Discounted Price ($) *</label>
                <input type="number" id="off-disc-price" required step="0.5" min="0" value="${existing?.discounted_price || 75}"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Start Date *</label>
                <input type="date" id="off-start" required value="${existing?.start_date || todayStr}"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono font-semibold" />
              </div>
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">End Date (Countdown Target) *</label>
                <input type="date" id="off-end" required value="${existing?.end_date || '2027-12-31'}"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono font-semibold" />
              </div>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Description</label>
              <textarea id="off-desc" rows="2" class="w-full px-3.5 py-2 rounded-xl border border-slate-200">${escapeHtml(existing?.description || '')}</textarea>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Photo URL</label>
              <div class="flex gap-2">
                <input type="text" id="off-image" value="${escapeHtml(existing?.image_url || '')}" placeholder="/static/images/..."
                  class="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-xs" />
                <label class="btn-secondary px-3.5 py-2 rounded-xl cursor-pointer font-bold">
                  <span>Upload</span>
                  <input type="file" id="off-file-input" accept="image/*" class="hidden" />
                </label>
              </div>
            </div>

            <div class="flex items-center gap-6 pt-2">
              <label class="flex items-center gap-2 font-bold text-slate-700">
                <input type="checkbox" id="off-active" ${existing ? (existing.is_active ? 'checked' : '') : 'checked'} class="w-4 h-4 text-pink-600 rounded" />
                <span>Active Promo</span>
              </label>
              <label class="flex items-center gap-2 font-bold text-slate-700">
                <input type="checkbox" id="off-featured" ${existing && existing.is_featured ? 'checked' : ''} class="w-4 h-4 text-pink-600 rounded" />
                <span>Featured on Home</span>
              </label>
            </div>

            <div class="pt-4 border-t border-slate-100 flex justify-end gap-2">
              <button type="button" id="cancel-off-btn" class="btn-secondary px-4 py-2 rounded-xl">Cancel</button>
              <button type="submit" class="btn-primary px-5 py-2 rounded-xl font-bold">
                ${isEdit ? 'Save Changes' : 'Publish Offer'}
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-off-modal").addEventListener("click", close);
    root.querySelector("#cancel-off-btn").addEventListener("click", close);

    const fileInput = root.querySelector("#off-file-input");
    fileInput.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("file", file);
      try {
        const uploadRes = await apiFetch("/api/upload", { method: "POST", body: formData });
        root.querySelector("#off-image").value = uploadRes.url;
        showToast("Photo uploaded!");
      } catch (err) {
        showToast(err.message, "error");
      }
    });

    root.querySelector("#offer-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const srvIdVal = root.querySelector("#off-service").value;
      const payload = {
        title: root.querySelector("#off-title").value.trim(),
        service_id: srvIdVal ? parseInt(srvIdVal) : null,
        original_price: parseFloat(root.querySelector("#off-orig-price").value),
        discounted_price: parseFloat(root.querySelector("#off-disc-price").value),
        start_date: root.querySelector("#off-start").value,
        end_date: root.querySelector("#off-end").value,
        description: root.querySelector("#off-desc").value.trim(),
        image_url: root.querySelector("#off-image").value.trim() || null,
        is_active: root.querySelector("#off-active").checked,
        is_featured: root.querySelector("#off-featured").checked,
        duration_minutes: parseInt(root.querySelector("#off-duration").value)
      };

      try {
        if (isEdit) {
          await apiFetch(`/api/offers/${existing.id}`, { method: "PUT", body: payload });
          showToast("Offer updated!");
        } else {
          await apiFetch("/api/offers", { method: "POST", body: payload });
          showToast("New offer published!");
        }
        close();
        await this.loadAllData();
        this.renderOffersTab();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // --- PENDING BOOKINGS HELPERS ---
  updatePendingBadge() {
    const count = this.bookings.filter(b => b.status === 'pending').length;
    const badge = document.getElementById('pending-bookings-badge');
    if (badge) {
      badge.textContent = count;
      if (count > 0) badge.classList.remove('hidden');
      else badge.classList.add('hidden');
    }
  }

  showPendingNotification() {
    const count = this.bookings.filter(b => b.status === 'pending').length;
    if (count > 0) {
      showToast(`🔔 New Booking Request\nYou have ${count} pending booking${count > 1 ? 's' : ''} waiting for approval.`, 'info');
    }
  }

  async confirmBooking(id) {
    try {
      await apiFetch(`/api/bookings/${id}/status`, {
        method: 'PATCH',
        body: { status: 'confirmed' }
      });
      showToast('✓ Booking confirmed successfully.', 'success');
      await this.loadAllData();
      this.renderCurrentTab();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async rejectBooking(id) {
    try {
      await apiFetch(`/api/bookings/${id}/status`, {
        method: 'PATCH',
        body: { status: 'rejected' }
      });
      showToast('✓ Booking request rejected.', 'success');
      await this.loadAllData();
      this.renderCurrentTab();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  // --- BOOKING DETAIL MODAL ---
  openBookingDetailModal(b) {
    const root = document.getElementById("admin-modal-root");
    const symbol = this.settings?.currency_symbol || "$";
    const clientWa = b.customer_phone.replace(/[^0-9]/g, "");
    const directChatUrl = `https://wa.me/${clientWa}?text=${encodeURIComponent(`Hello ${b.customer_name}! 🌸 Regarding your appointment (#${b.booking_code}) at Blossom Dreams on ${b.appointment_date} at ${formatTimeDisplay(b.appointment_time)}...`)}`;

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h4 class="font-serif font-bold text-slate-900 text-base">Booking #${b.booking_code}</h4>
              <p class="text-[10px] text-pink-700 font-bold uppercase">Guest Profile & Details</p>
            </div>
            <button id="close-bdetail-modal" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 hover:text-slate-800">✕</button>
          </div>

          <div class="py-4 space-y-3.5 text-xs">
            <div class="flex justify-between items-center bg-slate-50 p-3.5 rounded-2xl border border-slate-100">
              <span class="text-slate-500 font-semibold">Status:</span>
              <span>${this.getStatusBadge(b.status)}</span>
            </div>

            <div class="space-y-2 border-b border-slate-100 pb-3">
              <div class="flex justify-between">
                <span class="text-slate-400">Treatment:</span>
                <strong class="text-slate-900">${escapeHtml(b.service_name)}</strong>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Location:</span>
                <strong class="text-slate-900">${escapeHtml(b.location_name || "—")}</strong>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Duration:</span>
                <span class="font-medium text-slate-800">${formatDuration(b.duration_minutes)}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Date & Time:</span>
                <strong class="text-pink-700 font-mono">${formatDatePretty(b.appointment_date)} at ${formatTimeDisplay(b.appointment_time)}</strong>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Total Price:</span>
                <strong class="text-slate-900 font-serif text-sm">${formatPrice(b.price, symbol)}</strong>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Booked On:</span>
                <span class="text-slate-600 font-mono">${formatDateTimePretty(b.created_at)}</span>
              </div>
            </div>

            <div class="space-y-2 border-b border-slate-100 pb-3">
              <div class="flex justify-between">
                <span class="text-slate-400">Guest Name:</span>
                <strong class="text-slate-900">${escapeHtml(b.customer_name)}</strong>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Phone:</span>
                <span class="font-mono font-bold text-slate-800">${escapeHtml(b.customer_phone)}</span>
              </div>
              ${b.customer_email ? `
                <div class="flex justify-between">
                  <span class="text-slate-400">Email:</span>
                  <span class="text-slate-700">${escapeHtml(b.customer_email)}</span>
                </div>
              ` : ''}
              ${b.notes ? `
                <div class="mt-2 p-3 bg-pink-50/60 rounded-xl text-pink-900 border border-pink-100">
                  <strong class="block mb-0.5 text-[10px] uppercase font-bold text-pink-700">Special Notes:</strong>
                  <span>${escapeHtml(b.notes)}</span>
                </div>
              ` : ''}
            </div>

            <div class="pt-2 space-y-2">
              <a href="${directChatUrl}" target="_blank" rel="noopener noreferrer"
                class="w-full py-3 rounded-2xl bg-[#25D366] hover:bg-[#20bd5a] text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition">
                <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.095 3.2 5.076 4.487.709.306 1.262.489 1.694.626.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg>
                <span>Direct WhatsApp Chat with Guest</span>
              </a>
              ${b.status === 'pending' ? `
                <button id="confirm-booking-detail-btn" class="w-full py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition">
                  <span>✔</span>
                  <span>Confirm Booking</span>
                </button>
                <button id="reject-booking-detail-btn" class="w-full py-3 rounded-2xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition">
                  <span>✖</span>
                  <span>Reject Booking</span>
                </button>
              ` : ''}
              <button id="delete-booking-detail-btn" class="w-full py-3 rounded-2xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition">
                <span>🗑</span>
                <span>Delete Booking</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    root.querySelector("#close-bdetail-modal").addEventListener("click", () => {
      root.innerHTML = "";
    });
    const confirmBtn = root.querySelector("#confirm-booking-detail-btn");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", () => this.confirmBooking(b.id));
    }
    const rejectBtn = root.querySelector("#reject-booking-detail-btn");
    if (rejectBtn) {
      rejectBtn.addEventListener("click", () => this.rejectBooking(b.id));
    }
    root.querySelector("#delete-booking-detail-btn").addEventListener("click", () => {
      this.confirmPermanentDeleteBooking(b);
    });
  }

  // --- MANUAL BOOKING MODAL ---
  openManualBookingModal() {
    const root = document.getElementById("admin-modal-root");
    const srvOptions = this.services.map(s => `<option value="${s.id}">${escapeHtml(s.name)} ($${s.price})</option>`).join('');
    const locOptions = (this.locations || []).map(l => `<option value="${l.id}">${escapeHtml(l.name)}</option>`).join('');
    const todayStr = new Date().toISOString().split('T')[0];

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-base">New Phone / Walk-in Booking</h4>
            <button id="close-manual-modal" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 hover:text-slate-800">✕</button>
          </div>

          <form id="manual-booking-form" class="py-4 space-y-3 text-xs">
            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Service *</label>
              <select id="man-service" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 font-semibold">
                ${srvOptions}
              </select>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Location</label>
              <select id="man-location" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 font-semibold">
                <option value="">No location (General)</option>
                ${locOptions}
              </select>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Date *</label>
                <input type="date" id="man-date" required value="${todayStr}" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono font-semibold" />
              </div>
              <div>
                <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Time (HH:MM) *</label>
                <input type="time" id="man-time" required value="10:00" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono font-semibold" />
              </div>
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Client Full Name *</label>
              <input type="text" id="man-name" required placeholder="e.g. Layla Khoury" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 font-semibold" />
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Client Phone Number *</label>
              <input type="tel" id="man-phone" required placeholder="+961..." class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 font-semibold" />
            </div>

            <div>
              <label class="block font-bold text-slate-700 uppercase tracking-wider mb-1">Notes</label>
              <textarea id="man-notes" rows="2" placeholder="Phone reservation / Walk-in" class="w-full px-3 py-2 rounded-xl border border-slate-200"></textarea>
            </div>

            <div class="pt-4 border-t border-slate-100 flex justify-end gap-2">
              <button type="button" id="cancel-manual-btn" class="btn-secondary px-4 py-2 rounded-xl">Cancel</button>
              <button type="submit" class="btn-primary px-5 py-2 rounded-xl font-bold">Reserve Slot</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-manual-modal").addEventListener("click", close);
    root.querySelector("#cancel-manual-btn").addEventListener("click", close);

    root.querySelector("#manual-booking-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        service_id: parseInt(root.querySelector("#man-service").value),
        appointment_date: root.querySelector("#man-date").value,
        appointment_time: root.querySelector("#man-time").value,
        location_id: parseInt(root.querySelector("#man-location").value) || null,
        customer_name: root.querySelector("#man-name").value.trim(),
        customer_phone: root.querySelector("#man-phone").value.trim(),
        notes: root.querySelector("#man-notes").value.trim() || "Manual phone reservation"
      };

      try {
        const b = await apiFetch("/api/bookings", {
          method: "POST",
          body: payload
        });
        showToast(`Manual booking reserved! Code: ${b.booking_code}`);
        close();
        await this.loadAllData();
        this.renderCurrentTab();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // --- CLOSED DATE MODALS ---
  openAddClosedDateModal() {
    const root = document.getElementById("admin-modal-root");
    const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split('T')[0];

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-sm bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-base">Add Holiday / Closed Date</h4>
            <button id="close-closed-modal" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">✕</button>
          </div>
          <form id="add-closed-form" class="py-4 space-y-3 text-xs">
            <div>
              <label class="block font-bold text-slate-700 mb-1">Closed Date *</label>
              <input type="date" id="cls-date" required value="${tomorrowStr}" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono font-semibold" />
            </div>
            <div>
              <label class="block font-bold text-slate-700 mb-1">Reason / Holiday Name *</label>
              <input type="text" id="cls-reason" required placeholder="e.g. National Holiday / Atelier Renovation" class="w-full px-3 py-2 rounded-xl border border-slate-200" />
            </div>
            <div class="pt-3 border-t border-slate-100 flex justify-end gap-2">
              <button type="submit" class="btn-primary px-4 py-2 rounded-xl font-bold">Save Closed Date</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-closed-modal").addEventListener("click", close);
    root.querySelector("#add-closed-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiFetch("/api/availability/closed-dates", {
          method: "POST",
          body: {
            closed_date: root.querySelector("#cls-date").value,
            reason: root.querySelector("#cls-reason").value.trim()
          }
        });
        showToast("Closed date added.");
        close();
        this.renderAvailabilityTab();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // --- GALLERY MODAL ---
  openAddGalleryModal() {
    const root = document.getElementById("admin-modal-root");

    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
        <div class="relative w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl modal-content-anim border border-slate-200">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-serif font-bold text-slate-900 text-base">Add Portfolio Photo</h4>
            <button id="close-gal-modal" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">✕</button>
          </div>
          <form id="add-gallery-form" class="py-4 space-y-3 text-xs">
            <div>
              <label class="block font-bold text-slate-700 mb-1">Image (File Upload or URL) *</label>
              <div class="flex gap-2">
                <input type="text" id="gal-url" required placeholder="/static/images/..." class="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-xs" />
                <label class="btn-secondary px-3.5 py-2 rounded-xl cursor-pointer font-bold">
                  <span>Upload</span>
                  <input type="file" id="gal-file-input" accept="image/*" class="hidden" />
                </label>
              </div>
            </div>
            <div>
              <label class="block font-bold text-slate-700 mb-1">Title</label>
              <input type="text" id="gal-title" placeholder="e.g. Russian Manicure with Chrome Pearls" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-bold text-slate-700 mb-1">Category</label>
                <input type="text" id="gal-category" value="Nails" class="w-full px-3 py-2 rounded-xl border border-slate-200 font-semibold" />
              </div>
              <div class="flex items-center pt-5">
                <label class="flex items-center gap-2 font-bold text-slate-700">
                  <input type="checkbox" id="gal-featured" class="w-4 h-4 text-pink-600 rounded" />
                  <span>Featured</span>
                </label>
              </div>
            </div>
            <div>
              <label class="block font-bold text-slate-700 mb-1">Caption</label>
              <textarea id="gal-caption" rows="2" placeholder="Brief note about the technique or shade" class="w-full px-3 py-2 rounded-xl border border-slate-200"></textarea>
            </div>
            <div class="pt-3 border-t border-slate-100 flex justify-end gap-2">
              <button type="submit" class="btn-primary px-4 py-2 rounded-xl font-bold">Add to Portfolio</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const close = () => { root.innerHTML = ""; };
    root.querySelector("#close-gal-modal").addEventListener("click", close);

    const fileInput = root.querySelector("#gal-file-input");
    fileInput.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("file", file);
      try {
        const uploadRes = await apiFetch("/api/upload", { method: "POST", body: formData });
        root.querySelector("#gal-url").value = uploadRes.url;
        showToast("Portfolio image uploaded!");
      } catch (err) {
        showToast(err.message, "error");
      }
    });

    root.querySelector("#add-gallery-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiFetch("/api/gallery", {
          method: "POST",
          body: {
            image_url: root.querySelector("#gal-url").value.trim(),
            title: root.querySelector("#gal-title").value.trim(),
            category: root.querySelector("#gal-category").value.trim(),
            caption: root.querySelector("#gal-caption").value.trim(),
            is_featured: root.querySelector("#gal-featured").checked
          }
        });
        showToast("Photo added to portfolio!");
        close();
        this.renderGalleryTab();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
}

// Instantiate on load
document.addEventListener("DOMContentLoaded", () => {
  const adminApp = new AdminApp();
  adminApp.init();
});





