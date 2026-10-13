"""Windows/macOS/Linux 공통 실행기. --demo는 원본 DB와 분리된 시연용 DB를 사용합니다."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--demo',action='store_true',help='별도 시연 DB와 샘플 계정 사용')
parser.add_argument('--host',default='127.0.0.1')
parser.add_argument('--port',type=int,default=5000)
args=parser.parse_args()
root=Path(__file__).resolve().parent
if args.demo:
    demo=root/'instance'/'demo.db'
    if not demo.exists():
        subprocess.run([sys.executable,str(root/'seed_demo.py'),'--output',str(demo)],check=True,cwd=root)
    os.environ['KDU_DATABASE']=str(demo)
    os.environ['KDU_ATTACHMENT_FOLDER']=str(root/'instance'/'demo-attachments')
import app
app.app.run(host=args.host,port=args.port,debug=False)
