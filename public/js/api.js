// API Client & Utility Library for Blossom Dreams

const TOKEN_KEY = "blossom_admin_token";
const USER_KEY = "blossom_admin_user";

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token, user = null) {
  localStorage.setItem(TOKEN_KEY, token);
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getCurrentUser() {
  const userStr = localStorage.getItem(USER_KEY);
  try {
    return userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    return null;
  }
}

export async function apiFetch(endpoint, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};

  // Attach auth token if available
  const token = getAuthToken();
  console.log(`[apiFetch] ${options.method || 'GET'} ${endpoint} token present:`, !!token);
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  console.log(`[apiFetch] ${options.method || 'GET'} ${endpoint} Authorization header:`, headers["Authorization"] ? 'SET' : 'MISSING');

  // If body is an object and not FormData, stringify it
  if (options.body && !(options.body instanceof FormData) && typeof options.body === "object") {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(endpoint, {
      ...options,
      headers
    });

    // Handle HTTP errors
    if (!response.ok) {
      let errorDetail = `Request failed with status ${response.status}`;
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch (e) {
        // Not JSON
      }

      if (response.status === 401 && window.location.pathname.includes("/admin")) {
        // Unauthorized on admin page, clear credentials
        clearAuthToken();
      }

      const err = new Error(errorDetail);
      err.status = response.status;
      throw err;
    }

    // Parse JSON
    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// Toast Notification System - Professional reusable component
export function showToast(message, type = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = "pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg min-w-[280px] max-w-md animate-slide-in transform transition-all duration-300";
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "polite");

  const icons = {
    success: `<svg class="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`,
    error: `<svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`,
    warning: `<svg class="w-5 h-5 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`,
    info: `<svg class="w-5 h-5 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
  };

  const colors = {
    success: "bg-white border-l-4 border-emerald-500 text-slate-800",
    error: "bg-white border-l-4 border-red-500 text-slate-800",
    warning: "bg-white border-l-4 border-amber-500 text-slate-800",
    info: "bg-white border-l-4 border-blue-500 text-slate-800"
  };

  toast.className += ` ${colors[type] || colors.success}`;
  toast.innerHTML = `
    ${icons[type] || icons.success}
    <span class="text-sm font-medium flex-1">${escapeHtml(message)}</span>
    <button type="button" class="text-slate-400 hover:text-slate-600 flex-shrink-0 ml-2" aria-label="Dismiss">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
    </button>
  `;

  const dismissBtn = toast.querySelector("button");
  dismissBtn.addEventListener("click", () => dismissToast(toast));

  container.appendChild(toast);

  // Auto dismiss after 5s for success/info, 8s for error/warning
  const delay = (type === "error" || type === "warning") ? 8000 : 5000;
  setTimeout(() => dismissToast(toast), delay);
}

function dismissToast(toast) {
  toast.style.opacity = "0";
  toast.style.transform = "translateX(100%)";
  setTimeout(() => toast.remove(), 300);
}

// Add keyframe for slide-in animation (injected once)
if (!document.getElementById("toast-anim-style")) {
  const style = document.createElement("style");
  style.id = "toast-anim-style";
  style.textContent = `
    @keyframes slide-in {
      from { opacity: 0; transform: translateX(100%); }
      to { opacity: 1; transform: translateX(0); }
    }
    .animate-slide-in { animation: slide-in 0.3s cubic-bezier(0.16,1,0.3,1) forwards; }
  `;
  document.head.appendChild(style);
}

export function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function formatPrice(price, symbol = "$") {
  if (price === null || price === undefined) return "";
  const num = parseFloat(price);
  return `${symbol}${num.toFixed(0)}`;
}

export function formatDuration(minutes) {
  if (!minutes) return "";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return `${h}h ${m}m`;
  if (h > 0) return `${h} hr`;
  return `${m} mins`;
}

export function formatDatePretty(dateStr) {
  if (!dateStr) return "";
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric"
  });
}

// Convert a 24-hour "HH:MM" API value into a friendly 12-hour display string,
// e.g. "09:00" -> "9:00 AM", "13:30" -> "1:30 PM", "00:00" -> "12:00 AM".
// The internal database/API representation stays HH:MM; only the display changes.
export function formatTimeDisplay(hhmm) {
  if (!hhmm) return "";
  const parts = String(hhmm).split(":");
  const h = parseInt(parts[0], 10);
  const m = parts[1] ? parts[1].padStart(2, "0") : "00";
  if (Number.isNaN(h) || h < 0 || h > 23) return String(hhmm);
  const period = h >= 12 ? "PM" : "AM";
  let displayHour = h % 12;
  if (displayHour === 0) displayHour = 12;
  return `${displayHour}:${m} ${period}`;
}
