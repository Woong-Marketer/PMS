from pathlib import Path

base = Path('/home/user/pms_app')
app_path = base / 'app.py'
work_logs_template_path = base / 'templates' / 'work_logs.html'
edit_template_path = base / 'templates' / 'edit_work_log.html'

a = app_path.read_text()
old_block = """@app.route('/work-logs', methods=['GET', 'POST'])
@role_required('member', 'manager', 'superadmin')
def work_logs():
    conn = get_db()
    if request.method == 'POST':
        work_date = request.form.get('work_date', date.today().isoformat())
        entries_json = request.form.get('entries_json', '[]')
        try:
            entries = json.loads(entries_json)
        except json.JSONDecodeError:
            entries = []

        saved_count = 0
        for entry in entries:
            department_id = entry.get('department_id')
            category_id = entry.get('category_id')
            hours = entry.get('hours')
            detail = (entry.get('detail') or '').strip()
            if department_id and category_id and hours and detail:
                conn.execute(
                    \"\"\"
                    INSERT INTO work_logs (user_id, work_date, department_id, category_id, hours, detail, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    \"\"\",
                    (
                        session['user_id'],
                        work_date,
                        int(department_id),
                        int(category_id),
                        float(hours),
                        detail,
                        datetime.now().isoformat(timespec='seconds')
                    )
                )
                saved_count += 1
        conn.commit()
        if saved_count:
            flash(f'{saved_count}건의 업무 일지가 저장되었습니다.', 'success')
        else:
            flash('저장할 유효한 업무 항목이 없습니다.', 'warning')
        return redirect(url_for('work_logs'))

    if session.get('role') in ['superadmin', 'manager']:
        logs = conn.execute(
            \"\"\"
            SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
            FROM work_logs wl
            JOIN users u ON wl.user_id = u.id
            JOIN departments d ON wl.department_id = d.id
            JOIN task_categories tc ON wl.category_id = tc.id
            ORDER BY wl.work_date DESC, wl.id DESC
            LIMIT 100
            \"\"\"
        ).fetchall()
    else:
        logs = conn.execute(
            \"\"\"
            SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
            FROM work_logs wl
            JOIN users u ON wl.user_id = u.id
            JOIN departments d ON wl.department_id = d.id
            JOIN task_categories tc ON wl.category_id = tc.id
            WHERE wl.user_id = ?
            ORDER BY wl.work_date DESC, wl.id DESC
            LIMIT 100
            \"\"\",
            (session['user_id'],)
        ).fetchall()

    departments = get_departments_with_categories()
    conn.close()
    return render_template('work_logs.html', logs=logs, departments=departments)


@app.route('/dashboard')
"""
new_block = """def can_manage_work_log(log_row):
    return session.get('role') in ['superadmin', 'manager'] or log_row['user_id'] == session.get('user_id')


@app.route('/work-logs', methods=['GET', 'POST'])
@role_required('member', 'manager', 'superadmin')
def work_logs():
    conn = get_db()
    if request.method == 'POST':
        work_date = request.form.get('work_date', date.today().isoformat())
        entries_json = request.form.get('entries_json', '[]')
        try:
            entries = json.loads(entries_json)
        except json.JSONDecodeError:
            entries = []

        saved_count = 0
        for entry in entries:
            department_id = entry.get('department_id')
            category_id = entry.get('category_id')
            hours = entry.get('hours')
            detail = (entry.get('detail') or '').strip()
            if department_id and category_id and hours and detail:
                conn.execute(
                    \"\"\"
                    INSERT INTO work_logs (user_id, work_date, department_id, category_id, hours, detail, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    \"\"\",
                    (
                        session['user_id'],
                        work_date,
                        int(department_id),
                        int(category_id),
                        float(hours),
                        detail,
                        datetime.now().isoformat(timespec='seconds')
                    )
                )
                saved_count += 1
        conn.commit()
        if saved_count:
            flash(f'{saved_count}건의 업무 일지가 저장되었습니다.', 'success')
        else:
            flash('저장할 유효한 업무 항목이 없습니다.', 'warning')
        return redirect(url_for('work_logs'))

    if session.get('role') in ['superadmin', 'manager']:
        logs = conn.execute(
            \"\"\"
            SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
            FROM work_logs wl
            JOIN users u ON wl.user_id = u.id
            JOIN departments d ON wl.department_id = d.id
            JOIN task_categories tc ON wl.category_id = tc.id
            ORDER BY wl.work_date DESC, wl.id DESC
            LIMIT 100
            \"\"\"
        ).fetchall()
    else:
        logs = conn.execute(
            \"\"\"
            SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
            FROM work_logs wl
            JOIN users u ON wl.user_id = u.id
            JOIN departments d ON wl.department_id = d.id
            JOIN task_categories tc ON wl.category_id = tc.id
            WHERE wl.user_id = ?
            ORDER BY wl.work_date DESC, wl.id DESC
            LIMIT 100
            \"\"\",
            (session['user_id'],)
        ).fetchall()

    departments = get_departments_with_categories()
    conn.close()
    return render_template('work_logs.html', logs=logs, departments=departments)


@app.route('/work-logs/<int:log_id>/edit', methods=['GET', 'POST'])
@role_required('member', 'manager', 'superadmin')
def edit_work_log(log_id):
    conn = get_db()
    log = conn.execute(
        \"\"\"
        SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
        FROM work_logs wl
        JOIN users u ON wl.user_id = u.id
        JOIN departments d ON wl.department_id = d.id
        JOIN task_categories tc ON wl.category_id = tc.id
        WHERE wl.id = ?
        \"\"\",
        (log_id,)
    ).fetchone()

    if not log:
        conn.close()
        flash('업무 일지를 찾을 수 없습니다.', 'warning')
        return redirect(url_for('work_logs'))

    if not can_manage_work_log(log):
        conn.close()
        flash('본인이 작성한 업무 일지만 수정할 수 있습니다.', 'danger')
        return redirect(url_for('work_logs'))

    if request.method == 'POST':
        work_date = request.form.get('work_date', '').strip()
        department_id = request.form.get('department_id', '').strip()
        category_id = request.form.get('category_id', '').strip()
        hours = request.form.get('hours', '').strip()
        detail = request.form.get('detail', '').strip()

        if not work_date or not department_id or not category_id or not hours or not detail:
            flash('모든 항목을 입력해주세요.', 'danger')
        else:
            category_match = conn.execute(
                'SELECT id FROM task_categories WHERE id = ? AND department_id = ?',
                (int(category_id), int(department_id))
            ).fetchone()
            if not category_match:
                flash('선택한 부서와 업무 분류가 일치하지 않습니다.', 'danger')
            else:
                conn.execute(
                    \"\"\"
                    UPDATE work_logs
                    SET work_date = ?, department_id = ?, category_id = ?, hours = ?, detail = ?
                    WHERE id = ?
                    \"\"\",
                    (work_date, int(department_id), int(category_id), float(hours), detail, log_id)
                )
                conn.commit()
                conn.close()
                flash('업무 일지가 수정되었습니다.', 'success')
                return redirect(url_for('work_logs'))

    departments = get_departments_with_categories()
    conn.close()
    return render_template('edit_work_log.html', log=log, departments=departments)


@app.route('/work-logs/<int:log_id>/delete', methods=['POST'])
@role_required('member', 'manager', 'superadmin')
def delete_work_log(log_id):
    conn = get_db()
    log = conn.execute('SELECT id, user_id FROM work_logs WHERE id = ?', (log_id,)).fetchone()

    if not log:
        conn.close()
        flash('업무 일지를 찾을 수 없습니다.', 'warning')
        return redirect(url_for('work_logs'))

    if not can_manage_work_log(log):
        conn.close()
        flash('본인이 작성한 업무 일지만 삭제할 수 있습니다.', 'danger')
        return redirect(url_for('work_logs'))

    conn.execute('DELETE FROM work_logs WHERE id = ?', (log_id,))
    conn.commit()
    conn.close()
    flash('업무 일지가 삭제되었습니다.', 'info')
    return redirect(url_for('work_logs'))


@app.route('/dashboard')
"""
if old_block not in a:
    raise SystemExit('app.py target block not found')
a = a.replace(old_block, new_block)
app_path.write_text(a)

work_logs_template_path.write_text("""{% extends 'base.html' %}
{% block title %}업무 일지 | 사내 PMS{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h2 class="fw-bold mb-1">일일 업무 일지</h2>
        <p class="text-muted mb-0">업무 등록은 팝업에서, 기존 기록의 수정과 삭제는 목록에서 바로 관리할 수 있습니다.</p>
    </div>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#logModal">업무 등록</button>
</div>

<div class="card shadow-sm">
    <div class="card-body">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="fw-bold mb-0">최근 업무 기록</h5>
            <span class="text-muted small">최대 100건</span>
        </div>
        <div class="table-responsive">
            <table class="table align-middle">
                <thead>
                    <tr>
                        <th>일자</th>
                        <th>작성자</th>
                        <th>부서</th>
                        <th>업무 분류</th>
                        <th>소요 시간</th>
                        <th>상세 내용</th>
                        <th>관리</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in logs %}
                    <tr>
                        <td>{{ log.work_date }}</td>
                        <td>{{ log.user_name }}</td>
                        <td>{{ log.department_name }}</td>
                        <td>{{ log.category_name }}</td>
                        <td>{{ log.hours }}시간</td>
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
                        <td colspan="7">
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
                    <div class="text-muted small">부서 → 업무 분류 → 소요 시간 → 상세 내용 순서로 입력하세요.</div>
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

edit_template_path.write_text("""{% extends 'base.html' %}
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
        {% set selected_hours = request.form.get('hours', '%.1f'|format(log.hours)) %}
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
                <div class="col-md-3">
                    <label class="form-label">업무 분류</label>
                    <select class="form-select" id="categorySelect" name="category_id" required></select>
                </div>
                <div class="col-md-3">
                    <label class="form-label">소요 시간</label>
                    <select class="form-select" name="hours" required>
                        {% for step in range(1, 25) %}
                        {% set hour_value = '%.1f'|format(step * 0.5) %}
                        <option value="{{ hour_value }}" {% if selected_hours == hour_value %}selected{% endif %}>{{ hour_value }}시간</option>
                        {% endfor %}
                    </select>
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
const selectedCategoryId = {{ selected_category_id|tojson }};

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

print('UPDATED_WORKLOG_PERMISSIONS')
