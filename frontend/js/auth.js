// CampusCare Authentication
// Keep only this authentication code in auth.js

window.API_BASE_URL = window.CAMPUSCARE_API_BASE_URL;

async function registerUser(event) {
    if (event) {
        event.preventDefault();
    }

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!name || !email || !password) {
        alert("Please fill all fields.");
        return;
    }

    try {
        const response = await fetch(
            `${window.API_BASE_URL}/api/auth/register`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    name: name,
                    email: email,
                    password: password
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            alert(data.detail || "Registration failed.");
            return;
        }

        alert("Registration successful! Please login.");
        window.location.href = "login.html";

    } catch (error) {
        console.error("Registration error:", error);
        alert("Cannot connect to CampusCare backend.");
    }
}


async function loginUser(event) {
    if (event) {
        event.preventDefault();
    }

    const emailElement = document.getElementById("email");
    const passwordElement = document.getElementById("password");

    if (!emailElement || !passwordElement) {
        alert("Login form fields not found.");
        return;
    }

    const email = emailElement.value.trim();
    const password = passwordElement.value;

    if (!email || !password) {
        alert("Please enter email and password.");
        return;
    }

    try {
        console.log("Sending login request...");

        const response = await fetch(
            `${window.API_BASE_URL}/api/auth/login`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            }
        );

        const data = await response.json();

        console.log("Login response:", data);

        if (!response.ok) {
            alert(data.detail || "Invalid email or password.");
            return;
        }

        // Save authentication information
        localStorage.setItem(
            "access_token",
            data.access_token
        );

        localStorage.setItem(
            "user",
            JSON.stringify(data.user)
        );

        console.log("Login successful.");
        console.log("User:", data.user);

        // STUDENT → STUDENT DASHBOARD
        if (["student", "faculty"].includes(data.user.role)) {
            window.location.href = "student-dashboard.html";
            return;
        }

        // STAFF → STAFF DASHBOARD
        if (data.user.role === "staff") {
            window.location.href = "staff-dashboard.html";
            return;
        }

        // ADMIN → ADMIN DASHBOARD
        if (data.user.role === "admin") {
            window.location.href = "admin-dashboard.html";
            return;
        }

        alert("Unknown user role.");

    } catch (error) {
        console.error("Login error:", error);
        alert(
            "Cannot connect to CampusCare backend.\n\n" +
            "Make sure FastAPI is running on port 8000."
        );
    }
}


function logoutUser() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");

    window.location.href = "login.html";
}


// Make functions available to HTML buttons/forms
window.loginUser = loginUser;
window.registerUser = registerUser;
window.logoutUser = logoutUser;
