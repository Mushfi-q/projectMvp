const API_URL = "";

// Auth Guard
const token = localStorage.getItem("access_token");
if (!token) {
    window.location.href = "/";
}

const authHeaders = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
    "Accept": "application/json"
};

// -----------------------------------------
// Panel Switching
// -----------------------------------------
function switchPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => {
        p.classList.remove('active');
        p.classList.add('hidden');
    });
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const target = document.getElementById(`panel-${panelId}`);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }

    // Highlight the clicked nav item
    event.currentTarget.classList.add('active');

    // Load departments for dropdown selectors
    if (panelId === 'batches' || panelId === 'faculty' || panelId === 'subjects') {
        const selectMap = { batches: 'batchDeptId', faculty: 'facDeptId', subjects: 'subjDeptId' };
        loadDepartmentsInto(selectMap[panelId]);
    }

    // Load data tables for the active panel
    loadTableData(panelId);
}

// -----------------------------------------
// Utility: Alert Display
// -----------------------------------------
function showAlert(elementId, message, type = 'error') {
    const el = document.getElementById(elementId);
    el.innerText = message;
    el.className = `alert ${type}`;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 5000);
}

// -----------------------------------------
// Global Delete Handler (with cascade warning)
// -----------------------------------------
async function deleteItem(entityRoute, itemId, panelId) {
    // Step 1: Check what dependents will also be deleted
    try {
        const checkRes = await fetch(`${API_URL}/admin/dependents/${entityRoute}/${itemId}`, { headers: authHeaders });
        const checkData = await checkRes.json();

        let warningMsg = `⚠️ DELETE ${entityRoute.toUpperCase()} #${itemId}\n\n`;

        if (checkData.success && checkData.data && Object.keys(checkData.data).length > 0) {
            warningMsg += `This will ALSO permanently delete:\n\n`;
            for (const [type, count] of Object.entries(checkData.data)) {
                warningMsg += `  • ${count} ${type}\n`;
            }
            warningMsg += `\nThis action CANNOT be undone. Continue?`;
        } else {
            warningMsg += `No dependent records found.\n\nThis action CANNOT be undone. Continue?`;
        }

        if (!confirm(warningMsg)) return;

    } catch (e) {
        console.error("Error checking dependents:", e);
        if (!confirm(`Delete ${entityRoute} #${itemId}? This cannot be undone.\n\n(Warning: Dependency check failed, so this might cascade-delete more than expected)`)) return;
    }

    // Step 2: Perform the cascade delete
    try {
        const res = await fetch(`${API_URL}/admin/${entityRoute}/${itemId}`, {
            method: 'DELETE',
            headers: authHeaders
        });
        const data = await res.json();
        if (res.ok) {
            loadTableData(panelId);
        } else {
            alert(data.detail || 'Delete failed.');
        }
    } catch (e) {
        alert('Network error during delete.');
    }
}

// -----------------------------------------
// Load Departments into a <select> element
// -----------------------------------------
async function loadDepartmentsInto(selectId) {
    const sel = document.getElementById(selectId);
    if (sel.options.length > 1) return; // already loaded
    try {
        const res = await fetch(`${API_URL}/auth/departments`);
        const data = await res.json();
        if (data.success) {
            sel.innerHTML = '<option value="">Select Department</option>';
            data.data.forEach(d => {
                sel.innerHTML += `<option value="${d.id}">${d.name}</option>`;
            });
        }
    } catch (e) {
        sel.innerHTML = '<option value="">Failed to load</option>';
    }
}

// -----------------------------------------
// Form: Create Department
// -----------------------------------------
document.getElementById('deptForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('deptName').value;
    try {
        const res = await fetch(`${API_URL}/admin/department`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('deptAlert', `✓ ${data.data}`, 'success');
            document.getElementById('deptForm').reset();
            loadTableData('departments');
        } else {
            showAlert('deptAlert', data.detail || 'Failed.');
        }
    } catch (err) {
        showAlert('deptAlert', 'Network error.');
    }
});

// -----------------------------------------
// Form: Create Batch
// -----------------------------------------
document.getElementById('batchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        department_id: parseInt(document.getElementById('batchDeptId').value),
        start_year: parseInt(document.getElementById('batchStart').value),
        end_year: parseInt(document.getElementById('batchEnd').value)
    };

    try {
        const res = await fetch(`${API_URL}/admin/batch`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('batchAlert', `✓ ${data.data}`, 'success');
            document.getElementById('batchForm').reset();
            loadTableData('batches');
        } else {
            showAlert('batchAlert', data.detail || 'Failed.');
        }
    } catch (err) {
        showAlert('batchAlert', 'Network error.');
    }
});

// -----------------------------------------
// Form: Create Semester
// -----------------------------------------
document.getElementById('semForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        batch_id: parseInt(document.getElementById('semBatchId').value),
        semester_number: parseInt(document.getElementById('semNumber').value),
        academic_year: document.getElementById('semYear').value,
        is_active: 1
    };

    try {
        const res = await fetch(`${API_URL}/admin/semester`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('semAlert', `✓ ${data.data}`, 'success');
            document.getElementById('semForm').reset();
            loadTableData('semesters');
        } else {
            showAlert('semAlert', data.detail || 'Failed.');
        }
    } catch (err) {
        showAlert('semAlert', 'Network error.');
    }
});

// -----------------------------------------
// Form: Create Faculty
// -----------------------------------------
document.getElementById('facultyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        user_id: parseInt(document.getElementById('facUserId').value),
        department_id: parseInt(document.getElementById('facDeptId').value),
        designation: document.getElementById('facDesignation').value
    };

    try {
        const res = await fetch(`${API_URL}/admin/faculty`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('facAlert', `✓ ${data.data}`, 'success');
            document.getElementById('facultyForm').reset();
            loadTableData('faculty');
        } else {
            showAlert('facAlert', data.detail || 'Failed.');
        }
    } catch (err) {
        showAlert('facAlert', 'Network error.');
    }
});

// -----------------------------------------
// Form: Upload PDF (with Subject + Module)
// -----------------------------------------
async function loadSubjectsForPdf() {
    const sel = document.getElementById('pdfSubjectId');
    if (sel.options.length > 1) return; // already loaded
    try {
        const res = await fetch(`${API_URL}/admin/subjects`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            sel.innerHTML = '<option value="">Select Subject</option>';
            data.data.forEach(s => {
                sel.innerHTML += `<option value="${s.id}">${s.name} (${s.code})</option>`;
            });
        } else {
            sel.innerHTML = '<option value="">No subjects found</option>';
        }
    } catch (e) {
        sel.innerHTML = '<option value="">Failed to load</option>';
    }
}

document.getElementById('pdfForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('pdfUploadBtn');
    btn.innerText = "Uploading & Indexing...";
    btn.disabled = true;

    const subjectId = document.getElementById('pdfSubjectId').value;
    const moduleNumber = document.getElementById('pdfModuleNumber').value;
    const fileInput = document.getElementById('pdfFile');

    if (!subjectId) {
        showAlert('pdfAlert', 'Please select a Subject!');
        btn.innerText = "Upload & Index";
        btn.disabled = false;
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch(`${API_URL}/admin/upload-pdf?subject_id=${subjectId}&module_number=${moduleNumber}`, {
            method: 'POST',
            headers: { "Authorization": `Bearer ${token}` },
            body: formData
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('pdfAlert', `✓ ${data.data}`, 'success');
            document.getElementById('pdfForm').reset();
            loadDocumentsTable();
        } else {
            showAlert('pdfAlert', data.detail || 'Upload failed.');
        }
    } catch (err) {
        showAlert('pdfAlert', 'Network error.');
    } finally {
        btn.innerText = "Upload & Index";
        btn.disabled = false;
    }
});

// -----------------------------------------
// Form: Promote Batch
// -----------------------------------------
document.getElementById('promoteForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const batchId = document.getElementById('promoteBatchId').value;

    if (!confirm(`Are you sure you want to promote Batch #${batchId}? This will archive all current semester data and advance students.`)) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/admin/promote/${batchId}`, {
            method: 'POST',
            headers: authHeaders
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('promoteAlert', `✓ ${data.data}`, 'success');
            document.getElementById('promoteForm').reset();
        } else {
            showAlert('promoteAlert', data.detail || 'Promotion failed.');
        }
    } catch (err) {
        showAlert('promoteAlert', 'Network error.');
    }
});

// -----------------------------------------
// Logout
// -----------------------------------------
function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "/";
}

// -----------------------------------------
// Data Table Loaders
// -----------------------------------------
async function loadTableData(panelId) {
    const loaders = {
        departments: loadDepartmentsTable,
        batches: loadBatchesTable,
        semesters: loadSemestersTable,
        faculty: loadFacultyTable,
        students: loadStudentsTable,
        enrollments: loadEnrollmentsTable,
        subjects: loadSubjectsTable,
        offerings: () => { loadSubjectOfferingsTable(); loadDropdownsForOfferings(); },
        pdf: () => { loadSubjectsForPdf(); loadDocumentsTable(); }
    };
    if (loaders[panelId]) loaders[panelId]();
}

async function loadDepartmentsTable() {
    const tbody = document.getElementById('deptTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/departments`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(d => `
                <tr><td class="mono">#${d.id}</td><td>${d.name}</td><td><button class="btn-delete" onclick="deleteItem('department',${d.id},'departments')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="3" style="color:var(--text-secondary)">No departments created yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

async function loadBatchesTable() {
    const tbody = document.getElementById('batchTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/batches`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(b => `
                <tr><td class="mono">#${b.id}</td><td>${b.department}</td><td>${b.start_year}</td><td>${b.end_year}</td><td><button class="btn-delete" onclick="deleteItem('batch',${b.id},'batches')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="color:var(--text-secondary)">No batches created yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

async function loadSemestersTable() {
    const tbody = document.getElementById('semTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/semesters`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(s => `
                <tr><td class="mono">#${s.id}</td><td>${s.batch} (ID:${s.batch_id})</td><td>Sem ${s.semester_number}</td><td>${s.academic_year}</td><td>${s.is_active ? '✅' : '❌'}</td><td><button class="btn-delete" onclick="deleteItem('semester',${s.id},'semesters')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" style="color:var(--text-secondary)">No semesters created yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

async function loadFacultyTable() {
    const tbody = document.getElementById('facTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/faculties`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(f => `
                <tr><td class="mono">#${f.id}</td><td>${f.name}</td><td>${f.email}</td><td>${f.department}</td><td>${f.designation}</td><td><button class="btn-delete" onclick="deleteItem('faculty',${f.id},'faculty')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text-secondary)">No faculty members linked yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

async function loadStudentsTable() {
    const tbody = document.getElementById('studentTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/students`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(s => `
                <tr><td class="mono">#${s.id}</td><td>${s.name}</td><td>${s.email}</td><td>${s.register_number}</td><td>${s.batch}</td><td>${s.semester}</td><td><button class="btn-delete" onclick="deleteItem('student',${s.id},'students')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" style="color:var(--text-secondary)">No students registered yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

async function loadEnrollmentsTable() {
    const tbody = document.getElementById('enrollTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/enrollments`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(e => `
                <tr><td class="mono">#${e.id}</td><td>${e.student}</td><td>${e.subject}</td><td>${e.subject_code}</td><td class="mono">#${e.offering_id}</td><td>${e.date}</td><td><button class="btn-delete" onclick="deleteItem('enrollment',${e.id},'enrollments')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="color:var(--text-secondary)">No enrollments found.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="7" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

async function loadDocumentsTable() {
    const tbody = document.getElementById('docTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/documents`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(d => `
                <tr><td class="mono">#${d.id}</td><td>${d.title}</td><td>${d.type}</td><td>${d.uploaded_by}</td><td>${d.uploaded_at}</td><td><button class="btn-delete" onclick="deleteItem('document',${d.id},'pdf')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" style="color:var(--text-secondary)">No documents uploaded yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

// Auto-load departments table on page load
loadTableData('departments');

// -----------------------------------------
// Form: Create Subject
// -----------------------------------------
document.getElementById('subjectForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        subject_name: document.getElementById('subjName').value,
        subject_code: document.getElementById('subjCode').value,
        department_id: parseInt(document.getElementById('subjDeptId').value)
    };
    try {
        const res = await fetch(`${API_URL}/admin/subject`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('subjAlert', `✓ ${data.data}`, 'success');
            document.getElementById('subjectForm').reset();
            loadTableData('subjects');
        } else {
            showAlert('subjAlert', data.detail || 'Failed.');
        }
    } catch (err) {
        showAlert('subjAlert', 'Network error.');
    }
});

// -----------------------------------------
// Form: Create Subject Offering
// -----------------------------------------

async function loadDropdownsForOfferings() {
    const [subRes, semRes, facRes] = await Promise.all([
        fetch(`${API_URL}/admin/subjects`, { headers: authHeaders }).then(r => r.json()),
        fetch(`${API_URL}/admin/semesters`, { headers: authHeaders }).then(r => r.json()),
        fetch(`${API_URL}/admin/faculties`, { headers: authHeaders }).then(r => r.json())
    ]);

    if (subRes.success) {
        document.getElementById('soSubjectId').innerHTML = '<option value="">Select Subject...</option>' +
            subRes.data.map(s => `<option value="${s.id}">${s.code} - ${s.name}</option>`).join('');
    }
    if (semRes.success) {
        document.getElementById('soSemesterId').innerHTML = '<option value="">Select Semester...</option>' +
            semRes.data.map(s => `<option value="${s.id}">Sem ${s.semester_number} (${s.batch})</option>`).join('');
    }
    if (facRes.success) {
        document.getElementById('soFacultyId').innerHTML = '<option value="">Select Faculty...</option>' +
            facRes.data.map(f => `<option value="${f.id}">${f.name} (${f.department})</option>`).join('');
    }
}

document.getElementById('subjectOfferingForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        subject_id: parseInt(document.getElementById('soSubjectId').value),
        semester_id: parseInt(document.getElementById('soSemesterId').value),
        faculty_id: parseInt(document.getElementById('soFacultyId').value)
    };
    try {
        const res = await fetch(`${API_URL}/admin/subject-offering`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            showAlert('soAlert', `✓ ${data.data}`, 'success');
            document.getElementById('subjectOfferingForm').reset();
            loadSubjectOfferingsTable();
        } else {
            showAlert('soAlert', data.detail || 'Failed.');
        }
    } catch (err) {
        showAlert('soAlert', 'Network error.');
    }
});

// -----------------------------------------
// Table: Subjects + Subject Offerings
// -----------------------------------------

async function loadSubjectsTable() {
    const tbody = document.getElementById('subjTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/subjects`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(s => `
                <tr><td class="mono">#${s.id}</td><td>${s.code}</td><td>${s.name}</td><td>${s.department}</td><td><button class="btn-delete" onclick="deleteItem('subject',${s.id},'subjects')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="color:var(--text-secondary)">No subjects created yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}

async function loadSubjectOfferingsTable() {
    const tbody = document.getElementById('soTableBody');
    try {
        const res = await fetch(`${API_URL}/admin/subject-offerings`, { headers: authHeaders });
        const data = await res.json();
        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(o => `
                <tr><td class="mono">#${o.id}</td><td class="mono">${o.code}</td><td>${o.subject}</td><td>Sem ${o.semester}</td><td>${o.faculty}</td><td><button class="btn-delete" onclick="deleteItem('subject-offering',${o.id},'offerings')">Delete</button></td></tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text-secondary)">No offerings created yet.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" style="color:var(--danger)">Failed to load.</td></tr>';
    }
}
