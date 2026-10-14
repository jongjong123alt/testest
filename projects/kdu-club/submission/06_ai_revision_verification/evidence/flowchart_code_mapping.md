# 순서도와 코드 연결
시작: app.py의 __main__ 옵션/seed_demo.py/Flask app.run. DB: init_db/migrate_database/get_db/close_connection.
요청 검사: protect_requests 및 기능별 student_required/owned_club/visible_club.
로그인: login/signup. 조회: index/club_detail/student_mypage/notifications.
신청: apply_club/register_club/cancel_apply. 관리: manage_club/manage_member/manage_post/manage_schedule/answer_qna.
입력/파일: text_field/date_field/validated_upload/registration_pdf. 상태 변경 알림: manage_member/professor_dashboard→notify.
오류: HTTPException handler와 각 POST의 ValueError rollback. 정상 응답 후 다음 요청을 받는 HTTP 서버입니다. 로그아웃은 세션만 종료합니다. 서버 종료는 Ctrl+C입니다.
서버 시작 전 DB 생성 오류는 터미널에 출력되고 시작이 중단될 수 있습니다. 순서도의 일반 오류 응답은 서버가 시작된 후의 요청 오류를 의미합니다.
