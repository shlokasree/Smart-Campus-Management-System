// Override these globals for custom hosting before this file is loaded.
const isLocalCampusCare = ["localhost", "127.0.0.1"].includes(location.hostname);
window.CAMPUSCARE_API_BASE_URL = window.CAMPUSCARE_API_BASE_URL ||
    (isLocalCampusCare ? "http://127.0.0.1:8000" : "https://campuscare-api.onrender.com");
window.CAMPUSCARE_ANALYTICS_BASE_URL = window.CAMPUSCARE_ANALYTICS_BASE_URL ||
    (isLocalCampusCare ? "http://127.0.0.1:5001" : "https://campuscare-analytics.onrender.com");
