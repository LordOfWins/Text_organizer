#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text Cleaner 업그레이드 매니저 - 메인 실행 스크립트
프로젝트 루트에서 실행되는 업그레이드 매니저 진입점
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """로깅 설정"""
    try:
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = log_dir / f"upgrade_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        print(f"[업그레이드 매니저] 로그 파일: {log_filename}")
        return True
        
    except Exception as e:
        print(f"[업그레이드 매니저] 로깅 설정 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("[업그레이드 매니저] 시작...")
    print(f"현재 디렉토리: {os.getcwd()}")
    print(f"Python 명령어: {sys.executable}")
    
    # 로깅 설정
    if not setup_logging():
        print("[업그레이드 매니저] 로깅 설정 실패, 기본 출력으로 진행")
    
    try:
        # src.core.upgrade_manager 모듈 임포트
        from src.core.upgrade_manager import UpgradeManager
        
        print("[업그레이드 매니저] 업그레이드 매니저 실행 중...")
        logging.info("업그레이드 매니저 시작")
        
        # 업그레이드 매니저 인스턴스 생성
        manager = UpgradeManager(guideline_manager=None)
        logging.info("업그레이드 매니저 인스턴스 생성 완료")
        
        # 업그레이드 실행 (자동 모드)
        logging.info("업그레이드 실행 시작")
        result = manager.execute_upgrade(auto_upgrade=True)
        
        if result:
            logging.info("업그레이드 성공 - 새 프로그램 실행 시도")
            print("[업그레이드 매니저] 업그레이드 성공 - 새 프로그램 실행 시도")
            
            # 빌드 완료 후 잠시 대기
            import time
            time.sleep(2)
            
            # 새 프로그램 실행 시도
            launch_result = manager.launch_new_program()
            if launch_result:
                logging.info("새 프로그램 실행 성공")
                print("[업그레이드 매니저] 새 프로그램 실행 성공")
                
                # 새 프로그램 실행 후 대기
                logging.info("새 프로그램 실행 완료 - 3초 대기 후 업그레이드 매니저 종료")
                print("[업그레이드 매니저] 새 프로그램 실행 완료 - 3초 대기 후 업그레이드 매니저 종료")
                time.sleep(3)
                
                # 업그레이드 매니저 완료
                logging.info("업그레이드 매니저 완료")
                print("[업그레이드 매니저] 업그레이드 매니저 완료")
            else:
                logging.error("새 프로그램 실행 실패")
                print("[업그레이드 매니저] 새 프로그램 실행 실패")
        else:
            logging.error("업그레이드 실패")
            print("[업그레이드 매니저] 업그레이드 실패")
            
    except ImportError as e:
        error_msg = f"필수 모듈을 찾을 수 없습니다: {e}"
        print(f"[업그레이드 매니저] {error_msg}")
        logging.error(error_msg)
        
    except Exception as e:
        error_msg = f"업그레이드 매니저 예외 발생: {e}"
        print(f"[업그레이드 매니저] {error_msg}")
        logging.error(error_msg)
        
    finally:
        logging.info("업그레이드 매니저 종료")
        print("[업그레이드 매니저] 종료")

if __name__ == "__main__":
    main() 