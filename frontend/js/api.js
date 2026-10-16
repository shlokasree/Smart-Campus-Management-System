const API_BASE_URL = window.CAMPUSCARE_API_BASE_URL;

/* ================================
   GET TOKEN
================================ */

function getToken() {
    return localStorage.getItem("access_token");
}

/* ================================
   API REQUEST
================================ */

async function apiRequest(endpoint, options = {}) {

    const token = getToken();

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: headers
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {

            if (response.status === 401) {
                localStorage.removeItem("access_token");
                localStorage.removeItem("user");

                alert("Session expired. Please login again.");

                window.location.href = "login.html";
                return;
            }

            throw new Error(
                data.detail || "Something went wrong"
            );
        }

        return data;

    } catch (error) {

        console.error("API Error:", error);

        if (error.message === "Failed to fetch") {
            alert(
                "Unable to connect to CampusCare backend.\n\n" +
                "Make sure FastAPI is running on port 8000."
            );
        } else {
            alert(error.message);
        }

        throw error;
    }
}
