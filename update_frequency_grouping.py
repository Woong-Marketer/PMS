from pathlib import Path

base = Path('/home/user/pms_app')
app_path = base / 'app.py'
work_logs_template = base / 'templates' / 'work_logs.html'
edit_template = base / 'templates' / 'edit_work_log.html'
work_logs_js = base / 'static' / 'js' / 'work_logs.js'
dashboard_template = base / 'templates' / 'dashboard.html'
dashboard_js = base / 'static' / 'js' / 'dashboard.js'
test_path = base / 'test_app.py'

app = app_path.read_text()
replacements = [
("""def enrich_work_logs(logs):
    users = {int(user['id']): user for user in storage.list_users()}
    departments = {int(dep['id']): dep for dep in storage.list_departments()}
    categories = {int(cat['id']): cat for cat in storage.list_categories()}
    enriched = []
    for log in logs:
        enriched.append({
            **log,
            'id': int(log['id']),
            'user_id': int(log['user_id']),
            'department_id': int(log['department_id']),
            'category_id': int(log['category_id']),
            'hours': float(log['hours']),
            'user_name': users.get(int(log['user_id']), {}).get('name', '-'),
            'department_name': departments.get(int(log['department_id']), {}).get('name', '-'),
            'category_name': categories.get(int(log['category_id']), {}).get('name', '-')
        })
    enriched.sort(key=lambda row: (row['work_date'], row['id']), reverse=True)
    return enriched
""",
"""def enrich_work_logs(logs):
    users = {int(user['id']): user for user in storage.list_users()}
    departments = {int(dep['id']): dep for dep in storage.list_departments()}
    categories = {int(cat['id']): cat for cat in storage.list_categories()}
    enriched = []
    for log in logs:
        enriched.append({
            **log,
            'id': int(log['id']),
            'user_id': int(log['user_id']),
            'department_id': int(log['department_id']),
            'category_id': int(log['category_id']),
            'hours': float(log.get('hours', 1) or 1),
            'user_name': users.get(int(log['user_id']), {}).get('name', '-'),
            'department_name': departments.get(int(log['department_id']), {}).get('name', '-'),
            'category_name': categories.get(int(log['category_id']), {}).get('name', '-')
        })
    enriched.sort(key=lambda row: (row['work_date'], row['id']), reverse=True)
    enriched.sort(key=lambda row: row['department_name'])
    enriched.sort(key=lambda row: row['user_name'])
    return enriched
"""),
("""        if user['status'] == 'pending':
            flash('회원가입 신청은 완료되었지만 아직 관리자 승인이 필요합니다.', 'warning')
            return render_template('login.html')

        if user['status'] == 'rejected':
            flash('이 계정은 관리자에 의해 반려되었습니다. 관리자에게 문의해주세요.', 'danger')
            return render_template('login.html')
""",
"""        user_status = user.get('status', 'approved')
        if user_status == 'pending':
            flash('회원가입 신청은 완료되었지만 아직 관리자 승인이 필요합니다.', 'warning')
            return render_template('login.html')

        if user_status == 'rejected':
            flash('이 계정은 관리자에 의해 반려되었습니다. 관리자에게 문의해주세요.', 'danger')
            return render_template('login.html')
"""),
("""    pending_users = sorted([user for user in all_users if user['status'] == 'pending'], key=lambda row: (row['created_at'], int(row['id'])))
    approved_users = sorted([user for user in all_users if user['status'] == 'approved'], key=lambda row: int(row['id']))
    rejected_users = sorted([user for user in all_users if user['status'] == 'rejected'], key=lambda row: (row['created_at'], int(row['id'])), reverse=True)
""",
"""    pending_users = sorted([user for user in all_users if user.get('status', 'approved') == 'pending'], key=lambda row: (row['created_at'], int(row['id'])))
    approved_users = sorted([user for user in all_users if user.get('status', 'approved') == 'approved'], key=lambda row: int(row['id']))
    rejected_users = sorted([user for user in all_users if user.get('status', 'approved') == 'rejected'], key=lambda row: (row['created_at'], int(row['id'])), reverse=True)
"""),
("""        for entry in entries:
            department_id = entry.get('department_id')
            category_id = entry.get('category_id')
            hours = entry.get('hours')
            detail = (entry.get('detail') or '').strip()
            if department_id and category_id and hours and detail:
                category = storage.get_category_by_id(int(category_id))
                if not category or int(category['department_id']) != int(department_id):
                    continue
                storage.create_work_log(
                    session['user_id'],
                    work_date,
                    int(department_id),
                    int(category_id),
                    float(hours),
                    detail,
                    datetime.now().isoformat(timespec='seconds')
                )
                saved_count += 1
""",
"""        for entry in entries:
            department_id = entry.get('department_id')
            category_id = entry.get('category_id')
            detail = (entry.get('detail') or '').strip()
            if department_id and category_id and detail:
                category = storage.get_category_by_id(int(category_id))
                if not category or int(category['department_id']) != int(department_id):
                    continue
                storage.create_work_log(
                    session['user_id'],
                    work_date,
                    int(department_id),
                    int(category_id),
                    1.0,
                    detail,
                    datetime.now().isoformat(timespec='seconds')
                )
                saved_count += 1
"""),
("""        category_id = request.form.get('category_id', '').strip()
        hours = request.form.get('hours', '').strip()
        detail = request.form.get('detail', '').strip()

        if not work_date or not department_id or not category_id or not hours or not detail:
            flash('모든 항목을 입력해주세요.', 'danger')
        else:
            category = storage.get_category_by_id(int(category_id)) if category_id.isdigit() else None
            if not category or int(category['department_id']) != int(department_id):
                flash('선택한 부서와 업무 분류가 일치하지 않습니다.', 'danger')
            else:
                storage.update_work_log(log_id, work_date, int(department_id), int(category_id), float(hours), detail)
                flash('업무 일지가 수정되었습니다.', 'success')
                return redirect(url_for('work_logs'))
""",
"""        category_id = request.form.get('category_id', '').strip()
        detail = request.form.get('detail', '').strip()

        if not work_date or not department_id or not category_id or not detail:
            flash('모든 항목을 입력해주세요.', 'danger')
        else:
            category = storage.get_category_by_id(int(category_id)) if category_id.isdigit() else None
            if not category or int(category['department_id']) != int(department_id):
                flash('선택한 부서와 업무 분류가 일치하지 않습니다.', 'danger')
            else:
                storage.update_work_log(log_id, work_date, int(department_id), int(category_id), 1.0, detail)
                flash('업무 일지가 수정되었습니다.', 'success')
                return redirect(url_for('work_logs'))
"""),
("""def dashboard():
    members = [user for user in storage.list_users() if user['status'] == 'approved' and user['role'] in ['member', 'manager', 'superadmin']]
    members.sort(key=lambda user: user['name'])
    return render_template('dashboard.html', members=members)
""",
"""def dashboard():
    members = [user for user in storage.list_users() if user.get('status', 'approved') == 'approved' and user.get('role', 'member') in ['member', 'manager', 'superadmin']]
    members.sort(key=lambda user: user['name'])
    return render_template('dashboard.html', members=members)
"""),
("""    enriched = enrich_work_logs(filtered_logs)
    total_hours = round(sum(float(log['hours']) for log in enriched), 2)

    category_totals = {}
    for log in enriched:
        category_totals.setdefault(log['category_name'], 0.0)
        category_totals[log['category_name']] += float(log['hours'])

    categories = []
    for label, value in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
        value = round(value, 2)
        percent = round((value / total_hours) * 100, 1) if total_hours else 0
        categories.append({'label': label, 'value': value, 'percent': percent})

    return jsonify({
        'period': period,
        'range': {'start': start_date, 'end': end_date},
        'total_hours': total_hours,
        'departments': [],
        'categories': categories,
        'daily': []
    })
""",
"""    enriched = enrich_work_logs(filtered_logs)
    total_count = len(enriched)

    category_totals = {}
    for log in enriched:
        category_totals.setdefault(log['category_name'], 0)
        category_totals[log['category_name']] += 1

    categories = []
    for label, value in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
        percent = round((value / total_count) * 100, 1) if total_count else 0
        categories.append({'label': label, 'value': value, 'percent': percent})

    return jsonify({
        'period': period,
        'range': {'start': start_date, 'end': end_date},
        'total_count': total_count,
        'departments': [],
        'categories': categories,
        'daily': []
    })
""")
]

for old, new in replacements:
    if old not in app:
        raise SystemExit(f'Pattern not found in app.py:\n{old[:120]}')
    app = app.replace(old, new)
app_path.write_text(app)

work_logs_template.write_text("""{% extends 'base.html' %}
{% block title %}업무 일지 | 사내 PMS{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h2 class="fw-bold mb-1">일일 업무 일지</h2>
        <p class="text-muted mb-0">업무 등록은 팝업에서, 기존 기록은 직원별로 묶어서 확인하고 수정·삭제할 수 있습니다.</p>
    </div>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#logModal">업무 등록</button>
</div>

<div class="card shadow-sm">
    <div class="card-body">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="fw-bold mb-0">최근 업무 기록</h5>
            <span class="text-muted small">직원명 기준 묶음 정렬 · 최대 100건</span>
        </div>
        <div class="table-responsive">
            <table class="table align-middle">
                <thead>
                    <tr>
                        <th>일자</th>
                        <th>작성자</th>
                        <th>부서</th>
                        <th>업무 분류</th>
                        <th>상세 내용</th>
                        <th>관리</th>
                    </tr>
                </thead>
                <tbody>
                    {% set ns = namespace(current_user='') %}
                    {% for log in logs %}
                        {% if log.user_name != ns.current_user %}
                        <tr class="table-light">
                            <td colspan="6" class="fw-semibold">{{ log.user_name }} 업무 기록</td>
                        </tr>
                        {% set ns.current_user = log.user_name %}
                        {% endif %}
                        <tr>
                            <td>{{ log.work_date }}</td>
                            <td>{{ log.user_name }}</td>
                            <td>{{ log.department_name }}</td>
                            <td>{{ log.category_name }}</td>
                            <td>{{ log.detail }}</td>
                            <td>
                                {% if session.get('role') in ['superadmin', 'manager'] or session.get('user_id') == log.user_id %}
                                <div class="d-flex gap-2 flex-wrap">
                                    <a href="{{ url_for('edit_work_log', log_id=log.id) }}" class="btn btn-sm btn-outline-primary">수정</a>
                                    <form method="post" action="{{ url_for('delete_work_log', log_id=log.id) }}" onsubmit="return confirm('해당 업무 일지를 삭제할까요?');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger">삭제</button>
                                    </form>
                                </div>
                                {% else %}
                                <span class="text-muted small">권한 없음</span>
                                {% endif %}
                            </td>
                        </tr>
                    {% else %}
                    <tr>
                        <td colspan="6">
                            <div class="empty-state">아직 등록된 업무 기록이 없습니다.</div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<div class="modal fade" id="logModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content border-0 shadow-lg rounded-4">
            <div class="modal-header">
                <div>
                    <h5 class="modal-title fw-bold">업무 일지 작성</h5>
                    <div class="text-muted small">부서 → 업무 분류 → 상세 내용 순서로 입력하세요.</div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="post" id="workLogForm">
                <div class="modal-body">
                    <div class="row g-3 align-items-end mb-4">
                        <div class="col-md-4 col-lg-3">
                            <label class="form-label">업무 일자</label>
                            <input type="date" class="form-control" name="work_date" value="{{ today_str }}" required>
                        </div>
                    </div>
                    <div id="entryRows"></div>
                    <input type="hidden" name="entries_json" id="entriesJson">
                    <button type="button" class="btn btn-outline-primary" id="addEntryBtn">업무 추가 +</button>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">닫기</button>
                    <button type="submit" class="btn btn-primary">업무 일지 저장</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script id="departments-data" type="application/json">{{ departments|tojson }}</script>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/work_logs.js') }}"></script>
{% endblock %}
""")

work_logs_js.write_text("""const departmentsData = JSON.parse(document.getElementById('departments-data').textContent);
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
""")

edit_template.write_text("""{% extends 'base.html' %}
{% block title %}업무 일지 수정 | 사내 PMS{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h2 class="fw-bold mb-1">업무 일지 수정</h2>
        <p class="text-muted mb-0">작성한 업무 내용을 수정할 수 있으며, 중간 관리자와 대표 관리자는 전체 기록을 관리할 수 있습니다.</p>
    </div>
    <a href="{{ url_for('work_logs') }}" class="btn btn-outline-secondary">목록으로</a>
</div>

<div class="card shadow-sm">
    <div class="card-body p-4">
        {% set selected_department_id = request.form.get('department_id', log.department_id|string) %}
        {% set selected_category_id = request.form.get('category_id', log.category_id|string) %}
        <form method="post">
            <div class="row g-3">
                <div class="col-md-3">
                    <label class="form-label">업무 일자</label>
                    <input type="date" class="form-control" name="work_date" value="{{ request.form.get('work_date', log.work_date) }}" required>
                </div>
                <div class="col-md-3">
                    <label class="form-label">부서</label>
                    <select class="form-select" id="departmentSelect" name="department_id" required>
                        <option value="">부서 선택</option>
                        {% for dep in departments %}
                        <option value="{{ dep.id }}" {% if selected_department_id == dep.id|string %}selected{% endif %}>{{ dep.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">업무 분류</label>
                    <select class="form-select" id="categorySelect" name="category_id" required></select>
                </div>
                <div class="col-12">
                    <label class="form-label">상세 내용</label>
                    <textarea class="form-control" name="detail" rows="5" placeholder="상세 업무 내용을 입력하세요" required>{{ request.form.get('detail', log.detail) }}</textarea>
                </div>
            </div>
            <div class="d-flex justify-content-end gap-2 mt-4">
                <a href="{{ url_for('work_logs') }}" class="btn btn-light">취소</a>
                <button type="submit" class="btn btn-primary">수정 저장</button>
            </div>
        </form>
    </div>
</div>

<script id="departments-data" type="application/json">{{ departments|tojson }}</script>
{% endblock %}

{% block scripts %}
<script>
const departmentsData = JSON.parse(document.getElementById('departments-data').textContent);
const departmentSelect = document.getElementById('departmentSelect');
const categorySelect = document.getElementById('categorySelect');
const selectedCategoryId = {{ request.form.get('category_id', log.category_id|string)|tojson }};

function buildCategoryOptions(departmentId, currentCategoryId) {
    const department = departmentsData.find(dep => String(dep.id) === String(departmentId));
    if (!department) {
        categorySelect.innerHTML = '<option value="">업무 분류 선택</option>';
        return;
    }

    const options = ['<option value="">업무 분류 선택</option>']
        .concat(department.categories.map(cat => {
            const selected = String(cat.id) === String(currentCategoryId) ? 'selected' : '';
            return `<option value="${cat.id}" ${selected}>${cat.name}</option>`;
        }));
    categorySelect.innerHTML = options.join('');
}

buildCategoryOptions(departmentSelect.value, selectedCategoryId);
departmentSelect.addEventListener('change', () => buildCategoryOptions(departmentSelect.value, ''));
</script>
{% endblock %}
""")

dashboard_template.write_text("""{% extends 'base.html' %}
{% block title %}대시보드 | 사내 PMS{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-3">
    <div>
        <h2 class="fw-bold mb-1">업무 기록 대시보드</h2>
        <p class="text-muted mb-0">일별·주별·월별 기준으로 어떤 업무를 자주 작성하는지 횟수 중심으로 확인할 수 있습니다.</p>
    </div>
</div>

<div class="filter-bar mb-4">
    <div class="row g-3 align-items-end">
        <div class="col-md-3">
            <label class="form-label">기간 필터</label>
            <select class="form-select" id="periodFilter">
                <option value="day">일별</option>
                <option value="week">주별</option>
                <option value="month">월별</option>
            </select>
        </div>
        <div class="col-md-4">
            <label class="form-label">팀원 필터</label>
            <select class="form-select" id="memberFilter">
                <option value="all">전체 팀원</option>
                {% for member in members %}
                <option value="{{ member.id }}">{{ member.name }} ({{ role_labels.get(member.role) }})</option>
                {% endfor %}
            </select>
        </div>
        <div class="col-md-2">
            <button class="btn btn-primary w-100" id="loadDashboardBtn">적용</button>
        </div>
    </div>
</div>

<div class="row g-4">
    <div class="col-12">
        <div class="card shadow-sm h-100">
            <div class="card-body">
                <h5 class="fw-bold mb-3">업무 분류별 작성 빈도</h5>
                <div class="chart-wrap"><canvas id="categoryChart"></canvas></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
{% endblock %}
""")

dashboard_js.write_text("""let categoryChart;

const palette = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#f97316'];

function buildChart(canvasId, type, labels, values, label, options = {}) {
    const canvas = document.getElementById(canvasId);
    const chartMap = {
        categoryChart,
    };
    if (chartMap[canvasId]) {
        chartMap[canvasId].destroy();
    }

    const instance = new Chart(canvas, {
        type,
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                backgroundColor: type === 'bar' ? '#4f46e5' : palette,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: type !== 'bar'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw}건`;
                        }
                    }
                }
            },
            scales: type === 'bar' ? {
                y: { beginAtZero: true }
            } : {},
            ...options
        }
    });

    if (canvasId === 'categoryChart') categoryChart = instance;
}

async function loadDashboard() {
    const period = document.getElementById('periodFilter').value;
    const userId = document.getElementById('memberFilter').value;

    const response = await fetch(`/api/dashboard-data?period=${period}&user_id=${userId}`);
    const data = await response.json();

    buildChart(
        'categoryChart',
        'pie',
        data.categories.map(item => `${item.label} (${item.percent}%)`),
        data.categories.map(item => item.value),
        '업무 분류별 작성 건수'
    );
}

document.getElementById('loadDashboardBtn').addEventListener('click', loadDashboard);
window.addEventListener('DOMContentLoaded', loadDashboard);
""")

test_path.write_text("""import os
import json
import tempfile
import importlib

DB_FILE = os.path.join(tempfile.gettempdir(), 'pms_test_grouping_frequency.db')
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

os.environ['DATABASE_BACKEND'] = 'sqlite'
os.environ['DATABASE_PATH'] = DB_FILE
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['INITIAL_ADMIN_USERNAME'] = 'admin'
os.environ['INITIAL_ADMIN_PASSWORD'] = 'admin1234'
os.environ['INITIAL_ADMIN_NAME'] = '대표 관리자'
os.environ['ENABLE_DEMO_USERS'] = 'false'
os.environ['ENABLE_DEMO_DATA'] = 'false'

app_module = importlib.import_module('app')
app = app_module.app
client = app.test_client()


def login(username, password):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def logout():
    return client.get('/logout', follow_redirects=True)


# 대표 관리자 로그인
admin_login = login('admin', 'admin1234')
assert admin_login.status_code == 200
assert '대시보드'.encode('utf-8') in admin_login.data

# 테스트 사용자 생성
for user_data in [
    {'name': 'A직원', 'username': 'membera', 'password': 'pw123456', 'role': 'member'},
    {'name': 'B직원', 'username': 'memberb', 'password': 'pw123456', 'role': 'member'},
    {'name': 'D관리자', 'username': 'manager1', 'password': 'pw123456', 'role': 'manager'},
]:
    response = client.post('/users', data=user_data, follow_redirects=True)
    assert response.status_code == 200
    assert '즉시 승인 상태'.encode('utf-8') in response.data

with app_module.get_db() as conn:
    department_marketing = conn.execute("SELECT id FROM departments WHERE name = '마케팅&경영지원'").fetchone()['id']
    department_production = conn.execute("SELECT id FROM departments WHERE name = '생산팀'").fetchone()['id']
    category_content = conn.execute("SELECT id FROM task_categories WHERE name = '콘텐츠 제작'").fetchone()['id']
    category_ad = conn.execute("SELECT id FROM task_categories WHERE name = '광고 운영'").fetchone()['id']
    category_quality = conn.execute("SELECT id FROM task_categories WHERE name = '품질 점검'").fetchone()['id']

logout()

# A직원 업무일지 2건 작성
login('membera', 'pw123456')
create_logs_a = client.post('/work-logs', data={
    'work_date': '2026-06-17',
    'entries_json': json.dumps([
        {'department_id': department_marketing, 'category_id': category_content, 'detail': 'A의 첫 번째 기록'},
        {'department_id': department_marketing, 'category_id': category_ad, 'detail': 'A의 두 번째 기록'},
    ])
}, follow_redirects=True)
assert create_logs_a.status_code == 200
assert '2건의 업무 일지가 저장되었습니다.'.encode('utf-8') in create_logs_a.data
logout()

# B직원 업무일지 1건 작성
login('memberb', 'pw123456')
create_logs_b = client.post('/work-logs', data={
    'work_date': '2026-06-17',
    'entries_json': json.dumps([
        {'department_id': department_marketing, 'category_id': category_content, 'detail': 'B의 기록'},
    ])
}, follow_redirects=True)
assert create_logs_b.status_code == 200
assert '1건의 업무 일지가 저장되었습니다.'.encode('utf-8') in create_logs_b.data
logout()

# D관리자 업무일지 1건 작성
login('manager1', 'pw123456')
create_logs_d = client.post('/work-logs', data={
    'work_date': '2026-06-18',
    'entries_json': json.dumps([
        {'department_id': department_production, 'category_id': category_quality, 'detail': 'D의 기록'},
    ])
}, follow_redirects=True)
assert create_logs_d.status_code == 200
logout()

# 관리자 화면에서 직원별 묶음 정렬 확인
login('admin', 'admin1234')
logs_page = client.get('/work-logs')
assert logs_page.status_code == 200
html = logs_page.data.decode('utf-8')
assert '소요 시간' not in html
assert 'A직원 업무 기록' in html
assert 'B직원 업무 기록' in html
assert 'D관리자 업무 기록' in html
assert html.find('A직원 업무 기록') < html.find('B직원 업무 기록') < html.find('D관리자 업무 기록')

with app_module.get_db() as conn:
    member_a_id = conn.execute("SELECT id FROM users WHERE username = 'membera'").fetchone()['id']
    member_a_logs = conn.execute(
        "SELECT id, hours, detail FROM work_logs WHERE user_id = ? ORDER BY id ASC",
        (member_a_id,)
    ).fetchall()
    own_edit_log_id = member_a_logs[0]['id']
    own_delete_log_id = member_a_logs[1]['id']
assert member_a_logs[0]['hours'] == 1.0

# 대시보드가 시간 대신 건수 기준으로 집계되는지 확인
api_response = client.get('/api/dashboard-data?period=month&user_id=all')
assert api_response.status_code == 200
data = api_response.get_json()
assert data['total_count'] == 4
category_map = {item['label']: item['value'] for item in data['categories']}
assert category_map['콘텐츠 제작'] == 2
assert category_map['광고 운영'] == 1
assert category_map['품질 점검'] == 1

# 본인 작성 업무일지 수정 가능 (소요 시간 입력 제거)
own_edit_page = client.get(f'/work-logs/{own_edit_log_id}/edit')
assert own_edit_page.status_code == 200
assert '소요 시간'.encode('utf-8') not in own_edit_page.data

logout()
login('membera', 'pw123456')
own_edit_submit = client.post(f'/work-logs/{own_edit_log_id}/edit', data={
    'work_date': '2026-06-19',
    'department_id': str(department_marketing),
    'category_id': str(category_content),
    'detail': 'A의 수정 완료'
}, follow_redirects=True)
assert own_edit_submit.status_code == 200
assert '업무 일지가 수정되었습니다.'.encode('utf-8') in own_edit_submit.data

with app_module.get_db() as conn:
    edited_log = conn.execute("SELECT work_date, hours, detail FROM work_logs WHERE id = ?", (own_edit_log_id,)).fetchone()
assert edited_log['work_date'] == '2026-06-19'
assert edited_log['hours'] == 1.0
assert edited_log['detail'] == 'A의 수정 완료'

# 본인 작성 업무일지 삭제 가능
own_delete_submit = client.post(f'/work-logs/{own_delete_log_id}/delete', follow_redirects=True)
assert own_delete_submit.status_code == 200
assert '업무 일지가 삭제되었습니다.'.encode('utf-8') in own_delete_submit.data

with app_module.get_db() as conn:
    deleted_log = conn.execute("SELECT id FROM work_logs WHERE id = ?", (own_delete_log_id,)).fetchone()
assert deleted_log is None

# 다른 일반 팀원은 타인 글 수정/삭제 불가
logout()
login('memberb', 'pw123456')
forbidden_edit = client.post(f'/work-logs/{own_edit_log_id}/edit', data={
    'work_date': '2026-06-20',
    'department_id': str(department_marketing),
    'category_id': str(category_content),
    'detail': '타인 수정 시도'
}, follow_redirects=True)
assert forbidden_edit.status_code == 200
assert '본인이 작성한 업무 일지만 수정할 수 있습니다.'.encode('utf-8') in forbidden_edit.data

forbidden_delete = client.post(f'/work-logs/{own_edit_log_id}/delete', follow_redirects=True)
assert forbidden_delete.status_code == 200
assert '본인이 작성한 업무 일지만 삭제할 수 있습니다.'.encode('utf-8') in forbidden_delete.data

# 중간 관리자는 모든 업무일지 수정 가능
logout()
login('manager1', 'pw123456')
manager_edit = client.post(f'/work-logs/{own_edit_log_id}/edit', data={
    'work_date': '2026-06-21',
    'department_id': str(department_marketing),
    'category_id': str(category_content),
    'detail': '중간관리자 수정 완료'
}, follow_redirects=True)
assert manager_edit.status_code == 200
assert '업무 일지가 수정되었습니다.'.encode('utf-8') in manager_edit.data

with app_module.get_db() as conn:
    manager_edited_log = conn.execute("SELECT work_date, hours, detail FROM work_logs WHERE id = ?", (own_edit_log_id,)).fetchone()
assert manager_edited_log['work_date'] == '2026-06-21'
assert manager_edited_log['hours'] == 1.0
assert manager_edited_log['detail'] == '중간관리자 수정 완료'

# 대표 관리자는 모든 업무일지 삭제 가능
logout()
login('admin', 'admin1234')
admin_delete = client.post(f'/work-logs/{own_edit_log_id}/delete', follow_redirects=True)
assert admin_delete.status_code == 200
assert '업무 일지가 삭제되었습니다.'.encode('utf-8') in admin_delete.data

with app_module.get_db() as conn:
    removed_by_admin = conn.execute("SELECT id FROM work_logs WHERE id = ?", (own_edit_log_id,)).fetchone()
assert removed_by_admin is None

print('ALL_TESTS_PASSED')
""")

print('UPDATED_GROUPING_AND_FREQUENCY')
