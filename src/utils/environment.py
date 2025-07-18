#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
환경 설정 유틸리티
Tcl/Tk 및 tkinter 환경 설정을 담당합니다.
"""

import logging
import os
import sys
from pathlib import Path


def setup_tcl_tk_environment():
    """Tcl/Tk 라이브러리 환경 설정"""
    try:
        if hasattr(sys, 'frozen'):
            # PyInstaller로 빌드된 환경
            base_path = Path(getattr(sys, '_MEIPASS', ''))
            tcl_path = base_path / "tcl"
            
            if tcl_path.exists():
                # Tcl/Tk 라이브러리 경로 설정
                tcl_lib_path = None
                tk_lib_path = None
                
                # Tcl 라이브러리 찾기
                for tcl_dir in tcl_path.glob("tcl*"):
                    init_tcl = tcl_dir / "init.tcl"
                    if init_tcl.exists():
                        tcl_lib_path = str(tcl_dir)
                        break
                
                # Tk 라이브러리 찾기
                for tk_dir in tcl_path.glob("tk*"):
                    pkg_index = tk_dir / "pkgIndex.tcl"
                    if pkg_index.exists():
                        tk_lib_path = str(tk_dir)
                        break
                
                # 환경 변수 설정
                if tcl_lib_path:
                    os.environ["TCL_LIBRARY"] = tcl_lib_path
                    logging.info(f"TCL_LIBRARY set: {tcl_lib_path}")
                
                if tk_lib_path:
                    os.environ["TK_LIBRARY"] = tk_lib_path
                    logging.info(f"TK_LIBRARY set: {tk_lib_path}")
                    
        else:
            # 일반 Python 환경
            base_prefix = Path(sys.base_prefix)
            tcl_path = base_prefix / "tcl"
            
            if tcl_path.exists():
                # Tcl 라이브러리 찾기
                tcl_patterns = list(tcl_path.glob("tcl*/init.tcl"))
                if tcl_patterns:
                    tcl_lib_path = str(tcl_patterns[0].parent)
                    os.environ["TCL_LIBRARY"] = tcl_lib_path
                    logging.info(f"TCL_LIBRARY set: {tcl_lib_path}")
                
                # Tk 라이브러리 찾기
                tk_patterns = list(tcl_path.glob("tk*/pkgIndex.tcl"))
                if tk_patterns:
                    tk_lib_path = str(tk_patterns[0].parent)
                    os.environ["TK_LIBRARY"] = tk_lib_path
                    logging.info(f"TK_LIBRARY set: {tk_lib_path}")
                    
    except Exception as e:
        logging.warning(f"Tcl/Tk environment setup failed: {e}")


def setup_tkinter_environment():
    """tkinter 모듈 환경 설정"""
    try:
        # Python 설치 경로에서 tkinter 찾기
        python_paths = [
            sys.prefix,
            sys.base_prefix,
            os.path.dirname(sys.executable),
            os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages'),
            os.path.join(os.path.dirname(sys.executable), 'DLLs'),
            os.path.join(os.path.dirname(sys.executable), 'tcl'),
            os.path.join(os.path.dirname(sys.executable), 'tk'),
        ]
        
        # 환경 변수에 Python 경로 추가
        current_path = os.environ.get('PATH', '')
        for path in python_paths:
            if os.path.exists(path) and path not in current_path:
                os.environ['PATH'] = path + os.pathsep + current_path
                logging.info(f"PATH에 추가됨: {path}")
        
        # PYTHONPATH 설정
        python_path = os.environ.get('PYTHONPATH', '')
        for path in python_paths:
            if os.path.exists(path) and path not in python_path:
                os.environ['PYTHONPATH'] = path + os.pathsep + python_path
                logging.info(f"PYTHONPATH에 추가됨: {path}")
        
        return True
    except Exception as e:
        logging.error(f"tkinter 환경 설정 실패: {e}")
        return False 