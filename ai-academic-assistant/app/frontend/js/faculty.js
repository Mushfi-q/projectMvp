const API_URL = "http://127.0.0.1:8000";
const token = localStorage.getItem("access_token");

if (!token) {
    window.location.href = "/";
}

const authHeaders = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
};

// Panel Switching
function switchPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    document.getElementById(`panel-${panelId}`).classList.remove('hidden');

    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`button[onclick="switchPanel('${panelId}')"]`).classList.add('active');

    // Trigger data loads
    if (panelId === 'offerings') loadMySubjects();
    if (panelId === 'assignments') loadAssignments();
    if (panelId === 'students' && document.getElementById('studentsSubject').value) fetchStudentsList(document.getElementById('studentsSubject').value);
    if (panelId === 'analytics' && document.getElementById('analyticsSubject').value) fetchAnalytics(document.getElementById('analyticsSubject').value);
}

// Utility API Call
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = { method, headers: authHeaders };
    if (body) options.body = JSON.stringify(body);
    const res = await fetch(`${API_URL}${endpoint}`, options);
    const data = await res.json();
    return { ok: res.ok, data };
}

// Alert helper
function showAlert(element, message, type = 'error') {
    element.textContent = message;
    element.className = `alert ${type}`;
    element.classList.remove('hidden');
    setTimeout(() => element.classList.add('hidden'), 5000);
}

// Ensure login is faculty
async function verifyFaculty() {
    const { ok, data } = await apiCall('/auth/me');
    if (!ok || data.data.role.toLowerCase() !== 'faculty') {
        localStorage.removeItem("access_token");
        window.location.href = "/";
    }
}

function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "/";
}

// ==========================================
// Generic: Load "My Subjects" Dropdowns
// ==========================================

async function loadMySubjects() {
    const { ok, data } = await apiCall('/faculty/my-subjects');
    const tbody = document.getElementById('mySubjectsTableBody');
    const dropdowns = document.querySelectorAll('.my-subjects-dropdown');

    if (ok) {
        tbody.innerHTML = '';
        const optionsHTML = '<option value="">Select a subject...</option>' +
            data.data.map(o => `<option value="${o.subject_offering_id}">${o.subject_code} - ${o.subject_name} (Sem ${o.semester_id})</option>`).join('');

        dropdowns.forEach(d => d.innerHTML = optionsHTML);

        if (data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">No subjects mapped yet.</td></tr>';
        } else {
            data.data.forEach(o => {
                tbody.innerHTML += `
                    <tr>
                        <td>${o.subject_offering_id}</td>
                        <td class="mono">${o.subject_code}</td>
                        <td>${o.subject_name}</td>
                        <td>${o.semester_id}</td>
                    </tr>
                `;
            });
        }
    } else {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--danger)">Failed to load subjects. Error: ${data.detail || 'Profile incomplete.'}</td></tr>`;
        dropdowns.forEach(d => d.innerHTML = `<option value="">Error Loading Subjects</option>`);
        showAlert(document.getElementById('subjectsAlert'), `Initialization failed: ${data.detail || 'Missing faculty profile.'}`, 'error');
    }
}

// ==========================================
// Assignments
// ==========================================

document.getElementById('assignmentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.disabled = true;

    const payload = {
        subject_offering_id: parseInt(document.getElementById('assignSubject').value),
        title: document.getElementById('assignTitle').value,
        description: document.getElementById('assignDesc').value,
        deadline: new Date(document.getElementById('assignDeadline').value).toISOString()
    };

    const { ok, data } = await apiCall('/faculty/assignment', 'POST', payload);

    if (ok) {
        showAlert(document.getElementById('assignmentAlert'), "Assignment created successfully!", 'success');
        e.target.reset();
        loadAssignments(); // refresh table
    } else {
        showAlert(document.getElementById('assignmentAlert'), data.detail || "Creation failed.");
    }
    btn.disabled = false;
});

async function loadAssignments() {
    const tbody = document.getElementById('assignmentsTableBody');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Loading...</td></tr>';
    const { ok, data } = await apiCall('/faculty/assignments');

    if (ok) {
        if (data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">No assignments created yet.</td></tr>';
        } else {
            tbody.innerHTML = data.data.map(a => `
                <tr>
                    <td class="mono">#${a.id}</td>
                    <td><strong>${a.title}</strong></td>
                    <td class="mono">${a.subject_code}</td>
                    <td>Sem ${a.semester_id}</td>
                    <td>${new Date(a.deadline).toLocaleString()}</td>
                </tr>
            `).join('');
        }
    } else {
        tbody.innerHTML = '<tr><td colspan="5" style="color:var(--danger)">Failed to load assignments.</td></tr>';
    }
}


// ==========================================
// Marks
// ==========================================

async function loadStudentsForDropdown(soId, dropdownId) {
    const select = document.getElementById(dropdownId);
    if (!soId) {
        select.innerHTML = '<option value="">Select subject first...</option>';
        return;
    }
    select.innerHTML = '<option value="">Loading students...</option>';
    const { ok, data } = await apiCall(`/faculty/students/${soId}`);
    if (ok && data.data) {
        select.innerHTML = '<option value="">Select a student...</option>' +
            data.data.map(s => `<option value="${s.student_id}">${s.register_number}</option>`).join('');
    } else {
        select.innerHTML = '<option value="">Error loading students</option>';
    }
}

document.getElementById('marksForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        subject_offering_id: parseInt(document.getElementById('marksSubject').value),
        student_id: parseInt(document.getElementById('marksStudent').value),
        marks_obtained: parseInt(document.getElementById('marksObtained').value),
        max_marks: parseInt(document.getElementById('marksMax').value)
    };

    const { ok, data } = await apiCall('/faculty/marks', 'POST', payload);
    if (ok) {
        showAlert(document.getElementById('marksAlert'), "Marks uploaded successfully!", 'success');
        document.getElementById('marksObtained').value = '';
    } else {
        showAlert(document.getElementById('marksAlert'), data.detail || "Upload failed.");
    }
});

// ==========================================
// Attendance Bulk
// ==========================================

let attendanceRoster = [];

document.getElementById('attendanceLoadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const soId = document.getElementById('attendanceSubject').value;
    const { ok, data } = await apiCall(`/faculty/students/${soId}`);

    if (ok && data.data && data.data.length > 0) {
        attendanceRoster = data.data;
        document.getElementById('attendanceRosterSection').classList.remove('hidden');
        renderAttendanceTable();
    } else {
        alert("No students found or error loading roster.");
    }
});

function renderAttendanceTable() {
    const tbody = document.getElementById('attendanceTableBody');
    tbody.innerHTML = attendanceRoster.map(s => `
        <tr>
            <td class="mono">${s.register_number}</td>
            <td>
                <select id="att_status_${s.student_id}" class="att-select" required>
                    <option value="Present">Present</option>
                    <option value="Absent">Absent</option>
                </select>
            </td>
        </tr>
    `).join('');
}

document.getElementById('attendanceSubmitForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const soId = document.getElementById('attendanceSubject').value;
    const date = document.getElementById('attendanceDate').value;

    const records = attendanceRoster.map(s => ({
        student_id: s.student_id,
        status: document.getElementById(`att_status_${s.student_id}`).value
    }));

    const { ok, data } = await apiCall('/faculty/attendance/bulk', 'POST', {
        subject_offering_id: parseInt(soId),
        date: date,
        records: records
    });

    if (ok) {
        showAlert(document.getElementById('attendanceAlert'), `Attendance submitted! ${data.marked} records added.`, 'success');
        document.getElementById('attendanceRosterSection').classList.add('hidden');
    } else {
        showAlert(document.getElementById('attendanceAlert'), data.detail || "Submission failed.");
    }
});

// ==========================================
// Student List
// ==========================================

async function fetchStudentsList(soId) {
    const tbody = document.getElementById('studentsTableBody');
    if (!soId) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;">Select a subject to view students</td></tr>';
        return;
    }

    tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;">Loading...</td></tr>';
    const { ok, data } = await apiCall(`/faculty/students/${soId}`);

    if (ok && data.data && data.data.length > 0) {
        tbody.innerHTML = data.data.map(s => `
            <tr>
                <td>${s.student_id}</td>
                <td class="mono">${s.register_number}</td>
            </tr>
        `).join('');
    } else {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;">No students enrolled.</td></tr>';
    }
}

// ==========================================
// Analytics
// ==========================================

async function fetchAnalytics(soId) {
    const dashboard = document.getElementById('analyticsDashboard');
    if (!soId) {
        dashboard.classList.add('hidden');
        return;
    }

    const { ok, data } = await apiCall(`/faculty/analytics/${soId}`);
    if (ok && data.data) {
        dashboard.classList.remove('hidden');
        document.getElementById('statAvgMarks').innerText = data.data.class_average.toFixed(1) + '%';
        document.getElementById('statAvgAtt').innerText = data.data.class_attendance_summary.toFixed(1) + '%';
        document.getElementById('statAvgComp').innerText = data.data.assignment_completion_rate.toFixed(1) + '%';

        const tbody = document.getElementById('lowPerformersBody');
        if (data.data.low_performers.length > 0) {
            tbody.innerHTML = data.data.low_performers.map(p => `
                <tr>
                    <td class="mono">${p.register_number}</td>
                    <td><span style="color:var(--danger);font-weight:bold;">${p.risk_level}</span></td>
                    <td>${p.attendance}%</td>
                    <td>${p.avg_marks}%</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No low performers detected.</td></tr>';
        }
    } else {
        dashboard.classList.add('hidden');
        showAlert(document.getElementById('analyticsAlert'), data.detail || "Error loading analytics.");
    }
}

// Initialize
verifyFaculty().then(() => {
    loadMySubjects();
});
