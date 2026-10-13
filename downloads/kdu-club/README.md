# KDU 동아리 — 공식 공고 반영 최신 버전

[최신 프로젝트 ZIP 다운로드](https://github.com/jongjong123alt/testest/raw/refs/heads/master/downloads/kdu-club/kdu_club_project_updated.zip)

[전체 소스·실행 안내](../../projects/kdu-club/README.md) · [검증 기록](../../projects/kdu-club/VERIFICATION.md) · [구현 화면](../../projects/kdu-club/qa/screenshots)

사용자가 제공한 **2026 메트로폴캠퍼스 동아리 모집 공고와 등록 서식**을 반영했습니다. 최소 20명, 지도교수·설립일·대표자, 12개월 활동 계획, 신규/기존 서류, PDF 준비본, 비공개 열람, 교수 사전 검토, 제출·평가·동아리실 안내를 제공합니다.

등록 자료 작성과 사전 검토는 날짜와 관계없이 이용할 수 있습니다. 공식 공고의 서식·자격·서류 검토 기준을 반영했습니다. 사이트의 저장·사전 확인은 학교 이메일 접수나 최종 승인이 아닙니다. 실제 제출은 신청자가 공고에 따라 별도로 진행합니다.

자동 테스트 **42개 통과**, Chromium 브라우저 검사 통과·콘솔 오류 0개. 모바일과 실제 학교 계정 인증은 포함하지 않습니다.

새 폴더에 압축을 풀고 `pip install -r requirements.txt` 후 `python app.py`로 실행하세요. 학생 `kdu_student / sample1234`, 교수 `kdu_professor / sample1234`입니다. 기존 DB와 instance 데이터는 먼저 보존하세요. 실행 시 기존 자료를 삭제하지 않고 필요한 구조만 추가합니다. 실제 등록 준비 PDF는 배포 ZIP에 포함하지 않습니다.
