# KDU 동아리 최종 제출 산출물

기준 소스: Git 854fef2. AI 초안: 사용자가 지정한 UI 최초 적용 Git 2fdda11. 제작·실행 검증 기준일: 2026년 10월 14일.

## 파일 위치와 제작 상태
|폴더|핵심 파일|상태|
|---|---|---|
|01_flowchart|flowchart.png / flowchart.pdf / flowchart.mmd|실제 동작 흐름 기준 작성. DOT와 보고서용 개요도 추가|
|02_report|project_report.docx / project_report.pdf / screenshots/|13개 구성 작성, 실제 실행 캡처 18개 포함. 추가 보고서 양식 첨부 확인 필요|
|03_source_code|source_code.zip / README.md / requirements.txt / kdu_club_project/|전체 실행 소스와 초기화 코드 포함. 개인 DB·서류 제외|
|04_commented_code|commented_source_code.zip / kdu_club_project/ / commentary_guide.md|한국어 기능 주석. 처리 코드 AST 일치 및 42개 테스트 통과|
|05_ai_initial_draft|ai_draft_explanation.docx / .pdf / ai_initial_draft/ui_initial_draft_2fdda11/|실제 Git 소스 추출. 업로드 ZIP을 초안으로 사용하지 않음|
|06_ai_revision_verification|ai_revision_verification.docx / .pdf / code_comparison.md / evidence/ / student_review_tasks.md|교수 7장 원문 연결 및 실제 변경·검증 기록. 학생 직접 수행 범위는 확인 필요|
|07_presentation|project_presentation.pptx / .pdf / presentation_script.docx / .pdf|11장, 발표 대본 약 6분 30초|

## 실행
03_source_code/source_code.zip을 별도 새 폴더에 풀고 README.md에 따라 설치하세요. Windows는 `py -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, `.\.venv\Scripts\python.exe app.py`입니다. pip 명령이 인식되지 않아도 Python의 모듈 실행을 사용합니다.
가상 학생 kdu_student / sample1234, 교수 kdu_professor / sample1234. 실제 학교 계정·개인 비밀번호가 아닙니다. DB와 가상 화면 자료는 첫 실행에 생성됩니다. 로컬 접속 http://127.0.0.1:5000, 서버 종료 Ctrl+C입니다.

## 실제 검증
- 제출 소스: unittest 42개 통과 (source_tests.log)
- 주석 소스: unittest 42개 통과 (commented_tests.log)
- Python AST 비교: 실행 처리 코드 동일
- Chromium: 주요 화면·검색·탭·신청·심사·첨부·일정·알림 검사 통과. 기록된 콘솔 오류 0
- 소스 ZIP과 주석 ZIP: 각각 새 폴더에서 python app.py 실행·시연 DB 생성·학생/교수 로그인·주요 화면 HTTP 200 확인 (archive_execution.json)
- DOCX/PPTX 재열기 및 LibreOffice PDF 변환, PDF 파싱·렌더링 검수. 상세 결과는 artifact_validation.json
- 과거 UI 초안은 정적 비교만 했고 이번 실행 테스트 대상은 최종 소스입니다.

## 과제 원문 확인
교수 제공 2회차_학생배포_미션설명문.pdf의 7장은 파일 업로드·검색/필터·알림의 검사 항목을 명시합니다. 이번 프로젝트는 세 기능을 구현하며 API는 미선택입니다. 원문 PDF와 추출 텍스트는 evidence에 보존했습니다. 과제 마감은 2026년 10월 20일이며 카카오워크 1:1 제출입니다.

## 제출 전에 직접 보완할 부분
1. 학번·이름 작성란에 본인 정보를 넣으세요. 교수 안내에 따라 실제 제출 ZIP 이름은 학번_이름_2회차.zip으로 바꾸세요. 요청하신 기본 파일명은 project_final_submission.zip입니다.
2. 보고서에 따로 사용할 양식은 현재 첨부 확인이 필요합니다. 지금 파일은 요청한 13개 구성으로 작성했습니다.
3. AI가 만든 기능을 학생 본인 직접 작성으로 기록하지 않았습니다. student_review_tasks.md의 후보를 이해하고 실제로 수행한 수정·검증만 본인 기록에 보완하세요. 교수의 “본인 수정” 조건 충족은 그 전에는 확정할 수 없습니다.
4. 개인 소감은 작성 초안으로 표시했습니다. 본인의 실제 경험으로 수정하세요.
5. 교수 아이디어 승인 원본과 본인 학습/작업 기록을 확인하세요. 대화에 전달된 승인 의견과 원본 승인은 구분했습니다.
6. Windows 사용자 PC에서 가상환경 설치·실행과 한글 문서/발표 화면을 최종 확인하세요. 현재 실행 검증 플랫폼은 Linux Python 3.12입니다.

실제 학교 SSO·승인·이메일 발송·운영 배포·모바일은 구현 또는 검증 범위가 아닙니다. 민감한 키·토큰·사용자 DB·등록 서류는 제출 소스에서 제외했습니다. 초안과 초기화 코드의 가상 인증 값은 실제 개인 인증정보가 아닙니다.
