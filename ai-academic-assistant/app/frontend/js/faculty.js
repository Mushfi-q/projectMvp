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
    document.querySelectorAll('.panel').forEach(p => {
        p.classList.add('hidden');
        p.classList.remove('active');
    });
    
    const target = document.getElementById(`panel-${panelId}`);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }

    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    const navBtn = document.querySelector(`button[onclick="switchPanel('${panelId}')"]`);
    if (navBtn) navBtn.classList.add('active');

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
                    <td>
                        <button class="action-btn" onclick="openSubmissionsModal(${a.id}, '${a.title}')">Submissions</button>
                    </td>
                </tr>
            `).join('');
        }
    } else {
        tbody.innerHTML = '<tr><td colspan="6" style="color:var(--danger)">Failed to load assignments.</td></tr>';
    }
}

// Submissions Modal Logic
async function openSubmissionsModal(assignmentId, title) {
    document.getElementById('submissionsModalTitle').textContent = `Submissions: ${title}`;
    document.getElementById('submissionsModal').classList.remove('hidden');
    loadSubmissions(assignmentId);
}

function closeSubmissionsModal() {
    document.getElementById('submissionsModal').classList.add('hidden');
}

async function loadSubmissions(assignmentId) {
    const tbody = document.getElementById('submissionsTableBody');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Loading submissions...</td></tr>';
    
    const { ok, data } = await apiCall(`/faculty/assignment/${assignmentId}/submissions`);
    
    if (ok) {
        if (data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No students have submitted yet.</td></tr>';
        } else {
            tbody.innerHTML = data.data.map(sub => {
                let currentMarks = sub.marks !== null ? sub.marks : '';
                let date = new Date(sub.submitted_at).toLocaleString();
                let fileLink = `<a href="/${sub.file_url}" target="_blank" style="color: var(--accent); text-decoration: none; font-weight: 600;">Download</a>`;
                
                return `
                    <tr>
                        <td>
                            <div style="font-weight: 600;">${sub.student_name}</div>
                            <div style="font-size: 12px; color: var(--text-secondary);">${sub.register_number}</div>
                        </td>
                        <td style="font-size: 13px;">${date}</td>
                        <td>${fileLink}</td>
                        <td>
                            <div style="display: flex; gap: 8px; align-items: center;">
                                <input type="number" id="grade_${sub.submission_id}" value="${currentMarks}" style="width: 70px; padding: 4px 8px;" placeholder="-" min="0">
                                <button onclick="saveGrade(${sub.submission_id})" style="padding: 4px 10px; background: var(--accent); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;">Save</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } else {
        tbody.innerHTML = '<tr><td colspan="4" style="color:var(--danger); text-align:center;">Failed to load submissions.</td></tr>';
    }
}

async function saveGrade(submissionId) {
    const marksInput = document.getElementById(`grade_${submissionId}`);
    const marks = parseInt(marksInput.value);
    
    if (isNaN(marks)) {
        alert("Please enter valid marks.");
        return;
    }
    
    const { ok, data } = await apiCall(`/faculty/submission/${submissionId}/grade`, 'POST', { marks: marks });
    
    if (ok) {
        alert("Grade saved successfully!");
        // Visual indicator of success
        marksInput.style.borderColor = "var(--accent)";
        setTimeout(() => marksInput.style.borderColor = "var(--border)", 2000);
    } else {
        alert(data.detail || "Failed to save grade.");
    }
}




// ==========================================
// Attendance Bulk
// ==========================================

async function fetchAttendanceHistory(soId) {
    const tbody = document.getElementById('attendanceHistoryTableBody');
    if (!soId) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Select a subject to view history</td></tr>';
        return;
    }

    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Loading...</td></tr>';
    const { ok, data } = await apiCall(`/faculty/attendance/history/${soId}`);

    if (ok && data.data && data.data.length > 0) {
        tbody.innerHTML = data.data.map(r => `
            <tr>
                <td>${r.date}</td>
                <td>${r.hours}</td>
                <td class="text-success fw-bold">${r.present_count}</td>
                <td class="${r.absent_count > 0 ? 'text-danger fw-bold' : ''}">${r.absent_count}</td>
            </tr>
        `).join('');
    } else {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No history found.</td></tr>';
    }
}

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
    const hours = parseInt(document.getElementById('attendanceHours').value);

    const records = attendanceRoster.map(s => ({
        student_id: s.student_id,
        status: document.getElementById(`att_status_${s.student_id}`).value
    }));

    const { ok, data } = await apiCall('/faculty/attendance/bulk', 'POST', {
        subject_offering_id: parseInt(soId),
        date: date,
        hours: hours,
        records: records
    });

    if (ok) {
        showAlert(document.getElementById('attendanceAlert'), `Attendance submitted! ${data.marked} records added.`, 'success');
        document.getElementById('attendanceRosterSection').classList.add('hidden');
        document.getElementById('attendanceLoadForm').reset();
        fetchAttendanceHistory(soId);
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
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Select a subject to view students</td></tr>';
        return;
    }

    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Loading...</td></tr>';
    const { ok, data } = await apiCall(`/faculty/students/${soId}`);

    if (ok && data.data && data.data.length > 0) {
        tbody.innerHTML = data.data.map(s => `
            <tr>
                <td>${s.student_id}</td>
                <td class="mono">${s.register_number}</td>
                <td class="${s.attendance < 75 ? 'text-danger fw-bold' : ''}">${parseFloat(s.attendance || 0).toFixed(1)}%</td>
                <td class="${s.marks < 50 ? 'text-danger fw-bold' : ''}">${parseFloat(s.marks || 0).toFixed(1)}%</td>
            </tr>
        `).join('');
    } else {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No students enrolled.</td></tr>';
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
