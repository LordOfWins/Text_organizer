#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
환경 검증 스크립트
업그레이드 후 필요한 모듈들이 제대로 설치되어 있는지 확인합니다.
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('environment_verify.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def check_python_version():
    """Python 버전 확인"""
    logging.info(f"Python 버전: {sys.version}")
    if sys.version_info < (3, 7):
        logging.error("Python 3.7 이상이 필요합니다.")
        return False
    return True

def check_tkinter():
    """tkinter 모듈 확인"""
    try:
        import tkinter
        logging.info("tkinter 모듈 로드 성공")
        
        # tkinter 창 생성 테스트
        root = tkinter.Tk()
        root.withdraw()  # 창 숨기기
        root.destroy()
        logging.info("tkinter 창 생성 테스트 성공")
        return True
    except ImportError as e:
        logging.error(f"tkinter 모듈 로드 실패: {e}")
        return False
    except Exception as e:
        logging.error(f"tkinter 테스트 실패: {e}")
        return False

def check_required_modules():
    """필수 모듈 확인"""
    required_modules = [
        'pathlib',
        'logging',
        're',
        'threading',
        'datetime',
        'subprocess',
        'shutil',
        'hashlib',
        'time',
        'typing',
        'io',
        'base64',
        'glob',
        'locale'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            logging.info(f"{module} 모듈 확인 완료")
        except ImportError:
            logging.error(f"{module} 모듈이 없습니다.")
            missing_modules.append(module)
    
    if missing_modules:
        logging.error(f"누락된 모듈: {missing_modules}")
        return False
    return True

def check_optional_modules():
    """선택적 모듈 확인"""
    optional_modules = {
        'pytesseract': 'OCR 기능',
        'PIL': '이미지 처리 기능',
        'pyperclip': '클립보드 기능',
        'psutil': '프로세스 관리 기능',
        'cv2': 'OpenCV (이미지 전처리)',
        'numpy': '수치 계산'
    }
    
    available_modules = {}
    for module, description in optional_modules.items():
        try:
            __import__(module)
            logging.info(f"{module} 모듈 사용 가능 ({description})")
            available_modules[module] = True
        except ImportError:
            logging.warning(f"{module} 모듈 없음 ({description})")
            available_modules[module] = False
    
    return available_modules

def check_project_files():
    """프로젝트 파일 확인"""
    required_files = [
        'text_cleaner.py',
        'text_processor.py',
        'guideline_manager.py',
        'upgrade_manager.py',
        'guidelines.json'
    ]
    
    missing_files = []
    for file_name in required_files:
        if Path(file_name).exists():
            logging.info(f"{file_name} 파일 확인 완료")
        else:
            logging.error(f"{file_name} 파일이 없습니다.")
            missing_files.append(file_name)
    
    if missing_files:
        logging.error(f"누락된 파일: {missing_files}")
        return False
    return True

def check_python_path():
    """Python 경로 확인"""
    logging.info(f"Python 실행 파일: {sys.executable}")
    logging.info(f"Python 경로: {sys.path}")
    
    # Python 설치 디렉토리 확인
    python_dir = Path(sys.executable).parent
    logging.info(f"Python 설치 디렉토리: {python_dir}")
    
    # tkinter 관련 경로 확인
    tkinter_paths = [
        python_dir / "Lib" / "tkinter",
        python_dir / "tcl",
        python_dir / "tk",
        python_dir / "DLLs"
    ]
    
    for path in tkinter_paths:
        if path.exists():
            logging.info(f"tkinter 관련 경로 확인: {path}")
        else:
            logging.warning(f"tkinter 관련 경로 없음: {path}")
    
    return True

def install_missing_modules():
    """누락된 모듈 설치"""
    logging.info("누락된 모듈 설치 시도...")
    
    modules_to_install = [
        'tkinter',
        'tk',
        'pytesseract',
        'Pillow',
        'pyperclip',
        'psutil',
        'opencv-python',
        'numpy'
    ]
    
    for module in modules_to_install:
        try:
            logging.info(f"{module} 설치 시도...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', module], 
                         check=True, capture_output=True, text=True)
            logging.info(f"{module} 설치 성공")
        except subprocess.CalledProcessError as e:
            logging.warning(f"{module} 설치 실패: {e}")

def main():
    """메인 함수"""
    setup_logging()
    logging.info("=" * 50)
    logging.info("환경 검증 시작")
    logging.info("=" * 50)
    
    # 기본 검증
    checks = {
        "Python 버전": check_python_version(),
        "tkinter 모듈": check_tkinter(),
        "필수 모듈": check_required_modules(),
        "프로젝트 파일": check_project_files(),
        "Python 경로": check_python_path()
    }
    
    # 선택적 모듈 확인
    optional_modules = check_optional_modules()
    
    # 결과 요약
    logging.info("=" * 50)
    logging.info("검증 결과 요약")
    logging.info("=" * 50)
    
    all_passed = True
    for check_name, result in checks.items():
        status = "성공" if result else "실패"
        logging.info(f"{check_name}: {status}")
        if not result:
            all_passed = False
    
    logging.info("선택적 모듈 상태:")
    for module, available in optional_modules.items():
        status = "사용 가능" if available else "사용 불가"
        logging.info(f"  {module}: {status}")
    
    if all_passed:
        logging.info("모든 필수 검증이 통과했습니다!")
        return True
    else:
        logging.error("일부 검증이 실패했습니다.")
        
        # tkinter가 없으면 설치 시도
        if not checks["tkinter 모듈"]:
            logging.info("tkinter 설치 시도...")
            install_missing_modules()
            
            # 재검증
            if check_tkinter():
                logging.info("tkinter 설치 후 검증 성공!")
                return True
            else:
                logging.error("tkinter 설치 후에도 검증 실패")
        
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("환경 검증 완료 - 모든 검증 통과!")
    else:
        print("환경 검증 실패 - 로그를 확인하세요.")
        sys.exit(1) 