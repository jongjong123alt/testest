"""D01–D12의 권한·상태·업로드·모집 경계를 임시 DB로 검증합니다."""
import os
import sys
import tempfile
import unittest
import io
import zipfile
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_sandbox=tempfile.TemporaryDirectory()
os.environ['KDU_DATABASE']=str(Path(_sandbox.name)/'initial.db')
import app as module
from werkzeug.security import generate_password_hash,check_password_hash
from PIL import Image

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        module.DATABASE=str(Path(self.temp.name)/'test.db')
        module.app.config.update(TESTING=True,ATTACHMENT_FOLDER=str(Path(self.temp.name)/'attachments'),NOW=lambda:datetime(2026,10,13,12))
        module.init_db()
        with module.app.app_context():
            db=module.get_db()
            for username,name in [('other','신청학생'),('outsider','무관학생')]:
                db.execute('INSERT INTO users(username,password,name,role) VALUES(?,?,?,?)',(username,generate_password_hash('password123'),name,'student'))
            rid=db.execute('INSERT INTO recruitment_rounds(club_id,starts_at,ends_at,capacity) VALUES(?,?,?,?)',(1,'2026-10-01T09:00','2026-10-31T23:59',20)).lastrowid
            db.execute('UPDATE clubs SET current_round_id=?,campus=?,activity_time=?,fee=?,requirements=? WHERE id=1',(rid,'글로벌캠퍼스','수요일 18:00','없음','전공 무관'))
            db.commit()
        self.owner=self.client(1);self.prof=self.client(2,'professor');self.student=self.client(3);self.outsider=self.client(4)

    def tearDown(self):
        self.temp.cleanup();module.app.config.pop('NOW',None)

    def client(self,uid,role='student'):
        c=module.app.test_client()
        with c.session_transaction() as s:s.update(user_id=uid,role=role,name='테스트',csrf_token='token')
        return c

    def post(self,c,path,data=None):
        return c.post(path,data={'csrf_token':'token',**(data or {})})

    def rows(self,sql,args=()):
        with module.app.app_context():return [dict(r) for r in module.get_db().execute(sql,args)]

    def execute(self,sql,args=()):
        with module.app.app_context():
            db=module.get_db();result=db.execute(sql,args);db.commit();return result.lastrowid

    def club_fields(self,**extra):
        return dict(name='새동아리',category='학술',description='함께 배우는 새 동아리입니다.',activity_plan='매주 함께 공부하고 프로젝트를 만들어요.',campus='글로벌캠퍼스',activity_time='수요일 18:00',fee='없음',room_location='301호',requirements='전공 무관',**extra)

    def apply(self,c=None,cid=1):
        return self.post(c or self.student,f'/clubs/apply/{cid}',dict(reason='함께 코딩을 배우고 싶습니다.',availability='수요일 참여 가능',goal='웹 서비스 만들기',personality='서로 존중'))

    def decide(self,action='approve',**extra):
        mid=self.rows('SELECT id FROM club_members ORDER BY id DESC')[0]['id']
        return self.post(self.owner,'/student/manage_member',dict(member_id=mid,action=action,**extra))

    def png(self):
        stream=io.BytesIO();Image.new('RGB',(8,8)).save(stream,format='PNG');return stream.getvalue()

    def upload(self,body=None,name='poster.png',client=None,club_id=1):
        return self.post(client or self.owner,f'/clubs/{club_id}/attachments/upload',dict(file=(io.BytesIO(self.png() if body is None else body),name)))

    def manager_fields(self,**extra):
        fields=dict(description='함께 배워요. 좋은 동아리입니다.',campus='글로벌캠퍼스',activity_time='수요일',fee='없음',requirements='전공 무관',room_location='302호',starts_at='2026-10-01T09:00',ends_at='2026-10-31T23:59',capacity='20')
        fields.update(extra);return fields

    def test_creation_approval_and_notification_once(self):
        self.assertEqual(self.post(self.owner,'/clubs/register',self.club_fields()).status_code,302)
        cid=self.rows("SELECT id FROM clubs WHERE name='새동아리'")[0]['id']
        self.assertEqual(self.rows('SELECT status FROM clubs WHERE id=?',(cid,))[0]['status'],'pending')
        self.assertNotIn('새동아리',self.student.get('/').text)
        self.assertEqual(self.student.get(f'/clubs/{cid}').status_code,403)
        self.assertIn('승인 대기',self.owner.get('/student/mypage').text)
        for _ in range(2):self.assertEqual(self.post(self.prof,'/professor/dashboard',dict(club_id=cid,action='approve')).status_code,302)
        self.assertEqual(self.rows('SELECT user_id FROM notifications'),[{'user_id':1}])
        self.assertIn('새동아리',self.student.get('/').text)

    def test_rejection_reason_required_and_resubmission(self):
        self.post(self.owner,'/clubs/register',self.club_fields());cid=self.rows('SELECT MAX(id) id FROM clubs')[0]['id']
        self.post(self.prof,'/professor/dashboard',dict(club_id=cid,action='reject'))
        self.assertEqual(self.rows('SELECT status FROM clubs WHERE id=?',(cid,))[0]['status'],'pending')
        self.post(self.prof,'/professor/dashboard',dict(club_id=cid,action='reject',rejection_reason='활동 계획을 보완해주세요.'))
        r=self.owner.get(f'/clubs/{cid}/resubmit');self.assertIn('활동 계획을 보완해주세요.',r.text)
        self.assertEqual(self.outsider.get(f'/clubs/{cid}/resubmit').status_code,403)
        self.assertEqual(self.post(self.owner,f'/clubs/{cid}/resubmit',self.club_fields()).status_code,302)
        c=self.rows('SELECT * FROM clubs WHERE id=?',(cid,))[0]
        self.assertEqual(c['status'],'pending');self.assertEqual(c['submission_count'],2)
        self.assertIn('이전 반려 사유',self.prof.get(f'/professor/dashboard?club={cid}').text)
        self.post(self.prof,'/professor/dashboard',dict(club_id=cid,action='approve'))
        self.assertEqual(len(self.rows('SELECT * FROM notifications')),2)
        self.assertEqual(self.owner.get(f'/clubs/{cid}/resubmit').status_code,409)

    def test_creation_validation_preserves_fields(self):
        fields=self.club_fields();fields['name']='X';r=self.post(self.owner,'/clubs/register',fields)
        self.assertEqual(r.status_code,400);self.assertIn(fields['activity_plan'],r.text)
        self.assertEqual(len(self.rows('SELECT * FROM clubs')),3)

    def test_member_authorization_and_repeat(self):
        self.apply();mid=self.rows('SELECT id FROM club_members')[0]['id']
        self.assertEqual(self.post(self.outsider,'/student/manage_member',dict(member_id=mid,action='approve')).status_code,403)
        for _ in range(2):self.decide()
        self.assertEqual(self.rows('SELECT user_id FROM notifications'),[{'user_id':3}])

    def test_member_rejection_and_result(self):
        self.apply();self.decide('reject')
        self.assertEqual(self.rows('SELECT status FROM club_members')[0]['status'],'pending')
        self.decide('reject',rejection_reason='활동 시간이 맞지 않습니다.')
        self.assertIn('활동 시간이 맞지 않습니다.',self.student.get('/student/mypage').text)
        self.assertNotIn('활동 시간이 맞지 않습니다.',self.outsider.get('/student/mypage').text)

    def test_application_required_fields_and_duplicate(self):
        r=self.post(self.student,'/clubs/apply/1',dict(reason='짧음',availability='가능',goal='공부',personality='존중'))
        self.assertEqual(r.status_code,400);self.assertIn('짧음',r.text)
        self.apply();self.assertEqual(self.apply().status_code,400)
        self.assertEqual(len(self.rows('SELECT * FROM club_members')),1)

    def test_cancellation_only_pending(self):
        self.apply();self.post(self.student,'/clubs/cancel_apply/1');self.assertEqual(len(self.rows('SELECT * FROM club_members')),0)
        self.apply();self.decide();self.post(self.student,'/clubs/cancel_apply/1');self.assertEqual(len(self.rows('SELECT * FROM club_members')),1)

    def test_recruitment_dates_and_filter(self):
        self.assertIn('KDU 코딩클럽',self.student.get('/?recruiting=1').text)
        self.assertNotIn('사운드웨이브',self.student.get('/?recruiting=1').text)
        for stamp in [datetime(2026,9,30,23,59),datetime(2026,11,1)]:
            module.app.config['NOW']=lambda s=stamp:s
            self.assertEqual(self.apply().status_code,400)
        module.app.config['NOW']=lambda:datetime(2026,10,13,12)
        self.assertEqual(self.apply().status_code,302)

    def test_capacity_and_closed_period_review(self):
        self.execute('UPDATE recruitment_rounds SET capacity=1 WHERE club_id=1')
        self.apply();self.apply(self.outsider)
        self.post(self.owner,'/clubs/1/manage',dict(action='close'))
        mids=self.rows('SELECT id FROM club_members ORDER BY id')
        for m in mids:self.post(self.owner,'/student/manage_member',dict(member_id=m['id'],action='approve'))
        self.assertEqual(len(self.rows("SELECT id FROM club_members WHERE status='approved'")),1)
        self.assertEqual(len(self.rows("SELECT id FROM club_members WHERE status='pending'")),1)
        self.assertEqual(len(self.rows('SELECT * FROM notifications')),1)

    def test_manager_validation_and_immutable_name(self):
        self.assertEqual(self.post(self.owner,'/clubs/1/manage',self.manager_fields(ends_at='2026-09-01T09:00')).status_code,400)
        self.assertEqual(self.post(self.owner,'/clubs/1/manage',self.manager_fields(capacity='0')).status_code,400)
        fields=self.manager_fields();fields['name']='변경 불가';fields['category']='봉사'
        self.assertEqual(self.post(self.owner,'/clubs/1/manage',fields).status_code,302)
        self.assertEqual(self.rows('SELECT name,category FROM clubs WHERE id=1')[0],{'name':'KDU 코딩클럽','category':'학술'})
        self.apply();self.decide()
        self.assertEqual(self.post(self.owner,'/clubs/1/manage',self.manager_fields(capacity='0')).status_code,400)

    def test_new_round_counts_exclude_old_members(self):
        self.apply();self.decide();self.post(self.owner,'/clubs/1/manage',dict(action='close'))
        r=self.post(self.owner,'/clubs/1/manage',self.manager_fields(new_round='1'))
        self.assertEqual(r.status_code,302)
        with module.app.app_context():
            club=module.row('SELECT * FROM clubs WHERE id=1');self.assertEqual(module.recruitment(club)['approved'],0)
        self.assertEqual(len(self.rows("SELECT * FROM club_members WHERE status='approved'")),1)
        self.assertEqual(self.apply().status_code,400) # 이미 부원인 학생은 새 모집 중복 가입 불가

    def test_new_round_requires_processing_pending(self):
        self.apply();self.post(self.owner,'/clubs/1/manage',dict(action='close'))
        self.assertEqual(self.post(self.owner,'/clubs/1/manage',self.manager_fields(new_round='1')).status_code,400)

    def test_concurrent_capacity_approval(self):
        self.execute('UPDATE recruitment_rounds SET capacity=1 WHERE club_id=1');self.apply();self.apply(self.outsider)
        mids=[r['id'] for r in self.rows('SELECT id FROM club_members')]
        def approve(mid):return self.post(self.client(1),'/student/manage_member',dict(member_id=mid,action='approve')).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(list(pool.map(approve,mids)),[302,302])
        self.assertEqual(len(self.rows("SELECT id FROM club_members WHERE status='approved'")),1)

    def test_search_binding_and_category(self):
        r=self.student.get('/',query_string={'keyword':'코딩','category':'학술'});self.assertEqual(r.status_code,200)
        self.assertIn('KDU 코딩클럽',r.text);self.assertNotIn('사운드웨이브',r.text)
        r=self.student.get('/',query_string={'keyword':"' OR 1=1 --",'category':"'"});self.assertEqual(r.status_code,200)
        self.assertNotIn('KDU 코딩클럽',r.text);self.assertEqual(len(self.rows('SELECT * FROM clubs')),3)

    def test_favorites_toggle_and_user_scope(self):
        self.post(self.student,'/clubs/favorite/1');self.assertIn('찜한 동아리 · 1',self.student.get('/student/mypage').text)
        self.assertIn('찜한 동아리 · 0',self.outsider.get('/student/mypage').text)
        self.post(self.student,'/clubs/favorite/1');self.assertEqual(len(self.rows('SELECT * FROM club_favorites')),0)

    def test_notification_read_scope_and_result(self):
        self.apply();self.decide();nid=self.rows('SELECT id FROM notifications')[0]['id']
        self.post(self.outsider,f'/notifications/{nid}/read');self.assertEqual(self.rows('SELECT is_read FROM notifications')[0]['is_read'],0)
        self.assertEqual(self.outsider.get(f'/notifications/{nid}/result').status_code,404)
        r=self.student.get(f'/notifications/{nid}/result');self.assertEqual(r.status_code,302);self.assertIn('application=',r.location)
        self.assertEqual(self.rows('SELECT is_read FROM notifications')[0]['is_read'],1)

    def test_read_all_scoped(self):
        self.apply();self.decide();self.post(self.outsider,'/notifications/read-all');self.assertEqual(self.rows('SELECT is_read FROM notifications')[0]['is_read'],0)
        self.post(self.student,'/notifications/read-all');self.assertEqual(self.rows('SELECT is_read FROM notifications')[0]['is_read'],1)

    def test_schedule_create_edit_delete_and_validation(self):
        fields=dict(title='Flask 스터디',description='함께 공부',location='302호',event_date='2026-10-14T18:00',end_date='2026-10-14T20:00')
        fields['end_date']='2026-10-14T17:00';self.assertEqual(self.post(self.owner,'/clubs/1/schedules',fields).status_code,400)
        fields['end_date']='2026-10-14T20:00';self.assertEqual(self.post(self.owner,'/clubs/1/schedules',fields).status_code,302)
        sid=self.rows('SELECT MAX(id) id FROM club_schedules')[0]['id'];fields['title']='수정 스터디'
        self.assertEqual(self.post(self.owner,f'/clubs/1/schedules/{sid}',fields).status_code,302)
        self.assertIn('수정 스터디',self.student.get('/clubs/1').text)
        self.assertEqual(self.outsider.get(f'/clubs/1/schedules/{sid}').status_code,403)
        self.post(self.owner,f'/clubs/1/schedules/{sid}',dict(action='delete'));self.assertNotIn('수정 스터디',self.student.get('/clubs/1').text)

    def test_schedule_cross_club_ids(self):
        self.assertEqual(self.owner.get('/clubs/1/schedules/2').status_code,404)
        self.assertEqual(self.owner.get('/clubs/1/posts/999').status_code,404)

    def test_upload_type_size_and_content(self):
        for body,name in [(b'MZ','bad.exe'),(b'not image','bad.png'),(b'not PDF','bad.pdf'),(b'no','bad.docx'),(b'x'*(10*1024*1024+1),'huge.pdf')]:
            with self.subTest(name=name):self.assertEqual(self.upload(body,name).status_code,400)
        self.assertEqual(len(self.rows('SELECT * FROM attachments')),0)
        self.assertEqual(self.upload(client=self.outsider).status_code,403)

    def test_valid_file_formats(self):
        doc=io.BytesIO()
        with zipfile.ZipFile(doc,'w') as z:z.writestr('word/document.xml','<document/>')
        for body,name in [(self.png(),'image.png'),(b'%PDF-1.4\n','document.pdf'),(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'+b'test','document.hwp'),(doc.getvalue(),'document.docx')]:
            self.assertEqual(self.upload(body,name).status_code,201)

    def test_post_multiple_attachments_edit_remove_and_preserve(self):
        aid=self.upload(b'%PDF-1.4\n','notice.pdf').json['id']
        fields=dict(title='공지',content='내용을 안내합니다.',attachment_ids=str(aid))
        self.assertEqual(self.post(self.owner,'/clubs/1/posts',fields).status_code,302)
        pid=self.rows('SELECT id FROM club_posts')[0]['id']
        self.assertIn('notice.pdf',self.student.get('/clubs/1').text)
        self.assertEqual(self.student.get(f'/attachments/{aid}').status_code,200)
        fields['title']='수정 공지';self.post(self.owner,f'/clubs/1/posts/{pid}',fields)
        self.assertIn('수정 공지',self.student.get('/clubs/1').text)
        self.post(self.owner,f'/clubs/1/posts/{pid}',dict(title='수정 공지',content='본문 유지'))
        self.assertNotIn('notice.pdf',self.student.get('/clubs/1').text)
        self.assertEqual(self.student.get(f'/attachments/{aid}').status_code,403)

    def test_post_validation_preserves_fields(self):
        aid=self.upload().json['id']
        r=self.post(self.owner,'/clubs/1/posts',dict(title='제목 유지',content='',attachment_ids=str(aid)))
        self.assertEqual(r.status_code,400);self.assertIn('제목 유지',r.text)
        self.assertEqual(len(self.rows('SELECT * FROM club_posts')),0)

    def test_post_attachment_limit_and_cross_club(self):
        ids=[str(self.upload().json['id']) for _ in range(4)]
        self.assertEqual(self.post(self.owner,'/clubs/1/posts',dict(title='공지',content='본문',attachment_ids=ids)).status_code,400)
        self.assertEqual(self.post(self.owner,'/clubs/2/posts',dict(title='공지',content='본문',attachment_ids=ids[:1])).status_code,400)
        self.assertEqual(len(self.rows('SELECT * FROM club_posts')),0)

    def test_private_qna_enforced(self):
        self.post(self.student,'/clubs/1/qna',dict(question='비밀 질문 테스트',is_private='1'))
        qid=self.rows('SELECT id FROM club_qna')[0]['id']
        self.assertIn('비밀 질문 테스트',self.owner.get('/clubs/1').text)
        self.assertIn('비밀 질문 테스트',self.student.get('/clubs/1').text)
        self.assertNotIn('비밀 질문 테스트',self.outsider.get('/clubs/1').text)
        self.assertNotIn('비밀 질문 테스트',module.app.test_client().get('/clubs/1').text)
        self.assertEqual(self.post(self.outsider,f'/clubs/qna/answer/{qid}',dict(answer='악성답변')).status_code,403)
        self.post(self.owner,f'/clubs/qna/answer/{qid}',dict(answer='개설자 답변'))
        self.assertIn('개설자 답변',self.student.get('/clubs/1').text)

    def test_professor_only_review(self):
        self.assertEqual(self.prof.get('/professor/dashboard').status_code,200)
        for path in ['/','/clubs/1','/student/mypage','/notifications','/clubs/1/manage','/clubs/1/members','/clubs/1/posts','/clubs/1/schedules']:
            self.assertEqual(self.prof.get(path).status_code,403,path)
        self.assertEqual(self.owner.get('/professor/dashboard').status_code,302)

    def test_csrf_rejected(self):
        self.assertEqual(self.owner.post('/clubs/register',data={}).status_code,400)
        self.assertEqual(self.owner.post('/clubs/1/attachments/upload',data={}).status_code,400)

    def test_password_hash_and_login(self):
        c=module.app.test_client();c.get('/signup')
        with c.session_transaction() as s:token=s['csrf_token']
        self.assertEqual(c.post('/signup',data=dict(csrf_token=token,username='new',password='secure123',name='신규')).status_code,302)
        password=self.rows("SELECT password FROM users WHERE username='new'")[0]['password'];self.assertTrue(check_password_hash(password,'secure123'));self.assertNotEqual(password,'secure123')
        c.post('/login',data=dict(csrf_token=token,username='new',password='wrong'))
        with c.session_transaction() as s:self.assertNotIn('user_id',s)
        self.assertEqual(c.post('/login',data=dict(csrf_token=token,username='new',password='secure123')).status_code,302)
        with c.session_transaction() as s:self.assertEqual(s['role'],'student')

    def test_unknown_ids_and_invalid_actions(self):
        self.assertEqual(self.student.get('/clubs/999').status_code,404)
        self.assertEqual(self.student.get('/clubs/apply/999').status_code,404)
        self.assertEqual(self.post(self.owner,'/clubs/qna/answer/999',dict(answer='답변')).status_code,404)
        self.assertEqual(self.post(self.prof,'/professor/dashboard',dict(club_id=1,action='bad')).status_code,400)
        self.assertEqual(self.post(self.prof,'/professor/dashboard',dict(club_id=999,action='approve')).status_code,404)

    def test_all_desktop_screens_render(self):
        for path in ['/','/login','/clubs/1','/clubs/apply/1','/student/mypage','/notifications','/clubs/register','/clubs/1/manage','/clubs/1/members','/clubs/1/posts','/clubs/1/schedules','/clubs/1/schedules/1']:
            r=self.owner.get(path);self.assertEqual(r.status_code,200,path);self.assertIn('KDU 동아리',r.text)
        self.assertEqual(self.prof.get('/professor/dashboard').status_code,200)

    def test_migration_repeatable_preserves_data(self):
        before=self.rows('SELECT * FROM users')
        with module.app.app_context():
            module.migrate_database(module.get_db());module.migrate_database(module.get_db())
        self.assertEqual(before,self.rows('SELECT * FROM users'))
        self.assertEqual(len(self.rows('SELECT * FROM clubs')),3)

if __name__=='__main__':unittest.main()
