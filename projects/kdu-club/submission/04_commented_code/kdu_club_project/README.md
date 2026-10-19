# KDU 동아리 웹사이트 실행 안내

언어: Python / 서버: Flask / DB: SQLite / 화면: Jinja2·HTML·CSS·JavaScript.
Python 3.10 이상이 필요하며 3.12를 권장합니다. 검증 환경은 Python 3.12, Linux입니다. Windows에서의 설치·실행은 아래 절차를 사용하며, 사용자 PC의 실행 결과는 확인 필요입니다.

## Windows PowerShell
```powershell
python app.py
```
`python`이 없다면 `py app.py`를 사용하세요. 둘 다 없다면 Python을 설치하고 새 PowerShell을 여세요. 필요한 라이브러리는 전용 .venv에 자동 설치합니다. 최초 설치에는 인터넷 연결이 필요하며, 재실행은 준비된 환경을 재사용합니다.

## Linux / macOS
```bash
python3 app.py
```
브라우저에서 http://127.0.0.1:5000 에 접속합니다. 서버 종료는 터미널 Ctrl+C입니다. 포트 충돌 시 `app.py --port 5003`을 사용하세요.

첫 실행에서 seed_demo.py가 schema.sql을 사용하여 instance/demo.db와 화면 확인용 가상 데이터를 생성합니다. 실제 사용자 DB·등록 PDF·.env·키·토큰은 제출 소스에 포함하지 않았습니다. 실행용 가상 계정은 학생 kdu_student / sample1234, 교수 kdu_professor / sample1234입니다. 이 값은 실제 학교 계정이나 비밀 인증정보가 아닙니다.

두 번째 실행은 DB를 보존합니다. 기존 DB에는 누락된 필드와 테이블을 추가하며 평문 비밀번호를 해시로 바꿉니다. `init_db()`나 schema.sql은 새 DB 생성용이므로 기존 DB에 직접 실행하지 마세요.

## 기능
검색·분야/모집 필터, 가입 신청/취소, 찜, 내 활동 두 탭, 개설 신청/교수 검토/재신청, 부원 심사와 정원, 공지·첨부 파일, 일정, 공개·비밀 Q&A, 인앱 알림과 읽음 처리.
개설 신청은 이름·분야·소개가 필수입니다. 상세 정보·월별 계획·PDF는 선택이며 첨부 이름은 자유입니다. 공지 첨부는 PDF/HWP/DOCX/JPG/PNG, 파일별 10MiB/공지당 3개 제한이 있습니다. 등록 첨부 PDF는 10MiB까지이며 파싱 가능해야 합니다.

## 설정
KDU_DATABASE: DB 경로. KDU_ATTACHMENT_FOLDER: 공지 첨부 경로. KDU_REGISTRATION_FOLDER: 등록 서류 경로. KDU_SECRET_KEY: 직접 설정하는 세션 서명 키. 비밀 값을 소스나 Git에 저장하지 마세요. 지정하지 않으면 실행마다 임의 키를 생성하므로 재시작 후 다시 로그인해야 합니다.
`python app.py --original`은 루트 database.db를 사용합니다. 제출 ZIP에는 기존 개인 DB가 없어 초기화 데이터로 만들어집니다.

## 검증
`python -m unittest discover -s tests -v`는 임시 DB로 테스트합니다.
브라우저 검사: `python qa/run_browser_checks.py`. 별도 Node.js와 Playwright 및 Chromium이 필요합니다(서버 실행에는 필요 없음). `npm install playwright`, Chromium 설치 및 CHROMIUM_PATH 설정이 필요할 수 있습니다. 검사 시 실제 학교에 연락하지 않습니다.
의존성은 requirements.txt의 고정 버전을 사용합니다. SQLite는 Python 내장 모듈입니다.
