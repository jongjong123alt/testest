# UI 최초 적용 초안과 최종 코드 비교

초안: Git 2fdda11 (사용자가 이번 제출 기준으로 지정). 최종: 854fef2. 과거 업로드 ZIP을 초안으로 사용하지 않습니다. 이 표의 수정은 AI가 수행한 작업이며 학생 직접 코딩으로 표시하지 않습니다.

검색 바인딩·업로드 형식 검사·상태 기반 알림은 UI 초안에 이미 있습니다. 최종본에서 유지·검증한 사항으로 별도 기록하며 초안에 없던 기능이라고 주장하지 않습니다.

## 1. 직접 실행
- 파일/함수: app.py / __main__
- 수정 근거 커밋: cf7f92e
- 이유: DB 자동 생성·원본 보존과 실행 옵션 추가
- 관련 항목: 추가 점검
- 검증: archive_execution.json (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```

if __name__=='__main__':
    app.run(debug=os.environ.get('KDU_DEBUG')=='1')
```
### 수정 후 실제 코드(발췌)
```
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

...
if __name__=='__main__':
    app.run(host=launch_args.host, port=launch_args.port, debug=False)
```

## 2. 한국 시각 계산
- 파일/함수: app.py / now
- 수정 근거 커밋: 60734a8
- 이유: ZoneInfo 의존성을 고정 UTC+09:00으로 바꿔 Windows 시스템 시간대 DB 누락 대응
- 관련 항목: 추가 점검
- 검증: test_login_without_system_timezone_database (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```
def now():
    """학교 현지 시각으로 모든 모집·일정 경계를 판단합니다."""
    override = app.config.get('NOW')
    return override() if override else datetime.now(ZoneInfo('Asia/Seoul')).replace(tzinfo=None)
```
### 수정 후 실제 코드(발췌)
```
def now():
    """학교 현지 시각으로 모든 모집·일정 경계를 판단합니다."""
    override = app.config.get('NOW')
    # 현재 한국 시각은 UTC+09:00입니다. Windows의 시스템 시간대 DB에 의존하지 않습니다.
    return override() if override else datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
```

## 3. 빈 모집 정보
- 파일/함수: app.py / recruitment
- 수정 근거 커밋: 60734a8
- 이유: 누락·잘못된 모집 날짜와 정원을 미설정 상태로 처리하여 500 방지
- 관련 항목: 추가 점검
- 검증: test_incomplete_recruitment_does_not_break_login_or_management (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```
def recruitment(club):
    r = row('SELECT * FROM recruitment_rounds WHERE id=? AND club_id=?', (club['current_round_id'], club['id']))
    if not r:
        return {'id': None, 'starts_at': '', 'ends_at': '', 'capacity': 0, 'approved': 0, 'pending': 0, 'state': '미설정', 'open': False}
    approved = row("SELECT COUNT(*) n FROM club_members WHERE recruitment_id=? AND status='approved'", (r['id'],))['n']
    pending = row("SELECT COUNT(*) n FROM club_members WHERE recruitment_id=? AND status='pending'", (r['id'],))['n']
    current = now().isoformat(timespec='minutes')
    state = '모집 예정' if current < r['starts_at'] else '모집중'
    if r['closed'] or current > r['ends_at'] or approved >= r['capacity']:
        state = '모집 마감'
    return {**dict(r), 'approved': approved, 'pending': pending, 'state': state, 'open': state == '모집중'}
```
### 수정 후 실제 코드(발췌)
```
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
```

## 4. SQL 파일 인코딩
- 파일/함수: app.py / init_db
- 수정 근거 커밋: 60734a8
- 이유: schema.sql 읽기에 UTF-8을 명시해 Windows CP949 실패 대응
- 관련 항목: 추가 점검
- 검증: test_schema_initialization_with_windows_default_encoding (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```
def init_db():
    """새 데모 DB 초기화용. 기존 DB에는 호출하지 않습니다."""
    with app.app_context():
        db = get_db()
        db.executescript('DROP TABLE IF EXISTS attachments; DROP TABLE IF EXISTS recruitment_rounds;')
        db.executescript((BASE_DIR / 'schema.sql').read_text())
        migrate_database(db)
```
### 수정 후 실제 코드(발췌)
```
def init_db():
    """새 데모 DB 초기화용. 기존 DB에는 호출하지 않습니다."""
    with app.app_context():
        db = get_db()
        db.executescript('DROP TABLE IF EXISTS registration_documents; DROP TABLE IF EXISTS attachments; DROP TABLE IF EXISTS recruitment_rounds;')
        db.executescript((BASE_DIR / 'schema.sql').read_text(encoding='utf-8'))
        migrate_database(db)
```

## 5. 개설 입력 선택화
- 파일/함수: app.py / club_form_values
- 수정 근거 커밋: 63333d6 → 2ec80d3
- 이유: 공식 서식 구조 추가 후 요청에 따라 상세 정보·월별 계획·회원 수 등을 선택으로 변경
- 관련 항목: 7장 파일 업로드: 제한 유지
- 검증: test_review_without_pdf_or_manual_attestation (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```
def club_form_values():
    category = request.form.get('category')
    if category not in CATEGORIES:
        raise ValueError('올바른 분류를 선택해주세요.')
    return {'name': text_field('name', 2, 30), 'category': category,
            'description': text_field('description', 10, 1000), 'activity_plan': text_field('activity_plan', 10, 2000),
            'campus': text_field('campus', 1, 80), 'activity_time': text_field('activity_time', 1, 100),
            'fee': text_field('fee', 1, 80), 'room_location': request.form.get('room_location', '').strip()[:100],
            'requirements': text_field('requirements', 1, 500)}
```
### 수정 후 실제 코드(발췌)
```
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
```

## 6. 선택 PDF 첨부
- 파일/함수: app.py / registration_pdf
- 수정 근거 커밋: 63333d6 → 2ec80d3
- 이유: 등록 PDF 보관을 추가하되 파일명 자유·선택 첨부. 파싱과 용량 제한은 유지
- 관련 항목: 7장 파일 업로드
- 검증: test_registration_free_filename_optional_forms_and_valid_pdf (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```
(UI 초안에는 해당 함수 없음)
```
### 수정 후 실제 코드(발췌)
```
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
```

## 7. 내 활동 탭 통합
- 파일/함수: templates/student_mypage.html / activity_tabs
- 수정 근거 커밋: fc52894
- 이유: 4개 탭을 신청 현황·개설 신청 두 탭으로 통합
- 관련 항목: 추가 점검
- 검증: Chromium tab visibility checks (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```
<button data-tab="applications" class="active">신청 현황</button>
<button data-tab="joined">가입 동아리</button>
<button data-tab="favorites">찜</button>
<button data-tab="created">개설 신청</button>
```
### 수정 후 실제 코드(발췌)
```
<button data-tab="applications" class="active">신청 현황</button>
<button data-tab="created">개설 신청</button>
```

## 8. 제출 화면 표기
- 파일/함수: templates/base.html / heading
- 수정 근거 커밋: 854fef2
- 이유: D01–D12와 개발용 문구를 제거하고 사용 안내로 변경
- 관련 항목: 추가 점검
- 검증: Chromium body text assertions (이번 실행 로그 참조)
- 작성 주체: AI 수행 / 학생 직접 수정은 별도 확인
### 수정 전 실제 코드(발췌)
```
{% macro heading(number,title,subtitle) %}<div class="page-heading"><p class="eyebrow">{{ number }} · 경동대 동아리 프로젝트</p><h1>{{ title }}</h1><p>{{ subtitle }}</p></div>{% endmacro %}
```
### 수정 후 실제 코드(발췌)
```
{% macro heading(title,subtitle) %}<div class="page-heading"><h1>{{ title }}</h1><p>{{ subtitle }}</p></div>{% endmacro %}
```
