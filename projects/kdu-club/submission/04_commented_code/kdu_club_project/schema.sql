-- 새 DB의 사용자·동아리·신청·공지·일정·질문·알림 구조와 가상 초기 데이터를 정의합니다. 기존 DB에 직접 실행하지 마세요.
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS club_qna;
DROP TABLE IF EXISTS club_schedules;
DROP TABLE IF EXISTS club_favorites;
DROP TABLE IF EXISTS club_posts;
DROP TABLE IF EXISTS club_members;
DROP TABLE IF EXISTS clubs;
DROP TABLE IF EXISTS users;

-- 사용자 테이블
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL
);

-- 동아리 테이블 (방번호, 오픈채팅 링크 추가)
CREATE TABLE clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    image_path TEXT,
    room_location TEXT,
    open_chat_link TEXT,
    status TEXT DEFAULT 'pending',
    applicant_id INTEGER,
    FOREIGN KEY (applicant_id) REFERENCES users (id)
);

-- 동아리 가입 신청 테이블 (지원 동기 질문 답변 추가)
CREATE TABLE club_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER,
    user_id INTEGER,
    reason TEXT,
    availability TEXT,
    goal TEXT,
    personality TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (club_id) REFERENCES clubs (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 찜하기 테이블
CREATE TABLE club_favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    club_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (club_id) REFERENCES clubs (id)
);

-- 동아리 활동 게시판 (공지/후기)
CREATE TABLE club_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER,
    user_id INTEGER,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES clubs (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 동아리별 캘린더 일정 테이블
CREATE TABLE club_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER,
    title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (club_id) REFERENCES clubs (id)
);

-- 동아리별 익명 Q&A 방명록 테이블
CREATE TABLE club_qna (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER,
    user_id INTEGER,
    question TEXT NOT NULL,
    answer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES clubs (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 인앱 알림 테이블
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 초기 테스트 계정 (학생: 20211234, 교수: prof1)
INSERT INTO users (username, password, name, role) VALUES ('20211234', '1234', '윤종민', 'student');
INSERT INTO users (username, password, name, role) VALUES ('prof1', '1234', '김교수', 'professor');

-- 🌟 풍성한 데모 시연을 위한 기본 샘플 동아리 데이터 삽입
INSERT INTO clubs (name, category, description, room_location, open_chat_link, status, applicant_id)
VALUES ('KDU 코딩클럽', '학술', '알고리즘 및 웹 프로그래밍을 함께 공부하는 동아리입니다. 초보자 환영!', '학생회관 301호', 'https://open.kakao.com/o/sample1', 'approved', 1);

INSERT INTO clubs (name, category, description, room_location, open_chat_link, status, applicant_id)
VALUES ('사운드웨이브', '공연', '통기타와 밴드 합주를 통해 캠퍼스의 로망을 즐기는 밴드 동아리입니다.', '동아리관 지하 102호', 'https://open.kakao.com/o/sample2', 'approved', 1);

INSERT INTO clubs (name, category, description, room_location, open_chat_link, status, applicant_id)
VALUES ('피닉스 FC', '체육', '매주 주말 함께 모여 축구를 즐기는 축구 동아리입니다. 실력 무관!', '대운동장', 'https://open.kakao.com/o/sample3', 'approved', 1);

-- 샘플 일정 데이터
INSERT INTO club_schedules (club_id, title, event_date, description) VALUES (1, '2026 1학기 정기 스터디 오리엔테이션', '2026-03-10', '신입 부원 대상 파이썬 기초 세션 진행');
INSERT INTO club_schedules (club_id, title, event_date, description) VALUES (2, '교내 버스킹 공연', '2026-05-20', '학생식당 앞 광장 정오 공연');
