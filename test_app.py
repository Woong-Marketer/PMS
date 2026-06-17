import os
import json
import tempfile
import importlib

DB_FILE = os.path.join(tempfile.gettempdir(), 'pms_test_worklog_permissions.db')
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


# 1) 대표 관리자 로그인
admin_login = login('admin', 'admin1234')
assert admin_login.status_code == 200
assert '대시보드'.encode('utf-8') in admin_login.data

# 2) 관리자 페이지에서 테스트 계정 생성 (팀원 2명 + 중간 관리자 1명)
for user_data in [
    {'name': '팀원 A', 'username': 'membera', 'password': 'pw123456', 'role': 'member'},
    {'name': '팀원 B', 'username': 'memberb', 'password': 'pw123456', 'role': 'member'},
    {'name': '중간 관리자', 'username': 'manager1', 'password': 'pw123456', 'role': 'manager'},
]:
    response = client.post('/users', data=user_data, follow_redirects=True)
    assert response.status_code == 200
    assert '즉시 승인 상태'.encode('utf-8') in response.data

logout()

# 3) 팀원 A가 자신의 업무일지 2건 작성
member_a_login = login('membera', 'pw123456')
assert member_a_login.status_code == 200
assert '업무 일지'.encode('utf-8') in member_a_login.data

with app_module.get_db() as conn:
    department = conn.execute("SELECT id FROM departments WHERE name = '마케팅&경영지원'").fetchone()
    category_content = conn.execute("SELECT id FROM task_categories WHERE name = '콘텐츠 제작'").fetchone()
    category_ad = conn.execute("SELECT id FROM task_categories WHERE name = '광고 운영'").fetchone()

entries_payload = [
    {
        'department_id': department['id'],
        'category_id': category_content['id'],
        'hours': '2.0',
        'detail': '초기 업무 내용'
    },
    {
        'department_id': department['id'],
        'category_id': category_ad['id'],
        'hours': '1.5',
        'detail': '삭제 예정 업무'
    }
]
create_logs = client.post('/work-logs', data={
    'work_date': '2026-06-17',
    'entries_json': json.dumps(entries_payload)
}, follow_redirects=True)
assert create_logs.status_code == 200
assert '2건의 업무 일지가 저장되었습니다.'.encode('utf-8') in create_logs.data

with app_module.get_db() as conn:
    member_a_id = conn.execute("SELECT id FROM users WHERE username = 'membera'").fetchone()['id']
    member_a_logs = conn.execute(
        "SELECT id, detail FROM work_logs WHERE user_id = ? ORDER BY id ASC",
        (member_a_id,)
    ).fetchall()
    own_edit_log_id = member_a_logs[0]['id']
    own_delete_log_id = member_a_logs[1]['id']

# 4) 본인 작성 업무일지 수정 가능
own_edit_page = client.get(f'/work-logs/{own_edit_log_id}/edit')
assert own_edit_page.status_code == 200
assert '업무 일지 수정'.encode('utf-8') in own_edit_page.data

own_edit_submit = client.post(f'/work-logs/{own_edit_log_id}/edit', data={
    'work_date': '2026-06-17',
    'department_id': str(department['id']),
    'category_id': str(category_content['id']),
    'hours': '3.0',
    'detail': '본인 수정 완료'
}, follow_redirects=True)
assert own_edit_submit.status_code == 200
assert '업무 일지가 수정되었습니다.'.encode('utf-8') in own_edit_submit.data

with app_module.get_db() as conn:
    edited_log = conn.execute("SELECT hours, detail FROM work_logs WHERE id = ?", (own_edit_log_id,)).fetchone()
assert edited_log['hours'] == 3.0
assert edited_log['detail'] == '본인 수정 완료'

# 5) 본인 작성 업무일지 삭제 가능
own_delete_submit = client.post(f'/work-logs/{own_delete_log_id}/delete', follow_redirects=True)
assert own_delete_submit.status_code == 200
assert '업무 일지가 삭제되었습니다.'.encode('utf-8') in own_delete_submit.data

with app_module.get_db() as conn:
    deleted_log = conn.execute("SELECT id FROM work_logs WHERE id = ?", (own_delete_log_id,)).fetchone()
assert deleted_log is None

logout()

# 6) 팀원 B는 다른 사람 업무일지 수정/삭제 불가
member_b_login = login('memberb', 'pw123456')
assert member_b_login.status_code == 200
assert '업무 일지'.encode('utf-8') in member_b_login.data

forbidden_edit = client.post(f'/work-logs/{own_edit_log_id}/edit', data={
    'work_date': '2026-06-17',
    'department_id': str(department['id']),
    'category_id': str(category_content['id']),
    'hours': '4.0',
    'detail': '타인 수정 시도'
}, follow_redirects=True)
assert forbidden_edit.status_code == 200
assert '본인이 작성한 업무 일지만 수정할 수 있습니다.'.encode('utf-8') in forbidden_edit.data

forbidden_delete = client.post(f'/work-logs/{own_edit_log_id}/delete', follow_redirects=True)
assert forbidden_delete.status_code == 200
assert '본인이 작성한 업무 일지만 삭제할 수 있습니다.'.encode('utf-8') in forbidden_delete.data
logout()

# 7) 중간 관리자는 모든 업무일지 수정 가능
manager_login = login('manager1', 'pw123456')
assert manager_login.status_code == 200
assert '대시보드'.encode('utf-8') in manager_login.data

manager_edit = client.post(f'/work-logs/{own_edit_log_id}/edit', data={
    'work_date': '2026-06-18',
    'department_id': str(department['id']),
    'category_id': str(category_content['id']),
    'hours': '4.5',
    'detail': '중간관리자 수정 완료'
}, follow_redirects=True)
assert manager_edit.status_code == 200
assert '업무 일지가 수정되었습니다.'.encode('utf-8') in manager_edit.data

with app_module.get_db() as conn:
    manager_edited_log = conn.execute("SELECT work_date, hours, detail FROM work_logs WHERE id = ?", (own_edit_log_id,)).fetchone()
assert manager_edited_log['work_date'] == '2026-06-18'
assert manager_edited_log['hours'] == 4.5
assert manager_edited_log['detail'] == '중간관리자 수정 완료'
logout()

# 8) 대표 관리자는 모든 업무일지 삭제 가능
admin_relogin = login('admin', 'admin1234')
assert admin_relogin.status_code == 200
assert '대시보드'.encode('utf-8') in admin_relogin.data

admin_delete = client.post(f'/work-logs/{own_edit_log_id}/delete', follow_redirects=True)
assert admin_delete.status_code == 200
assert '업무 일지가 삭제되었습니다.'.encode('utf-8') in admin_delete.data

with app_module.get_db() as conn:
    removed_by_admin = conn.execute("SELECT id FROM work_logs WHERE id = ?", (own_edit_log_id,)).fetchone()
assert removed_by_admin is None

print('ALL_TESTS_PASSED')
