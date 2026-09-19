
(function () {
  "use strict";

  
  
  const PRODUCTION_API_BASE_URL = "";

  const isLocalHost =
    location.hostname === "127.0.0.1" ||
    location.hostname === "localhost" ||
    location.hostname === "";

  let apiBaseUrl = window.PREPLINE_API_BASE_URL || "";

  if (!apiBaseUrl) {
    if (isLocalHost) {
      apiBaseUrl = "http://127.0.0.1:8000";
    } else if (PRODUCTION_API_BASE_URL) {
      apiBaseUrl = PRODUCTION_API_BASE_URL;
    } else {
      apiBaseUrl = `${location.protocol}//${location.host}`;
    }
  }

  
  
  apiBaseUrl = apiBaseUrl.replace(/\/+$/, "");

  const wsProtocol = apiBaseUrl.startsWith("https://") ? "wss" : "ws";
  const wsBaseUrl = wsProtocol + "://" + apiBaseUrl.replace(/^https?:\/\//, "");

  window.API_BASE_URL = apiBaseUrl;
  window.WS_BASE_URL = wsBaseUrl;
})();
