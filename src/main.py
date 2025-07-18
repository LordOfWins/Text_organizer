#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text Cleaner 메인 애플리케이션
리팩토링된 구조로 개선된 메인 진입점
"""

import sys
import os
# 프로젝트 루트(src의 상위)만 sys.path에 추가 (임포트 경로 일관성)
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import tkinter as tk
from pathlib import Path

# src/utils, src/ui 등 내부 모듈은 절대 경로로 임포트
try:
    from src.utils.environment import setup_tcl_tk_environment, setup_tkinter_environment
    from src.utils.logging_utils import setup_logging
    from src.ui.app import TextCleanerApp
except ImportError as e:
    print("필수 모듈을 찾을 수 없습니다. 경로 및 파일 구성을 확인하세요.")
    print(f"ImportError: {e}")
    sys.exit(1)


def main():
    """메인 함수 - 리팩토링된 구조"""
    # 환경 설정
    setup_tcl_tk_environment()
    setup_tkinter_environment()
    
    # 로깅 설정
    user_action_logger = setup_logging()
    
    try:
        # Tkinter 루트 윈도우 생성
        root = tk.Tk()
        
        # 애플리케이션 인스턴스 생성
        app = TextCleanerApp(root, user_action_logger)
        
        # 윈도우 종료 이벤트 바인딩
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        # 윈도우 중앙 정렬
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
        
        # 메인 루프 시작
        root.mainloop()
        
    except Exception as e:
        error_msg = f"애플리케이션 실행 중 오류 발생: {e}"
        print(error_msg)
        if user_action_logger:
            user_action_logger.error(error_msg)


if __name__ == "__main__":
    main() 