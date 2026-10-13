# 경동대학교 동아리 플랫폼 수정본

[kdu_club_project_updated.zip 다운로드](https://github.com/jongjong123alt/testest/raw/refs/heads/master/downloads/kdu-club/kdu_club_project_updated.zip)

ZIP 파일에는 수정된 Flask 소스, 템플릿, 기존 데이터베이스와 업로드 이미지, 설치 의존성, 테스트 및 실행 안내가 포함되어 있습니다. 압축 해제 후 프로젝트의 README.md를 확인하세요.

## 주요 보완

- 교수 승인 전 동아리 공개 방지 및 개설 신청 상태 표시
- 가입 승인 권한 검사
- 알림 중복 방지 및 읽음 처리
- 업로드 용량·형식 검사, 비밀번호 해시, CSRF 보호
- DB 구조 보완과 기존 데이터 유지

자동 테스트 10개와 실제 서버 응답 및 DB 보존 검증을 통과했습니다. [검증 기록](VERIFICATION.md)을 확인하세요.

UI는 기존 화면을 유지하며 Figma 디자인 적용은 추후 작업입니다. 실제 학교 계정 인증은 연동되어 있지 않습니다.
