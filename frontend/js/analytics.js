const ANALYTICS_BASE_URL = window.CAMPUSCARE_ANALYTICS_BASE_URL;

async function loadAnalytics() {
    try {
        const response = await fetch(
            `${ANALYTICS_BASE_URL}/analytics/summary`
        );

        if (!response.ok) {
            throw new Error("Analytics service unavailable");
        }

        const data = await response.json();

        console.log("CampusCare Analytics:", data);

        const total = document.getElementById("analytics-total");
        const pending = document.getElementById("analytics-pending");
        const inProgress = document.getElementById("analytics-progress");
        const resolved = document.getElementById("analytics-resolved");
        const rate = document.getElementById("analytics-rate");

        if (total) {
            total.textContent = data.total_complaints;
        }

        if (pending) {
            pending.textContent = data.pending;
        }

        if (inProgress) {
            inProgress.textContent = data.in_progress;
        }

        if (resolved) {
            resolved.textContent = data.resolved;
        }

        if (rate) {
            rate.textContent = `${data.resolution_rate}%`;
        }

    } catch (error) {
        console.error("Analytics error:", error);
    }
}

document.addEventListener("DOMContentLoaded", loadAnalytics);
