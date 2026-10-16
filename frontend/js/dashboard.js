const DASHBOARD_API_URL = window.CAMPUSCARE_API_BASE_URL;


// ==========================================
// CHECK LOGIN
// ==========================================

function checkDashboardLogin() {

    const token = localStorage.getItem("access_token");
    const user = localStorage.getItem("user");

    if (!token || !user) {

        alert("Please login first.");

        window.location.href = "login.html";

        return false;
    }

    return true;
}


// ==========================================
// LOAD STUDENT DETAILS
// ==========================================

function loadStudentDetails() {

    const userData = localStorage.getItem("user");

    if (!userData) {
        return;
    }

    try {

        const user = JSON.parse(userData);

        console.log("Logged in user:", user);


        // Student name

        const studentName =
            document.getElementById("studentName");

        if (studentName && user.name) {

            studentName.textContent = user.name;

        }


        // Student avatar

        const studentAvatar =
            document.getElementById("studentAvatar");

        if (studentAvatar && user.name) {

            studentAvatar.textContent =
                user.name.charAt(0).toUpperCase();

        }

    } catch (error) {

        console.error(
            "User data error:",
            error
        );

    }
}


// ==========================================
// LOAD COMPLAINTS
// ==========================================

async function loadDashboardComplaints() {

    if (!checkDashboardLogin()) {
        return;
    }

    const token =
        localStorage.getItem("access_token");


    try {

        console.log("Loading complaints...");


        const response = await fetch(
            `${DASHBOARD_API_URL}/api/complaints`,
            {
                method: "GET",

                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );


        const data = await response.json();


        console.log(
            "Complaint API response:",
            data
        );


        // Unauthorized

        if (response.status === 401) {

            localStorage.removeItem("access_token");
            localStorage.removeItem("user");

            alert(
                "Your session has expired. Please login again."
            );

            window.location.href =
                "login.html";

            return;
        }


        // Other error

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to load complaints."
            );
        }


        const complaints =
            data.complaints || [];


        updateDashboardStatistics(
            complaints
        );


        displayRecentComplaints(
            complaints
        );


    } catch (error) {

        console.error(
            "Complaint loading error:",
            error
        );


        const container =
            document.getElementById(
                "recentComplaints"
            );


        if (container) {

            container.innerHTML = `
                <div class="empty-state">

                    <h3>Unable to load complaints</h3>

                    <p>
                        Please make sure the CampusCare
                        backend is running.
                    </p>

                </div>
            `;

        }
    }
}


// ==========================================
// UPDATE STATISTICS
// ==========================================

function updateDashboardStatistics(
    complaints
) {

    const total =
        complaints.length;


    const inProgress =
        complaints.filter(
            complaint =>
                String(complaint.status)
                    .toLowerCase()
                    .trim() === "in progress"
        ).length;


    const resolved =
        complaints.filter(
            complaint =>
                String(complaint.status)
                    .toLowerCase()
                    .trim() === "resolved"
        ).length;


    const totalElement =
        document.getElementById(
            "totalComplaints"
        );


    const progressElement =
        document.getElementById(
            "inProgressComplaints"
        );


    const resolvedElement =
        document.getElementById(
            "resolvedComplaints"
        );


    if (totalElement) {

        totalElement.textContent =
            total;

    }


    if (progressElement) {

        progressElement.textContent =
            inProgress;

    }


    if (resolvedElement) {

        resolvedElement.textContent =
            resolved;

    }
}


// ==========================================
// DISPLAY RECENT COMPLAINTS
// ==========================================

function displayRecentComplaints(
    complaints
) {

    const container =
        document.getElementById(
            "recentComplaints"
        );


    if (!container) {
        return;
    }


    // No complaints

    if (complaints.length === 0) {

        container.innerHTML = `
            <div class="empty-state">

                <h3>No complaints yet</h3>

                <p>
                    You have not submitted any complaints yet.
                </p>

                <a
                    href="complaint-form.html"
                    class="dashboard-button"
                >
                    Report an Issue
                </a>

            </div>
        `;

        return;
    }


    // Latest 5 complaints

    const recentComplaints =
        complaints.slice(0, 5);


    container.innerHTML =
        recentComplaints
            .map(
                complaint => `

                <div class="complaint-item">

                    <div class="complaint-info">

                        <h3>
                            ${escapeDashboardHTML(
                                complaint.title
                            )}
                        </h3>

                        <p>
                            #CC-${complaint.complaint_id}
                            ·
                            ${escapeDashboardHTML(
                                complaint.category
                            )}
                        </p>

                        <p>
                            ${escapeDashboardHTML(
                                complaint.location
                            )}
                        </p>

                    </div>

                    <span
                        class="status-badge ${getDashboardStatusClass(
                            complaint.status
                        )}"
                    >
                        ${escapeDashboardHTML(
                            complaint.status
                        )}
                    </span>

                </div>

            `
            )
            .join("");
}


// ==========================================
// STATUS CLASS
// ==========================================

function getDashboardStatusClass(status) {

    const value =
        String(status)
            .toLowerCase()
            .trim();


    if (value === "resolved") {

        return "status-resolved";

    }


    if (value === "in progress") {

        return "status-progress";

    }


    return "status-pending";
}


// ==========================================
// HTML SECURITY
// ==========================================

function escapeDashboardHTML(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value ?? "";

    return div.innerHTML;
}


// ==========================================
// START DASHBOARD
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log(
            "CampusCare dashboard loaded."
        );


        loadStudentDetails();

        loadDashboardComplaints();

    }
);
