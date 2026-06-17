const departmentsData = JSON.parse(document.getElementById('departments-data').textContent);
const entryRows = document.getElementById('entryRows');
const addEntryBtn = document.getElementById('addEntryBtn');
const workLogForm = document.getElementById('workLogForm');
const entriesJson = document.getElementById('entriesJson');

function buildDepartmentOptions() {
    return ['<option value="">부서 선택</option>']
        .concat(departmentsData.map(dep => `<option value="${dep.id}">${dep.name}</option>`))
        .join('');
}

function buildCategoryOptions(departmentId) {
    const department = departmentsData.find(dep => String(dep.id) === String(departmentId));
    if (!department) {
        return '<option value="">업무 분류 선택</option>';
    }
    return ['<option value="">업무 분류 선택</option>']
        .concat(department.categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`))
        .join('');
}

function createEntryRow() {
    const wrapper = document.createElement('div');
    wrapper.className = 'work-entry-row';
    wrapper.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <strong>업무 항목</strong>
            <button type="button" class="btn btn-sm btn-outline-danger remove-entry-btn">삭제</button>
        </div>
        <div class="row g-3">
            <div class="col-lg-3">
                <label class="form-label">1단계 - 부서 선택</label>
                <select class="form-select department-select" required>${buildDepartmentOptions()}</select>
            </div>
            <div class="col-lg-3">
                <label class="form-label">2단계 - 업무 분류 선택</label>
                <select class="form-select category-select" required>
                    <option value="">업무 분류 선택</option>
                </select>
            </div>
            <div class="col-lg-6">
                <label class="form-label">3단계 - 상세 내용 입력</label>
                <input type="text" class="form-control detail-input" placeholder="상세 업무 내용을 입력하세요" required>
            </div>
        </div>
    `;

    const departmentSelect = wrapper.querySelector('.department-select');
    const categorySelect = wrapper.querySelector('.category-select');
    const removeBtn = wrapper.querySelector('.remove-entry-btn');

    departmentSelect.addEventListener('change', () => {
        categorySelect.innerHTML = buildCategoryOptions(departmentSelect.value);
    });

    removeBtn.addEventListener('click', () => {
        if (document.querySelectorAll('.work-entry-row').length > 1) {
            wrapper.remove();
        } else {
            alert('최소 1개의 업무 항목은 유지되어야 합니다.');
        }
    });

    entryRows.appendChild(wrapper);
}

addEntryBtn.addEventListener('click', createEntryRow);

workLogForm.addEventListener('submit', (event) => {
    const rows = Array.from(document.querySelectorAll('.work-entry-row'));
    const payload = rows.map(row => ({
        department_id: row.querySelector('.department-select').value,
        category_id: row.querySelector('.category-select').value,
        detail: row.querySelector('.detail-input').value.trim()
    }));

    const validEntries = payload.filter(item => item.department_id && item.category_id && item.detail);
    if (!validEntries.length) {
        event.preventDefault();
        alert('최소 1개 이상의 유효한 업무 항목을 입력해주세요.');
        return;
    }
    entriesJson.value = JSON.stringify(validEntries);
});

createEntryRow();
