"""화면 시연용 DB 생성. 기존 DB는 덮어쓰지 않습니다."""
import argparse
import os
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--output',default='instance/demo.db')
args=parser.parse_args()
output=Path(args.output).resolve()
if output.exists():raise SystemExit('이미 존재하는 DB는 덮어쓰지 않습니다. 다른 출력 경로를 지정하세요.')
output.parent.mkdir(parents=True,exist_ok=True)
os.environ['KDU_DATABASE']=str(output)
os.environ['KDU_ATTACHMENT_FOLDER']=str(output.parent/'demo-attachments')
import app
from werkzeug.security import generate_password_hash
from datetime import timedelta

today=app.now();starts=today.replace(day=1,hour=9,minute=0,second=0,microsecond=0)
ends=(starts.replace(day=28)+timedelta(days=4)).replace(day=1,hour=0,minute=0)-timedelta(minutes=1)
with app.app.app_context():
 db=app.get_db()
 db.execute('UPDATE users SET username=?,password=?,name=? WHERE id=1',('kdu_student',generate_password_hash('sample1234'),'김민준'))
 db.execute('UPDATE users SET username=?,password=?,name=? WHERE id=2',('kdu_professor',generate_password_hash('sample1234'),'김교수'))
 def user(name):
  # 해당 기능의 데이터를 준비하거나 공통 처리를 수행합니다.
  return db.execute('INSERT INTO users(username,password,name,role) VALUES(?,?,?,?)',('demo_'+str(db.execute('SELECT COUNT(*) FROM users').fetchone()[0]),generate_password_hash('sample1234'),name,'student')).lastrowid
 owner2,owner3=user('박서연'),user('최유진')
 db.execute('UPDATE clubs SET applicant_id=? WHERE id=2',(owner2,));db.execute('UPDATE clubs SET applicant_id=? WHERE id=3',(owner3,))
 for c in db.execute('SELECT * FROM clubs').fetchall():
  rid=db.execute('INSERT INTO recruitment_rounds(club_id,starts_at,ends_at,capacity) VALUES(?,?,?,?)',(c['id'],starts.isoformat(timespec='minutes'),ends.isoformat(timespec='minutes'),20 if c['id']==1 else 12 if c['id']==2 else 15)).lastrowid
  if c['id']==2:db.execute('UPDATE recruitment_rounds SET starts_at=?,ends_at=? WHERE id=?',((ends+timedelta(days=1)).isoformat(timespec='minutes'),(ends+timedelta(days=15)).isoformat(timespec='minutes'),rid))
  if c['id']==3:db.execute('UPDATE recruitment_rounds SET closed=1 WHERE id=?',(rid,))
  db.execute('UPDATE clubs SET current_round_id=?,campus=?,activity_time=?,fee=?,requirements=?,description=?,activity_plan=? WHERE id=?',
             (rid,'메디컬캠퍼스' if c['id']==2 else '글로벌캠퍼스','매주 수요일 18:00–20:00' if c['id']==1 else '매주 목요일' if c['id']==2 else '매주 토요일','월 5,000원' if c['id']==1 else '없음','전공 무관 · 정기 활동 참여 가능',
              '개발에 관심 있는 학생들이 모여 기초를 배우고 작은 프로젝트를 만드는 동아리입니다. 처음 시작하는 분도 환영해요. 매주 스터디와 팀 프로젝트를 함께 진행합니다.' if c['id']==1 else c['description'],
              '1–2주: Python·Flask 기초 스터디 / 3–4주: 팀 구성과 아이디어 정리 / 5–8주: 동아리 웹 서비스 만들기 / 9주: 결과 공유',c['id']))
 rid=db.execute('SELECT current_round_id FROM clubs WHERE id=1').fetchone()[0]
 for i in range(24):
  uid=1 if i==0 else user(['정하늘','윤지우','이서연','박지훈','최유진'][i%5]+str(i))
  db.execute('INSERT INTO club_members(club_id,user_id,reason,availability,goal,personality,status,recruitment_id,submitted_at,reviewed_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
             (1,uid,'혼자 공부할 때 막혔던 부분을 함께 해결하고 싶어요. Flask로 작은 웹 서비스를 만들며 협업을 경험하고 싶습니다.','매주 수요일 18:00 정기 활동에 참여할 수 있어요.','이번 학기에 팀원들과 동아리 웹 서비스를 완성하고 싶어요.','서로의 속도를 존중하고, 배운 내용을 나누는 것을 중요하게 생각해요.','approved',rid if i<8 else None,starts.isoformat(timespec='minutes'),(starts+timedelta(days=4+i%3)).isoformat(timespec='minutes')))
 for name in ['이서연','박지훈','최유진']:
  uid=user(name)
  db.execute('INSERT INTO club_members(club_id,user_id,reason,availability,goal,personality,status,recruitment_id,submitted_at) VALUES(?,?,?,?,?,?,?,?,?)',
             (1,uid,'혼자 공부할 때 막혔던 부분을 함께 해결하고 싶어요. Flask로 작은 웹 서비스를 만들며 협업을 경험하고 싶습니다.','매주 수요일 18:00 참여 가능합니다.','이번 학기에 팀원들과 동아리 웹서비스를 완성하고 싶어요.','서로의 속도를 존중하고, 배운 내용을 나누는 것을 중요하게 생각해요.','pending',rid,(starts+timedelta(days=9)).isoformat(timespec='minutes')))
 for cid,status,reason in [(2,'pending',''),(3,'rejected','토요일 정기 활동 참여가 어려워요. 현재 모집이 마감되어 재신청할 수 없어요.')]:
  db.execute('INSERT INTO club_members(club_id,user_id,reason,availability,goal,personality,status,rejection_reason,submitted_at,reviewed_at) VALUES(?,1,?,?,?,?,?,?,?,?)',
             (cid,'함께 활동하며 배우고 싶습니다.','정기 참여 가능','동아리 활동','협력',status,reason,starts.isoformat(timespec='minutes'),starts.isoformat(timespec='minutes') if reason else None))
 for cid in [1,3]:db.execute('INSERT INTO club_favorites(user_id,club_id) VALUES(1,?)',(cid,))
 for status,title,owner,count in [('rejected','KDU 코딩클럽',1,1),('pending','KDU 코딩클럽 스터디',1,2),('pending','사운드웨이브 신규 모임',owner2,1)]:
  db.execute('INSERT INTO clubs(name,category,description,activity_plan,campus,activity_time,fee,requirements,room_location,status,applicant_id,rejection_reason,submitted_at,reviewed_at,submission_count) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
             (title,'학술' if '코딩' in title else '공연','개발에 관심 있는 학생들이 모여 기초를 배우고 작은 프로젝트를 만드는 동아리입니다.','1–2주: Python·Flask 기초 스터디 / 3–4주: 팀 구성과 아이디어 정리 / 5–8주: 동아리 웹 서비스 만들기','글로벌캠퍼스','수요일 18:00–20:00','월 5,000원','전공 무관 · 정기 활동 참여 가능','학생회관 302호',status,owner,'활동 계획에 주차별 진행 내용과 정기 활동 장소를 구체적으로 작성해주세요.' if count>1 or status=='rejected' else '',starts.isoformat(timespec='minutes'),starts.isoformat(timespec='minutes'),count))
 db.execute('UPDATE club_schedules SET title=?,event_date=?,end_date=?,location=?,description=? WHERE id=1',('Flask 기초 스터디',(today+timedelta(days=1)).replace(hour=18,minute=0).isoformat(timespec='minutes'),(today+timedelta(days=1)).replace(hour=20,minute=0).isoformat(timespec='minutes'),'학생회관 302호','Flask 페이지 이동과 폼 제출을 실습해요. 노트북과 정리한 자료를 준비해주세요.'))
 db.execute('INSERT INTO club_schedules(club_id,title,event_date,end_date,location,description) VALUES(1,?,?,?,?,?)',('팀 프로젝트 아이디어 나누기',(today+timedelta(days=8)).replace(hour=18,minute=0).isoformat(timespec='minutes'),(today+timedelta(days=8)).replace(hour=20,minute=0).isoformat(timespec='minutes'),'학생회관 302호','함께 만들 서비스 아이디어를 나눠요.'))
 pid=db.execute('INSERT INTO club_posts(club_id,user_id,title,content) VALUES(1,1,?,?)',('10월 스터디 안내와 준비 자료','이번 주는 Flask의 페이지 이동과 폼 제출을 배워요. 노트북과 아래 자료를 준비해 주세요.')).lastrowid
 folder=Path(app.app.config['ATTACHMENT_FOLDER']);folder.mkdir(parents=True,exist_ok=True)
 filename='demo-study.pdf';data=b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n';(folder/filename).write_bytes(data)
 db.execute('INSERT INTO attachments(club_id,user_id,post_id,name,stored_name,size) VALUES(1,1,?,?,?,?)',(pid,'10월_스터디_자료.pdf',filename,len(data)))
 db.execute('INSERT INTO club_qna(club_id,user_id,question,answer) VALUES(1,1,?,?)',('코딩을 처음 배우는데 가입할 수 있나요?','물론이에요! 기초 스터디부터 함께 시작할 수 있어요.'))
 mid=db.execute('SELECT id FROM club_members WHERE user_id=1 AND club_id=1').fetchone()[0]
 app.notify(1,'KDU 코딩클럽 가입이 승인되었어요.','membership',1,mid)
 mid=db.execute('SELECT id FROM club_members WHERE user_id=1 AND club_id=3').fetchone()[0]
 app.notify(1,'피닉스 FC 가입 신청이 반려되었어요.','membership',3,mid)
 app.notify(1,'KDU 코딩클럽 등록 서류 사전 확인 예시입니다. 학교 최종 승인과는 별개입니다.','club',1)
 db.execute('UPDATE notifications SET is_read=1 WHERE id=(SELECT MAX(id) FROM notifications)')
 db.commit()
print('샘플 DB:',output)
print('시연 계정: kdu_student / sample1234, kdu_professor / sample1234')
