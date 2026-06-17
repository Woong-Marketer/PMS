import os
import tempfile
import importlib

DB_FILE = os.path.join(tempfile.gettempdir(), 'pms_test_approval.db')
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

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

# 회원가입 신청
register_response = client.post('/register', data={
    'name': '신규 팀원',
    'username': 'newmember',
    'password': 'pw123456'
}, follow_redirects=True)
assert register_response.status_code == 200
assert '회원가입 신청이 접수되었습니다.'.encode('utf-8') in register_response.data

# 승인 전 로그인 차단
pending_login = client.post('/login', data={'username': 'newmember', 'password': 'pw123456'}, follow_redirects=True)
assert pending_login.status_code == 200
assert '관리자 승인이 필요합니다.'.encode('utf-8') in pending_login.data

# 관리자 로그인
admin_login = client.post('/login', data={'username': 'admin', 'password': 'admin1234'}, follow_redirects=True)
assert admin_login.status_code == 200
assert '대시보드'.encode('utf-8') in admin_login.data

# 승인 및 권한 부여
approve_response = client.post('/users/2/approve', data={'role': 'member'}, follow_redirects=True)
assert approve_response.status_code == 200
assert '권한이 부여되었습니다.'.encode('utf-8') in approve_response.data

# 승인 후 로그인 가능
client.get('/logout', follow_redirects=True)
approved_login = client.post('/login', data={'username': 'newmember', 'password': 'pw123456'}, follow_redirects=True)
assert approved_login.status_code == 200
assert '업무 일지'.encode('utf-8') in approved_login.data

# 관리자 화면 접근 확인
client.get('/logout', follow_redirects=True)
client.post('/login', data={'username': 'admin', 'password': 'admin1234'}, follow_redirects=True)
users_page = client.get('/users')
assert users_page.status_code == 200
assert '회원가입 승인 대기'.encode('utf-8') in users_page.data

print('ALL_TESTS_PASSED')
