const departmentsData = JSON.parse(document.getElementById('departments-data').textContent);
const entryRows = document.getElementById('entryRows');
const addEntryBtn = document.getElementById('addEntryBtn');
const workLogForm = document.getElementById('workLogForm');
const entriesJson = document.getElementById('entriesJson');
const selectedDepartmentId = JSON.parse(document.getElementById('selected-department-id').textContent || '""');

function buildDepartmentOptions(currentDepartmentId = '') {
    return ['<option value="">부서 선택</option>']
        .concat(departmentsData.map(dep => {
            const selected = String(dep.id) === String(currentDepartmentId) ? 'selected' : '';
            return `<option value="${dep.id}" ${selected}>${dep.name}</option>`;
        }))
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

function createEntryRow(defaultDepartmentId = '', defaultCategoryId = '', defaultDetail = '') {
    const wrapper = document.createElement('div');
    wrapper.className = 'work-entry-row';
    wrapper.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <strong>업무 항목</strong>
            <button type="button" class="btn btn-sm btn-outline-danger remove-entry-btn">삭제</button>
        </div>
        <div class="row g-3">
            <div class="col-lg-3">
                <label class="form-label">부서</label>
                <select class="form-select department-select" required>${buildDepartmentOptions(defaultDepartmentId)}</select>
            </div>
            <div class="col-lg-3">
                <label class="form-label">업무 분류</label>
                <select class="form-select category-select" required>
                    <option value="">업무 분류 선택</option>
                </select>
            </div>
            <div class="col-lg-6">
                <label class="form-label">상세 내용</label>
                <input type="text" class="form-control detail-input" placeholder="예: 광고 소재 검수, 거래처 응대, 샘플 테스트" value="${defaultDetail}" required>
            </div>
        </div>
    `;

    const departmentSelect = wrapper.querySelector('.department-select');
    const categorySelect = wrapper.querySelector('.category-select');
    const detailInput = wrapper.querySelector('.detail-input');
    const removeBtn = wrapper.querySelector('.remove-entry-btn');

    const syncCategories = (currentCategoryId = '') => {
        categorySelect.innerHTML = buildCategoryOptions(departmentSelect.value);
        if (currentCategoryId) {
            categorySelect.value = String(currentCategoryId);
        }
    };

    syncCategories(defaultCategoryId);

    departmentSelect.addEventListener('change', () => {
        syncCategories('');
        categorySelect.focus();
    });

    categorySelect.addEventListener('change', () => {
        if (categorySelect.value) {
            detailInput.focus();
        }
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

function getLastSelectedDepartmentId() {
    const rows = Array.from(document.querySelectorAll('.work-entry-row'));
    const lastRow = rows[rows.length - 1];
    return lastRow ? lastRow.querySelector('.department-select').value : '';
}

addEntryBtn.addEventListener('click', () => createEntryRow(getLastSelectedDepartmentId() || selectedDepartmentId));

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

createEntryRow(selectedDepartmentId);
