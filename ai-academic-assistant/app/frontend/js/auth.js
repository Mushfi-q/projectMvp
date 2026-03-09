const API_URL = "";

document.addEventListener("DOMContentLoaded", () => {

    // View Switching
    const loginView = document.getElementById("loginView");
    const registerView = document.getElementById("registerView");
    const showRegisterLink = document.getElementById("showRegister");
    const showLoginLink = document.getElementById("showLogin");

    // UI Elements
    const loginAlert = document.getElementById("loginAlert");
    const registerAlert = document.getElementById("registerAlert");
    const loginBtn = document.getElementById("loginBtn");
    const registerBtn = document.getElementById("registerBtn");

    // Clear alerts fn
    const clearAlerts = () => {
        loginAlert.style.display = 'none';
        loginAlert.className = 'alert';
        registerAlert.style.display = 'none';
        registerAlert.className = 'alert';
    };

    const showAlert = (el, message, type = 'error') => {
        el.innerText = message;
        el.className = `alert ${type}`;
        el.style.display = 'block';
    };

    // Toggle logic
    showRegisterLink.addEventListener("click", () => {
        loginView.classList.add("hidden");
        registerView.classList.remove("hidden");
        clearAlerts();
        loadDepartments();
    });

    showLoginLink.addEventListener("click", () => {
        registerView.classList.add("hidden");
        loginView.classList.remove("hidden");
        clearAlerts();
    });

    // Role Toggle: show/hide student vs faculty fields
    const regRole = document.getElementById("regRole");
    const studentFields = document.getElementById("studentFields");
    const facultyFields = document.getElementById("facultyFields");
    const regBatch = document.getElementById("regBatch");
    const regSemester = document.getElementById("regSemester");

    regRole.addEventListener("change", () => {
        if (regRole.value === "faculty") {
            studentFields.classList.add("hidden");
            facultyFields.classList.remove("hidden");
            regBatch.removeAttribute("required");
            regSemester.removeAttribute("required");
        } else {
            studentFields.classList.remove("hidden");
            facultyFields.classList.add("hidden");
            regBatch.setAttribute("required", "");
            regSemester.setAttribute("required", "");
        }
    });

    // Populate Departments dynamically
    async function loadDepartments() {
        const deptSelect = document.getElementById("regDepartment");
        if (deptSelect.options.length > 1) return; // already loaded

        try {
            const res = await fetch(`${API_URL}/auth/departments`);
            const data = await res.json();

            if (data.success) {
                deptSelect.innerHTML = '<option value="">Select Department</option>';
                data.data.forEach(d => {
                    deptSelect.innerHTML += `<option value="${d.id}">${d.name}</option>`;
                });
            } else {
                deptSelect.innerHTML = '<option value="">Failed to load</option>';
            }
        } catch (e) {
            deptSelect.innerHTML = '<option value="">Network error</option>';
        }
    }

    // Populate Batches based on Department
    document.getElementById("regDepartment").addEventListener("change", async (e) => {
        const deptId = e.target.value;
        const batchSelect = document.getElementById("regBatch");

        if (!deptId) {
            batchSelect.innerHTML = '<option value="">Select Dept First</option>';
            return;
        }

        batchSelect.innerHTML = '<option value="">Loading...</option>';
        try {
            const res = await fetch(`${API_URL}/auth/departments/${deptId}/batches`);
            const data = await res.json();

            if (data.success && data.data.length > 0) {
                batchSelect.innerHTML = '<option value="">Select Batch</option>';
                data.data.forEach(b => {
                    batchSelect.innerHTML += `<option value="${b.id}">${b.start_year} - ${b.end_year}</option>`;
                });
            } else {
                batchSelect.innerHTML = '<option value="">No batches found</option>';
            }
        } catch (err) {
            batchSelect.innerHTML = '<option value="">Network error</option>';
        }
    });

    // Handle Login
    document.getElementById("loginForm").addEventListener("submit", async (e) => {
        e.preventDefault();

        const email = document.getElementById("loginEmail").value;
        const password = document.getElementById("loginPassword").value;

        loginBtn.innerText = "Authenticating...";
        loginBtn.disabled = true;
        clearAlerts();

        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);
        formData.append("grant_type", "password");

        try {
            const res = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData.toString()
            });

            const data = await res.json();

            if (res.ok) {
                localStorage.setItem("access_token", data.access_token);

                // Fetch user role for redirection
                const roleRes = await fetch(`${API_URL}/auth/me`, {
                    headers: { "Authorization": `Bearer ${data.access_token}` }
                });
                const roleData = await roleRes.json();

                if (roleData.success && roleData.data.role.toLowerCase() === "faculty") {
                    window.location.href = "/faculty";
                } else if (roleData.success && roleData.data.role.toLowerCase() === "admin") {
                    window.location.href = "/admin"; // Will map later
                } else {
                    window.location.href = "/app"; // Student dashboard
                }
            } else {
                showAlert(loginAlert, data.detail || "Invalid credentials.");
            }
        } catch (error) {
            showAlert(loginAlert, "Network error. Server may be down.");
        } finally {
            loginBtn.innerText = "Secure Login";
            loginBtn.disabled = false;
        }
    });

    // Handle Register
    document.getElementById("registerForm").addEventListener("submit", async (e) => {
        e.preventDefault();

        const role = document.getElementById("regRole").value;
        const name = document.getElementById("regName").value;
        const email = document.getElementById("regEmail").value;
        const department_id = document.getElementById("regDepartment").value;
        const password = document.getElementById("regPassword").value;
        const confirm_password = document.getElementById("regConfirmPassword").value;

        if (password !== confirm_password) {
            showAlert(registerAlert, "Passwords do not match!");
            return;
        }

        registerBtn.innerText = "Creating Profile...";
        registerBtn.disabled = true;
        clearAlerts();

        let endpoint, payload;

        if (role === "faculty") {
            endpoint = `${API_URL}/auth/register-faculty`;
            payload = {
                name, email, password, confirm_password,
                department_id: parseInt(department_id),
                designation: document.getElementById("regDesignation").value
            };
        } else {
            const batch_id = document.getElementById("regBatch").value;
            const semester_number = document.getElementById("regSemester").value;

            if (!batch_id) {
                showAlert(registerAlert, "Please select a Batch!");
                registerBtn.innerText = "Create Account";
                registerBtn.disabled = false;
                return;
            }

            endpoint = `${API_URL}/auth/register`;
            payload = {
                name, email, password, confirm_password,
                department_id: parseInt(department_id),
                batch_id: parseInt(batch_id),
                semester_number: parseInt(semester_number)
            };
        }

        try {
            const res = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.ok) {
                showAlert(registerAlert, data.data || "Registration successful! You may now login.", "success");
                document.getElementById("registerForm").reset();
                // Reset role toggle back to student
                studentFields.classList.remove("hidden");
                facultyFields.classList.add("hidden");
                setTimeout(() => {
                    showLoginLink.click();
                }, 3000);
            } else {
                showAlert(registerAlert, data.detail || "Registration failed.");
            }
        } catch (error) {
            showAlert(registerAlert, "Network error. Server may be down.");
        } finally {
            registerBtn.innerText = "Create Account";
            registerBtn.disabled = false;
        }
    });
});
