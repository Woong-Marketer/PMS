import os
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

with app_module.get_db() as conn:
    department_marketing = conn.execute("SELECT id FROM departments WHERE name = '마케팅&경영지원'").fetchone()['id']
    department_research = conn.execute("SELECT id FROM departments WHERE name = '연구소'").fetchone()['id']
    department_production = conn.execute("SELECT id FROM departments WHERE name = '생산팀'").fetchone()['id']
    category_content = conn.execute("SELECT id FROM task_categories WHERE name = '콘텐츠 제작'").fetchone()['id']
    category_ad = conn.execute("SELECT id FROM task_categories WHERE name = '광고 운영'").fetchone()['id']
    category_quality = conn.execute("SELECT id FROM task_categories WHERE name = '품질 점검'").fetchone()['id']

# 테스트 사용자 생성
for user_data in [
    {'name': 'A직원', 'username': 'membera', 'password': 'pw123456', 'role': 'member', 'department_id': str(department_marketing)},
    {'name': 'B직원', 'username': 'memberb', 'password': 'pw123456', 'role': 'member', 'department_id': str(department_research)},
    {'name': 'D관리자', 'username': 'manager1', 'password': 'pw123456', 'role': 'manager', 'department_id': str(department_production)},
]:
    response = client.post('/users', data=user_data, follow_redirects=True)
    assert response.status_code == 200
    assert '즉시 승인 상태'.encode('utf-8') in response.data

# 사용자 관리 화면에 부서 변경 UI가 보이는지 확인
users_page = client.get('/users')
assert users_page.status_code == 200
assert '현재 부서'.encode('utf-8') in users_page.data
assert '부서 변경'.encode('utf-8') in users_page.data

# 승인 완료 사용자 부서 변경 확인
change_department = client.post('/users/2/department', data={'department_id': str(department_production)}, follow_redirects=True)
assert change_department.status_code == 200
assert '사용자 부서가 변경되었습니다.'.encode('utf-8') in change_department.data
with app_module.get_db() as conn:
    changed_department = conn.execute("SELECT department_id FROM users WHERE username = 'membera'").fetchone()
assert changed_department['department_id'] == department_production

# 다시 원래 부서로 복원
restore_department = client.post('/users/2/department', data={'department_id': str(department_marketing)}, follow_redirects=True)
assert restore_department.status_code == 200

logout()

# 회원가입 화면에 부서 드롭다운이 보이는지 확인
register_page = client.get('/register')
assert register_page.status_code == 200
assert 'name="department_id"'.encode('utf-8') in register_page.data

# 회원가입 시 부서 저장 확인
register_submit = client.post('/register', data={
    'name': '신규 팀원',
    'username': 'newmember',
    'password': 'pw123456',
    'department_id': str(department_research)
}, follow_redirects=True)
assert register_submit.status_code == 200
assert '회원가입 신청이 접수되었습니다.'.encode('utf-8') in register_submit.data
with app_module.get_db() as conn:
    new_member = conn.execute("SELECT department_id, status FROM users WHERE username = 'newmember'").fetchone()
assert new_member['department_id'] == department_research
assert new_member['status'] == 'pending'

# A직원 업무일지 2건 작성
login('membera', 'pw123456')
work_logs_page = client.get('/work-logs')
assert work_logs_page.status_code == 200
assert f'id="selected-department-id" type="application/json">{department_marketing}<'.encode('utf-8') in work_logs_page.data
assert '같은 부서 업무 추가 +'.encode('utf-8') in work_logs_page.data

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

# 일반 팀원도 전체 업무일지를 일별로 조회할 수 있는지 확인
login('membera', 'pw123456')
shared_logs_page = client.get('/work-logs?view_date=2026-06-17')
assert shared_logs_page.status_code == 200
shared_html = shared_logs_page.data.decode('utf-8')
assert '2026-06-17 업무 기록' in shared_html
assert 'A직원 업무 기록' in shared_html
assert 'B직원 업무 기록' in shared_html
assert 'D관리자 업무 기록' not in shared_html
assert '기록 찾기' in shared_html
assert '검색어' in shared_html

# 날짜를 바꾸면 해당 날짜 기록만 보이는지 확인
next_day_page = client.get('/work-logs?view_date=2026-06-18')
assert next_day_page.status_code == 200
next_day_html = next_day_page.data.decode('utf-8')
assert 'D관리자 업무 기록' in next_day_html
assert 'A직원 업무 기록' not in next_day_html
logout()

# 관리자 화면에서 직원별 묶음 정렬 및 검색 확인
login('admin', 'admin1234')
logs_page = client.get('/work-logs?view_date=2026-06-17')
assert logs_page.status_code == 200
html = logs_page.data.decode('utf-8')
assert '소요 시간' not in html
assert 'A직원 업무 기록' in html
assert 'B직원 업무 기록' in html
assert 'D관리자 업무 기록' not in html
assert html.find('A직원 업무 기록') < html.find('B직원 업무 기록')

search_page = client.get('/work-logs?view_date=2026-06-17&keyword=광고')
assert search_page.status_code == 200
search_html = search_page.data.decode('utf-8')
assert 'A의 두 번째 기록' in search_html
assert '검색 초기화' in search_html
assert '검색 조건에 맞는 업무 기록이 없습니다.' not in search_html

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
