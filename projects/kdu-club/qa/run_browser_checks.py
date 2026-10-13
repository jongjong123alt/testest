"""임시 시연 DB와 자체 서버만 생성·종료하는 브라우저 검증 실행기."""
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='kdu-browser-') as temp:
    db=Path(temp)/'demo.db'
    subprocess.run([sys.executable,str(root/'seed_demo.py'),'--output',str(db)],cwd=root,check=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    url=f'http://127.0.0.1:{port}'
    env={**os.environ,'KDU_DATABASE':str(db),'KDU_ATTACHMENT_FOLDER':str(Path(temp)/'demo-attachments'),'KDU_QA_URL':url}
    with (Path(temp)/'server.log').open('w') as log:
        server=subprocess.Popen([sys.executable,'-m','flask','--app','app','run','--host','127.0.0.1','--port',str(port)],cwd=root,env=env,stdout=log,stderr=log)
        try:
            for _ in range(50):
                try:
                    with urllib.request.urlopen(url+'/health',timeout=1) as response:
                        if response.status==200:break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('QA server failed to start')
            subprocess.run(['node',str(root/'qa/browser_check.js')],cwd=root,env=env,check=True,timeout=120)
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()
