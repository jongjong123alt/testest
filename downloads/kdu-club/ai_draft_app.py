"""경동대학교 동아리 과제: 데스크톱 UI와 실제 신청·운영 흐름."""
# 외부 라이브러리를 읽기 전에 실행 환경을 준비합니다. 테스트 import에는 적용하지 않습니다.
if __name__ == '__main__':
    from bootstrap import ensure_dependencies
    ensure_dependencies()

import os
import uuid
import secrets
import hmac
import sqlite3
import zipfile
import io
import json
from pypdf import PdfReader
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import (Flask, render_template, request, redirect, url_for, session, g,
                   abort, flash, jsonify, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
# python app.py는 원본 DB와 분리된 시연 화면을 바로 실행합니다.
# import app(테스트·Flask CLI)은 기존 설정을 그대로 사용합니다.
if __name__ == '__main__':
    import argparse
    import subprocess
    import sys
    parser = argparse.ArgumentParser(description='KDU 동아리 웹사이트 실행')
    parser.add_argument('--original', action='store_true', help='시연 DB 대신 기존 database.db 사용')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    launch_args = parser.parse_args()
    if not launch_args.original and 'KDU_DATABASE' not in os.environ:
        demo_path = BASE_DIR / 'instance' / 'demo.db'
        if not demo_path.exists():
            subprocess.run([sys.executable, str(BASE_DIR / 'seed_demo.py'),
                            '--output', str(demo_path)], cwd=BASE_DIR, check=True)
        os.environ['KDU_DATABASE'] = str(demo_path)
        os.environ.setdefault('KDU_ATTACHMENT_FOLDER', str(BASE_DIR / 'instance' / 'demo-attachments'))

DATABASE = os.environ.get('KDU_DATABASE', str(BASE_DIR / 'database.db'))
app = Flask(__name__)
app.secret_key = os.environ.get('KDU_SECRET_KEY') or secrets.token_hex(32)
app.config.update(MAX_CONTENT_LENGTH=32 * 1024 * 1024,
                  UPLOAD_FOLDER=str(BASE_DIR / 'static' / 'uploads'),
                  REGISTRATION_FOLDER=os.environ.get('KDU_REGISTRATION_FOLDER', str(BASE_DIR / 'instance' / 'registration-packets')),
                  ATTACHMENT_FOLDER=os.environ.get('KDU_ATTACHMENT_FOLDER', str(BASE_DIR / 'instance' / 'attachments')),
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
CATEGORIES = {'학술':'학술', '체육':'체육', '예술':'예술', '취미·교양':'취미·교양', '종교':'종교', '사회·봉사':'사회·봉사'}
STATUS_NAMES = {'pending': '심사 대기', 'approved': '승인 완료', 'rejected': '반려'}


def now():
    """학교 현지 시각으로 모든 모집·일정 경계를 판단합니다."""
    override = app.config.get('NOW')
    # 현재 한국 시각은 UTC+09:00입니다. Windows의 시스템 시간대 DB에 의존하지 않습니다.
    return override() if override else datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)


def get_db():
    if '_database' not in g:
        g._database = sqlite3.connect(DATABASE, timeout=30)
        g._database.row_factory = sqlite3.Row
        g._database.execute('PRAGMA foreign_keys = ON')
    return g._database


@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('_database', None)
    if db is not None:
        db.close()


def migrate_database(db):
    """기존 테이블과 데이터를 보존하며 D01–D12에 필요한 필드만 추가합니다."""
    additions = {
        'clubs': {'campus': "TEXT NOT NULL DEFAULT ''", 'activity_time': "TEXT NOT NULL DEFAULT ''",
                  'fee': "TEXT NOT NULL DEFAULT ''", 'requirements': "TEXT NOT NULL DEFAULT ''",
                  'activity_plan': "TEXT NOT NULL DEFAULT ''", 'rejection_reason': "TEXT NOT NULL DEFAULT ''",
                  'reviewed_at': 'TEXT', 'submitted_at': 'TEXT', 'submission_count': 'INTEGER NOT NULL DEFAULT 1',
                  'current_round_id': 'INTEGER', 'registration_kind':"TEXT NOT NULL DEFAULT 'legacy'",
                  'established_on':'TEXT', 'advisor_name':'TEXT', 'representative_name':'TEXT',
                  'founding_member_count':'INTEGER', 'monthly_plan_json':"TEXT NOT NULL DEFAULT '{}'",
                  'registration_attestations':"TEXT NOT NULL DEFAULT '{}'"},
        'club_members': {'availability': 'TEXT', 'goal': 'TEXT', 'personality': 'TEXT',
                         'recruitment_id': 'INTEGER', 'rejection_reason': "TEXT NOT NULL DEFAULT ''",
                         'submitted_at': 'TEXT', 'reviewed_at': 'TEXT'},
        'club_schedules': {'end_date': 'TEXT', 'location': "TEXT NOT NULL DEFAULT ''"},
        'club_qna': {'is_private': 'INTEGER NOT NULL DEFAULT 0'},
        'notifications': {'is_read': 'INTEGER NOT NULL DEFAULT 0', 'kind': "TEXT NOT NULL DEFAULT 'legacy'",
                          'club_id': 'INTEGER', 'member_id': 'INTEGER'}
    }
    for table, columns in additions.items():
        existing = {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}
        for name, definition in columns.items():
            if name not in existing:
                db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS recruitment_rounds (
            id INTEGER PRIMARY KEY, club_id INTEGER NOT NULL REFERENCES clubs(id),
            starts_at TEXT, ends_at TEXT, capacity INTEGER NOT NULL DEFAULT 20 CHECK(capacity > 0),
            closed INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS registration_documents (
            id INTEGER PRIMARY KEY, club_id INTEGER NOT NULL REFERENCES clubs(id),
            user_id INTEGER NOT NULL REFERENCES users(id), submission_count INTEGER NOT NULL,
            name TEXT NOT NULL, stored_name TEXT NOT NULL, size INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY, club_id INTEGER NOT NULL REFERENCES clubs(id),
            user_id INTEGER NOT NULL REFERENCES users(id), post_id INTEGER REFERENCES club_posts(id),
            name TEXT NOT NULL, stored_name TEXT, legacy_path TEXT, size INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    ''')
    for user in db.execute('SELECT id, password FROM users').fetchall():
        if not user['password'].startswith(('scrypt:', 'pbkdf2:')):
            db.execute('UPDATE users SET password=? WHERE id=?', (generate_password_hash(user['password']), user['id']))
    # 과거 단일 첨부는 복사·삭제 없이 새 첨부 목록에서 계속 다운로드합니다.
    for post in db.execute('SELECT * FROM club_posts WHERE file_path IS NOT NULL').fetchall():
        if not db.execute('SELECT 1 FROM attachments WHERE post_id=? AND legacy_path=?', (post['id'], post['file_path'])).fetchone():
            path = BASE_DIR / 'static' / post['file_path'].removeprefix('static/')
            db.execute('INSERT INTO attachments(club_id,user_id,post_id,name,legacy_path,size) VALUES(?,?,?,?,?,?)',
                       (post['club_id'], post['user_id'], post['id'], path.name, post['file_path'], path.stat().st_size if path.is_file() else 0))
    db.commit()


def init_db():
    """새 데모 DB 초기화용. 기존 DB에는 호출하지 않습니다."""
    with app.app_context():
        db = get_db()
        db.executescript('DROP TABLE IF EXISTS registration_documents; DROP TABLE IF EXISTS attachments; DROP TABLE IF EXISTS recruitment_rounds;')
        db.executescript((BASE_DIR / 'schema.sql').read_text(encoding='utf-8'))
        migrate_database(db)


if not Path(DATABASE).exists():
    init_db()
with app.app_context():
    migrate_database(get_db())


def row(sql, args=()):
    return get_db().execute(sql, args).fetchone()


def rows(sql, args=()):
    return get_db().execute(sql, args).fetchall()


def student_required():
    if session.get('role') != 'student':
        abort(403 if session.get('user_id') else 401, description='학생 계정으로 로그인해주세요.')


def owned_club(club_id, approved=True):
    student_required()
    club = row('SELECT * FROM clubs WHERE id=?', (club_id,))
    if not club:
        abort(404)
    if club['applicant_id'] != session['user_id'] or (approved and club['status'] != 'approved'):
        abort(403, description='이 동아리의 승인된 개설자만 운영할 수 있습니다.')
    return club


def visible_club(club_id):
    if session.get('role') == 'professor':
        abort(403, description='교수 계정은 개설 심사 화면만 이용합니다.')
    club = row('SELECT * FROM clubs WHERE id=?', (club_id,))
    if not club:
        abort(404)
    if club['status'] != 'approved' and club['applicant_id'] != session.get('user_id'):
        abort(403)
    return club


def recruitment(club):
    r = row('SELECT * FROM recruitment_rounds WHERE id=? AND club_id=?', (club['current_round_id'], club['id']))
    if not r:
        return {'id': None, 'starts_at': '', 'ends_at': '', 'capacity': 0, 'approved': 0, 'pending': 0, 'state': '미설정', 'open': False}
    approved = row("SELECT COUNT(*) n FROM club_members WHERE recruitment_id=? AND status='approved'", (r['id'],))['n']
    pending = row("SELECT COUNT(*) n FROM club_members WHERE recruitment_id=? AND status='pending'", (r['id'],))['n']
    # 이전 버전/미완성 모집 정보는 신규 신청을 막고 관리 화면에서 보완합니다.
    try:
        starts = datetime.fromisoformat(r['starts_at'])
        ends = datetime.fromisoformat(r['ends_at'])
        capacity = int(r['capacity'])
        if starts.tzinfo or ends.tzinfo or ends <= starts or capacity < 1:
            raise ValueError()
    except (TypeError, ValueError):
        return {**dict(r), 'starts_at': r['starts_at'] or '', 'ends_at': r['ends_at'] or '',
                'capacity': 0, 'approved': approved, 'pending': pending, 'state': '미설정', 'open': False}
    current = now().replace(second=0, microsecond=0)
    state = '모집 예정' if current < starts else '모집중'
    if r['closed'] or current > ends or approved >= capacity:
        state = '모집 마감'
    return {**dict(r), 'capacity': capacity, 'approved': approved, 'pending': pending,
            'state': state, 'open': state == '모집중'}


def club_view(club):
    return {**dict(club), 'recruitment': recruitment(club)}


def text_field(name, minimum=1, maximum=500):
    value = request.form.get(name, '').strip()
    if not minimum <= len(value) <= maximum:
        raise ValueError(f'{FIELD_NAMES.get(name, name)} 항목은 {minimum}–{maximum}자로 입력해주세요.')
    return value


FIELD_NAMES = {'name': '동아리명', 'description': '소개', 'activity_plan': '활동 계획', 'campus': '활동 캠퍼스',
               'activity_time': '활동 요일·시간', 'fee': '회비', 'requirements': '가입 조건', 'reason': '지원동기',
               'availability': '참여가능여부', 'goal': '목표', 'personality': '가치관', 'title': '제목',
               'content': '본문', 'location': '장소', 'rejection_reason': '반려 사유'}


FIELD_NAMES.update({'advisor_name':'지도교수','representative_name':'대표자'})
for month in range(1,13):
    FIELD_NAMES[f'monthly_activity_{month}']=f'{month}월 활동 내용'
    FIELD_NAMES[f'monthly_effect_{month}']=f'{month}월 기대효과'


def date_field(name):
    try:
        value = request.form.get(name, '').strip().replace('.', '-').replace(' ', 'T')
        date = datetime.fromisoformat(value)
        if date.tzinfo or 'T' not in value:
            raise ValueError()
        return date.isoformat(timespec='minutes')
    except ValueError:
        raise ValueError('시작·종료 일시를 올바르게 입력해주세요.')


def notify(uid, message, kind, club_id, member_id=None):
    get_db().execute('INSERT INTO notifications(user_id,message,kind,club_id,member_id,created_at) VALUES(?,?,?,?,?,?)',
                     (uid, message, kind, club_id, member_id, now().isoformat(timespec='minutes')))


@app.context_processor
def common_context():
    session.setdefault('csrf_token', secrets.token_hex(32))
    return {'csrf_token':session['csrf_token'], 'categories':{**CATEGORIES,'공연':'예술','봉사':'사회·봉사'},
            'category_options':CATEGORIES,'status_names':STATUS_NAMES}


@app.before_request
def protect_requests():
    if request.method == 'POST':
        expected = session.get('csrf_token', '')
        supplied = request.headers.get('X-CSRF-Token', '') or request.form.get('csrf_token', '')
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400, description='요청이 만료되었습니다. 새로고침 후 다시 시도해주세요.')
    if session.get('role') == 'professor' and request.endpoint not in {
        'professor_dashboard', 'login', 'logout', 'static', 'health', 'official_guide', 'download_registration_packet'}:
        abort(403, description='교수 계정은 동아리 개설 심사만 이용합니다.')


@app.errorhandler(HTTPException)
def http_error(error):
    message = '요청 크기가 너무 큽니다. 첨부 파일은 각각 10MB, 최대 3개까지 가능합니다.' if error.code == 413 else error.description
    if request.path.endswith('/attachments/upload'):
        return jsonify(error=message), error.code
    return render_template('error.html', code=error.code, message=message), error.code


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = row('SELECT * FROM users WHERE username=?', (request.form.get('username', '').strip(),))
        if user and check_password_hash(user['password'], request.form.get('password', '')):
            session.clear()
            session.update(user_id=user['id'], username=user['username'], name=user['name'], role=user['role'])
            return redirect(url_for('professor_dashboard' if user['role'] == 'professor' else 'index'))
        return render_template('login.html', error='아이디 또는 비밀번호를 다시 확인해 주세요.', values=request.form)
    return render_template('login.html', values={})


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        try:
            username = text_field('username', 2, 40)
            name = text_field('name', 1, 30)
            password = text_field('password', 8, 128)
            if row('SELECT id FROM users WHERE username=?', (username,)):
                raise ValueError('이미 사용 중인 아이디입니다.')
            get_db().execute('INSERT INTO users(username,password,name,role) VALUES(?,?,?,?)',
                             (username, generate_password_hash(password), name, 'student'))
            get_db().commit()
            flash('회원가입을 완료했습니다. 로그인해주세요.', 'success')
            return redirect(url_for('login'))
        except (ValueError, sqlite3.IntegrityError) as e:
            error = str(e) if isinstance(e, ValueError) else '이미 사용 중인 아이디입니다.'
    return render_template('signup.html', error=error, values=request.form), 400 if error else 200


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.get('/')
def index():
    keyword = request.args.get('keyword', '').strip()
    category = request.args.get('category', 'all')
    query = "SELECT * FROM clubs WHERE status='approved'"
    params = []
    if keyword:
        query += ' AND name LIKE ?'
        params.append(f'%{keyword}%')
    if category != 'all':
        aliases={'예술':['예술','공연'],'사회·봉사':['사회·봉사','봉사']}
        selected=aliases.get(category,[category])
        query += ' AND category IN ('+','.join('?' for _ in selected)+')'
        params.extend(selected)
    clubs = [club_view(c) for c in rows(query + ' ORDER BY id', params)]
    recruiting_only = request.args.get('recruiting') == '1'
    if recruiting_only:
        clubs = [c for c in clubs if c['recruitment']['open']]
    favorites = {r['club_id'] for r in rows('SELECT club_id FROM club_favorites WHERE user_id=?', (session.get('user_id', 0),))}
    return render_template('index.html', clubs=clubs, keyword=keyword, category=category,
                           recruiting_only=recruiting_only, favorite_club_ids=favorites)


def club_form_values():
    category=request.form.get('category')
    if category not in CATEGORIES:
        raise ValueError('동아리 분야를 선택해주세요.')
    kind=request.form.get('registration_kind','new')
    if kind not in {'new','existing'}:
        raise ValueError('등록 유형을 선택해주세요.')
    established=request.form.get('established_on','').strip()
    if established:
        try:datetime.strptime(established,'%Y-%m-%d')
        except ValueError:raise ValueError('설립일자의 날짜 형식을 확인해주세요.')
    count=request.form.get('founding_member_count','').strip()
    try:
        count=int(count) if count else None
        if count is not None and count<0:raise ValueError()
    except ValueError:
        raise ValueError('회원 수는 0 이상의 숫자로 입력해주세요.')
    monthly={str(month):{'activity':text_field(f'monthly_activity_{month}',0,1000),
                         'effect':text_field(f'monthly_effect_{month}',0,500)} for month in range(1,13)}
    return {'name':text_field('name',1,30),'category':category,
            'description':text_field('description',1,1000),
            'activity_plan':text_field('activity_plan',0,2000),
            'campus':text_field('campus',0,100),'activity_time':text_field('activity_time',0,100),
            'fee':text_field('fee',0,80),'room_location':text_field('room_location',0,100),
            'requirements':text_field('requirements',0,500),'registration_kind':kind,
            'established_on':established or None,'advisor_name':text_field('advisor_name',0,50),
            'representative_name':text_field('representative_name',0,30),'founding_member_count':count,
            'monthly_plan_json':json.dumps(monthly,ensure_ascii=False),
            'registration_attestations':'{}'}


def registration_pdf(file,values):
    if not file or not file.filename:
        return None, None
    actual=Path(file.filename.replace('\\','/')).name
    data=file.read(10*1024*1024+1)
    if len(data)>10*1024*1024:raise ValueError('사이트 보관용 PDF는 10MB 이하여야 합니다.')
    try:
        pdf=PdfReader(io.BytesIO(data))
        if pdf.is_encrypted or len(pdf.pages)==0 or not data.startswith(b'%PDF-'):
            raise ValueError()
    except Exception:
        raise ValueError('읽을 수 있는 암호화되지 않은 PDF를 첨부해주세요.')
    return data,actual


@app.get('/official-guide')
def official_guide():
    return render_template('official_guide.html')


@app.get('/registration-documents/<int:document_id>')
def download_registration_packet(document_id):
    doc=row('SELECT d.*,c.applicant_id FROM registration_documents d JOIN clubs c ON c.id=d.club_id WHERE d.id=?',(document_id,))
    if not doc:abort(404)
    if session.get('role')!='professor' and session.get('user_id')!=doc['applicant_id']:abort(403)
    path=Path(app.config['REGISTRATION_FOLDER'])/doc['stored_name']
    if not path.resolve().is_relative_to(Path(app.config['REGISTRATION_FOLDER']).resolve()) or not path.is_file():abort(404)
    response=send_file(path,as_attachment=True,download_name=doc['name'])
    response.headers['Cache-Control']='private, no-store'
    return response


@app.route('/clubs/register',methods=['GET','POST'])
@app.route('/clubs/<int:club_id>/resubmit',methods=['GET','POST'])
def register_club(club_id=None):
    if session.get('role')!='student':return redirect(url_for('login'))
    club=owned_club(club_id,approved=False) if club_id else None
    if club and club['status']!='rejected':abort(409,description='반려된 준비 자료만 수정 후 재검토할 수 있습니다.')
    error=None;stored_path=None
    if request.method=='POST':
        try:
            values=club_form_values()
            data,filename=registration_pdf(request.files.get('registration_pdf'),values)
            db=get_db();db.execute('BEGIN IMMEDIATE')
            if club:
                updated=db.execute('UPDATE clubs SET '+','.join(f'{key}=?' for key in values)+
                                   ",status='pending',submitted_at=?,submission_count=submission_count+1 WHERE id=? AND status='rejected'",
                                   (*values.values(),now().isoformat(timespec='minutes'),club_id))
                if not updated.rowcount:abort(409)
                version=club['submission_count']+1
            else:
                club_id=db.execute('INSERT INTO clubs('+','.join(values)+',status,applicant_id,submitted_at) VALUES('+
                                   ','.join('?' for _ in range(len(values)+3))+')',
                                   (*values.values(),'pending',session['user_id'],now().isoformat(timespec='minutes'))).lastrowid
                version=1
            if data is not None:
                folder=Path(app.config['REGISTRATION_FOLDER']);folder.mkdir(parents=True,exist_ok=True)
                stored_path=folder/(uuid.uuid4().hex+'.pdf');stored_path.write_bytes(data)
                db.execute('INSERT INTO registration_documents(club_id,user_id,submission_count,name,stored_name,size,created_at) VALUES(?,?,?,?,?,?,?)',
                           (club_id,session['user_id'],version,filename,stored_path.name,len(data),now().isoformat(timespec='minutes')))
            db.commit();stored_path=None
            flash('서류 준비 자료를 저장했습니다. 학교 이메일 제출이나 최종 승인이 완료된 것은 아닙니다.','success')
            return redirect(url_for('student_mypage',tab='created'))
        except ValueError as e:
            get_db().rollback();error=str(e)
        finally:
            if stored_path:stored_path.unlink(missing_ok=True)
    vals=request.form if request.method=='POST' else dict(club or {})
    if club and request.method!='POST':
        for month,plan in json.loads(club['monthly_plan_json'] or '{}').items():
            vals[f'monthly_activity_{month}']=plan.get('activity','');vals[f'monthly_effect_{month}']=plan.get('effect','')
    docs=rows('SELECT * FROM registration_documents WHERE club_id=? ORDER BY id DESC',(club_id,)) if club else []
    return render_template('register_club.html',club=club,values=vals,error=error,documents=docs),400 if error else 200


@app.route('/clubs/apply/<int:club_id>', methods=['GET', 'POST'])
def apply_club(club_id):
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    club = visible_club(club_id)
    if club['status'] != 'approved':
        abort(403)
    error = None
    if request.method == 'POST':
        try:
            values = {key: text_field(key, 10 if key == 'reason' else 1, 500) for key in ('reason', 'availability', 'goal', 'personality')}
            db = get_db()
            db.execute('BEGIN IMMEDIATE')
            club = row('SELECT * FROM clubs WHERE id=?', (club_id,))
            r = recruitment(club)
            if not r['open']:
                raise ValueError('모집 기간이 아니거나 정원이 마감되어 신청할 수 없습니다.')
            if row('SELECT id FROM club_members WHERE club_id=? AND user_id=? AND (status=\'approved\' OR recruitment_id=?)',
                   (club_id, session['user_id'], r['id'])):
                raise ValueError('이미 가입했거나 이번 모집에 신청한 동아리입니다.')
            db.execute('INSERT INTO club_members(club_id,user_id,reason,availability,goal,personality,status,recruitment_id,submitted_at) VALUES(?,?,?,?,?,?,\'pending\',?,?)',
                       (club_id, session['user_id'], *values.values(), r['id'], now().isoformat(timespec='minutes')))
            db.commit()
            flash('가입 신청을 제출했습니다.', 'success')
            return redirect(url_for('student_mypage'))
        except ValueError as e:
            get_db().rollback()
            error = str(e)
    return render_template('club_apply.html', club=club_view(club), values=request.form, error=error), 400 if error else 200


@app.post('/clubs/cancel_apply/<int:club_id>')
def cancel_apply(club_id):
    student_required()
    get_db().execute("DELETE FROM club_members WHERE club_id=? AND user_id=? AND status='pending'", (club_id, session['user_id']))
    get_db().commit()
    flash('대기 중인 신청을 취소했습니다.', 'success')
    return redirect(url_for('student_mypage'))


@app.post('/clubs/favorite/<int:club_id>')
def toggle_favorite(club_id):
    student_required()
    club = visible_club(club_id)
    if club['status'] != 'approved':
        abort(403)
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    if row('SELECT id FROM club_favorites WHERE club_id=? AND user_id=?', (club_id, session['user_id'])):
        db.execute('DELETE FROM club_favorites WHERE club_id=? AND user_id=?', (club_id, session['user_id']))
    else:
        db.execute('INSERT INTO club_favorites(club_id,user_id) VALUES(?,?)', (club_id, session['user_id']))
    db.commit()
    return redirect(url_for('club_detail', club_id=club_id) if request.form.get('return_to') == 'detail' else url_for('index'))


@app.get('/clubs/<int:club_id>')
def club_detail(club_id):
    club = visible_club(club_id)
    uid = session.get('user_id', 0)
    qnas = rows('SELECT * FROM club_qna WHERE club_id=? AND (is_private=0 OR user_id=? OR ?=?) ORDER BY id DESC',
                (club_id, uid, uid, club['applicant_id']))
    posts = [dict(p, attachments=rows('SELECT * FROM attachments WHERE post_id=?', (p['id'],)))
             for p in rows('SELECT * FROM club_posts WHERE club_id=? ORDER BY id DESC', (club_id,))]
    return render_template('club_detail.html', club=club_view(club), posts=posts,
                           schedules=[s for s in rows('SELECT * FROM club_schedules WHERE club_id=? ORDER BY event_date', (club_id,))
                                      if (s['end_date'] or (s['event_date'] + 'T23:59' if len(s['event_date'])==10 else s['event_date'])) >= now().isoformat(timespec='minutes')], qnas=qnas,
                           membership=row('SELECT * FROM club_members WHERE club_id=? AND user_id=? ORDER BY id DESC', (club_id, uid)),
                           is_favorite=bool(row('SELECT id FROM club_favorites WHERE club_id=? AND user_id=?', (club_id, uid))))


@app.post('/clubs/<int:club_id>/qna')
def add_qna(club_id):
    student_required()
    club = visible_club(club_id)
    if club['status'] != 'approved':
        abort(403)
    try:
        question = text_field('question', 1, 500)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('club_detail', club_id=club_id, _anchor='qna'))
    get_db().execute('INSERT INTO club_qna(club_id,user_id,question,is_private) VALUES(?,?,?,?)',
                     (club_id, session['user_id'], question, int(request.form.get('is_private') == '1')))
    get_db().commit()
    return redirect(url_for('club_detail', club_id=club_id, _anchor='qna'))


@app.post('/clubs/qna/answer/<int:qna_id>')
def answer_qna(qna_id):
    student_required()
    qna = row('SELECT * FROM club_qna WHERE id=?', (qna_id,))
    if not qna:
        abort(404)
    owned_club(qna['club_id'])
    try:
        answer = text_field('answer', 1, 1000)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('club_detail', club_id=qna['club_id'], _anchor='qna'))
    get_db().execute('UPDATE club_qna SET answer=? WHERE id=?', (answer, qna_id))
    get_db().commit()
    return redirect(url_for('club_detail', club_id=qna['club_id'], _anchor='qna'))


@app.get('/student/mypage')
def student_mypage():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    uid = session['user_id']
    applications = rows('SELECT m.*, c.name,c.category,c.campus,c.activity_time,c.fee,c.status club_status FROM club_members m JOIN clubs c ON m.club_id=c.id WHERE m.user_id=? ORDER BY m.id DESC', (uid,))
    created = [dict(c,documents=rows('SELECT * FROM registration_documents WHERE club_id=? ORDER BY id DESC',(c['id'],)))
               for c in rows('SELECT * FROM clubs WHERE applicant_id=? ORDER BY id DESC',(uid,))]
    favorites = rows("SELECT c.* FROM clubs c JOIN club_favorites f ON f.club_id=c.id WHERE f.user_id=? AND c.status='approved'", (uid,))
    return render_template('student_mypage.html', applications=applications, created=created,
                           favorites=[club_view(c) for c in favorites], joined=[a for a in applications if a['status']=='approved'],
                           pending_count=sum(a['status']=='pending' for a in applications), selected_application=request.args.get('application',type=int))


@app.get('/notifications')
def notifications():
    student_required()
    uid = session['user_id']
    all_notices = rows('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC', (uid,))
    unread_count = sum(not n['is_read'] for n in all_notices)
    return render_template('notifications.html', notifications=all_notices, unread_count=unread_count)


@app.post('/notifications/read-all')
def read_all_notifications():
    student_required()
    flash('알림을 하나씩 선택하여 읽음 처리해주세요.', 'info')
    return redirect(url_for('notifications'))


@app.post('/notifications/<int:notification_id>/read')
def read_notification(notification_id):
    student_required()
    get_db().execute('UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?', (notification_id,session['user_id']))
    get_db().commit()
    return redirect(url_for('notifications'))


@app.get('/notifications/<int:notification_id>/result')
def notification_result(notification_id):
    student_required()
    n = row('SELECT * FROM notifications WHERE id=? AND user_id=?', (notification_id,session['user_id']))
    if not n:
        abort(404)
    get_db().execute('UPDATE notifications SET is_read=1 WHERE id=?', (n['id'],))
    get_db().commit()
    return redirect(url_for('student_mypage', tab='created') if n['kind']=='club' else url_for('student_mypage', application=n['member_id']))


@app.route('/clubs/<int:club_id>/manage', methods=['GET', 'POST'])
def manage_club(club_id):
    club = owned_club(club_id)
    error = None
    if request.method == 'POST':
        try:
            db = get_db()
            db.execute('BEGIN IMMEDIATE')
            club = owned_club(club_id)
            r = recruitment(club)
            if request.form.get('action') == 'close':
                if not r['id']:
                    raise ValueError('먼저 모집 기간을 설정해주세요.')
                db.execute('UPDATE recruitment_rounds SET closed=1 WHERE id=?', (r['id'],))
            else:
                values = {key:text_field(key,10 if key=='description' else 1,1000 if key=='description' else 500)
                          for key in ('description','campus','activity_time','fee','requirements')}
                values['room_location'] = request.form.get('room_location','').strip()[:100]
                starts, ends = date_field('starts_at'), date_field('ends_at')
                if ends <= starts:
                    raise ValueError('모집 종료는 시작보다 늦어야 합니다.')
                try:
                    capacity = int(request.form.get('capacity',''))
                    if not 1 <= capacity <= 1000:
                        raise ValueError()
                except ValueError:
                    raise ValueError('신규 정원은 1–1,000명으로 입력해주세요.')
                new_round = not r['id'] or request.form.get('new_round')=='1'
                if new_round:
                    if r['id'] and (not (r['closed'] or now().isoformat(timespec='minutes') > r['ends_at']) or r['pending']):
                        raise ValueError('현재 모집을 마감하고 대기 신청을 모두 심사한 뒤 새 모집을 열 수 있습니다.')
                    cur = db.execute('INSERT INTO recruitment_rounds(club_id,starts_at,ends_at,capacity) VALUES(?,?,?,?)', (club_id,starts,ends,capacity))
                    db.execute('UPDATE clubs SET current_round_id=? WHERE id=?', (cur.lastrowid,club_id))
                else:
                    if capacity < r['approved']:
                        raise ValueError('정원은 이번 모집에서 승인된 인원보다 작을 수 없습니다.')
                    db.execute('UPDATE recruitment_rounds SET starts_at=?,ends_at=?,capacity=? WHERE id=?', (starts,ends,capacity,r['id']))
                db.execute('UPDATE clubs SET '+','.join(f'{key}=?' for key in values)+' WHERE id=?', (*values.values(),club_id))
            db.commit()
            flash('변경 사항을 저장했습니다.', 'success')
            return redirect(url_for('manage_club',club_id=club_id))
        except ValueError as e:
            get_db().rollback()
            error = str(e)
    return render_template('manage_club.html', club=club_view(club), values=request.form if error else {}, error=error,
                           total_members=row("SELECT COUNT(*) n FROM club_members WHERE club_id=? AND status='approved'", (club_id,))['n']), 400 if error else 200


@app.get('/clubs/<int:club_id>/members')
def manage_members(club_id):
    club=owned_club(club_id)
    members=rows('SELECT m.*, u.name student_name FROM club_members m JOIN users u ON u.id=m.user_id WHERE m.club_id=? ORDER BY m.id DESC',(club_id,))
    selected_id=request.args.get('application',type=int)
    tab=request.args.get('tab','pending')
    choices=[m for m in members if m['status']=='approved'] if tab=='approved' else [m for m in members if m['status']!='pending'] if tab=='processed' else [m for m in members if m['status']=='pending']
    selected=next((m for m in choices if m['id']==selected_id),None) or next(iter(choices),None)
    return render_template('manage_members.html',club=club_view(club),members=members,selected=selected,
                           error=None,total_members=sum(m['status']=='approved' for m in members))


@app.post('/student/manage_member')
def manage_member():
    student_required()
    mem=row('SELECT * FROM club_members WHERE id=?',(request.form.get('member_id'),))
    if not mem:
        abort(404)
    club=owned_club(mem['club_id'])
    action=request.form.get('action')
    if action not in {'approve','reject'}:
        abort(400)
    try:
        rejection = text_field('rejection_reason',1,500) if action=='reject' else ''
        db=get_db(); db.execute('BEGIN IMMEDIATE')
        mem=row('SELECT * FROM club_members WHERE id=?',(mem['id'],))
        if mem['status']=='pending':
            if action=='approve' and mem['recruitment_id']:
                r=row('SELECT * FROM recruitment_rounds WHERE id=? AND club_id=?',(mem['recruitment_id'],club['id']))
                count=row("SELECT COUNT(*) n FROM club_members WHERE recruitment_id=? AND status='approved'",(mem['recruitment_id'],))['n']
                if not r or count>=r['capacity']:
                    raise ValueError('이번 모집 정원을 초과해 승인할 수 없습니다.')
            new_status='approved' if action=='approve' else 'rejected'
            db.execute("UPDATE club_members SET status=?, rejection_reason=?,reviewed_at=? WHERE id=? AND status='pending'",
                       (new_status,rejection,now().isoformat(timespec='minutes'),mem['id']))
            notify(mem['user_id'],f"{club['name']} 가입 신청이 {'승인' if action=='approve' else '반려'}되었어요.",'membership',club['id'],mem['id'])
        db.commit()
    except ValueError as e:
        get_db().rollback(); flash(str(e),'error')
    return redirect(url_for('manage_members',club_id=club['id'],application=mem['id']))


@app.route('/professor/dashboard',methods=['GET','POST'])
def professor_dashboard():
    if session.get('role')!='professor':
        return redirect(url_for('login'))
    if request.method=='POST':
        action=request.form.get('action')
        if action not in {'approve','reject'}:
            abort(400)
        try:
            rejection=text_field('rejection_reason',1,500) if action=='reject' else ''
            db=get_db();db.execute('BEGIN IMMEDIATE')
            club=row('SELECT * FROM clubs WHERE id=?',(request.form.get('club_id'),))
            if not club:
                abort(404)
            if club['status']=='pending':
                db.execute("UPDATE clubs SET status=?,rejection_reason=?,reviewed_at=? WHERE id=? AND status='pending'",
                           ('approved' if action=='approve' else 'rejected',rejection,now().isoformat(timespec='minutes'),club['id']))
                notify(club['applicant_id'],f"{club['name']} 등록 준비 자료가 {'사전 확인 완료' if action=='approve' else '보완 요청'}되었어요. 학교 최종 승인과는 별개입니다.",'club',club['id'])
            db.commit()
            return redirect(url_for('professor_dashboard',club=club['id']))
        except ValueError as e:
            get_db().rollback();flash(str(e),'error')
    clubs=rows('SELECT c.*,u.name applicant_name FROM clubs c LEFT JOIN users u ON c.applicant_id=u.id ORDER BY c.id DESC')
    selected=next((c for c in clubs if c['id']==request.args.get('club',type=int)),None) or next((c for c in clubs if c['status']=='pending'),None)
    return render_template('professor_dashboard.html',clubs=clubs,selected=selected,
                           monthly_plan=json.loads(selected['monthly_plan_json'] or '{}') if selected else {},
                           documents=rows('SELECT * FROM registration_documents WHERE club_id=? ORDER BY id DESC',(selected['id'],)) if selected else [])


@app.route('/clubs/<int:club_id>/schedules',methods=['GET','POST'])
@app.route('/clubs/<int:club_id>/schedules/<int:schedule_id>',methods=['GET','POST'])
def manage_schedule(club_id,schedule_id=None):
    club=owned_club(club_id)
    schedule=row('SELECT * FROM club_schedules WHERE id=? AND club_id=?',(schedule_id,club_id)) if schedule_id else None
    if schedule_id and not schedule:
        abort(404)
    error=None
    if request.method=='POST':
        if request.form.get('action')=='delete':
            if not schedule:
                abort(404)
            get_db().execute('DELETE FROM club_schedules WHERE id=? AND club_id=?',(schedule_id,club_id));get_db().commit()
            flash('일정을 삭제했습니다.','success')
            return redirect(url_for('manage_schedule',club_id=club_id))
        try:
            title=text_field('title',1,100);description=text_field('description',1,2000);location=text_field('location',1,100)
            starts,ends=date_field('event_date'),date_field('end_date')
            if ends<=starts:
                raise ValueError('종료 일시는 시작 일시보다 늦어야 합니다.')
            if schedule:
                get_db().execute('UPDATE club_schedules SET title=?,description=?,location=?,event_date=?,end_date=? WHERE id=? AND club_id=?',
                                 (title,description,location,starts,ends,schedule_id,club_id))
            else:
                get_db().execute('INSERT INTO club_schedules(title,description,location,event_date,end_date,club_id) VALUES(?,?,?,?,?,?)',
                                 (title,description,location,starts,ends,club_id))
            get_db().commit();flash('일정을 저장했습니다.','success')
            return redirect(url_for('manage_schedule',club_id=club_id))
        except ValueError as e:
            error=str(e)
    return render_template('manage_schedule.html',club=club_view(club),schedule=schedule,
                           values=request.form if error else dict(schedule or {}),error=error,
                           schedules=rows('SELECT * FROM club_schedules WHERE club_id=? ORDER BY event_date',(club_id,))),400 if error else 200


def validated_upload(file):
    """PDF 첨부의 용량과 헤더를 확인합니다."""
    data = file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('파일은 각각 10MB 이하여야 합니다.')
    ext = Path(file.filename or '').suffix.lower()
    if ext != '.pdf' or not data.startswith(b'%PDF-'):
        raise ValueError('PDF 파일만 첨부할 수 있습니다.')
    return data, ext


@app.post('/clubs/<int:club_id>/attachments/upload')
def upload_attachment(club_id):
    owned_club(club_id)
    file=request.files.get('file')
    if not file:
        return jsonify(error='파일을 선택해주세요.'),400
    try:
        data,ext=validated_upload(file)
        folder=Path(app.config['ATTACHMENT_FOLDER']);folder.mkdir(parents=True,exist_ok=True)
        filename=uuid.uuid4().hex+ext;path=folder/filename
        path.write_bytes(data)
        try:
            cursor=get_db().execute('INSERT INTO attachments(club_id,user_id,name,stored_name,size) VALUES(?,?,?,?,?)',
                                     (club_id,session['user_id'],Path(file.filename.replace('\\','/')).name[:150],filename,len(data)))
            get_db().commit()
        except Exception:
            path.unlink(missing_ok=True);raise
        return jsonify(id=cursor.lastrowid,name=Path(file.filename.replace('\\','/')).name[:150],size=len(data)),201
    except ValueError as e:
        return jsonify(error=str(e)),400


@app.get('/attachments/<int:attachment_id>')
def download_attachment(attachment_id):
    attachment=row('SELECT * FROM attachments WHERE id=?',(attachment_id,))
    if not attachment:
        abort(404)
    if attachment['post_id'] is None:
        owned_club(attachment['club_id'])
    else:
        visible_club(attachment['club_id'])
    path=Path(app.config['ATTACHMENT_FOLDER'])/attachment['stored_name'] if attachment['stored_name'] else BASE_DIR/'static'/attachment['legacy_path'].removeprefix('static/')
    root=Path(app.config['ATTACHMENT_FOLDER']) if attachment['stored_name'] else BASE_DIR/'static'
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        abort(404,description='첨부파일을 찾을 수 없습니다.')
    return send_file(path,as_attachment=True,download_name=attachment['name'])


@app.route('/clubs/<int:club_id>/posts',methods=['GET','POST'])
@app.route('/clubs/<int:club_id>/posts/<int:post_id>',methods=['GET','POST'])
def manage_post(club_id,post_id=None):
    club=owned_club(club_id)
    post=row('SELECT * FROM club_posts WHERE id=? AND club_id=?',(post_id,club_id)) if post_id else None
    if post_id and not post:
        abort(404)
    error=None
    attachments=rows('SELECT * FROM attachments WHERE post_id=?',(post_id,)) if post else []
    if request.method=='POST':
        try:
            title=text_field('title',1,100);content=text_field('content',1,5000)
            try:
                ids=[int(i) for i in request.form.getlist('attachment_ids')]
            except ValueError:
                raise ValueError('첨부파일 선택을 확인해주세요.')
            if len(ids)>3 or len(set(ids))!=len(ids):
                raise ValueError('첨부파일은 최대 3개까지 가능합니다.')
            db=get_db()
            db.execute('BEGIN IMMEDIATE')
            selected=[]
            for aid in ids:
                a=row('SELECT * FROM attachments WHERE id=? AND club_id=?',(aid,club_id))
                if not a or (a['post_id'] is None and a['user_id']!=session['user_id']) or (a['post_id'] is not None and a['post_id']!=post_id):
                    raise ValueError('사용할 수 없는 첨부파일입니다.')
                selected.append(a)
            db=get_db()
            if post:
                db.execute('UPDATE club_posts SET title=?,content=?,file_path=NULL WHERE id=? AND club_id=?',(title,content,post_id,club_id))
                db.execute('UPDATE attachments SET post_id=NULL WHERE post_id=?',(post_id,))
            else:
                post_id=db.execute('INSERT INTO club_posts(club_id,user_id,title,content,created_at) VALUES(?,?,?,?,?)',(club_id,session['user_id'],title,content,now().isoformat(timespec='minutes'))).lastrowid
            for aid in ids:
                db.execute('UPDATE attachments SET post_id=? WHERE id=?',(post_id,aid))
            db.commit();flash('공지를 저장했습니다.','success')
            return redirect(url_for('manage_post',club_id=club_id))
        except ValueError as e:
            get_db().rollback()
            error=str(e)
            if 'selected' in locals():
                attachments=selected
    return render_template('manage_post.html',club=club_view(club),post=post,attachments=attachments,
                           values=request.form if error else dict(post or {}),error=error,
                           posts=rows('SELECT * FROM club_posts WHERE club_id=? ORDER BY id DESC',(club_id,))),400 if error else 200


# 구버전 공지 URL을 새 편집기로 연결합니다.
@app.post('/clubs/<int:club_id>/post')
def create_club_post(club_id):
    return manage_post(club_id)


if __name__=='__main__':
    app.run(host=launch_args.host, port=launch_args.port, debug=False)
