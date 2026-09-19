
(() => {
  "use strict";

  const API_BASE_URL = window.API_BASE_URL || "";
  let firebaseAuth = null;
  let currentUser = null;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        existing.addEventListener("load", resolve, { once: true });
        existing.addEventListener("error", reject, { once: true });
        if (window.firebase) resolve();
        return;
      }

      const script = document.createElement("script");
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  async function init() {
    if (!API_BASE_URL) return false;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/config`);
      if (!response.ok) return false;
      const data = await response.json();

      if (!data.enabled || !data.config) {
        return false;
      }

      await loadScript(
        "https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js",
      );
      await loadScript(
        "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth-compat.js",
      );

      if (!window.firebase) return false;

      if (!window.firebase.apps.length) {
        window.firebase.initializeApp(data.config);
      }

      firebaseAuth = window.firebase.auth();
      firebaseAuth.onAuthStateChanged((user) => {
        currentUser = user || null;
        window.dispatchEvent(
          new CustomEvent("prepline-auth-changed", {
            detail: { user: currentUser },
          }),
        );
      });

      return true;
    } catch (error) {
      console.warn(
        "PREPLINE Firebase Auth unavailable; using anonymous mode.",
        error,
      );
      return false;
    }
  }

  window.preplineAuthReady = init();

  window.getPreplineAuthHeaders = async function () {
    await window.preplineAuthReady;

    if (!currentUser) return {};

    try {
      const token = await currentUser.getIdToken();
      return token ? { Authorization: `Bearer ${token}` } : {};
    } catch (error) {
      console.warn(
        "Could not get Firebase ID token; continuing anonymously.",
        error,
      );
      return {};
    }
  };

  window.preplineSignInWithGoogle = async function () {
    await window.preplineAuthReady;

    if (!firebaseAuth) {
      throw new Error(
        "Google sign-in is not configured yet. PREPLINE will continue in anonymous mode.",
      );
    }

    const provider = new window.firebase.auth.GoogleAuthProvider();
    return firebaseAuth.signInWithPopup(provider);
  };

  window.preplineSignOut = async function () {
    await window.preplineAuthReady;
    if (firebaseAuth) await firebaseAuth.signOut();
  };

  window.preplineFetch = async function (url, options = {}) {
    const authHeaders = await window.getPreplineAuthHeaders();
    const headers = new Headers(options.headers || {});

    Object.entries(authHeaders).forEach(([key, value]) => {
      headers.set(key, value);
    });

    return fetch(url, { ...options, headers });
  };
})();
