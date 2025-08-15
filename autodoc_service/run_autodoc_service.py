#!/usr/bin/env python3
"""
AutoDoc Service 실행 스크립트 (크로스플랫폼)

Python 기반 실행 스크립트로 모든 플랫폼에서 동작
"""
import sys
import os
import subprocess
from pathlib import Path


def check_python_version():
    """Python 버전 확인"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 이상이 필요합니다.")
        print(f"현재 버전: {sys.version}")
        return False
    return True


def install_dependencies():
    """의존성 설치"""
    print("📦 의존성 설치 중...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt 파일이 없습니다.")
        return False
    
    # 오프라인 모드 확인
    wheels_dir = Path(__file__).parent / "wheels"
    
    if wheels_dir.exists():
        print("🔧 오프라인 모드: wheels 디렉터리에서 설치")
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "--no-index", "--find-links", str(wheels_dir),
            "-r", str(requirements_file)
        ]
    else:
        print("🌐 온라인 모드: PyPI에서 설치")
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "-r", str(requirements_file)
        ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 의존성 설치 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 의존성 설치 실패: {e}")
        print(f"출력: {e.stdout}")
        print(f"에러: {e.stderr}")
        return False


def check_templates():
    """템플릿 파일 존재 확인"""
    print("🔍 템플릿 파일 확인 중...")
    
    templates_dir = Path(__file__).parent / "templates"
    required_templates = [
        "template.docx",
        "template.xlsx", 
        "template_list.xlsx"
    ]
    
    missing_templates = []
    for template in required_templates:
        template_path = templates_dir / template
        if not template_path.exists():
            missing_templates.append(template)
        else:
            print(f"✅ {template} 발견")
    
    if missing_templates:
        print(f"❌ 누락된 템플릿 파일: {missing_templates}")
        print(f"템플릿 디렉터리: {templates_dir}")
        return False
    
    print("✅ 모든 템플릿 파일 확인됨")
    return True


def create_documents_dir():
    """문서 출력 디렉터리 생성"""
    documents_dir = Path(__file__).parent / "documents"
    documents_dir.mkdir(exist_ok=True)
    print(f"📁 문서 디렉터리 준비: {documents_dir}")


def run_server(host="0.0.0.0", port=8000):
    """FastAPI 서버 실행"""
    print(f"🚀 AutoDoc Service 시작 중...")
    print(f"   주소: http://{host}:{port}")
    print(f"   API 문서: http://{host}:{port}/docs")
    print("   종료하려면 Ctrl+C를 누르세요")
    
    try:
        import uvicorn
        from app.main import app
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except ImportError:
        print("❌ uvicorn 모듈을 찾을 수 없습니다. 의존성을 먼저 설치하세요.")
        return False
    except KeyboardInterrupt:
        print("\n👋 AutoDoc Service가 종료되었습니다.")
        return True
    except Exception as e:
        print(f"❌ 서버 실행 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("🏗️  AutoDoc Service 시작")
    print("=" * 50)
    
    # Python 버전 확인
    if not check_python_version():
        return 1
    
    # 의존성 설치 (선택사항 - 이미 설치된 경우 스킵)
    try:
        import fastapi
        import uvicorn
        print("✅ 주요 의존성이 이미 설치되어 있습니다.")
    except ImportError:
        if not install_dependencies():
            return 1
    
    # 템플릿 확인
    if not check_templates():
        print("\n⚠️  템플릿 파일이 없어도 서버는 시작할 수 있습니다.")
        print("   API 호출 시 404 오류가 발생할 수 있습니다.")
        
        response = input("\n계속 진행하시겠습니까? (y/N): ").strip().lower()
        if response not in ('y', 'yes'):
            print("❌ 실행이 취소되었습니다.")
            return 1
    
    # 문서 디렉터리 생성
    create_documents_dir()
    
    # 서버 실행
    if run_server():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())