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
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

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

// Toast Notification System
export function showToast(message, type = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = "toast-msg";

  const isSuccess = type === "success";
  const isError = type === "error";

  if (isSuccess) {
    toast.style.background = "#1E293B";
    toast.style.color = "#F8FAFC";
    toast.style.borderLeft = "4px solid #10B981";
    toast.innerHTML = `
      <span style="color:#10B981; font-size:1.2rem;">✓</span>
      <span>${escapeHtml(message)}</span>
    `;
  } else if (isError) {
    toast.style.background = "#1E293B";
    toast.style.color = "#F8FAFC";
    toast.style.borderLeft = "4px solid #EF4444";
    toast.innerHTML = `
      <span style="color:#EF4444; font-size:1.2rem;">✕</span>
      <span>${escapeHtml(message)}</span>
    `;
  } else {
    toast.style.background = "#1E293B";
    toast.style.color = "#F8FAFC";
    toast.style.borderLeft = "4px solid #F59E0B";
    toast.innerHTML = `
      <span style="color:#F59E0B; font-size:1.2rem;">ℹ</span>
      <span>${escapeHtml(message)}</span>
    `;
  }

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
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
