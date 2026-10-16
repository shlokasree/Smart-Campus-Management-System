
/* =====================================================
   CAMPUSCARE COMPLAINTS
   ===================================================== */

// Use the configured API URL, with a local fallback.
const COMPLAINTS_API_URL =
    (window.CAMPUSCARE_API_BASE_URL || "http://127.0.0.1:8000")
        .replace(/\/+$/, "");


/* =====================================================
   HELPER: FORMAT API ERRORS
   ===================================================== */

function getComplaintErrorMessage(data) {
    if (typeof data?.detail === "string") {
        return data.detail;
    }

    if (Array.isArray(data?.detail)) {
        return data.detail
            .map(item => item.msg || JSON.stringify(item))
            .join("\n");
    }

    if (data?.detail && typeof data.detail === "object") {
        return JSON.stringify(data.detail, null, 2);
    }

    if (typeof data?.message === "string") {
        return data.message;
    }

    return "An unexpected error occurred. Please try again.";
}


async function readApiResponse(response) {
    const text = await response.text();

    if (!text) {
        return {};
    }

    try {
        return JSON.parse(text);
    } catch {
        return { detail: text };
    }
}


/* =====================================================
   CHECK LOGIN
   ===================================================== */

function checkComplaintLogin() {
    const token = localStorage.getItem("access_token");
    const user = localStorage.getItem("user");

    if (!token || !user) {
        alert("Please login first.");
        window.location.href = "login.html";
        return false;
    }

    try {
        JSON.parse(user);
    } catch {
        localStorage.removeItem("user");
        localStorage.removeItem("access_token");

        alert("Your login session is invalid. Please login again.");
        window.location.href = "login.html";
        return false;
    }

    return true;
}


/* =====================================================
   LOAD USER DETAILS
   ===================================================== */

function loadUserDetails() {
    const userData = localStorage.getItem("user");

    if (!userData) {
        return;
    }

    try {
        const user = JSON.parse(userData);

        const studentName = document.getElementById("studentName");
        const email = document.getElementById("email");

        if (studentName && user.name) {
            studentName.value = user.name;
        }

        if (email && user.email) {
            email.value = user.email;
        }
    } catch (error) {
        console.error("User data error:", error);
    }
}


/* =====================================================
   SHOW FORM MESSAGE
   ===================================================== */


function showComplaintMessage(text, type = "error") {
    const messageElement =
        document.getElementById("message") ||
        document.getElementById("errorMessage") ||
        document.getElementById("formMessage");

    const safeMessage =
        typeof text === "string"
            ? text
            : text && typeof text === "object"
                ? JSON.stringify(text)
                : String(text ?? "Something went wrong.");

    if (messageElement) {
        messageElement.textContent = safeMessage;
        messageElement.style.display = "block";

        messageElement.classList.remove("error", "success");
        messageElement.classList.add(type);
        messageElement.setAttribute("role", "alert");
    } else {
        alert(safeMessage);
    }
}

/* =====================================================
   SUBMIT COMPLAINT
   POST /api/complaints
   ===================================================== */

async function submitComplaint(event) {
    event.preventDefault();

    if (!checkComplaintLogin()) {
        return;
    }

    const token = localStorage.getItem("access_token");

    const studentName =
        document.getElementById("studentName")?.value.trim() || "";

    const email =
        document.getElementById("email")?.value.trim() || "";

    const title =
        document.getElementById("issueTitle")?.value.trim() || "";

    const category =
        document.getElementById("issueCategory")?.value || "";

    const location =
        document.getElementById("location")?.value.trim() || "";

    const description =
        document.getElementById("description")?.value.trim() || "";

    const priority =
        document.getElementById("priority")?.value || "";

    // Validate required fields.
    if (!studentName) {
        showComplaintMessage("Please enter your name.");
        return;
    }

    if (!email) {
        showComplaintMessage("Please enter your email.");
        return;
    }

    if (!title) {
        showComplaintMessage("Please enter a complaint title.");
        return;
    }

    if (!category) {
        showComplaintMessage("Please select a complaint category.");
        return;
    }

    if (!location) {
        showComplaintMessage("Please enter the location.");
        return;
    }

    if (!description) {
        showComplaintMessage("Please describe the issue.");
        return;
    }

    if (!priority) {
        showComplaintMessage("Please select a priority.");
        return;
    }

    const complaintData = {
        student_name: studentName,
        email: email,
        title: title,
        category: category,
        location: location,
        description: description,
        priority: priority
    };

    const submitButton =
        document.querySelector(
            '#complaintForm button[type="submit"], ' +
            '#complaintForm input[type="submit"]'
        );

    const originalButtonText = submitButton
        ? (submitButton.tagName === "INPUT"
            ? submitButton.value
            : submitButton.textContent)
        : "";

    if (submitButton) {
        submitButton.disabled = true;

        if (submitButton.tagName === "INPUT") {
            submitButton.value = "Submitting...";
        } else {
            submitButton.textContent = "Submitting...";
        }
    }

    console.log("Submitting complaint:", complaintData);

    try {
        const response = await fetch(
            `${COMPLAINTS_API_URL}/api/complaints`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(complaintData)
            }
        );

        const data = await readApiResponse(response);

        console.log("Complaint API response:", response.status, data);

        if (response.status === 401) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("user");

            alert(
                "Your login session has expired. Please login again."
            );

            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            const errorMessage = getComplaintErrorMessage(data);

            console.error(
                "Complaint submission failed:",
                response.status,
                data
            );

            showComplaintMessage(
                `Error ${response.status}: ${errorMessage}`
            );
            return;
        }

        showComplaintMessage(
            "Complaint submitted successfully!",
            "success"
        );

        setTimeout(() => {
            window.location.href = "track-complaint.html";
        }, 800);

    } catch (error) {
        console.error("Complaint submission error:", error);

        showComplaintMessage(
            "Cannot connect to the CampusCare backend. " +
            "Check that FastAPI is running at " +
            COMPLAINTS_API_URL + " and that the API URL is correct."
        );

    } finally {
        if (submitButton) {
            submitButton.disabled = false;

            if (submitButton.tagName === "INPUT") {
                submitButton.value = originalButtonText;
            } else {
                submitButton.textContent = originalButtonText;
            }
        }
    }
}


/* =====================================================
   LOAD COMPLAINTS
   GET /api/complaints
   ===================================================== */

async function loadComplaints() {
    if (!checkComplaintLogin()) {
        return;
    }

    const token = localStorage.getItem("access_token");

    const container =
        document.getElementById("complaintsContainer");

    try {
        const response = await fetch(
            `${COMPLAINTS_API_URL}/api/complaints`,
            {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        const data = await readApiResponse(response);

        if (response.status === 401) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("user");

            alert("Please login again.");
            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            throw new Error(getComplaintErrorMessage(data));
        }

        // Support either a direct array or { complaints: [...] }.
        const complaints = Array.isArray(data)
            ? data
            : data.complaints;

        if (!Array.isArray(complaints)) {
            throw new Error(
                "The API response does not contain a complaints list."
            );
        }

        displayComplaints(complaints);

    } catch (error) {
        console.error("Loading complaints error:", error);

        if (container) {
            container.replaceChildren();

            const heading = document.createElement("h2");
            heading.textContent = "Unable to load complaints";

            const paragraph = document.createElement("p");
            paragraph.textContent = error.message;

            container.append(heading, paragraph);
        } else {
            showComplaintMessage(error.message);
        }
    }
}


/* =====================================================
   DISPLAY COMPLAINTS
   ===================================================== */

function escapeHTML(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}


function displayComplaints(complaints) {
    const container =
        document.getElementById("complaintsContainer");

    if (!container) {
        return;
    }

    container.replaceChildren();

    if (!complaints.length) {
        const wrapper = document.createElement("div");
        wrapper.className = "empty-complaints";

        const heading = document.createElement("h2");
        heading.textContent = "No complaints yet";

        const paragraph = document.createElement("p");
        paragraph.textContent =
            "You have not submitted any complaints yet.";

        const link = document.createElement("a");
        link.href = "complaint-form.html";
        link.className = "new-complaint-btn";
        link.textContent = "Report an Issue";

        wrapper.append(heading, paragraph, link);
        container.appendChild(wrapper);
        return;
    }

    complaints.forEach(complaint => {
        const card = document.createElement("div");
        card.className = "complaint-card";

        const header = document.createElement("div");
        header.className = "complaint-card-header";

        const titleArea = document.createElement("div");

        const heading = document.createElement("h2");
        heading.textContent = complaint.title ?? "Untitled complaint";

        const complaintId = document.createElement("div");
        complaintId.className = "complaint-id";
        complaintId.textContent =
            `Complaint ID: #CC-${complaint.complaint_id ?? "N/A"}`;

        titleArea.append(heading, complaintId);

        const status = document.createElement("span");
        status.className = "status-badge";
        status.textContent = complaint.status ?? "Pending";

        header.append(titleArea, status);

        const details = document.createElement("div");
        details.className = "complaint-details";

        [
            ["Category", complaint.category],
            ["Location", complaint.location],
            ["Priority", complaint.priority]
        ].forEach(([label, value]) => {
            const box = document.createElement("div");
            box.className = "detail-box";

            const labelElement = document.createElement("span");
            labelElement.className = "detail-label";
            labelElement.textContent = label;

            const valueElement = document.createElement("span");
            valueElement.className = "detail-value";
            valueElement.textContent = value ?? "N/A";

            box.append(labelElement, valueElement);
            details.appendChild(box);
        });

        const descriptionBox = document.createElement("div");
        descriptionBox.className = "complaint-description";

        const descriptionTitle = document.createElement("strong");
        descriptionTitle.textContent = "Description";

        const descriptionText = document.createElement("p");
        descriptionText.textContent =
            complaint.description ?? "No description provided.";

        descriptionBox.append(descriptionTitle, descriptionText);

        card.append(header, details, descriptionBox);
        container.appendChild(card);
    });
}


/* =====================================================
   PAGE START
   ===================================================== */

document.addEventListener("DOMContentLoaded", function () {
    loadUserDetails();

    const complaintForm =
        document.getElementById("complaintForm");

    if (complaintForm) {
        complaintForm.addEventListener(
            "submit",
            submitComplaint
        );
    }

    const complaintsContainer =
        document.getElementById("complaintsContainer");

    if (complaintsContainer) {
        loadComplaints();
    }
});
