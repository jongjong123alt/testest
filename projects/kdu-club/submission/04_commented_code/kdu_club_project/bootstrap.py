"""직접 실행할 때만 의존성을 준비합니다. 웹앱을 import할 때는 설치하지 않습니다."""
import importlib
from importlib import metadata
import os
from pathlib import Path
import subprocess
import sys


def dependencies_ready(requirements):
    """고정한 버전과 실제 import를 확인하여 불완전한 설치도 감지합니다."""
    try:
        for line in requirements.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            name, version = line.split('==', 1)
            if metadata.version(name) != version:
                return False
        for module in ('flask', 'werkzeug.security', 'PIL.Image', 'pypdf'):
            importlib.import_module(module)
        return True
    except (metadata.PackageNotFoundError, ImportError, OSError, ValueError):
        return False


def environment_python(folder):
    """Windows와 macOS/Linux의 가상환경 실행 파일 위치를 구분합니다."""
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def ensure_dependencies():
    """필요하면 전용 환경을 설치한 후 같은 실행 인자로 앱을 다시 시작합니다."""
    if sys.version_info < (3, 10):
        raise SystemExit('Python 3.10 이상이 필요합니다. Python 3.12 설치를 권장합니다.')
    base = Path(__file__).resolve().parent
    requirements = base / 'requirements.txt'
    if not requirements.is_file():
        raise SystemExit('requirements.txt가 없습니다. ZIP 전체를 압축 해제한 뒤 실행해주세요.')
    if dependencies_ready(requirements):
        return

    folder = base / '.venv'
    python = environment_python(folder)
    try:
        if not python.is_file():
            print('실행에 필요한 전용 환경을 준비합니다...', flush=True)
            subprocess.run([sys.executable, '-m', 'venv', str(folder)], check=True)

        # 현재 Python과 달라도 이미 준비된 전용 환경이면 다운로드 없이 사용합니다.
        check = [str(python), str(base / 'bootstrap.py'), '--check']
        if subprocess.run(check, check=False).returncode != 0:
            print('필요한 라이브러리를 자동 설치합니다. 인터넷 연결이 필요합니다.', flush=True)
            pip = subprocess.run([str(python), '-m', 'pip', '--version'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if pip.returncode != 0:
                subprocess.run([str(python), '-m', 'ensurepip', '--upgrade'], check=True)
            subprocess.run([str(python), '-m', 'pip', 'install',
                            '--disable-pip-version-check', '--no-input',
                            '-r', str(requirements)], check=True)
            # 실패한 설치를 무한 재시작하지 않도록 실행 전에 다시 확인합니다.
            subprocess.run(check, check=True)
        print('준비가 완료되었습니다. 사이트를 시작합니다.', flush=True)
        # 설치 과정에서 읽은 모듈 캐시를 제거하기 위해 새 Python 프로세스로 실행합니다.
        os.execv(str(python), [str(python), str(base / 'app.py'), *sys.argv[1:]])
    except (OSError, subprocess.CalledProcessError) as error:
        print('\n자동 설치 또는 실행을 완료하지 못했습니다: ' + str(error), file=sys.stderr)
        print('인터넷 연결과 폴더 쓰기 권한을 확인한 뒤 python app.py를 다시 실행해주세요.\n'
              'venv/ensurepip가 없다는 오류라면 해당 기능이 포함된 Python을 설치해주세요.\n'
              'Python 3.12를 권장합니다. 위 설치 오류 메시지도 함께 확인해주세요.', file=sys.stderr)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        raise SystemExit('\n설치를 중단했습니다. 다시 실행하면 설치를 재시도합니다.') from None


if __name__ == '__main__':
    # 부모 프로세스가 설치 상태만 확인하는 내부 명령입니다.
    raise SystemExit(0 if dependencies_ready(Path(__file__).with_name('requirements.txt')) else 1)
