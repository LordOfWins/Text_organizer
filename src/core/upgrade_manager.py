#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업그레이드 관리 모듈
text_cleaner의 업그레이드 기능을 담당합니다.
상업용 기준의 안정성과 보안을 제공합니다.
"""

import hashlib
import logging
import os
import subprocess
import sys
import time
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil 모듈이 설치되지 않았습니다. 프로세스 종료 기능이 제한됩니다.")

try:
    from tkinter import messagebox
except ImportError:
    messagebox = None  # type: ignore

# tkinter 모듈 경로 설정 및 설치 확인
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

# tkinter 환경 설정 실행
setup_tkinter_environment()

# tkinter 설치 확인 및 안내
try:
    import tkinter
    logging.info("tkinter 모듈 로드 성공")
except ImportError:
    try:
        # 추가 시도: 직접 경로에서 import
        import sys
        python_dir = os.path.dirname(sys.executable)
        tkinter_path = os.path.join(python_dir, 'Lib', 'tkinter')
        if os.path.exists(tkinter_path):
            sys.path.insert(0, tkinter_path)
            import tkinter
            logging.info("tkinter 모듈 직접 경로에서 로드 성공")
        else:
            raise ImportError("tkinter 경로를 찾을 수 없습니다")
    except ImportError:
        import sys
        print("""[오류] Python에 tkinter 모듈이 설치되어 있지 않습니다.
This program requires the tkinter module for GUI.

설치 방법(Windows):
    py -m pip install tk
    또는
    py -m pip install tkinter

설치 후 프로그램을 다시 실행해 주세요.
Please install tkinter and restart the program.
""")
        sys.exit(1)


class UpgradeManager:
    """업그레이드 관리 클래스 - 상업용 기준"""
    
    def __init__(self, guideline_manager):
        self.guideline_manager = guideline_manager
        self.upgrade_log_file = None
        self.backup_path = None
        self.rollback_available = False
        
    def _setup_upgrade_logging(self):
        """업그레이드 전용 로깅 설정"""
        try:
            base_path = self.get_base_path()
            log_dir = base_path / "logs"
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.upgrade_log_file = log_dir / f"upgrade_{timestamp}.log"
            
            # 업그레이드 전용 로거 설정
            upgrade_logger = logging.getLogger('upgrade')
            upgrade_logger.setLevel(logging.INFO)
            
            # 파일 핸들러 추가
            file_handler = logging.FileHandler(self.upgrade_log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 포맷터 설정
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            upgrade_logger.addHandler(file_handler)
            
            logging.info("업그레이드 로깅 설정 완료: %s", self.upgrade_log_file)
            return True
            
        except Exception as e:
            logging.error("업그레이드 로깅 설정 실패: %s", e)
            return False

    def _check_admin_privileges(self) -> bool:
        """관리자 권한 확인"""
        try:
            if os.name == 'nt':  # Windows
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                # Linux/Mac 환경에서 관리자 권한 확인
                try:
                    # Windows가 아닌 환경에서만 geteuid 사용
                    if hasattr(os, 'geteuid'):
                        return os.geteuid() == 0
                    else:
                        # Windows 환경에서 geteuid가 없는 경우
                        return False
                except AttributeError:
                    # geteuid가 없는 경우
                    return False
        except Exception as e:
            logging.warning("관리자 권한 확인 실패: %s", e)
            return False

    def _request_admin_privileges(self) -> bool:
        """관리자 권한 요청 (Windows UAC) - 개선된 버전"""
        try:
            if os.name == 'nt' and not self._check_admin_privileges():
                logging.info("관리자 권한 요청 중...")
                
                # 현재 스크립트 경로
                script_path = sys.executable if hasattr(sys, 'frozen') else sys.argv[0]
                
                # 관리자 권한으로 재실행
                import ctypes
                result = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", str(script_path), None, None, 1
                )
                
                if result > 32:
                    logging.info("관리자 권한 요청 성공")
                    return True
                else:
                    logging.warning("관리자 권한 요청 실패 - 일반 권한으로 계속 진행")
                    return True  # 실패해도 계속 진행
            else:
                return True
                
        except Exception as e:
            logging.warning("관리자 권한 요청 실패: %s - 일반 권한으로 계속 진행", e)
            return True  # 예외 발생해도 계속 진행

    def _calculate_file_hash(self, file_path: Path) -> str:
        """파일 해시 계산 (SHA-256)"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logging.error("파일 해시 계산 실패: %s", e)
            return ""

    def _validate_file_integrity(self, file_path: Path, expected_hash: Optional[str] = None) -> bool:
        """파일 무결성 검증"""
        try:
            if not file_path.exists():
                logging.error("파일이 존재하지 않음: %s", file_path)
                return False
                
            actual_hash = self._calculate_file_hash(file_path)
            logging.info("파일 해시: %s -> %s", file_path.name, actual_hash)
            
            if expected_hash and actual_hash != expected_hash:
                logging.error("파일 무결성 검증 실패: %s", file_path)
                return False
                
            return True
            
        except Exception as e:
            logging.error("파일 무결성 검증 실패: %s", e)
            return False

    def _create_comprehensive_backup(self) -> bool:
        """포괄적인 백업 생성"""
        try:
            base_path = self.get_base_path()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_path = base_path / f"backup_upgrade_{timestamp}"
            
            logging.info("포괄적 백업 시작: %s", self.backup_path)
            
            # 백업 디렉토리 생성
            self.backup_path.mkdir(exist_ok=True)
            
            # 중요 파일들 백업
            important_files = [
                "guidelines.json",
                "text_cleaner.py",
                "text_processor.py",
                "guideline_manager.py",
                "upgrade_manager.py"
            ]
            
            for file_name in important_files:
                source_file = base_path / file_name
                if source_file.exists():
                    backup_file = self.backup_path / file_name
                    shutil.copy2(source_file, backup_file)
                    logging.info("백업 완료: %s", file_name)
            
            # 로그 디렉토리 백업
            log_dir = base_path / "logs"
            if log_dir.exists():
                backup_log_dir = self.backup_path / "logs"
                shutil.copytree(log_dir, backup_log_dir, dirs_exist_ok=True)
                logging.info("로그 디렉토리 백업 완료")
            
            # 백업 완료 확인
            if self.backup_path.exists() and any(self.backup_path.iterdir()):
                self.rollback_available = True
                logging.info("포괄적 백업 완료: %s", self.backup_path)
                return True
            else:
                logging.error("백업 생성 실패")
                return False
                
        except Exception as e:
            logging.error("포괄적 백업 실패: %s", e)
            return False

    def _rollback_from_backup(self) -> bool:
        """백업에서 복원"""
        try:
            if not self.rollback_available or not self.backup_path:
                logging.error("롤백 불가능: 백업이 없습니다")
                return False
                
            logging.info("백업에서 복원 시작: %s", self.backup_path)
            
            base_path = self.get_base_path()
            
            # 중요 파일들 복원
            for backup_file in self.backup_path.glob("*"):
                if backup_file.is_file():
                    target_file = base_path / backup_file.name
                    shutil.copy2(backup_file, target_file)
                    logging.info("복원 완료: %s", backup_file.name)
            
            # 로그 디렉토리 복원
            backup_log_dir = self.backup_path / "logs"
            if backup_log_dir.exists():
                log_dir = base_path / "logs"
                if log_dir.exists():
                    shutil.rmtree(log_dir)
                shutil.copytree(backup_log_dir, log_dir)
                logging.info("로그 디렉토리 복원 완료")
            
            logging.info("백업에서 복원 완료")
            return True
            
        except Exception as e:
            logging.error("백업에서 복원 실패: %s", e)
            return False

    def get_base_path(self) -> Path:
        """프로젝트 기본 경로 반환"""
        # exe 파일에서 실행되는 경우와 Python 스크립트에서 실행되는 경우를 구분
        if hasattr(sys, 'frozen'):
            # exe 파일에서 실행되는 경우
            exe_path = Path(sys.executable)
            # dist/text_cleaner/text_cleaner.exe -> 프로젝트 루트
            if exe_path.name == "text_cleaner.exe":
                # dist/text_cleaner/ 폴더에서 상위로 올라가서 프로젝트 루트 찾기
                current_dir = exe_path.parent
                if current_dir.name == "text_cleaner":
                    # dist/text_cleaner/ -> dist/ -> 프로젝트 루트
                    return current_dir.parent.parent
                else:
                    # 직접 프로젝트 루트에 있는 경우
                    return current_dir
            else:
                # upgrade_manager.exe인 경우
                return exe_path.parent
        else:
            # Python 스크립트에서 실행되는 경우
            # src/core/upgrade_manager.py -> src/core -> src -> 프로젝트 루트
            current_file = Path(__file__).resolve()
            return current_file.parent.parent.parent

    def find_build_script(self) -> Optional[Path]:
        """빌드 스크립트 찾기 및 검증"""
        base_path = self.get_base_path()
        
        # 빌드 스크립트 파일들 검색
        build_scripts = [
            base_path / "build_exe.bat",
            base_path / "build_optimized.bat",
            base_path / "build.bat"
        ]
        
        for script in build_scripts:
            if script.exists():
                # 스크립트 파일 무결성 검증
                if self._validate_file_integrity(script):
                    logging.info("빌드 스크립트 발견 및 검증 완료: %s", script)
                    return script
                else:
                    logging.warning("빌드 스크립트 무결성 검증 실패: %s", script)
        
        logging.info("빌드 스크립트를 찾을 수 없음 - Python 직접 빌드 모드")
        return None

    def backup_before_upgrade(self) -> bool:
        """업그레이드 전 백업 수행 (개선된 버전)"""
        try:
            # 가이드라인 매니저가 있으면 백업 수행
            if self.guideline_manager and hasattr(self.guideline_manager, 'backup_guidelines_before_upgrade'):
                base_path = self.get_base_path()
                guideline_backup = self.guideline_manager.backup_guidelines_before_upgrade(base_path)
            else:
                logging.info("가이드라인 매니저가 없어 가이드라인 백업을 건너뜁니다")
                guideline_backup = True
            
            # 포괄적 백업
            comprehensive_backup = self._create_comprehensive_backup()
            
            if guideline_backup and comprehensive_backup:
                logging.info("모든 백업 완료")
                return True
            else:
                logging.warning("일부 백업 실패 - 업그레이드는 계속 진행")
                return True  # 백업 실패해도 업그레이드는 계속 진행
                
        except Exception as e:
            logging.error("업그레이드 전 백업 실패: %s", e)
            # 백업 실패해도 업그레이드는 계속 진행
            return True

    def kill_process_tree(self, pid: int, timeout: int = 10) -> bool:
        """프로세스 트리 전체를 강제 종료 (psutil 사용)"""
        if not PSUTIL_AVAILABLE:
            logging.warning("psutil이 없어 기본 종료 방식 사용")
            return self.kill_process_basic(pid, timeout)
        
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # 자식 프로세스들 먼저 종료
            for child in children:
                try:
                    logging.info("자식 프로세스 종료: %d (%s)", child.pid, child.name())
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logging.warning("자식 프로세스 종료 실패: %s", e)
            
            # 자식 프로세스들이 종료될 때까지 대기
            gone, alive = psutil.wait_procs(children, timeout=timeout)
            
            # 살아있는 프로세스들 강제 종료
            for p in alive:
                try:
                    logging.info("자식 프로세스 강제 종료: %d (%s)", p.pid, p.name())
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logging.warning("자식 프로세스 강제 종료 실패: %s", e)
            
            # 부모 프로세스 종료
            try:
                logging.info("부모 프로세스 종료: %d (%s)", parent.pid, parent.name())
                parent.terminate()
                parent.wait(timeout=timeout)
            except psutil.NoSuchProcess:
                pass
            except psutil.TimeoutExpired:
                try:
                    logging.info("부모 프로세스 강제 종료: %d", parent.pid)
                    parent.kill()
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logging.warning("부모 프로세스 강제 종료 실패: %s", e)
            
            return True
            
        except psutil.NoSuchProcess:
            logging.info("프로세스 %d가 이미 종료됨", pid)
            return True
        except Exception as e:
            logging.error("프로세스 트리 종료 실패: %s", e)
            return False

    def kill_process_basic(self, pid: int, timeout: int = 10) -> bool:
        """기본 프로세스 종료 방식 (psutil 없을 때)"""
        try:
            # Windows에서 taskkill 사용
            if os.name == 'nt':
                subprocess.run(f'taskkill /f /pid {pid}', shell=True, capture_output=True, timeout=timeout)
            else:
                os.kill(pid, 9)  # SIGKILL
            return True
        except Exception as e:
            logging.error("기본 프로세스 종료 실패: %s", e)
            return False

    def kill_all_python_processes(self) -> bool:
        """모든 Python 관련 프로세스 종료"""
        if not PSUTIL_AVAILABLE:
            logging.warning("psutil이 없어 Python 프로세스 종료를 건너뜀")
            return True
        
        try:
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # 현재 프로세스는 제외
                    if proc.pid == os.getpid():
                        continue
                    
                    # Python 관련 프로세스 확인
                    if (proc.name() and 'python' in proc.name().lower()) or \
                       (proc.cmdline() and any('text_cleaner' in cmd.lower() for cmd in proc.cmdline() if cmd)):
                        
                        logging.info("Python 프로세스 발견: %d (%s)", proc.pid, proc.name())
                        if self.kill_process_tree(proc.pid, timeout=5):
                            killed_count += 1
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                except Exception as e:
                    logging.warning("프로세스 확인 중 오류: %s", e)
            
            logging.info("총 %d개의 Python 프로세스 종료됨", killed_count)
            return True
            
        except Exception as e:
            logging.error("Python 프로세스 종료 실패: %s", e)
            return False

    def force_kill_all_processes(self) -> bool:
        """Python에서 직접 모든 관련 프로세스 완전 강제 종료"""
        try:
            logging.info("Python에서 직접 완전 강제 종료 시작")
            
            # Windows에서 taskkill 명령으로 직접 종료
            if os.name == 'nt':
                kill_commands = [
                    'taskkill /f /im "text_cleaner.exe" /t',
                    'taskkill /f /im "pythonw.exe" /t',
                    'taskkill /f /im "pyinstaller.exe" /t'
                ]
                
                for cmd in kill_commands:
                    try:
                        logging.info("실행: %s", cmd)
                        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
                        if result.returncode == 0:
                            logging.info("성공: %s", cmd)
                        else:
                            logging.warning("실패: %s - %s", cmd, result.stderr.decode('utf-8', errors='ignore'))
                    except Exception as e:
                        logging.warning("명령 실행 실패: %s - %s", cmd, e)
                
                # 현재 프로세스는 제외 (업그레이드가 중단되지 않도록)
                current_pid = os.getpid()
                logging.info("현재 프로세스 PID %d는 제외하고 종료", current_pid)
                
                # 프로세스 종료 확인
                logging.info("프로세스 종료 확인 중...")
                time.sleep(1)
                
                # 남은 프로세스 확인
                remaining_processes = []
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.pid == os.getpid():
                            continue
                        if (proc.name() and 'python' in proc.name().lower()) or \
                           (proc.name() and 'text_cleaner' in proc.name().lower()):
                            remaining_processes.append(f"{proc.pid} ({proc.name()})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                if remaining_processes:
                    logging.warning("Remaining processes: %s", ', '.join(remaining_processes))
                else:
                    logging.info("All related processes terminated successfully")
                
                return True
            else:
                # Linux/Mac 환경
                logging.info("Linux/Mac 환경에서 프로세스 종료")
                return self.kill_all_python_processes()
                
        except Exception as e:
            logging.error("완전 강제 종료 실패: %s", e)
            return False

    def execute_upgrade(self, auto_upgrade: bool = False) -> bool:
        """간단한 업그레이드 실행"""
        try:
            logging.info("=== 간단한 업그레이드 시작 ===")
            
            # 환경 검증 추가
            if not self.validate_upgrade_environment():
                logging.error("업그레이드 환경 검증 실패")
                # 환경 검증 스크립트 실행 시도
                if self.run_environment_verification():
                    logging.info("환경 검증 스크립트 실행 성공, 재검증 시도")
                    if not self.validate_upgrade_environment():
                        logging.error("환경 재검증도 실패")
                        return False
                else:
                    logging.error("환경 검증 스크립트 실행 실패")
                    return False
            
            if auto_upgrade:
                # 1단계: text_cleaner.exe 종료
                logging.info("1단계: text_cleaner.exe 종료 중...")
                self.terminate_current_program()
                time.sleep(2)  # 프로세스 종료 대기
                
                # 2단계: 배치 파일을 통한 빌드 (우선 시도)
                logging.info("2단계: 배치 파일을 통한 빌드 시도...")
                build_script = self.find_build_script()
                if build_script and build_script.exists():
                    logging.info("배치 파일 발견: %s", build_script)
                    build_success = self._build_with_batch(build_script)
                else:
                    logging.info("배치 파일을 찾을 수 없음, Python 빌드 시도...")
                    build_success = self._build_with_python()
                
                if not build_success:
                    logging.error("빌드 실패")
                    return False
                
                # 3단계: 빌드 후 환경 재검증
                logging.info("3단계: 빌드 후 환경 재검증...")
                if not self.validate_upgrade_environment():
                    logging.warning("빌드 후 환경 검증 실패, 계속 진행")
                    
                # 4단계: 새 프로그램 실행 (중복 실행 방지)
                logging.info("4단계: 새 프로그램 실행 중...")
                # launch_new_program은 메인 스크립트에서 호출하므로 여기서는 건너뜀
                logging.info("빌드 완료 - 메인 스크립트에서 새 프로그램 실행 예정")
                return True
            else:
                logging.info("수동 업그레이드 모드")
                return True
            
        except Exception as e:
            logging.error("업그레이드 실패: %s", e)
            return False

    def _build_with_python(self) -> bool:
        """PyInstaller로 간단한 빌드"""
        try:
            logging.info("PyInstaller 빌드 시작")
            
            base_path = self.get_base_path()
            
            # 기존 빌드 파일 정리 (강화된 버전)
            for path in ["dist", "build"]:
                full_path = base_path / path
                if full_path.exists():
                    try:
                        # 파일 잠금 해제를 위한 대기
                        time.sleep(2)
                        
                        # 먼저 일반적인 삭제 시도
                        shutil.rmtree(full_path, ignore_errors=True)
                        logging.info("삭제됨: %s", full_path)
                        
                        # 삭제 확인
                        if full_path.exists():
                            logging.warning("일반 삭제 실패, 강제 삭제 시도: %s", full_path)
                            # 강제 삭제 시도
                            if os.name == 'nt':
                                # Windows에서 강제 삭제
                                result = subprocess.run(f'rmdir /s /q "{full_path}"', shell=True, capture_output=True, timeout=30)
                                if result.returncode == 0:
                                    logging.info("Windows 강제 삭제 완료: %s", full_path)
                                else:
                                    logging.warning("Windows 강제 삭제 실패: %s", result.stderr)
                                    # 추가 대기 후 재시도
                                    time.sleep(5)
                                    subprocess.run(f'rmdir /s /q "{full_path}"', shell=True, capture_output=True)
                            else:
                                # Linux/Mac에서 강제 삭제
                                subprocess.run(f'rm -rf "{full_path}"', shell=True, capture_output=True)
                                logging.info("Linux/Mac 강제 삭제 완료: %s", full_path)
                    except Exception as e:
                        logging.error("빌드 폴더 삭제 실패: %s - %s", full_path, e)
            
            # .spec 파일 삭제 (강화된 버전)
            for spec_file in base_path.glob("*.spec"):
                try:
                    spec_file.unlink()
                    logging.info("삭제됨: %s", spec_file)
                except PermissionError:
                    logging.warning("spec 파일 삭제 실패 (잠겨있음): %s", spec_file)
                    # 강제 삭제 시도
                    try:
                        subprocess.run(f'del /f /q "{spec_file}"', shell=True, capture_output=True, timeout=5)
                        logging.info("spec 파일 강제 삭제 성공: %s", spec_file)
                    except Exception as e:
                        logging.error("spec 파일 강제 삭제 실패: %s - %s", spec_file, e)
                except Exception as e:
                    logging.warning("spec 파일 삭제 실패: %s - %s", spec_file, e)
            
            # PyInstaller 설치 확인 및 설치 (강화된 버전)
            try:
                import PyInstaller  # type: ignore
                logging.info("PyInstaller 버전: %s", PyInstaller.__version__)
            except ImportError:
                logging.info("PyInstaller 설치 중...")
                
                # 현재 Python 환경에 직접 설치
                try:
                    install_result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--quiet", "pyinstaller"],
                        capture_output=True, 
                        text=True,
                        timeout=60
                    )
                    if install_result.returncode == 0:
                        logging.info("PyInstaller 설치 성공")
                    else:
                        logging.error("PyInstaller 설치 실패: %s", install_result.stderr)
                        return False
                except Exception as e:
                    logging.error("PyInstaller 설치 시도 실패: %s", e)
                    return False
                
                # 설치 후 다시 확인
                try:
                    import PyInstaller  # type: ignore
                    logging.info("PyInstaller 설치 확인 완료: %s", PyInstaller.__version__)
                except ImportError:
                    logging.error("PyInstaller 설치 후에도 임포트 실패")
                    return False
            
            # src/main.py를 진입점으로 사용
            main_script = base_path / "src" / "main.py"
            
            if main_script.exists():
                # Tcl/Tk 인코딩 문제 해결을 위한 환경 변수 설정 (강화된 버전)
                env = os.environ.copy()
                env['PYTHONPATH'] = str(base_path)
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # Python 3.11 환경 변수 추가
                python311_path = "C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311"
                if python311_path not in env.get('PATH', ''):
                    env['PATH'] = f"{python311_path};{python311_path}\\Scripts;{env.get('PATH', '')}"
                
                # PyInstaller 경로 추가 (Python 3.11 환경)
                pyinstaller_path = "C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages"
                if pyinstaller_path not in env.get('PYTHONPATH', ''):
                    env['PYTHONPATH'] = f"{pyinstaller_path};{env.get('PYTHONPATH', '')}"
                
                # Tcl/Tk 인코딩 문제 해결을 위한 추가 옵션
                runtime_hook_path = base_path / "runtime_hook.py"
                
                # Python 3.11 실행 경로 확인 및 수정
                python_executable = sys.executable
                logging.info("현재 Python 실행 경로: %s", python_executable)
                
                # Python 3.11 명시적 사용 시도
                try:
                    # py -3.11 명령어로 Python 3.11 사용
                    python311_result = subprocess.run(
                        ["py", "-3.11", "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if python311_result.returncode == 0:
                        python_executable = "py -3.11"
                        logging.info("Python 3.11 사용: %s", python_executable)
                    else:
                        logging.warning("Python 3.11 명령어 실패, 현재 Python 사용")
                except Exception as e:
                    logging.warning("Python 3.11 확인 실패: %s, 현재 Python 사용", e)
                
                # PyInstaller 모듈 경로 확인
                try:
                    import PyInstaller  # type: ignore
                    pyinstaller_path = PyInstaller.__file__
                    logging.info("PyInstaller 경로: %s", pyinstaller_path)
                except Exception as e:
                    logging.warning("PyInstaller 경로 확인 실패: %s", e)
                
                # PyInstaller 실행 방법 결정 (Python 3.11 사용)
                if python_executable == "py -3.11":
                    pyinstaller_cmd = ["py", "-3.11", "-m", "PyInstaller"]
                else:
                    pyinstaller_cmd = [python_executable, "-m", "PyInstaller"]
                logging.info("PyInstaller 실행 방법: %s", " ".join(pyinstaller_cmd))
                
                # Tcl/Tk 인코딩 문제 해결을 위한 최소 설정 (onedir 모드로 변경)
                cmd = pyinstaller_cmd + [
                    "--noconfirm", "--clean", "--onedir", "--windowed",  # --onefile 대신 --onedir 사용
                    "--name", "text_cleaner",
                    "--add-data", f"{base_path / 'guidelines.json'};.",
                    "--add-data", f"{base_path / 'fonts'};fonts",
                    "--hidden-import", "tkinter",
                    "--hidden-import", "tkinter.ttk",
                    "--hidden-import", "tkinter.messagebox",
                    "--hidden-import", "tkinter.filedialog",
                    "--hidden-import", "PIL",
                    "--hidden-import", "PIL.Image",
                    "--hidden-import", "PIL.ImageTk",
                    "--hidden-import", "cv2",
                    "--hidden-import", "pytesseract",
                    "--hidden-import", "psutil",
                    "--distpath", str(base_path / "dist"),
                    "--workpath", str(base_path / "build"),
                    "--specpath", str(base_path),
                    str(main_script)
                ]
                logging.info("새로운 구조로 빌드: %s", main_script)
            else:
                logging.error("메인 스크립트를 찾을 수 없음: %s", main_script)
                return False
            
            # 빌드 전 추가 파일 잠금 해제 및 대기
            logging.info("빌드 전 추가 파일 잠금 해제 및 대기")
            self._force_unlock_exe_file()
            time.sleep(3)  # 추가 대기 시간
            
            logging.info("PyInstaller 빌드 실행: %s", " ".join(cmd))
            
            # 실시간으로 출력을 보기 위해 Popen 사용 (강화된 버전)
            # Windows에서 한글 인코딩 문제 해결
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=base_path,
                env=env,
                startupinfo=startupinfo
            )
            
            # 실시간으로 출력 읽기
            output_lines = []
            if process.stdout:
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        output_lines.append(output.strip())
                        logging.info("PyInstaller: %s", output.strip())
            
            returncode = process.wait()
            logging.info("PyInstaller 빌드 완료 (returncode: %d)", returncode)
            
            if returncode == 0:
                # 빌드 결과 확인 (onedir 모드)
                exe_path = base_path / "dist" / "text_cleaner" / "text_cleaner.exe"
                if exe_path.exists():
                    logging.info("빌드 성공: %s", exe_path)
                    return True
                else:
                    logging.error("빌드 실패: text_cleaner.exe가 생성되지 않음")
                    logging.error("dist 폴더 내용: %s", list((base_path / "dist").glob("*")) if (base_path / "dist").exists() else "dist 폴더 없음")
                    return False
            else:
                logging.error("PyInstaller 빌드 실패 (returncode: %d)", returncode)
                logging.error("빌드 출력: %s", output_lines)
                return False
                
        except Exception as e:
            logging.error("PyInstaller 빌드 실패: %s", e)
            return False

    def _build_with_batch(self, build_script: Path) -> bool:
        """배치 파일로 빌드 (개선된 버전)"""
        try:
            logging.info("배치 파일로 빌드 시작: %s", build_script)
            
            # Windows 환경에서 안전한 subprocess 실행
            if os.name == 'nt':  # Windows
                # Windows에서 한글 인코딩 문제 해결
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                # 환경 변수 설정
                env = os.environ.copy()
                env['PYTHONPATH'] = str(build_script.parent)
                env['PYTHONIOENCODING'] = 'utf-8'
                
                process = subprocess.Popen(
                    [str(build_script)], 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, 
                    encoding='utf-8',
                    errors='replace',
                    cwd=build_script.parent,
                    startupinfo=startupinfo,
                    shell=True,
                    env=env
                )
                
                # 실시간으로 출력 읽기
                output_lines = []
                if process.stdout:
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            output_lines.append(output.strip())
                            logging.info("빌드: %s", output.strip())
                
                returncode = process.wait()
                logging.info("배치 파일 빌드 완료 (returncode: %d)", returncode)
            else:
                # Linux/Mac 환경
                result = subprocess.run(
                    [str(build_script)], 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    errors='replace',
                    cwd=build_script.parent,
                    timeout=300
                )
                returncode = result.returncode
                output_lines = result.stdout.splitlines() if result.stdout else []
            
            # 빌드 결과 확인
            base_path = self.get_base_path()
            
            # text_cleaner.exe 확인 (onedir 모드)
            new_exe_path = base_path / "dist" / "text_cleaner" / "text_cleaner.exe"
            if not new_exe_path.exists():
                # onefile 모드 확인
                new_exe_path = base_path / "dist" / "text_cleaner.exe"
            
            if new_exe_path.exists():
                logging.info("배치 파일 빌드 성공: %s", new_exe_path)
                return True
            elif returncode == 0:
                # returncode가 0이면 성공으로 간주
                logging.info("배치 파일 빌드 성공 (returncode: 0)")
                return True
            else:
                logging.error("배치 파일 빌드 실패: returncode %d", returncode)
                if output_lines:
                    logging.error("빌드 출력: %s", output_lines)
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("배치 파일 빌드 시간 초과")
            return False
        except Exception as e:
            logging.error("배치 파일 빌드 실패: %s", e)
            return False

    def terminate_current_program(self) -> bool:
        """text_cleaner 관련 프로세스 정확히 종료 (개선된 버전)"""
        try:
            logging.info("1단계: text_cleaner.exe 종료 중...")
            
            if os.name == 'nt':  # Windows
                # 1단계: text_cleaner.exe 종료
                cmd = 'taskkill /f /im "text_cleaner.exe"'
                try:
                    logging.info("실행: %s", cmd)
                    result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
                    if result.returncode == 0:
                        logging.info("text_cleaner.exe 종료 성공")
                    else:
                        logging.info("text_cleaner.exe가 이미 종료되었거나 실행 중이 아님")
                except Exception as e:
                    logging.warning("text_cleaner.exe 종료 실패: %s", e)
                
                # 2단계: text_cleaner 관련 Python 프로세스 종료
                logging.info("2단계: text_cleaner 관련 Python 프로세스 종료 중...")
                if PSUTIL_AVAILABLE:
                    try:
                        terminated_count = 0
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            if proc.info['name']:
                                # text_cleaner.exe 또는 text_cleaner 관련 Python 프로세스만 종료
                                should_terminate = False
                                
                                if proc.info['name'].lower() == 'text_cleaner.exe':
                                    should_terminate = True
                                elif (proc.info['name'].lower() == 'python.exe' and 
                                      proc.info.get('cmdline')):
                                    cmdline = ' '.join(proc.info['cmdline']).lower()
                                    # text_cleaner 관련 명령어 확인
                                    if any(keyword in cmdline for keyword in [
                                        'text_cleaner', 'main.py', 'src/main.py', 
                                        'app.py', 'src/ui/app.py'
                                    ]):
                                        should_terminate = True
                                
                                if should_terminate:
                                    try:
                                        logging.info("text_cleaner 관련 프로세스 종료: PID %s, 이름: %s, 명령어: %s", 
                                                   proc.info['pid'], proc.info['name'], 
                                                   ' '.join(proc.info.get('cmdline', [])))
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                        terminated_count += 1
                                    except psutil.NoSuchProcess:
                                        pass
                                    except Exception as e:
                                        logging.warning("프로세스 종료 실패 (PID %s): %s", proc.info['pid'], e)
                        
                        logging.info("종료된 text_cleaner 관련 프로세스 수: %d", terminated_count)
                        
                    except Exception as e:
                        logging.warning("psutil 프로세스 종료 실패: %s", e)
                else:
                    # psutil이 없는 경우 대안 방법
                    logging.info("psutil이 없어 대안 방법으로 Python 프로세스 종료 시도")
                    try:
                        # 현재 실행 중인 Python 프로세스 중 text_cleaner 관련 프로세스 찾기
                        cmd = 'wmic process where "name=\'python.exe\' and commandline like \'%text_cleaner%\'" call terminate'
                        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
                        if result.returncode == 0:
                            logging.info("WMIC를 통한 Python 프로세스 종료 성공")
                        else:
                            logging.info("WMIC를 통한 Python 프로세스 종료 실패 또는 해당 프로세스 없음")
                    except Exception as e:
                        logging.warning("WMIC 프로세스 종료 실패: %s", e)
                
                # 3단계: 추가 대기 시간으로 프로세스 완전 종료 확인
                logging.info("3단계: 프로세스 완전 종료 대기 중...")
                time.sleep(3)
                
                # 4단계: 파일 잠금 해제를 위한 대기
                logging.info("4단계: 파일 잠금 해제 대기 중...")
                time.sleep(2)
                
                # 5단계: 파일 핸들러 해제를 위한 가비지 컬렉션
                import gc
                gc.collect()
                
                # 6단계: 강제로 dist/text_cleaner.exe 파일 잠금 해제
                logging.info("6단계: dist/text_cleaner.exe 파일 잠금 해제 시도...")
                self._force_unlock_exe_file()
                
                logging.info("text_cleaner 프로세스 종료 완료")
                return True
            else:
                # Linux/Mac 환경
                return self.kill_all_python_processes()
                
        except Exception as e:
            logging.error("프로세스 종료 중 오류 발생: %s", e)
            return False

    def _force_unlock_exe_file(self) -> bool:
        """dist/text_cleaner.exe 파일의 잠금을 강제로 해제"""
        try:
            base_path = self.get_base_path()
            exe_path = base_path / "dist" / "text_cleaner.exe"
            
            if not exe_path.exists():
                logging.info("text_cleaner.exe 파일이 존재하지 않음")
                return True
            
            # Windows에서 파일 잠금 해제 시도
            if os.name == 'nt':
                # 방법 1: 모든 text_cleaner 관련 프로세스 강제 종료
                logging.info("방법 1: 모든 text_cleaner 관련 프로세스 강제 종료")
                try:
                    # text_cleaner.exe 프로세스 강제 종료
                    subprocess.run("taskkill /f /im text_cleaner.exe", shell=True, capture_output=True, timeout=5)
                    
                    # Python 프로세스 중 text_cleaner 관련 프로세스 강제 종료
                    if PSUTIL_AVAILABLE:
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            if proc.info['name'] and proc.info['name'].lower() == 'python.exe':
                                try:
                                    cmdline = ' '.join(proc.info.get('cmdline', [])).lower()
                                    if any(keyword in cmdline for keyword in ['text_cleaner', 'main.py', 'src/main.py']):
                                        logging.info(f"text_cleaner 관련 Python 프로세스 강제 종료: PID {proc.info['pid']}")
                                        proc.kill()
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                except Exception as e:
                    logging.warning(f"프로세스 강제 종료 중 오류: {e}")
                
                # 방법 2: 파일 핸들러 해제를 위한 대기
                logging.info("방법 2: 파일 핸들러 해제 대기")
                time.sleep(3)
                
                # 방법 3: 파일 삭제 시도
                logging.info("방법 3: 파일 삭제 시도")
                try:
                    exe_path.unlink()
                    logging.info("text_cleaner.exe 파일 삭제 성공")
                    return True
                except PermissionError:
                    logging.warning("text_cleaner.exe 파일 삭제 실패 (잠겨있음)")
                    
                    # 방법 4: 추가 대기 후 재시도
                    logging.info("방법 4: 추가 대기 후 재시도")
                    time.sleep(5)
                    try:
                        exe_path.unlink()
                        logging.info("text_cleaner.exe 파일 삭제 성공 (재시도)")
                        return True
                    except PermissionError:
                        logging.error("text_cleaner.exe 파일 삭제 실패 (최종)")
                        
                        # 방법 5: 파일 이름 변경 시도
                        logging.info("방법 5: 파일 이름 변경 시도")
                        try:
                            backup_path = exe_path.with_suffix('.exe.bak')
                            exe_path.rename(backup_path)
                            logging.info(f"text_cleaner.exe 파일 이름 변경 성공: {backup_path}")
                            return True
                        except Exception as e:
                            logging.error(f"파일 이름 변경 실패: {e}")
                            
                            # 방법 6: 강제 삭제 명령어 사용
                            logging.info("방법 6: 강제 삭제 명령어 사용")
                            try:
                                subprocess.run(f'del /f /q "{exe_path}"', shell=True, capture_output=True, timeout=10)
                                if not exe_path.exists():
                                    logging.info("강제 삭제 명령어로 파일 삭제 성공")
                                    return True
                                else:
                                    logging.error("강제 삭제 명령어로도 파일 삭제 실패")
                                    return False
                            except Exception as e:
                                logging.error(f"강제 삭제 명령어 실패: {e}")
                                return False
                            
            else:
                # Linux/Mac 환경
                try:
                    exe_path.unlink()
                    logging.info("text_cleaner.exe 파일 삭제 성공")
                    return True
                except Exception as e:
                    logging.warning(f"파일 삭제 실패: {e}")
                    return False
                    
        except Exception as e:
            logging.error(f"파일 잠금 해제 중 예외 발생: {e}")
            return False

    def launch_new_program(self) -> bool:
        """새 text_cleaner.exe 실행"""
        try:
            logging.info("새 text_cleaner.exe 실행 시작")
            
            # 새 실행 파일 경로 확인 (onedir 모드)
            base_path = self.get_base_path()
            new_exe_path = base_path / "dist" / "text_cleaner" / "text_cleaner.exe"
            
            if not new_exe_path.exists():
                logging.error("text_cleaner.exe를 찾을 수 없습니다")
                return False
            
            logging.info("text_cleaner.exe 발견: %s", new_exe_path)
            
            # Windows 환경에서 새 프로그램 실행
            if os.name == 'nt':
                try:
                    # os.startfile로 새 프로그램 실행
                    os.startfile(str(new_exe_path))
                    logging.info("text_cleaner.exe 실행 완료")
                    
                    # 3초 대기 후 cmd 창 닫기
                    logging.info("새 프로그램 실행 완료 - 3초 대기 후 cmd 창 닫기")
                    time.sleep(3)
                    
                    # cmd 창 닫기 (개선된 방법)
                    try:
                        # 현재 프로세스의 부모 프로세스(CMD) 종료
                        if PSUTIL_AVAILABLE:
                            current_process = psutil.Process()
                            parent_process = current_process.parent()
                            if parent_process and "cmd.exe" in parent_process.name().lower():
                                # 부모 프로세스의 부모도 확인 (실제 CMD 창)
                                grandparent = parent_process.parent()
                                if grandparent and "cmd.exe" in grandparent.name().lower():
                                    grandparent.terminate()
                                    logging.info("CMD 창 종료 완료 (grandparent)")
                                else:
                                    parent_process.terminate()
                                    logging.info("CMD 창 종료 완료 (parent)")
                        else:
                            # psutil이 없는 경우 대안 방법
                            subprocess.run("taskkill /f /im cmd.exe", shell=True, capture_output=True)
                            logging.info("CMD 창 종료 시도 완료")
                    except Exception as e:
                        logging.warning("CMD 창 종료 실패: %s", e)
                    
                    return True
                except Exception as e:
                    logging.error("프로그램 실행 실패: %s", e)
                    return False
            else:
                logging.error("지원하지 않는 운영체제")
                return False
            
        except Exception as e:
            logging.error("새 프로그램 실행 중 오류: %s", e)
            return False

    def restart_program(self) -> bool:
        """프로그램 재시작 (기존 프로세스 종료 후 새 프로그램 실행) - 하위 호환성"""
        return self.launch_new_program()

    def validate_upgrade_environment(self) -> bool:
        """업그레이드 환경 검증 (개선된 버전)"""
        try:
            logging.info("업그레이드 환경 검증 시작")
            
            # Python 설치 확인
            if not sys.executable:
                logging.error("Python 실행 파일을 찾을 수 없음")
                return False

            # 기본 경로 확인
            base_path = self.get_base_path()
            if not base_path.exists():
                logging.error("기본 경로가 존재하지 않음: %s", base_path)
                return False

            # src/main.py 파일 존재 확인
            main_script = base_path / "src" / "main.py"
            if not main_script.exists():
                logging.error("메인 스크립트를 찾을 수 없음: %s", main_script)
                return False
            
            # 메인 스크립트 무결성 검증
            if not self._validate_file_integrity(main_script):
                logging.error("메인 스크립트 무결성 검증 실패")
                return False

            # tkinter 모듈 확인 (중요!)
            try:
                import tkinter
                logging.info("tkinter 모듈 확인 완료")
            except ImportError:
                logging.error("tkinter 모듈을 찾을 수 없습니다. 환경 검증 스크립트를 실행하세요.")
                return False

            # psutil 설치 확인
            if not PSUTIL_AVAILABLE:
                logging.warning("psutil 모듈이 설치되지 않았습니다. 프로세스 종료 기능이 제한됩니다.")

            # 디스크 공간 확인
            try:
                disk_usage = shutil.disk_usage(base_path)
                free_space_gb = disk_usage.free / (1024**3)
                if free_space_gb < 1.0:  # 1GB 미만
                    logging.warning("디스크 공간 부족: %.2f GB", free_space_gb)
                else:
                    logging.info("디스크 공간 확인: %.2f GB 사용 가능", free_space_gb)
            except Exception as e:
                logging.warning("디스크 공간 확인 실패: %s", e)

            logging.info("업그레이드 환경 검증 완료")
            return True
            
        except Exception as e:
            logging.error("업그레이드 환경 검증 실패: %s", e)
            return False

    def run_environment_verification(self) -> bool:
        """환경 검증 스크립트 실행"""
        try:
            logging.info("환경 검증 스크립트 실행 시작")
            
            base_path = self.get_base_path()
            verify_script = base_path / "verify_environment.py"
            
            if not verify_script.exists():
                logging.error("환경 검증 스크립트를 찾을 수 없음: %s", verify_script)
                return False
            
            # 환경 검증 스크립트 실행
            result = subprocess.run(
                [sys.executable, str(verify_script)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logging.info("환경 검증 성공")
                return True
            else:
                logging.error("환경 검증 실패: %s", result.stderr)
                return False
                
        except Exception as e:
            logging.error("환경 검증 스크립트 실행 실패: %s", e)
            return False 

    def _create_temp_upgrade_script(self) -> Optional[Path]:
        """임시 업그레이드 스크립트 생성 - 독립 실행 방식"""
        try:
            import tempfile
            
            # 프로젝트 루트 경로 찾기
            base_path = self.get_base_path()
            
            # 임시 스크립트 내용 생성 - 독립 실행 방식
            script_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
임시 업그레이드 스크립트
독립적으로 실행되는 업그레이드 프로세스
"""

import sys
import os
import logging
import subprocess
import time
import shutil
from pathlib import Path

# 로깅 설정
def setup_logging():
    """로깅 설정"""
    project_root = r"{base_path}"
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, "temp_upgrade.log"), encoding='utf-8')
        ]
    )

setup_logging()

print("[임시 업그레이드 스크립트] 시작...")
logging.info("임시 업그레이드 스크립트 시작")

try:
    project_root = r"{base_path}"
    logging.info(f"프로젝트 루트: {{project_root}}")
    
    # Python 실행 파일 경로 확인
    python_exe = sys.executable
    logging.info(f"Python 실행 파일: {{python_exe}}")
    
    # 방법 1: 배치 파일을 통한 업그레이드
    build_bat = os.path.join(project_root, "build.bat")
    if os.path.exists(build_bat):
        print("[임시 업그레이드 스크립트] build.bat를 통한 업그레이드 시도")
        logging.info("build.bat를 통한 업그레이드 시도")
        
        # 환경 변수 설정
        env = os.environ.copy()
        env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
        
        # 배치 파일 실행
        result = subprocess.run(
            [build_bat],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            shell=True
        )
        
        if result.returncode == 0:
            print("[임시 업그레이드 스크립트] build.bat 업그레이드 성공")
            logging.info("build.bat 업그레이드 성공")
            logging.info(f"출력: {{result.stdout}}")
            
            # 새 프로그램 실행 시도
            time.sleep(2)
            new_exe = os.path.join(project_root, "dist", "text_cleaner.exe")
            if os.path.exists(new_exe):
                try:
                    subprocess.Popen([new_exe], cwd=project_root)
                    print("[임시 업그레이드 스크립트] 새 프로그램 실행 성공")
                    logging.info("새 프로그램 실행 성공")
                except Exception as e:
                    print(f"[임시 업그레이드 스크립트] 새 프로그램 실행 실패: {{e}}")
                    logging.error(f"새 프로그램 실행 실패: {{e}}")
        else:
            print(f"[임시 업그레이드 스크립트] build.bat 업그레이드 실패: {{result.stderr}}")
            logging.error(f"build.bat 업그레이드 실패: {{result.stderr}}")
            logging.error(f"출력: {{result.stdout}}")
    else:
        print(f"[임시 업그레이드 스크립트] build.bat를 찾을 수 없음: {{build_bat}}")
        logging.error(f"build.bat를 찾을 수 없음: {{build_bat}}")
        
        # 방법 2: 직접 Python 스크립트 실행
        main_script = os.path.join(project_root, "src", "main.py")
        if os.path.exists(main_script):
            print("[임시 업그레이드 스크립트] main.py 직접 실행 시도")
            logging.info("main.py 직접 실행 시도")
            
            # 환경 변수 설정
            env = os.environ.copy()
            env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
            
            # main.py 실행
            result = subprocess.run(
                [python_exe, main_script],
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                print("[임시 업그레이드 스크립트] main.py 실행 성공")
                logging.info("main.py 실행 성공")
            else:
                print(f"[임시 업그레이드 스크립트] main.py 실행 실패: {{result.stderr}}")
                logging.error(f"main.py 실행 실패: {{result.stderr}}")
        else:
            print(f"[임시 업그레이드 스크립트] main.py를 찾을 수 없음: {{main_script}}")
            logging.error(f"main.py를 찾을 수 없음: {{main_script}}")
        
except Exception as e:
    print(f"[임시 업그레이드 스크립트] 예상치 못한 오류: {{e}}")
    logging.error(f"예상치 못한 오류: {{e}}")
    import traceback
    logging.error(traceback.format_exc())

finally:
    print("[임시 업그레이드 스크립트] 종료")
    logging.info("임시 업그레이드 스크립트 종료")
    
    # 임시 파일 정리
    try:
        current_script = Path(__file__)
        if current_script.exists():
            current_script.unlink()
            print("[임시 업그레이드 스크립트] 임시 파일 삭제 완료")
    except Exception as e:
        print(f"[임시 업그레이드 스크립트] 임시 파일 삭제 실패: {{e}}")
'''
            
            # 임시 파일 생성
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                prefix='temp_upgrade_',
                delete=False,
                encoding='utf-8'
            )
            
            temp_file.write(script_content)
            temp_file.close()
            
            temp_path = Path(temp_file.name)
            logging.info(f"임시 업그레이드 스크립트 생성 완료: {temp_path}")
            return temp_path
            
        except Exception as e:
            logging.error(f"임시 업그레이드 스크립트 생성 실패: {e}")
            return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="text_cleaner 업그레이드 매니저")
    parser.add_argument("--upgrade-and-restart", action="store_true", help="업그레이드 후 새 exe 실행")
    args = parser.parse_args()

    if args.upgrade_and_restart:
        # 프로젝트 루트를 sys.path에 추가
        import sys
        from pathlib import Path
        
        # 현재 파일의 위치를 기준으로 프로젝트 루트 찾기
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # src/core/upgrade_manager.py -> src/core -> src -> project_root
        sys.path.insert(0, str(project_root))
        
        # 로깅 설정 강화
        from datetime import datetime
        log_filename = project_root / "logs" / f"upgrade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_filename.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        print("[업그레이드 매니저] 업그레이드 및 재시작 모드 진입")
        logging.info("업그레이드 매니저 시작")
        
        try:
            # 가이드라인 매니저 없이 최소 실행
            manager = UpgradeManager(guideline_manager=None)
            logging.info("업그레이드 매니저 인스턴스 생성 완료")
            
            # 업그레이드 실행(자동)
            logging.info("업그레이드 실행 시작")
            result = manager.execute_upgrade(auto_upgrade=True)
            
            if result:
                logging.info("업그레이드 성공 - 새 프로그램 실행 시도")
                print("[업그레이드 매니저] 업그레이드 성공 - 새 프로그램 실행 시도")
                
                # 빌드 완료 후 잠시 대기
                time.sleep(2)
                
                # 새 프로그램 실행 시도 (한 번만 실행)
                launch_result = manager.launch_new_program()
                if launch_result:
                    logging.info("새 프로그램 실행 성공")
                    print("[업그레이드 매니저] 새 프로그램 실행 성공")
                    
                    # 새 프로그램 실행 후 충분한 대기 시간
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
                
        except Exception as e:
            error_msg = f"업그레이드 매니저 예외 발생: {e}"
            logging.error(error_msg)
            print(f"[업그레이드 매니저] {error_msg}")
            
        logging.info("업그레이드 매니저 종료") 