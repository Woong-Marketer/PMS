from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
import sqlite3
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'pms.db'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'pms-secret-key-change-me')

app = Flask(__name__)
app.secret_key = SECRET_KEY

ROLE_LABELS = {
    'superadmin': '대표 관리자',
    'manager': '중간 관리자',
    'member': '일반 팀원'
}

STATUS_LABELS = {
    'pending': '승인 대기',
    'approved': '승인 완료',
    'rejected': '반려'
}

DEFAULT_DEPARTMENTS = [
    '마케팅&경영지원',
    '연구소',
    '생산팀'
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = get_db()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('superadmin', 'manager', 'member')),
            status TEXT NOT NULL DEFAULT 'approved',
            approved_at TEXT,
            approved_by INTEGER,
            created_at TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS task_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(department_id, name),
            FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            hours REAL NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(department_id) REFERENCES departments(id),
            FOREIGN KEY(category_id) REFERENCES task_categories(id)
        )
    ''')

    user_columns = {row['name'] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if 'status' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'approved'")
    if 'approved_at' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN approved_at TEXT")
    if 'approved_by' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN approved_by INTEGER")
    conn.execute("UPDATE users SET status = 'approved' WHERE status IS NULL OR TRIM(status) = ''")
    conn.commit()

    now = datetime.now().isoformat(timespec='seconds')

    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    if cur.fetchone()['cnt'] == 0:
        admin_username = os.environ.get('INITIAL_ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('INITIAL_ADMIN_PASSWORD', 'admin1234')
        admin_name = os.environ.get('INITIAL_ADMIN_NAME', '대표 관리자')
        bootstrap_users = [
            (admin_username, generate_password_hash(admin_password), admin_name, 'superadmin', 'approved', now, None, now),
        ]

        if os.environ.get('ENABLE_DEMO_USERS', 'false').lower() == 'true':
            bootstrap_users.extend([
                ('manager', generate_password_hash('manager1234'), '중간 관리자', 'manager', 'approved', now, 1, now),
                ('member1', generate_password_hash('member1234'), '팀원 1', 'member', 'approved', now, 1, now),
                ('member2', generate_password_hash('member1234'), '팀원 2', 'member', 'approved', now, 1, now),
            ])

        cur.executemany(
            "INSERT INTO users (username, password_hash, name, role, status, approved_at, approved_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            bootstrap_users
        )

    for dep_name in DEFAULT_DEPARTMENTS:
        cur.execute("INSERT OR IGNORE INTO departments (name, created_at) VALUES (?, ?)", (dep_name, now))

    conn.commit()

    cur.execute("SELECT id, name FROM departments ORDER BY id")
    departments = {row['name']: row['id'] for row in cur.fetchall()}

    default_categories = {
        '마케팅&경영지원': ['콘텐츠 제작', '광고 운영', '거래처 커뮤니케이션'],
        '연구소': ['제품 개발', '샘플 테스트', '기술 문서 작성'],
        '생산팀': ['생산 계획', '조립', '품질 점검']
    }
    for dep_name, categories in default_categories.items():
        department_id = departments.get(dep_name)
        if department_id:
            for category_name in categories:
                cur.execute(
                    "INSERT OR IGNORE INTO task_categories (department_id, name, created_at) VALUES (?, ?, ?)",
                    (department_id, category_name, now)
                )

    conn.commit()

    cur.execute("SELECT COUNT(*) AS cnt FROM work_logs")
    if cur.fetchone()['cnt'] == 0 and os.environ.get('ENABLE_DEMO_DATA', 'false').lower() == 'true':
        users = {row['username']: row['id'] for row in conn.execute("SELECT id, username FROM users").fetchall()}
        departments_by_name = {row['name']: row['id'] for row in conn.execute("SELECT id, name FROM departments").fetchall()}
        categories_by_key = {}
        for row in conn.execute("SELECT tc.id, tc.name, d.name AS department_name FROM task_categories tc JOIN departments d ON tc.department_id = d.id").fetchall():
            categories_by_key[(row['department_name'], row['name'])] = row['id']

        sample_logs = [
            (users.get('member1'), (date.today() - timedelta(days=2)).isoformat(), departments_by_name.get('마케팅&경영지원'), categories_by_key.get(('마케팅&경영지원', '콘텐츠 제작')), 2.0, '브랜드 콘텐츠 기획 및 게시물 작성', now),
            (users.get('member1'), (date.today() - timedelta(days=1)).isoformat(), departments_by_name.get('마케팅&경영지원'), categories_by_key.get(('마케팅&경영지원', '광고 운영')), 1.5, '광고 예산 점검 및 소재 수정', now),
            (users.get('member2'), date.today().isoformat(), departments_by_name.get('연구소'), categories_by_key.get(('연구소', '제품 개발')), 3.0, '시제품 성능 개선 회의 및 테스트', now),
            (users.get('manager'), date.today().isoformat(), departments_by_name.get('생산팀'), categories_by_key.get(('생산팀', '품질 점검')), 2.5, '주간 품질 리포트 검토', now),
        ]
        valid_logs = [row for row in sample_logs if all(row[:5])]
        if valid_logs:
            cur.executemany(
                "INSERT INTO work_logs (user_id, work_date, department_id, category_id, hours, detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                valid_logs
            )
            conn.commit()

    conn.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash('로그인이 필요합니다.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                flash('이 페이지에 접근할 권한이 없습니다.', 'danger')
                return redirect(url_for('home'))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


def get_departments_with_categories():
    conn = get_db()
    departments = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()
    results = []
    for dep in departments:
        cats = conn.execute(
            "SELECT * FROM task_categories WHERE department_id = ? ORDER BY name",
            (dep['id'],)
        ).fetchall()
        results.append({
            'id': dep['id'],
            'name': dep['name'],
            'categories': [dict(cat) for cat in cats]
        })
    conn.close()
    return results


def get_period_range(period: str):
    today = date.today()
    if period == 'day':
        start = end = today
    elif period == 'week':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    else:
        start = today.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


@app.context_processor
def inject_globals():
    return {
        'role_labels': ROLE_LABELS,
        'status_labels': STATUS_LABELS,
        'today_str': date.today().isoformat()
    }


@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('role') in ['superadmin', 'manager']:
            return redirect(url_for('dashboard'))
        return redirect(url_for('work_logs'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if not user or not check_password_hash(user['password_hash'], password):
            flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'danger')
            return render_template('login.html')

        if user['status'] == 'pending':
            flash('회원가입 신청은 완료되었지만 아직 관리자 승인이 필요합니다.', 'warning')
            return render_template('login.html')

        if user['status'] == 'rejected':
            flash('이 계정은 관리자에 의해 반려되었습니다. 관리자에게 문의해주세요.', 'danger')
            return render_template('login.html')

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['name'] = user['name']
        session['role'] = user['role']
        flash(f"{user['name']}님, 환영합니다.", 'success')
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()

        if not username or not password or not name:
            flash('이름, 아이디, 비밀번호를 모두 입력해주세요.', 'danger')
            return render_template('register.html')

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, name, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (username, generate_password_hash(password), name, 'member', 'pending', datetime.now().isoformat(timespec='seconds'))
            )
            conn.commit()
            flash('회원가입 신청이 접수되었습니다. 대표 관리자의 승인 후 로그인할 수 있습니다.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('이미 존재하는 아이디입니다.', 'danger')
            return render_template('register.html')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('login'))


@app.route('/users', methods=['GET', 'POST'])
@role_required('superadmin')
def users():
    conn = get_db()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'member').strip()
        if not username or not password or not name:
            flash('모든 필드를 입력해주세요.', 'danger')
        else:
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, name, role, status, approved_at, approved_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        username,
                        generate_password_hash(password),
                        name,
                        role,
                        'approved',
                        datetime.now().isoformat(timespec='seconds'),
                        session.get('user_id'),
                        datetime.now().isoformat(timespec='seconds')
                    )
                )
                conn.commit()
                flash('사용자가 즉시 승인 상태로 추가되었습니다.', 'success')
                return redirect(url_for('users'))
            except sqlite3.IntegrityError:
                flash('이미 존재하는 아이디입니다.', 'danger')

    pending_users = conn.execute(
        "SELECT * FROM users WHERE status = 'pending' ORDER BY created_at ASC, id ASC"
    ).fetchall()
    approved_users = conn.execute(
        "SELECT * FROM users WHERE status = 'approved' ORDER BY id ASC"
    ).fetchall()
    rejected_users = conn.execute(
        "SELECT * FROM users WHERE status = 'rejected' ORDER BY created_at DESC, id DESC"
    ).fetchall()
    conn.close()
    return render_template(
        'users.html',
        pending_users=pending_users,
        approved_users=approved_users,
        rejected_users=rejected_users
    )


@app.route('/users/<int:user_id>/approve', methods=['POST'])
@role_required('superadmin')
def approve_user(user_id):
    assigned_role = request.form.get('role', 'member').strip()
    if assigned_role not in ROLE_LABELS:
        assigned_role = 'member'

    conn = get_db()
    conn.execute(
        "UPDATE users SET status = 'approved', role = ?, approved_at = ?, approved_by = ? WHERE id = ?",
        (assigned_role, datetime.now().isoformat(timespec='seconds'), session.get('user_id'), user_id)
    )
    conn.commit()
    conn.close()
    flash('회원가입이 승인되었고 권한이 부여되었습니다.', 'success')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/reject', methods=['POST'])
@role_required('superadmin')
def reject_user(user_id):
    conn = get_db()
    conn.execute(
        "UPDATE users SET status = 'rejected', approved_at = NULL, approved_by = ? WHERE id = ?",
        (session.get('user_id'), user_id)
    )
    conn.commit()
    conn.close()
    flash('회원가입 요청이 반려되었습니다.', 'warning')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/role', methods=['POST'])
@role_required('superadmin')
def update_user_role(user_id):
    if user_id == session.get('user_id'):
        flash('현재 로그인한 대표 관리자 자신의 권한은 이 화면에서 변경할 수 없습니다.', 'warning')
        return redirect(url_for('users'))

    role = request.form.get('role', 'member').strip()
    if role not in ROLE_LABELS:
        role = 'member'

    conn = get_db()
    conn.execute("UPDATE users SET role = ? WHERE id = ? AND status = 'approved'", (role, user_id))
    conn.commit()
    conn.close()
    flash('사용자 권한이 변경되었습니다.', 'success')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@role_required('superadmin')
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash('현재 로그인한 대표 관리자 계정은 삭제할 수 없습니다.', 'warning')
        return redirect(url_for('users'))
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash('사용자가 삭제되었습니다.', 'info')
    return redirect(url_for('users'))


@app.route('/settings/departments', methods=['GET', 'POST'])
@role_required('superadmin')
def department_settings():
    conn = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        now = datetime.now().isoformat(timespec='seconds')
        try:
            if action == 'add_department':
                name = request.form.get('department_name', '').strip()
                if name:
                    conn.execute("INSERT INTO departments (name, created_at) VALUES (?, ?)", (name, now))
                    conn.commit()
                    flash('부서가 추가되었습니다.', 'success')
            elif action == 'edit_department':
                department_id = request.form.get('department_id')
                name = request.form.get('department_name', '').strip()
                conn.execute("UPDATE departments SET name = ? WHERE id = ?", (name, department_id))
                conn.commit()
                flash('부서명이 수정되었습니다.', 'success')
            elif action == 'delete_department':
                department_id = request.form.get('department_id')
                conn.execute("DELETE FROM task_categories WHERE department_id = ?", (department_id,))
                conn.execute("DELETE FROM departments WHERE id = ?", (department_id,))
                conn.commit()
                flash('부서가 삭제되었습니다.', 'info')
            elif action == 'add_category':
                department_id = request.form.get('department_id')
                category_name = request.form.get('category_name', '').strip()
                conn.execute(
                    "INSERT INTO task_categories (department_id, name, created_at) VALUES (?, ?, ?)",
                    (department_id, category_name, now)
                )
                conn.commit()
                flash('업무 분류가 추가되었습니다.', 'success')
            elif action == 'edit_category':
                category_id = request.form.get('category_id')
                category_name = request.form.get('category_name', '').strip()
                conn.execute("UPDATE task_categories SET name = ? WHERE id = ?", (category_name, category_id))
                conn.commit()
                flash('업무 분류가 수정되었습니다.', 'success')
            elif action == 'delete_category':
                category_id = request.form.get('category_id')
                conn.execute("DELETE FROM task_categories WHERE id = ?", (category_id,))
                conn.commit()
                flash('업무 분류가 삭제되었습니다.', 'info')
        except sqlite3.IntegrityError:
            flash('중복된 이름이 있어 저장할 수 없습니다.', 'danger')
        return redirect(url_for('department_settings'))

    data = get_departments_with_categories()
    conn.close()
    return render_template('department_settings.html', departments=data)


def can_manage_work_log(log_row):
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
                    """
                    INSERT INTO work_logs (user_id, work_date, department_id, category_id, hours, detail, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
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
            """
            SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
            FROM work_logs wl
            JOIN users u ON wl.user_id = u.id
            JOIN departments d ON wl.department_id = d.id
            JOIN task_categories tc ON wl.category_id = tc.id
            ORDER BY wl.work_date DESC, wl.id DESC
            LIMIT 100
            """
        ).fetchall()
    else:
        logs = conn.execute(
            """
            SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
            FROM work_logs wl
            JOIN users u ON wl.user_id = u.id
            JOIN departments d ON wl.department_id = d.id
            JOIN task_categories tc ON wl.category_id = tc.id
            WHERE wl.user_id = ?
            ORDER BY wl.work_date DESC, wl.id DESC
            LIMIT 100
            """,
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
        """
        SELECT wl.*, u.name AS user_name, d.name AS department_name, tc.name AS category_name
        FROM work_logs wl
        JOIN users u ON wl.user_id = u.id
        JOIN departments d ON wl.department_id = d.id
        JOIN task_categories tc ON wl.category_id = tc.id
        WHERE wl.id = ?
        """,
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
                    """
                    UPDATE work_logs
                    SET work_date = ?, department_id = ?, category_id = ?, hours = ?, detail = ?
                    WHERE id = ?
                    """,
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
@role_required('superadmin', 'manager')
def dashboard():
    conn = get_db()
    members = conn.execute(
        "SELECT id, name, role FROM users WHERE status = 'approved' AND role IN ('member', 'manager', 'superadmin') ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template('dashboard.html', members=members)


@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'})


@app.route('/api/categories/<int:department_id>')
@login_required
def api_categories(department_id):
    conn = get_db()
    categories = conn.execute(
        "SELECT id, name FROM task_categories WHERE department_id = ? ORDER BY name",
        (department_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in categories])


@app.route('/api/dashboard-data')
@role_required('superadmin', 'manager')
def api_dashboard_data():
    period = request.args.get('period', 'day')
    if period not in ['day', 'week', 'month']:
        period = 'day'
    user_id = request.args.get('user_id', 'all')
    start_date, end_date = get_period_range(period)

    conn = get_db()

    base_params = [start_date, end_date]
    user_clause = ''
    if user_id != 'all':
        user_clause = ' AND wl.user_id = ? '
        base_params.append(int(user_id))

    department_rows = conn.execute(
        f"""
        SELECT d.name AS label, ROUND(SUM(wl.hours), 2) AS value
        FROM work_logs wl
        JOIN departments d ON wl.department_id = d.id
        WHERE wl.work_date BETWEEN ? AND ? {user_clause}
        GROUP BY d.name
        ORDER BY value DESC
        """,
        tuple(base_params)
    ).fetchall()

    category_rows = conn.execute(
        f"""
        SELECT tc.name AS label, ROUND(SUM(wl.hours), 2) AS value
        FROM work_logs wl
        JOIN task_categories tc ON wl.category_id = tc.id
        WHERE wl.work_date BETWEEN ? AND ? {user_clause}
        GROUP BY tc.name
        ORDER BY value DESC
        """,
        tuple(base_params)
    ).fetchall()

    total_row = conn.execute(
        f"""
        SELECT ROUND(COALESCE(SUM(wl.hours), 0), 2) AS total_hours
        FROM work_logs wl
        WHERE wl.work_date BETWEEN ? AND ? {user_clause}
        """,
        tuple(base_params)
    ).fetchone()

    daily_rows = conn.execute(
        f"""
        SELECT wl.work_date AS label, ROUND(SUM(wl.hours), 2) AS value
        FROM work_logs wl
        WHERE wl.work_date BETWEEN ? AND ? {user_clause}
        GROUP BY wl.work_date
        ORDER BY wl.work_date ASC
        """,
        tuple(base_params)
    ).fetchall()

    conn.close()

    total_hours = float(total_row['total_hours'] or 0)

    def with_percent(rows):
        data = []
        for row in rows:
            value = float(row['value'] or 0)
            percent = round((value / total_hours) * 100, 1) if total_hours else 0
            data.append({'label': row['label'], 'value': value, 'percent': percent})
        return data

    return jsonify({
        'period': period,
        'range': {'start': start_date, 'end': end_date},
        'total_hours': total_hours,
        'departments': with_percent(department_rows),
        'categories': with_percent(category_rows),
        'daily': [{'label': row['label'], 'value': float(row['value'] or 0)} for row in daily_rows]
    })


init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
