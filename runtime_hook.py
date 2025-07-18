#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller Runtime Hook
Tcl/Tk 인코딩 문제 해결을 위한 런타임 훅
"""

import os
import sys
import tkinter as tk
from pathlib import Path

def fix_tcl_tk_encoding():
    """Tcl/Tk 인코딩 문제 해결"""
    try:
        # Tcl/Tk 인코딩 설정
        if hasattr(tk, '_default_root'):  # type: ignore
            root = tk._default_root  # type: ignore
            if root:
                # Tcl 인코딩 설정
                root.tk.eval('encoding system utf-8')
                
        # 환경 변수 설정
        os.environ['TCL_LIBRARY'] = ''
        os.environ['TK_LIBRARY'] = ''
        
        # Python 인코딩 설정 (Python 2 호환성)
        if hasattr(sys, 'setdefaultencoding'):  # type: ignore
            sys.setdefaultencoding('utf-8')  # type: ignore
            
    except Exception as e:
        # 오류가 발생해도 프로그램 실행을 계속
        pass

def setup_runtime_environment():
    """런타임 환경 설정"""
    try:
        # 현재 실행 파일의 디렉토리를 기준으로 경로 설정
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 경우
            base_path = Path(sys._MEIPASS)  # type: ignore
        else:
            # 일반 Python 실행
            base_path = Path(__file__).parent
            
        # 로그 디렉토리 생성
        log_dir = base_path / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # 환경 변수 설정
        os.environ['PYTHONPATH'] = str(base_path)
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
    except Exception as e:
        # 오류가 발생해도 프로그램 실행을 계속
        pass

# 런타임 훅 실행
if __name__ == '__main__':
    setup_runtime_environment()
    fix_tcl_tk_encoding()
else:
    # 모듈로 임포트된 경우에도 실행
    setup_runtime_environment()
    fix_tcl_tk_encoding() 