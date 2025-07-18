#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가이드라인 관리 모듈
text_cleaner의 가이드라인 관리 기능을 담당합니다.
"""

import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class GuidelineManager:
    """가이드라인 관리 클래스"""
    
    def __init__(self, user_data_path: Path):
        self.user_data_path = user_data_path
        
        # PyInstaller 환경에서 파일 경로 처리 개선
        if hasattr(sys, 'frozen'):
            # exe 실행 시: exe와 같은 디렉토리에서 먼저 찾기
            exe_dir = Path(sys.executable).parent
            self.guidelines_file = exe_dir / "guidelines.json"
            # exe 디렉토리에 없으면 user_data_path에서 찾기
            if not self.guidelines_file.exists():
                self.guidelines_file = user_data_path / "guidelines.json"
        else:
            # Python 스크립트 실행 시: 기존 방식
            self.guidelines_file = user_data_path / "guidelines.json"
        
        self.guidelines: Dict[str, Any] = {}
        self.load_guidelines()

    def load_guidelines(self) -> bool:
        """가이드라인 프리셋 로드"""
        try:
            logging.info("가이드라인 파일 경로: %s", self.guidelines_file)
            
            # 여러 경로에서 가이드라인 파일 찾기
            possible_paths = []
            
            if hasattr(sys, 'frozen'):
                # PyInstaller 환경
                exe_dir = Path(sys.executable).parent
                possible_paths = [
                    exe_dir / "guidelines.json",  # exe와 같은 디렉토리
                    exe_dir.parent / "guidelines.json",  # 상위 디렉토리
                    self.user_data_path / "guidelines.json",  # 사용자 데이터 경로
                ]
            else:
                # Python 스크립트 환경
                script_dir = Path(__file__).parent
                possible_paths = [
                    script_dir / "guidelines.json",  # 스크립트와 같은 디렉토리
                    self.user_data_path / "guidelines.json",  # 사용자 데이터 경로
                ]
            
            # 각 경로에서 파일 찾기
            for path in possible_paths:
                logging.info("가이드라인 파일 확인: %s", path)
                if path.exists():
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            self.guidelines = json.load(f)
                            self.guidelines_file = path  # 찾은 경로로 업데이트
                            logging.info("가이드라인 로드 완료: %d개 (경로: %s)", len(self.guidelines), path)
                            return True
                    except (json.JSONDecodeError, PermissionError) as e:
                        logging.warning("파일 읽기 실패 (%s): %s", path, e)
                        continue
            
            # 파일을 찾지 못한 경우 기본 가이드라인 생성
            logging.warning("가이드라인 파일을 찾을 수 없음 - 기본 가이드라인 생성")
            self.create_default_guidelines()
            return True
                
        except Exception as e:
            logging.error("가이드라인 로드 실패: %s: %s", type(e).__name__, e)
            return False

    def create_default_guidelines(self) -> bool:
        """기본 가이드라인 생성"""
        try:
            default_guidelines = {
                "기본": {
                    "description": "기본 텍스트 정리 규칙",
                    "rules": [
                        "Remove empty lines",
                        "Remove YouTube links", 
                        "Trim whitespace",
                        "Remove name emojis",
                        "Unify date formats",
                        "Unify time formats",
                        "Convert weekdays",
                        "Clean message format",
                        "Clean special characters"
                    ]
                }
            }
            
            self.guidelines = default_guidelines
            
            # 파일로 저장 시도
            try:
                self.save_guidelines()
                logging.info("기본 가이드라인 생성 및 저장 완료")
            except Exception as e:
                logging.warning("기본 가이드라인 저장 실패: %s", e)
                # 메모리에서만 사용
            
            return True
        except Exception as e:
            logging.error("기본 가이드라인 생성 실패: %s", e)
            return False

    def save_guidelines(self) -> bool:
        """가이드라인 프리셋 저장"""
        try:
            with open(self.guidelines_file, 'w', encoding='utf-8') as f:
                json.dump(self.guidelines, f, ensure_ascii=False, indent=2)
            logging.info("가이드라인 저장 완료")
            return True
        except (PermissionError, OSError) as e:
            logging.error("가이드라인 저장 실패: %s: %s", type(e).__name__, e)
            return False

    def restore_guidelines_from_backup(self) -> bool:
        """백업에서 가이드라인 복원"""
        try:
            if hasattr(sys, 'frozen'):
                base_path = Path(sys.executable).parent.parent
            else:
                base_path = Path(__file__).parent
            backup_path = base_path / "guidelines_backup" / "guidelines_backup.json"
            
            if backup_path.exists():
                shutil.copy2(backup_path, self.guidelines_file)
                logging.info("가이드라인 백업에서 복원 완료")
                self.load_guidelines()
                return True
            logging.warning("백업 파일이 없습니다")
            return False
        except Exception as e:
            logging.error("가이드라인 복원 실패: %s", e)
            return False

    def backup_guidelines_before_upgrade(self, base_path: Path) -> bool:
        """업그레이드 전 가이드라인 파일 백업"""
        try:
            backup_dir = base_path / "guidelines_backup"
            backup_dir.mkdir(exist_ok=True)
            backup_guidelines_path = backup_dir / "guidelines_backup.json"
            
            # 같은 파일인지 확인
            if self.guidelines_file.resolve() == backup_guidelines_path.resolve():
                logging.info("가이드라인 파일이 이미 백업 위치에 있음")
                return True
            
            if self.guidelines_file.exists():
                shutil.copy2(self.guidelines_file, backup_guidelines_path)
                logging.info("가이드라인 백업 완료: %s", backup_guidelines_path)
                self.create_restore_script(base_path)
                return True
            logging.warning("백업할 가이드라인 파일이 없습니다")
            return False
        except Exception as e:
            logging.error("가이드라인 백업 실패: %s", e)
            return False

    def create_restore_script(self, base_path: Path) -> bool:
        """백업 복원 스크립트 생성"""
        try:
            restore_script = (
                f'@echo off\n'
                f'echo 가이드라인 백업 복원 중...\n'
                f'if exist "{base_path}\\guidelines_backup.json" (\n'
                f'    copy "{base_path}\\guidelines_backup.json" "{base_path}\\guidelines.json"\n'
                f'    echo 가이드라인 복원 완료\n'
                f') else (\n'
                f'    echo 백업 파일을 찾을 수 없습니다\n'
                f')\npause\n'
            )
            restore_bat_path = base_path / "restore_guidelines.bat"
            with open(restore_bat_path, 'w', encoding='utf-8') as f:
                f.write(restore_script)
            logging.info("복원 스크립트 생성 완료: %s", restore_bat_path)
            return True
        except Exception as e:
            logging.error("복원 스크립트 생성 실패: %s", e)
            return False

    def get_guideline_names(self) -> list:
        """가이드라인 이름 목록 반환"""
        return list(self.guidelines.keys())

    def get_guideline(self, name: str) -> Optional[Dict[str, Any]]:
        """특정 가이드라인 반환"""
        return self.guidelines.get(name)

    def add_guideline(self, name: str, description: str, rules: list) -> bool:
        """새 가이드라인 추가"""
        try:
            self.guidelines[name] = {
                "description": description,
                "rules": rules
            }
            return self.save_guidelines()
        except Exception as e:
            logging.error("가이드라인 추가 실패: %s", e)
            return False

    def update_guideline(self, name: str, description: str, rules: list) -> bool:
        """가이드라인 수정"""
        return self.add_guideline(name, description, rules)

    def delete_guideline(self, name: str) -> bool:
        """가이드라인 삭제"""
        try:
            if name in self.guidelines:
                del self.guidelines[name]
                return self.save_guidelines()
            return False
        except Exception as e:
            logging.error("가이드라인 삭제 실패: %s", e)
            return False

    def has_guidelines(self) -> bool:
        """가이드라인 존재 여부 확인"""
        return len(self.guidelines) > 0