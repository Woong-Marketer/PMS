from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
import sqlite3
import os
import json

from dotenv import load_dotenv

try:
    from supabase import create_client
except ImportError:  # pragma: no cover
    create_client = None

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'pms.db'))
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
SECRET_KEY = os.environ.get('SECRET_KEY', 'pms-secret-key-change-me')
DB_BACKEND = os.environ.get('DATABASE_BACKEND', '').strip().lower() or ('supabase' if SUPABASE_URL and SUPABASE_KEY else 'sqlite')

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

DEFAULT_CATEGORIES = {
    '마케팅&경영지원': ['콘텐츠 제작', '광고 운영', '거래처 커뮤니케이션'],
    '연구소': ['제품 개발', '샘플 테스트', '기술 문서 작성'],
    '생산팀': ['생산 계획', '조립', '품질 점검']
}

BOOTSTRAP_ERROR = None


class StorageError(Exception):
    pass


class BaseStorage:
    backend_name = 'base'

    def init_db(self):
        raise NotImplementedError

    def get_user_by_username(self, username):
        raise NotImplementedError

    def list_users(self):
        raise NotImplementedError

    def create_user(self, username, password_hash, name, role, status, approved_at=None, approved_by=None, created_at=None):
        raise NotImplementedError

    def update_user_status_and_role(self, user_id, status, role, approved_at=None, approved_by=None):
        raise NotImplementedError

    def update_user_role(self, user_id, role):
        raise NotImplementedError

    def reject_user(self, user_id, approved_by=None):
        raise NotImplementedError

    def delete_user(self, user_id):
        raise NotImplementedError

    def list_departments(self):
        raise NotImplementedError

    def create_department(self, name, created_at):
        raise NotImplementedError

    def update_department(self, department_id, name):
        raise NotImplementedError

    def delete_department(self, department_id):
        raise NotImplementedError

    def list_categories(self):
        raise NotImplementedError

    def create_category(self, department_id, name, created_at):
        raise NotImplementedError

    def update_category(self, category_id, name):
        raise NotImplementedError

    def delete_category(self, category_id):
        raise NotImplementedError

    def list_work_logs(self):
        raise NotImplementedError

    def create_work_log(self, user_id, work_date, department_id, category_id, hours, detail, created_at):
        raise NotImplementedError

    def update_work_log(self, log_id, work_date, department_id, category_id, hours, detail):
        raise NotImplementedError

    def delete_work_log(self, log_id):
        raise NotImplementedError

    def get_user_by_id(self, user_id):
        users = self.list_users()
        return next((user for user in users if int(user['id']) == int(user_id)), None)

    def get_department_by_id(self, department_id):
        departments = self.list_departments()
        return next((dep for dep in departments if int(dep['id']) == int(department_id)), None)

    def get_category_by_id(self, category_id):
        categories = self.list_categories()
        return next((cat for cat in categories if int(cat['id']) == int(category_id)), None)

    def get_work_log_by_id(self, log_id):
        logs = self.list_work_logs()
        return next((log for log in logs if int(log['id']) == int(log_id)), None)

    def get_departments_with_categories(self):
        departments = sorted(self.list_departments(), key=lambda dep: dep['name'])
        categories = self.list_categories()
        results = []
        for dep in departments:
            dep_categories = [cat for cat in categories if int(cat['department_id']) == int(dep['id'])]
            dep_categories.sort(key=lambda cat: cat['name'])
            results.append({
                'id': int(dep['id']),
                'name': dep['name'],
                'categories': dep_categories
            })
        return results

    def ensure_bootstrap_data(self):
        now = datetime.now().isoformat(timespec='seconds')
        users = self.list_users()
        if not users:
            admin_username = os.environ.get('INITIAL_ADMIN_USERNAME', 'admin')
            admin_password = os.environ.get('INITIAL_ADMIN_PASSWORD', 'admin1234')
            admin_name = os.environ.get('INITIAL_ADMIN_NAME', '대표 관리자')
            admin = self.create_user(
                admin_username,
                generate_password_hash(admin_password),
                admin_name,
                'superadmin',
                'approved',
                approved_at=now,
                approved_by=None,
                created_at=now
            )

            if os.environ.get('ENABLE_DEMO_USERS', 'false').lower() == 'true':
                admin_id = admin['id']
                self.create_user('manager', generate_password_hash('manager1234'), '중간 관리자', 'manager', 'approved', approved_at=now, approved_by=admin_id, created_at=now)
                self.create_user('member1', generate_password_hash('member1234'), '팀원 1', 'member', 'approved', approved_at=now, approved_by=admin_id, created_at=now)
                self.create_user('member2', generate_password_hash('member1234'), '팀원 2', 'member', 'approved', approved_at=now, approved_by=admin_id, created_at=now)

        existing_departments = {dep['name']: dep for dep in self.list_departments()}
        for dep_name in DEFAULT_DEPARTMENTS:
            if dep_name not in existing_departments:
                self.create_department(dep_name, now)

        existing_departments = {dep['name']: dep for dep in self.list_departments()}
        categories = self.list_categories()
        existing_category_keys = {(int(cat['department_id']), cat['name']) for cat in categories}
        for dep_name, category_names in DEFAULT_CATEGORIES.items():
            dep = existing_departments.get(dep_name)
            if not dep:
                continue
            for category_name in category_names:
                key = (int(dep['id']), category_name)
                if key not in existing_category_keys:
                    self.create_category(dep['id'], category_name, now)
                    existing_category_keys.add(key)

        if os.environ.get('ENABLE_DEMO_DATA', 'false').lower() == 'true' and not self.list_work_logs():
            user_by_username = {user['username']: user for user in self.list_users()}
            dept_by_name = {dep['name']: dep for dep in self.list_departments()}
            category_by_key = {(int(cat['department_id']), cat['name']): cat for cat in self.list_categories()}
            sample_logs = [
                ('member1', (date.today() - timedelta(days=2)).isoformat(), '마케팅&경영지원', '콘텐츠 제작', 2.0, '브랜드 콘텐츠 기획 및 게시물 작성'),
                ('member1', (date.today() - timedelta(days=1)).isoformat(), '마케팅&경영지원', '광고 운영', 1.5, '광고 예산 점검 및 소재 수정'),
                ('member2', date.today().isoformat(), '연구소', '제품 개발', 3.0, '시제품 성능 개선 회의 및 테스트'),
                ('manager', date.today().isoformat(), '생산팀', '품질 점검', 2.5, '주간 품질 리포트 검토'),
            ]
            for username, work_date, dep_name, cat_name, hours, detail in sample_logs:
                user = user_by_username.get(username)
                dep = dept_by_name.get(dep_name)
                cat = category_by_key.get((int(dep['id']), cat_name)) if dep else None
                if user and dep and cat:
                    self.create_work_log(user['id'], work_date, dep['id'], cat['id'], hours, detail, now)


class SQLiteStorage(BaseStorage):
    backend_name = 'sqlite'

    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None

    def init_db(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = self._connect()
        cur = conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('superadmin', 'manager', 'member')),
                status TEXT NOT NULL DEFAULT 'approved' CHECK(status IN ('pending', 'approved', 'rejected')),
                approved_at TEXT,
                approved_by INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(approved_by) REFERENCES users(id) ON DELETE SET NULL
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
                FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE,
                FOREIGN KEY(category_id) REFERENCES task_categories(id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        conn.close()
        self.ensure_bootstrap_data()

    def list_users(self):
        conn = self._connect()
        rows = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_user_by_username(self, username):
        conn = self._connect()
        row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def create_user(self, username, password_hash, name, role, status, approved_at=None, approved_by=None, created_at=None):
        created_at = created_at or datetime.now().isoformat(timespec='seconds')
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO users (username, password_hash, name, role, status, approved_at, approved_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (username, password_hash, name, role, status, approved_at, approved_by, created_at)
        )
        conn.commit()
        user_id = cur.lastrowid
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return dict(row)

    def update_user_status_and_role(self, user_id, status, role, approved_at=None, approved_by=None):
        conn = self._connect()
        conn.execute(
            'UPDATE users SET status = ?, role = ?, approved_at = ?, approved_by = ? WHERE id = ?',
            (status, role, approved_at, approved_by, user_id)
        )
        conn.commit()
        conn.close()

    def update_user_role(self, user_id, role):
        conn = self._connect()
        conn.execute('UPDATE users SET role = ? WHERE id = ? AND status = ?', (role, user_id, 'approved'))
        conn.commit()
        conn.close()

    def reject_user(self, user_id, approved_by=None):
        conn = self._connect()
        conn.execute(
            "UPDATE users SET status = 'rejected', approved_at = NULL, approved_by = ? WHERE id = ?",
            (approved_by, user_id)
        )
        conn.commit()
        conn.close()

    def delete_user(self, user_id):
        conn = self._connect()
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

    def list_departments(self):
        conn = self._connect()
        rows = conn.execute('SELECT * FROM departments').fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_department(self, name, created_at):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute('INSERT INTO departments (name, created_at) VALUES (?, ?)', (name, created_at))
        conn.commit()
        department_id = cur.lastrowid
        row = conn.execute('SELECT * FROM departments WHERE id = ?', (department_id,)).fetchone()
        conn.close()
        return dict(row)

    def update_department(self, department_id, name):
        conn = self._connect()
        conn.execute('UPDATE departments SET name = ? WHERE id = ?', (name, department_id))
        conn.commit()
        conn.close()

    def delete_department(self, department_id):
        conn = self._connect()
        conn.execute('DELETE FROM departments WHERE id = ?', (department_id,))
        conn.commit()
        conn.close()

    def list_categories(self):
        conn = self._connect()
        rows = conn.execute('SELECT * FROM task_categories').fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_category(self, department_id, name, created_at):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute('INSERT INTO task_categories (department_id, name, created_at) VALUES (?, ?, ?)', (department_id, name, created_at))
        conn.commit()
        category_id = cur.lastrowid
        row = conn.execute('SELECT * FROM task_categories WHERE id = ?', (category_id,)).fetchone()
        conn.close()
        return dict(row)

    def update_category(self, category_id, name):
        conn = self._connect()
        conn.execute('UPDATE task_categories SET name = ? WHERE id = ?', (name, category_id))
        conn.commit()
        conn.close()

    def delete_category(self, category_id):
        conn = self._connect()
        conn.execute('DELETE FROM task_categories WHERE id = ?', (category_id,))
        conn.commit()
        conn.close()

    def list_work_logs(self):
        conn = self._connect()
        rows = conn.execute('SELECT * FROM work_logs').fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_work_log(self, user_id, work_date, department_id, category_id, hours, detail, created_at):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO work_logs (user_id, work_date, department_id, category_id, hours, detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, work_date, department_id, category_id, float(hours), detail, created_at)
        )
        conn.commit()
        log_id = cur.lastrowid
        row = conn.execute('SELECT * FROM work_logs WHERE id = ?', (log_id,)).fetchone()
        conn.close()
        return dict(row)

    def update_work_log(self, log_id, work_date, department_id, category_id, hours, detail):
        conn = self._connect()
        conn.execute(
            'UPDATE work_logs SET work_date = ?, department_id = ?, category_id = ?, hours = ?, detail = ? WHERE id = ?',
            (work_date, department_id, category_id, float(hours), detail, log_id)
        )
        conn.commit()
        conn.close()

    def delete_work_log(self, log_id):
        conn = self._connect()
        conn.execute('DELETE FROM work_logs WHERE id = ?', (log_id,))
        conn.commit()
        conn.close()


class SupabaseStorage(BaseStorage):
    backend_name = 'supabase'

    def __init__(self, supabase_url, supabase_key):
        if create_client is None:
            raise RuntimeError('supabase 패키지가 설치되지 않았습니다.')
        if not supabase_url or not supabase_key:
            raise RuntimeError('SUPABASE_URL 또는 SUPABASE_KEY가 비어 있습니다.')
        self.client = create_client(supabase_url, supabase_key)

    @staticmethod
    def _normalize_rows(rows):
        normalized = []
        for row in rows or []:
            normalized.append(dict(row))
        return normalized

    def _select_all(self, table_name, columns='*', page_size=1000):
        start = 0
        results = []
        while True:
            response = self.client.table(table_name).select(columns).range(start, start + page_size - 1).execute()
            page = self._normalize_rows(response.data)
            results.extend(page)
            if len(page) < page_size:
                break
            start += page_size
        return results

    def init_db(self):
        try:
            self.client.table('users').select('id').range(0, 0).execute()
            self.client.table('departments').select('id').range(0, 0).execute()
            self.client.table('task_categories').select('id').range(0, 0).execute()
            self.client.table('work_logs').select('id').range(0, 0).execute()
        except Exception as exc:
            raise RuntimeError(
                'Supabase 테이블이 아직 준비되지 않았습니다. ZIP에 포함된 supabase_schema.sql을 Supabase SQL Editor에서 1회 실행한 뒤 다시 배포해주세요.'
            ) from exc
        self.ensure_bootstrap_data()

    def list_users(self):
        return self._select_all('users')

    def get_user_by_username(self, username):
        users = self.list_users()
        return next((user for user in users if user['username'] == username), None)

    def create_user(self, username, password_hash, name, role, status, approved_at=None, approved_by=None, created_at=None):
        payload = {
            'username': username,
            'password_hash': password_hash,
            'name': name,
            'role': role,
            'status': status,
            'approved_at': approved_at,
            'approved_by': approved_by,
            'created_at': created_at or datetime.now().isoformat(timespec='seconds')
        }
        response = self.client.table('users').insert(payload).execute()
        return dict(response.data[0])

    def update_user_status_and_role(self, user_id, status, role, approved_at=None, approved_by=None):
        self.client.table('users').update({
            'status': status,
            'role': role,
            'approved_at': approved_at,
            'approved_by': approved_by
        }).eq('id', user_id).execute()

    def update_user_role(self, user_id, role):
        self.client.table('users').update({'role': role}).eq('id', user_id).eq('status', 'approved').execute()

    def reject_user(self, user_id, approved_by=None):
        self.client.table('users').update({
            'status': 'rejected',
            'approved_at': None,
            'approved_by': approved_by
        }).eq('id', user_id).execute()

    def delete_user(self, user_id):
        self.client.table('users').delete().eq('id', user_id).execute()

    def list_departments(self):
        return self._select_all('departments')

    def create_department(self, name, created_at):
        response = self.client.table('departments').insert({'name': name, 'created_at': created_at}).execute()
        return dict(response.data[0])

    def update_department(self, department_id, name):
        self.client.table('departments').update({'name': name}).eq('id', department_id).execute()

    def delete_department(self, department_id):
        self.client.table('departments').delete().eq('id', department_id).execute()

    def list_categories(self):
        return self._select_all('task_categories')

    def create_category(self, department_id, name, created_at):
        response = self.client.table('task_categories').insert({
            'department_id': int(department_id),
            'name': name,
            'created_at': created_at
        }).execute()
        return dict(response.data[0])

    def update_category(self, category_id, name):
        self.client.table('task_categories').update({'name': name}).eq('id', category_id).execute()

    def delete_category(self, category_id):
        self.client.table('task_categories').delete().eq('id', category_id).execute()

    def list_work_logs(self):
        return self._select_all('work_logs')

    def create_work_log(self, user_id, work_date, department_id, category_id, hours, detail, created_at):
        response = self.client.table('work_logs').insert({
            'user_id': int(user_id),
            'work_date': work_date,
            'department_id': int(department_id),
            'category_id': int(category_id),
            'hours': float(hours),
            'detail': detail,
            'created_at': created_at
        }).execute()
        return dict(response.data[0])

    def update_work_log(self, log_id, work_date, department_id, category_id, hours, detail):
        self.client.table('work_logs').update({
            'work_date': work_date,
            'department_id': int(department_id),
            'category_id': int(category_id),
            'hours': float(hours),
            'detail': detail
        }).eq('id', log_id).execute()

    def delete_work_log(self, log_id):
        self.client.table('work_logs').delete().eq('id', log_id).execute()


def get_storage():
    if DB_BACKEND == 'supabase':
        return SupabaseStorage(SUPABASE_URL, SUPABASE_KEY)
    return SQLiteStorage(SQLITE_DB_PATH)


storage = get_storage()


def get_db():
    if isinstance(storage, SQLiteStorage):
        return storage._connect()
    raise RuntimeError('SQLite 백엔드에서만 get_db를 사용할 수 있습니다.')


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


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if BOOTSTRAP_ERROR:
            flash('데이터베이스 설정이 아직 완료되지 않았습니다.', 'danger')
            return redirect(url_for('setup_error'))
        if 'user_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if BOOTSTRAP_ERROR:
                flash('데이터베이스 설정이 아직 완료되지 않았습니다.', 'danger')
                return redirect(url_for('setup_error'))
            if 'user_id' not in session:
                flash('로그인이 필요합니다.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                flash('이 페이지에 접근할 권한이 없습니다.', 'danger')
                return redirect(url_for('home'))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


def can_manage_work_log(log_row):
    return session.get('role') in ['superadmin', 'manager'] or int(log_row['user_id']) == int(session.get('user_id'))


def enrich_work_logs(logs):
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


def get_filtered_logs_for_view(user_id=None, limit=100):
    logs = storage.list_work_logs()
    if user_id is not None:
        logs = [log for log in logs if int(log['user_id']) == int(user_id)]
    enriched = enrich_work_logs(logs)
    return enriched[:limit]


def safe_create_user(username, password_hash, name, role, status, approved_at=None, approved_by=None, created_at=None):
    try:
        return storage.create_user(username, password_hash, name, role, status, approved_at=approved_at, approved_by=approved_by, created_at=created_at)
    except Exception as exc:
        message = str(exc).lower()
        if 'duplicate' in message or 'unique' in message or 'already exists' in message:
            raise StorageError('이미 존재하는 아이디입니다.') from exc
        raise


@app.context_processor
def inject_globals():
    return {
        'role_labels': ROLE_LABELS,
        'status_labels': STATUS_LABELS,
        'today_str': date.today().isoformat(),
        'db_backend': storage.backend_name,
        'bootstrap_error': BOOTSTRAP_ERROR,
    }


@app.route('/setup-error')
def setup_error():
    if not BOOTSTRAP_ERROR:
        return redirect(url_for('home'))
    return render_template('setup_error.html', error_message=BOOTSTRAP_ERROR)


@app.route('/')
def home():
    if BOOTSTRAP_ERROR:
        return redirect(url_for('setup_error'))
    if 'user_id' in session:
        if session.get('role') in ['superadmin', 'manager']:
            return redirect(url_for('dashboard'))
        return redirect(url_for('work_logs'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if BOOTSTRAP_ERROR:
        return redirect(url_for('setup_error'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = storage.get_user_by_username(username)

        if not user or not check_password_hash(user['password_hash'], password):
            flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'danger')
            return render_template('login.html')

        if user['status'] == 'pending':
            flash('회원가입 신청은 완료되었지만 아직 관리자 승인이 필요합니다.', 'warning')
            return render_template('login.html')

        if user['status'] == 'rejected':
            flash('이 계정은 관리자에 의해 반려되었습니다. 관리자에게 문의해주세요.', 'danger')
            return render_template('login.html')

        session['user_id'] = int(user['id'])
        session['username'] = user['username']
        session['name'] = user['name']
        session['role'] = user['role']
        flash(f"{user['name']}님, 환영합니다.", 'success')
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if BOOTSTRAP_ERROR:
        return redirect(url_for('setup_error'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()

        if not username or not password or not name:
            flash('이름, 아이디, 비밀번호를 모두 입력해주세요.', 'danger')
            return render_template('register.html')

        try:
            safe_create_user(
                username,
                generate_password_hash(password),
                name,
                'member',
                'pending',
                approved_at=None,
                approved_by=None,
                created_at=datetime.now().isoformat(timespec='seconds')
            )
            flash('회원가입 신청이 접수되었습니다. 대표 관리자의 승인 후 로그인할 수 있습니다.', 'success')
            return redirect(url_for('login'))
        except StorageError as exc:
            flash(str(exc), 'danger')
            return render_template('register.html')

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
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'member').strip()
        if not username or not password or not name:
            flash('모든 필드를 입력해주세요.', 'danger')
        else:
            try:
                safe_create_user(
                    username,
                    generate_password_hash(password),
                    name,
                    role,
                    'approved',
                    approved_at=datetime.now().isoformat(timespec='seconds'),
                    approved_by=session.get('user_id'),
                    created_at=datetime.now().isoformat(timespec='seconds')
                )
                flash('사용자가 즉시 승인 상태로 추가되었습니다.', 'success')
                return redirect(url_for('users'))
            except StorageError as exc:
                flash(str(exc), 'danger')

    all_users = storage.list_users()
    pending_users = sorted([user for user in all_users if user['status'] == 'pending'], key=lambda row: (row['created_at'], int(row['id'])))
    approved_users = sorted([user for user in all_users if user['status'] == 'approved'], key=lambda row: int(row['id']))
    rejected_users = sorted([user for user in all_users if user['status'] == 'rejected'], key=lambda row: (row['created_at'], int(row['id'])), reverse=True)
    return render_template('users.html', pending_users=pending_users, approved_users=approved_users, rejected_users=rejected_users)


@app.route('/users/<int:user_id>/approve', methods=['POST'])
@role_required('superadmin')
def approve_user(user_id):
    assigned_role = request.form.get('role', 'member').strip()
    if assigned_role not in ROLE_LABELS:
        assigned_role = 'member'

    storage.update_user_status_and_role(
        user_id,
        'approved',
        assigned_role,
        approved_at=datetime.now().isoformat(timespec='seconds'),
        approved_by=session.get('user_id')
    )
    flash('회원가입이 승인되었고 권한이 부여되었습니다.', 'success')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/reject', methods=['POST'])
@role_required('superadmin')
def reject_user(user_id):
    storage.reject_user(user_id, approved_by=session.get('user_id'))
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

    storage.update_user_role(user_id, role)
    flash('사용자 권한이 변경되었습니다.', 'success')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@role_required('superadmin')
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash('현재 로그인한 대표 관리자 계정은 삭제할 수 없습니다.', 'warning')
        return redirect(url_for('users'))

    storage.delete_user(user_id)
    flash('사용자가 삭제되었습니다.', 'info')
    return redirect(url_for('users'))


@app.route('/settings/departments', methods=['GET', 'POST'])
@role_required('superadmin')
def department_settings():
    if request.method == 'POST':
        action = request.form.get('action')
        now = datetime.now().isoformat(timespec='seconds')
        try:
            if action == 'add_department':
                name = request.form.get('department_name', '').strip()
                if name:
                    storage.create_department(name, now)
                    flash('부서가 추가되었습니다.', 'success')
            elif action == 'edit_department':
                department_id = request.form.get('department_id')
                name = request.form.get('department_name', '').strip()
                storage.update_department(int(department_id), name)
                flash('부서명이 수정되었습니다.', 'success')
            elif action == 'delete_department':
                department_id = request.form.get('department_id')
                storage.delete_department(int(department_id))
                flash('부서가 삭제되었습니다.', 'info')
            elif action == 'add_category':
                department_id = request.form.get('department_id')
                category_name = request.form.get('category_name', '').strip()
                storage.create_category(int(department_id), category_name, now)
                flash('업무 분류가 추가되었습니다.', 'success')
            elif action == 'edit_category':
                category_id = request.form.get('category_id')
                category_name = request.form.get('category_name', '').strip()
                storage.update_category(int(category_id), category_name)
                flash('업무 분류가 수정되었습니다.', 'success')
            elif action == 'delete_category':
                category_id = request.form.get('category_id')
                storage.delete_category(int(category_id))
                flash('업무 분류가 삭제되었습니다.', 'info')
        except Exception as exc:
            message = str(exc).lower()
            if 'duplicate' in message or 'unique' in message or 'already exists' in message:
                flash('중복된 이름이 있어 저장할 수 없습니다.', 'danger')
            else:
                flash('저장 중 오류가 발생했습니다. 입력값을 다시 확인해주세요.', 'danger')
        return redirect(url_for('department_settings'))

    data = storage.get_departments_with_categories()
    return render_template('department_settings.html', departments=data)


@app.route('/work-logs', methods=['GET', 'POST'])
@role_required('member', 'manager', 'superadmin')
def work_logs():
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
        if saved_count:
            flash(f'{saved_count}건의 업무 일지가 저장되었습니다.', 'success')
        else:
            flash('저장할 유효한 업무 항목이 없습니다.', 'warning')
        return redirect(url_for('work_logs'))

    if session.get('role') in ['superadmin', 'manager']:
        logs = get_filtered_logs_for_view(limit=100)
    else:
        logs = get_filtered_logs_for_view(user_id=session['user_id'], limit=100)

    departments = storage.get_departments_with_categories()
    return render_template('work_logs.html', logs=logs, departments=departments)


@app.route('/work-logs/<int:log_id>/edit', methods=['GET', 'POST'])
@role_required('member', 'manager', 'superadmin')
def edit_work_log(log_id):
    raw_log = storage.get_work_log_by_id(log_id)
    if not raw_log:
        flash('업무 일지를 찾을 수 없습니다.', 'warning')
        return redirect(url_for('work_logs'))

    if not can_manage_work_log(raw_log):
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
            category = storage.get_category_by_id(int(category_id)) if category_id.isdigit() else None
            if not category or int(category['department_id']) != int(department_id):
                flash('선택한 부서와 업무 분류가 일치하지 않습니다.', 'danger')
            else:
                storage.update_work_log(log_id, work_date, int(department_id), int(category_id), float(hours), detail)
                flash('업무 일지가 수정되었습니다.', 'success')
                return redirect(url_for('work_logs'))

    log = enrich_work_logs([raw_log])[0]
    departments = storage.get_departments_with_categories()
    return render_template('edit_work_log.html', log=log, departments=departments)


@app.route('/work-logs/<int:log_id>/delete', methods=['POST'])
@role_required('member', 'manager', 'superadmin')
def delete_work_log(log_id):
    log = storage.get_work_log_by_id(log_id)
    if not log:
        flash('업무 일지를 찾을 수 없습니다.', 'warning')
        return redirect(url_for('work_logs'))

    if not can_manage_work_log(log):
        flash('본인이 작성한 업무 일지만 삭제할 수 있습니다.', 'danger')
        return redirect(url_for('work_logs'))

    storage.delete_work_log(log_id)
    flash('업무 일지가 삭제되었습니다.', 'info')
    return redirect(url_for('work_logs'))


@app.route('/dashboard')
@role_required('superadmin', 'manager')
def dashboard():
    members = [user for user in storage.list_users() if user['status'] == 'approved' and user['role'] in ['member', 'manager', 'superadmin']]
    members.sort(key=lambda user: user['name'])
    return render_template('dashboard.html', members=members)


@app.route('/healthz')
def healthz():
    status = 'ok' if not BOOTSTRAP_ERROR else 'error'
    return jsonify({'status': status, 'backend': storage.backend_name, 'error': BOOTSTRAP_ERROR})


@app.route('/api/categories/<int:department_id>')
@login_required
def api_categories(department_id):
    categories = [cat for cat in storage.list_categories() if int(cat['department_id']) == int(department_id)]
    categories.sort(key=lambda cat: cat['name'])
    return jsonify([{'id': int(row['id']), 'name': row['name']} for row in categories])


@app.route('/api/dashboard-data')
@role_required('superadmin', 'manager')
def api_dashboard_data():
    period = request.args.get('period', 'day')
    if period not in ['day', 'week', 'month']:
        period = 'day'
    user_id = request.args.get('user_id', 'all')
    start_date, end_date = get_period_range(period)

    logs = storage.list_work_logs()
    filtered_logs = []
    for log in logs:
        if not (start_date <= log['work_date'] <= end_date):
            continue
        if user_id != 'all' and int(log['user_id']) != int(user_id):
            continue
        filtered_logs.append(log)

    enriched = enrich_work_logs(filtered_logs)
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


try:
    storage.init_db()
except Exception as exc:  # pragma: no cover
    BOOTSTRAP_ERROR = str(exc)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
