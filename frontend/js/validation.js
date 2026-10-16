// ==========================================
// CampusCare - Form Validation
// frontend/js/validation.js
// ==========================================


// ==========================================
// Email Validation
// ==========================================

function isValidEmail(email) {

    const emailPattern =
        /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    return emailPattern.test(email);
}


// ==========================================
// Password Validation
// ==========================================

function isValidPassword(password) {

    return password.length >= 8;
}


// ==========================================
// Registration Validation
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const registerForm =
            document.getElementById(
                "registerForm"
            );


        if (registerForm) {

            registerForm.addEventListener(
                "submit",
                function (event) {

                    const email =
                        document.getElementById(
                            "email"
                        )?.value.trim();


                    const password =
                        document.getElementById(
                            "password"
                        )?.value;


                    if (!isValidEmail(email)) {

                        event.preventDefault();

                        alert(
                            "Please enter a valid email address."
                        );

                        return;
                    }


                    if (!isValidPassword(password)) {

                        event.preventDefault();

                        alert(
                            "Password must contain at least 8 characters."
                        );

                        return;
                    }

                }
            );
        }


        // ==========================================
        // Complaint Form Validation
        // ==========================================

        const complaintForm =
            document.getElementById(
                "complaintForm"
            );


        if (complaintForm) {

            complaintForm.addEventListener(
                "submit",
                function (event) {

                    const title =
                        document.getElementById(
                            "title"
                        )?.value.trim();


                    const description =
                        document.getElementById(
                            "description"
                        )?.value.trim();


                    if (!title) {

                        event.preventDefault();

                        alert(
                            "Please enter a complaint title."
                        );

                        return;
                    }


                    if (!description) {

                        event.preventDefault();

                        alert(
                            "Please describe your complaint."
                        );

                        return;
                    }


                    if (description.length < 10) {

                        event.preventDefault();

                        alert(
                            "Complaint description should contain at least 10 characters."
                        );

                        return;
                    }

                }
            );
        }

    }
);
