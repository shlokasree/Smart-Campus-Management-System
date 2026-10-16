// ==========================================
// CampusCare - Staff Dashboard
// ==========================================

const STAFF_API_URL = window.CAMPUSCARE_API_BASE_URL;


// ==========================================
// Get logged-in user
// ==========================================

function getLoggedInUser() {
    try {
        const userData = localStorage.getItem("user");

        if (!userData) {
            return null;
        }

        return JSON.parse(userData);

    } catch (error) {
        console.error("Unable to read user data:", error);
        return null;
    }
}


// ==========================================
// Get authentication token
// ==========================================

function getStaffToken() {
    return localStorage.getItem("access_token");
}


// ==========================================
// Check staff login
// ==========================================

function checkStaffLogin() {

    const token = getStaffToken();
    const user = getLoggedInUser();

    if (!token || !user) {
        alert("Please login first.");
        window.location.href = "login.html";
        return false;
    }

    if (!["staff", "admin"].includes(user.role)) {
        alert("Staff access required.");
        window.location.href = "student-dashboard.html";
        return false;
    }

    return true;
}


// ==========================================
// Update staff name
// ==========================================

function displayStaffUser() {

    const user = getLoggedInUser();

    if (!user) {
        return;
    }

    const name = user.name || "Staff";

    const welcomeElement =
        document.getElementById("staffWelcomeName");

    const avatarElement =
        document.getElementById("staffAvatar");

    if (welcomeElement) {
        welcomeElement.textContent = name;
    }

    if (avatarElement) {
        avatarElement.textContent =
            name.charAt(0).toUpperCase();
    }
}


// ==========================================
// Load all staff complaints
// ==========================================

async function loadStaffComplaints() {

    if (!checkStaffLogin()) {
        return;
    }

    const token = getStaffToken();

    const container =
        document.getElementById("staffComplaintsContainer");

    if (!container) {
        console.error(
            "staffComplaintsContainer not found."
        );
        return;
    }

    container.innerHTML = `
        <div class="loading-message">
            <p>Loading complaints...</p>
        </div>
    `;

    try {

        const response = await fetch(
            `${STAFF_API_URL}/api/staff/complaints`,
            {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                }
            }
        );

        const data = await response.json().catch(() => ({}));

        console.log("Staff complaints response:", data);

        // -----------------------------
        // Unauthorized
        // -----------------------------

        if (response.status === 401) {

            alert("Your session has expired. Please login again.");

            localStorage.removeItem("access_token");
            localStorage.removeItem("user");

            window.location.href = "login.html";

            return;
        }


        // -----------------------------
        // Forbidden
        // -----------------------------

        if (response.status === 403) {

            container.innerHTML = `
                <div class="empty-state">
                    <h3>Access denied</h3>
                    <p>You do not have staff access.</p>
                </div>
            `;

            return;
        }


        // -----------------------------
        // Other errors
        // -----------------------------

        if (!response.ok) {

            throw new Error(
                data.detail || "Unable to load complaints."
            );
        }


        // -----------------------------
        // Get complaints
        // -----------------------------

        const complaints =
            Array.isArray(data)
                ? data
                : (data.complaints || []);


        console.log("Complaints:", complaints);


        // Update statistics
        updateStaffStatistics(complaints);


        // Display complaints
        displayStaffComplaints(complaints);

    } catch (error) {

        console.error(
            "Staff complaints error:",
            error
        );

        container.innerHTML = `
            <div class="empty-state">
                <h3>Unable to load complaints</h3>
                <p>
                    Please make sure the CampusCare backend
                    is running.
                </p>
            </div>
        `;
    }
}


// ==========================================
// Update dashboard statistics
// ==========================================

function updateStaffStatistics(complaints) {

    const totalElement =
        document.getElementById("totalComplaints");

    const progressElement =
        document.getElementById("inProgressComplaints");

    const pendingElement =
        document.getElementById("pendingComplaints");


    const total = complaints.length;


    const inProgress =
        complaints.filter(complaint => {

            const status =
                String(complaint.status || "")
                    .trim()
                    .toLowerCase();

            return (
                status === "in progress" ||
                status === "in_progress"
            );

        }).length;


    const pending =
        complaints.filter(complaint => {

            const status =
                String(complaint.status || "")
                    .trim()
                    .toLowerCase();

            return status === "pending";

        }).length;


    if (totalElement) {
        totalElement.textContent = total;
    }

    if (progressElement) {
        progressElement.textContent = inProgress;
    }

    if (pendingElement) {
        pendingElement.textContent = pending;
    }
}


// ==========================================
// Display complaints
// ==========================================

function displayStaffComplaints(complaints) {

    const container =
        document.getElementById("staffComplaintsContainer");

    if (!container) {
        return;
    }


    // No complaints
    if (!complaints || complaints.length === 0) {

        container.innerHTML = `
            <div class="empty-state">
                <h3>No complaints yet</h3>
                <p>
                    There are no complaints available
                    at the moment.
                </p>
            </div>
        `;

        return;
    }


    container.innerHTML = complaints.map(complaint => {

        const complaintId =
            complaint.complaint_id;

        const title =
            escapeHTML(complaint.title);

        const category =
            escapeHTML(complaint.category);

        const location =
            escapeHTML(complaint.location);

        const description =
            escapeHTML(complaint.description);

        const studentName =
            escapeHTML(
                complaint.student_name || "Student"
            );

        const status =
            String(
                complaint.status || "Pending"
            ).trim();


        const normalizedStatus =
            status.toLowerCase();


        let actionButton = "";


        // Pending → Start Work
        if (normalizedStatus === "pending" || normalizedStatus === "submitted") {

            actionButton = `
                <button
                    class="staff-action-button"
                    onclick="startComplaint(${complaintId})"
                >
                    Start Work
                </button>
            `;
        }


        // In Progress → Mark Resolved
        else if (
            normalizedStatus === "in progress" ||
            normalizedStatus === "in_progress"
        ) {

            actionButton = `
                <button
                    class="staff-action-button"
                    onclick="resolveComplaint(${complaintId})"
                >
                    Mark Resolved
                </button>
            `;
        }


        // Resolved
        else if (normalizedStatus === "resolved") {

            actionButton = `
                <span class="resolved-label">
                    Resolved
                </span>
            `;
        }


        return `
            <div class="staff-complaint-card">

                <div class="staff-complaint-content">

                    <h3>
                        ${title}
                    </h3>

                    <p class="complaint-meta">
                        #CC-${complaintId}
                        · ${category}
                        · Location: ${location}
                    </p>

                    <p class="complaint-description">
                        ${description}
                    </p>

                    <p class="complaint-reporter">
                        Reported by:
                        <strong>${studentName}</strong>
                    </p>

                </div>


                <div class="staff-complaint-actions">

                    <span class="
                        status-badge
                        ${getStatusClass(status)}
                    ">
                        ${escapeHTML(status)}
                    </span>

                    ${actionButton}

                </div>

            </div>
        `;

    }).join("");
}


// ==========================================
// Start complaint
// Pending → In Progress
// ==========================================

async function startComplaint(complaintId) {

    await updateComplaintStatus(
        complaintId,
        "In Progress"
    );
}


// ==========================================
// Resolve complaint
// In Progress → Resolved
// ==========================================

async function resolveComplaint(complaintId) {

    await updateComplaintStatus(
        complaintId,
        "Resolved"
    );
}


// ==========================================
// Update complaint status
// ==========================================

async function updateComplaintStatus(
    complaintId,
    newStatus
) {

    if (!checkStaffLogin()) {
        return;
    }

    const token = getStaffToken();


    try {

        const response = await fetch(
            `${STAFF_API_URL}/api/staff/complaints/${complaintId}/status`,
            {
                method: "PUT",

                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    status: newStatus
                })
            }
        );


        const data =
            await response.json().catch(() => ({}));


        console.log(
            "Status update response:",
            data
        );


        // -----------------------------
        // Unauthorized
        // -----------------------------

        if (response.status === 401) {

            alert(
                "Your session has expired. Please login again."
            );

            localStorage.removeItem("access_token");
            localStorage.removeItem("user");

            window.location.href = "login.html";

            return;
        }


        // -----------------------------
        // Error
        // -----------------------------

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to update complaint status."
            );
        }


        // -----------------------------
        // Success
        // -----------------------------

        alert(
            `Complaint status updated to ${newStatus}.`
        );


        // Reload complaints
        await loadStaffComplaints();

    } catch (error) {

        console.error(
            "Status update error:",
            error
        );

        alert(
            error.message ||
            "Unable to update complaint status."
        );
    }
}


// ==========================================
// Status CSS class
// ==========================================

function getStatusClass(status) {

    const normalized =
        String(status || "")
            .trim()
            .toLowerCase();


    if (normalized === "pending") {
        return "status-pending";
    }


    if (
        normalized === "in progress" ||
        normalized === "in_progress"
    ) {
        return "status-progress";
    }


    if (normalized === "resolved") {
        return "status-resolved";
    }


    return "status-pending";
}


// ==========================================
// HTML protection
// ==========================================

function escapeHTML(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value ?? "";

    return div.innerHTML;
}


// ==========================================
// Logout
// ==========================================

function logoutStaff() {

    localStorage.removeItem("access_token");
    localStorage.removeItem("user");

    window.location.href = "login.html";
}


// ==========================================
// Page initialization
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        if (!checkStaffLogin()) {
            return;
        }

        displayStaffUser();

        loadStaffComplaints();
    }
);
