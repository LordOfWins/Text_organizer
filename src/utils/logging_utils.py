#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로깅 유틸리티
로깅 설정 및 사용자 액션 로깅을 담당합니다.
"""

import datetime
import logging
import sys
from pathlib import Path
from typing import Optional


def get_user_data_path() -> Path:
    """사용자 데이터 폴더 경로 반환"""
    if hasattr(sys, 'frozen'):
        return Path.home() / "AppData" / "Local" / "text_cleaner"
    return Path(__file__).parent.parent.parent


def setup_logging() -> logging.Logger:
    """로깅 설정"""
    user_data_path = get_user_data_path()
    log_dir = user_data_path / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"text_cleaner_{datetime.datetime.now().strftime('%Y%m%d')}.log"
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 기본 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 사용자 액션 전용 로거 설정
    user_action_logger = logging.getLogger('user_action')
    user_action_logger.setLevel(logging.INFO)
    
    # 사용자 액션 전용 파일 핸들러
    user_action_file = log_dir / f"user_actions_{datetime.datetime.now().strftime('%Y%m%d')}.log"
    user_action_handler = logging.FileHandler(user_action_file, encoding='utf-8')
    user_action_handler.setLevel(logging.INFO)
    
    # 사용자 액션 전용 포맷터
    user_action_formatter = logging.Formatter('%(asctime)s - [USER_ACTION] - %(message)s')
    user_action_handler.setFormatter(user_action_formatter)
    
    user_action_logger.addHandler(user_action_handler)
    user_action_logger.propagate = False  # 중복 로그 방지
    
    logging.info("=" * 50)
    logging.info("text_cleaner started")
    logging.info("Log file: %s", log_file)
    logging.info("User action log file: %s", user_action_file)
    logging.info("=" * 50)

    return user_action_logger


def log_user_action(action: str, details: Optional[str] = None, success: bool = True) -> None:
    """사용자 액션 로깅"""
    try:
        status = "Success" if success else "Fail"
        message = f"{action} - {status}"
        if details:
            message += f" - {details}"
        
        user_action_logger = logging.getLogger('user_action')
        user_action_logger.info(message)
    except Exception as e:
        logging.warning(f"User action logging failed: {e}") 