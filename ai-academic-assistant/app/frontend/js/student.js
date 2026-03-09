const API_URL = "";

// Authentication Guard
const token = localStorage.getItem("access_token");
if (!token) {
    window.location.href = "/";
}

// Global Headers
const authHeaders = {
    "Authorization": `Bearer ${token}`,
    "Accept": "application/json"
};

// -----------------------------------------
// View Switching Logic
// -----------------------------------------
function switchView(viewId) {
    // Hide all panels
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.add('hidden');
        panel.classList.remove('active');
    });

    // Show selected panel
    const target = document.getElementById(`view-${viewId}`);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }

    // Trigger data loads dynamically based on view
    if (viewId === 'dashboard') loadDashboardAnalytics();
    else if (viewId === 'subjects') loadSubjects();
    else if (viewId === 'assignments') loadAssignments();
    else if (viewId === 'marks') {
        loadMarks();
        loadAttendance();
    }
}

// -----------------------------------------
// Modal Logic
// -----------------------------------------
function openSubmissionModal(assignmentId, title) {
    document.getElementById('submissionAssignmentId').value = assignmentId;
    document.getElementById('submittingAssignmentTitle').innerText = title;
    document.getElementById('submissionModal').classList.remove('hidden');
}

function closeSubmissionModal() {
    document.getElementById('submissionForm').reset();
    document.getElementById('submissionModal').classList.add('hidden');
}

// -----------------------------------------
// Data Fetching: Dashboard Analytics
// -----------------------------------------
async function loadDashboardAnalytics() {
    const container = document.getElementById('analyticsContainer');
    try {
        const res = await fetch(`${API_URL}/student/dashboard/analytics`, { headers: authHeaders });
        const data = await res.json();

        if (res.status === 404) {
            container.innerHTML = `<p style="color: var(--warning-orange); padding: 20px;">Your student profile hasn't been mapped by an Administrator yet. Please contact Admin to link your Academic profile.</p>`;
            return;
        }

        if (!data.success) throw new Error("Failed to load analytics");

        container.innerHTML = `
            <div class="stat-card">
                <h3>Total Assessed Subjects</h3>
                <div class="value">${data.data.risk_ranking.length}</div>
            </div>
            <div class="stat-card">
                <h3>High Risk Subjects</h3>
                <div class="value risk-high">${data.data.weak_subjects.length}</div>
            </div>
        `;

        let riskHtml = `<div class="stat-card" style="grid-column: span 2;">
            <h3 style="margin-bottom: 20px;">AI Risk Analysis</h3>`;

        data.data.risk_ranking.forEach(r => {
            let color = r.risk_label === "High" ? "var(--danger)" : (r.risk_label === "Low" ? "var(--accent)" : "#FBBF24");
            riskHtml += `<div style="display:flex; justify-content:space-between; padding: 12px 0; border-bottom: 1px solid var(--border-color);">
                <span>${r.subject}</span>
                <span style="color: ${color}; font-weight: 500;">${r.risk_label} Risk</span>
            </div>`;
        });
        riskHtml += `</div>`;

        container.innerHTML += riskHtml;

    } catch (e) {
        container.innerHTML = `<p style="color: var(--danger)">Unable to load insights.</p>`;
    }
}

// -----------------------------------------
// Data Fetching: Subjects
// -----------------------------------------
async function loadSubjects() {
    const container = document.getElementById('subjectsContainer');
    try {
        const res = await fetch(`${API_URL}/student/subjects`, { headers: authHeaders });

        if (res.status === 404) {
            container.innerHTML = `<p style="color: var(--warning-orange); padding: 20px;">Your academic profile is not mapped yet.</p>`;
            return;
        }

        const data = await res.json();

        let html = `<table class="modern-table">
            <thead><tr><th>Subject Code</th><th>Subject Name</th><th>Faculty</th><th>Offering ID</th></tr></thead><tbody>`;

        data.data.forEach(s => {
            html += `<tr>
                <td style="font-family: monospace; color: var(--accent);">${s.subject_code}</td>
                <td style="font-weight: 500;">${s.subject_name}</td>
                <td>${s.faculty_name}</td>
                <td>#${s.subject_offering_id}</td>
            </tr>`;
        });

        container.innerHTML = html + `</tbody></table>`;
    } catch (e) {
        container.innerHTML = `<p>No subjects loaded.</p>`;
    }
}

// -----------------------------------------
// Data Fetching: Assignments & Submissions
// -----------------------------------------
async function loadAssignments() {
    const tbody = document.getElementById('assignmentsList');
    try {
        const res = await fetch(`${API_URL}/student/assignments`, { headers: authHeaders });

        if (res.status === 404) {
            tbody.innerHTML = `<tr><td colspan="4" style="color: var(--warning-orange)">Academic profile not linked.</td></tr>`;
            return;
        }

        const data = await res.json();

        tbody.innerHTML = '';
        data.data.forEach(a => {
            let date = new Date(a.deadline).toLocaleDateString();
            tbody.innerHTML += `<tr>
                <td style="font-weight: 500;">${a.title}</td>
                <td style="color: var(--danger); font-size: 13px;">${date}</td>
                <td>#${a.subject_offering_id}</td>
                <td>
                    <button class="action-btn" onclick="openSubmissionModal(${a.id}, '${a.title}')">
                        Upload
                    </button>
                </td>
            </tr>`;
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4">Error loading assignments</td></tr>`;
    }
}

// Handle Upload Form Submission
document.getElementById('submissionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('uploadFileBtn');
    btn.innerText = "Uploading...";
    btn.disabled = true;

    const assignmentId = document.getElementById('submissionAssignmentId').value;
    const fileInput = document.getElementById('submissionFile');

    // Using FormData for Multipart file upload
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch(`${API_URL}/student/submit-assignment?assignment_id=${assignmentId}`, {
            method: 'POST',
            headers: { "Authorization": `Bearer ${token}` }, // Note: NO Content-Type to let browser handle multipart boundaries
            body: formData
        });

        if (res.ok) {
            alert("Assignment submitted to the Dropbox!");
            closeSubmissionModal();
        } else {
            alert("Error submitting. Please try again.");
        }
    } catch (err) {
        alert("Network failure.");
    } finally {
        btn.innerText = "Upload & Submit";
        btn.disabled = false;
    }
});

// -----------------------------------------
// Data Fetching: Marks & Attendance
// -----------------------------------------
async function loadMarks() {
    const tbody = document.getElementById('marksList');
    try {
        const res = await fetch(`${API_URL}/student/marks`, { headers: authHeaders });

        if (res.status === 404) {
            tbody.innerHTML = `<tr><td colspan="3" style="color: var(--warning-orange)">Academic profile not linked.</td></tr>`;
            return;
        }

        const data = await res.json();
        tbody.innerHTML = '';
        data.data.forEach(m => {
            tbody.innerHTML += `<tr>
                <td>#${m.subject_offering_id}</td>
                <td style="font-weight: 600;">${m.marks_obtained}</td>
                <td style="color: var(--text-secondary);">${m.max_marks}</td>
            </tr>`;
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="3">Failed to load</td></tr>`;
    }
}

async function loadAttendance() {
    const tbody = document.getElementById('attendanceList');
    try {
        const res = await fetch(`${API_URL}/student/attendance`, { headers: authHeaders });

        if (res.status === 404) {
            tbody.innerHTML = `<tr><td colspan="2" style="color: var(--warning-orange)">Academic profile not linked.</td></tr>`;
            return;
        }

        const data = await res.json();
        tbody.innerHTML = '';
        data.data.forEach(a => {
            let color = a.percentage >= 75 ? "var(--accent)" : "var(--danger)";
            tbody.innerHTML += `<tr>
                <td>${a.subject}</td>
                <td style="color: ${color}; font-weight: 600;">${a.percentage.toFixed(1)}%</td>
            </tr>`;
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="2">Failed to load</td></tr>`;
    }
}

// -----------------------------------------
// AI Chat Engine (Per-Subject)
// -----------------------------------------
const chatHistory = document.getElementById('chatHistory');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
let activeSessionId = null;
let activeSubjectOfferingId = null;
let activeSubjectName = null;

// In-memory chat histories per subject (keyed by subject_offering_id)
const chatHistories = {};

// Load enrolled subjects into sidebar
async function loadSubjectChats() {
    const container = document.getElementById('subjectChatList');
    try {
        const res = await fetch(`${API_URL}/student/subjects`, { headers: authHeaders });
        if (res.status === 404) {
            container.innerHTML = '<div style="padding:8px 16px;font-size:12px;color:var(--warning-orange);">Profile not linked.</div>';
            return;
        }
        const data = await res.json();
        if (!data.success || data.data.length === 0) {
            container.innerHTML = '<div style="padding:8px 16px;font-size:12px;color:var(--text-secondary);">No subjects enrolled.</div>';
            return;
        }

        container.innerHTML = '';
        data.data.forEach(s => {
            const btn = document.createElement('button');
            btn.className = 'nav-item subject-chat-btn';
            btn.dataset.soId = s.subject_offering_id;
            btn.dataset.name = s.subject_name;
            btn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${s.subject_code} — ${s.subject_name}</span>
            `;
            btn.onclick = () => openSubjectChat(s.subject_offering_id, s.subject_name, s.subject_code);
            container.appendChild(btn);
        });
    } catch (e) {
        container.innerHTML = '<div style="padding:8px 16px;font-size:12px;color:var(--danger);">Failed to load.</div>';
    }
}

async function openSubjectChat(soId, name, code) {
    // Save current chat history before switching
    if (activeSubjectOfferingId !== null) {
        chatHistories[activeSubjectOfferingId] = chatHistory.innerHTML;
    }

    activeSubjectOfferingId = soId;
    activeSubjectName = name;
    activeSessionId = null;

    // Highlight active sidebar button
    document.querySelectorAll('.subject-chat-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`.subject-chat-btn[data-so-id="${soId}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    // Restore from in-memory cache (fast switch within session)
    if (chatHistories[soId]) {
        chatHistory.innerHTML = chatHistories[soId];
    } else {
        // First open — load from server
        chatHistory.innerHTML = '<div style="padding:20px;color:var(--text-secondary);text-align:center;">Loading chat history...</div>';
        try {
            const res = await fetch(`${API_URL}/chat/history/${soId}`, { headers: authHeaders });
            const data = await res.json();
            chatHistory.innerHTML = '';
            if (data.success && data.data.length > 0) {
                data.data.forEach(m => {
                    appendMessage(m.role, m.content, m.message_id);
                });
            } else {
                appendMessage('assistant', `Hi! I'm your <strong>${name}</strong> (${code}) AI tutor. Ask me anything about this subject's syllabus, modules, or concepts.`);
            }
        } catch (e) {
            chatHistory.innerHTML = '';
            appendMessage('assistant', `Hi! I'm your <strong>${name}</strong> (${code}) AI tutor. Ask me anything about this subject's syllabus, modules, or concepts.`);
        }
    }

    // Enable input
    chatInput.disabled = false;
    chatInput.placeholder = `Ask about ${name}...`;
    sendBtn.disabled = false;

    // Switch to chat view
    switchView('chat');
    chatInput.focus();
}

// Handle Enter to submit, Shift+Enter for newline
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

function appendMessage(role, content, messageId = null) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const isUser = role === 'user';
    const svgIcon = isUser
        ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
        : '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2zm0 15c-3.31 0-6-2.69-6-6s2.69-6 6-6 6 2.69 6 6-2.69 6-6 6z"></path><path d="M12 22A10 10 0 1 0 12 2a10 10 0 0 0 0 20z"></path></svg>';

    let actionsHtml = '';
    if (!isUser && messageId) {
        actionsHtml = `
            <div class="feedback-actions">
                <button class="feedback-btn" onclick="submitFeedback(${messageId}, 1, this)">Good</button>
                <button class="feedback-btn" onclick="submitFeedback(${messageId}, -1, this)">Poor</button>
            </div>
        `;
    }

    div.innerHTML = `
        <div class="message-inner">
            <div class="avatar">${svgIcon}</div>
            <div class="message-content">
                ${content}
                ${actionsHtml}
            </div>
        </div>
    `;
    chatHistory.appendChild(div);
    chatHistory.parentElement.scrollTop = chatHistory.parentElement.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query || !activeSubjectOfferingId) return;

    const payload = {
        message: query,
        subject_offering_id: activeSubjectOfferingId
    };

    if (activeSessionId) payload.session_id = activeSessionId;

    chatInput.value = '';
    chatInput.style.height = '56px';
    appendMessage('user', query);
    sendBtn.disabled = true;

    try {
        const res = await fetch(`${API_URL}/chat/`, {
            method: 'POST',
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok && data.success) {
            activeSessionId = data.session_id;
            appendMessage('assistant', data.data, data.message_id);
        } else {
            appendMessage('assistant', data.detail || "I'm having trouble connecting. Please try again.");
        }
    } catch (err) {
        appendMessage('assistant', "Network Error. Unable to reach CampusAI servers.");
    } finally {
        sendBtn.disabled = false;
        chatInput.focus();
    }
});

// Auto-expand textarea
chatInput.addEventListener('input', function () {
    this.style.height = '56px';
    this.style.height = (this.scrollHeight) + 'px';
});

// -----------------------------------------
// Feedback Engine Integration
// -----------------------------------------
async function submitFeedback(messageId, rating, btnElement) {
    try {
        const res = await fetch(`${API_URL}/chat/feedback`, {
            method: 'POST',
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message_id: messageId, rating: rating })
        });

        if (res.ok) {
            const siblingBtn = rating === 1 ? btnElement.nextElementSibling : btnElement.previousElementSibling;
            if (siblingBtn) siblingBtn.classList.remove('active');
            btnElement.classList.add('active');
            btnElement.innerText = rating === 1 ? "Thanks!" : "Noted.";
        }
    } catch (e) {
        console.warn("Feedback submission failed.");
    }
}

// -----------------------------------------
// Utility
// -----------------------------------------
function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "/";
}

// -----------------------------------------
// Init: Load subjects into sidebar on page load
// -----------------------------------------
loadSubjectChats();

