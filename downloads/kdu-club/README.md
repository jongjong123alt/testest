# KDU 동아리 — D01–D12 데스크톱 UI 구현본

[최신 수정본 ZIP 다운로드](https://github.com/jongjong123alt/testest/raw/refs/heads/master/downloads/kdu-club/kdu_club_project_updated.zip)

[전체 소스와 실행 안내](../../projects/kdu-club/README.md) · [검증 기록](../../projects/kdu-club/VERIFICATION.md) · [화면 캡처](../../projects/kdu-club/qa/screenshots)

제공받은 동아리 과제의 화면을 Flask·SQLite·Jinja2에 적용했습니다. FOCURVE와 무관하며 모바일 UI는 포함하지 않습니다. 로그인, 탐색·검색·찜, 가입 신청, 내 활동, 알림, 개설 재신청, 모집 관리, 가입 심사, 공지 첨부, 일정 관리, 교수 개설 심사를 구현했습니다.

자동 테스트 35개와 Chromium 브라우저 검증이 통과했습니다. 엄격한 Figma 원본 픽셀·폰트 일치 검증은 미완료이며 자세한 범위는 소스의 design-qa.md에 기록했습니다.

ZIP을 해제하고 의존성을 설치한 뒤 `python app.py`로 실행하세요. 학생은 `kdu_student / sample1234`, 교수는 `kdu_professor / sample1234`입니다. 기존 database.db와 별도 시연 DB를 함께 포함하고 있으며 python app.py는 기본적으로 시연 DB를 사용하며, 기존 DB는 python app.py --original로 실행합니다. 전체 소스 폴더는 런타임 DB를 Git에서 제외하고 필요 시 생성합니다.
