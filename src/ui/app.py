#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text Cleaner 메인 애플리케이션 UI
리팩토링된 구조로 개선된 사용자 인터페이스
"""

import logging
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk, filedialog
from typing import Dict, Any, Optional, Tuple, List, Union, Callable
from functools import lru_cache
import weakref

# 절대 경로 import로 수정
from src.core.text_processor import TextProcessor
from src.core.guideline_manager import GuidelineManager
from src.core.upgrade_manager import UpgradeManager
from src.ocr.ocr_processor import OCRProcessor
from src.utils.logging_utils import log_user_action, get_user_data_path
from src.utils.locale_utils import get_ui_text, format_ui_text


class TextCleanerApp:
    """Text Cleaner 메인 애플리케이션 클래스 - 리팩토링된 구조"""

    # UI 상수
    WINDOW_WIDTH: int = 900
    WINDOW_HEIGHT: int = 700
    THREAD_DAEMON: bool = True
    
    # 텍스트 위젯 설정
    TEXT_HEIGHT: int = 18
    TEXT_WIDTH: int = 90
    TEXT_FONT: Tuple[str, int] = ("Microsoft YaHei UI", 10)
    
    # 레이아웃 설정
    MAIN_PADDING: str = "15"
    FRAME_PADDING: str = "10"
    BUTTON_PADDING: int = 5
    
    # 성능 최적화 설정
    MAX_TEXT_LENGTH: int = 100000  # 최대 텍스트 길이 제한
    BATCH_SIZE: int = 1000  # 배치 처리 크기
    DEBOUNCE_DELAY: int = 300  # 디바운스 지연 시간 (ms)

    def __init__(self, root: tk.Tk, user_action_logger: Optional[logging.Logger] = None) -> None:
        """애플리케이션 초기화"""
        logging.info("Application initialization started")
        
        self.root: tk.Tk = root
        self.user_action_logger: Optional[logging.Logger] = user_action_logger
        self.text: Dict[str, str] = get_ui_text()
        
        # 성능 최적화를 위한 변수들
        self._debounce_timer: Optional[str] = None
        self._text_cache: Dict[str, str] = {}
        self._processing_lock: threading.Lock = threading.Lock()
        
        # 윈도우 설정
        self._setup_window()
        
        # 모듈 초기화
        self._initialize_modules()
        
        # 아이콘 설정
        self._setup_icon()

        # UI 구성
        self._setup_ui()
        
        # 상태 변수
        self.processing: bool = False
        
        logging.info("Application initialization completed")

    def _setup_window(self) -> None:
        """윈도우 기본 설정"""
        self.root.title(self.text['title'])
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.resizable(True, True)

    def _initialize_modules(self) -> None:
        """모듈 초기화"""
        user_data_path: Path = get_user_data_path()
        self.text_processor: TextProcessor = TextProcessor()
        self.guideline_manager: GuidelineManager = GuidelineManager(user_data_path)
        self.upgrade_manager: UpgradeManager = UpgradeManager(self.guideline_manager)
        self.ocr_processor: OCRProcessor = OCRProcessor()
        self.current_guideline: Optional[str] = None

        # 가이드라인 로드
        self.guideline_manager.load_guidelines()
        self.guidelines: Dict[str, Any] = self.guideline_manager.guidelines

    def _setup_icon(self) -> None:
        """아이콘 설정"""
        try:
            icon_path: Path = Path(__file__).parent.parent.parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
                logging.info("Icon set successfully")
            else:
                logging.info("Icon file not found, using default icon")
        except Exception as e:
            logging.warning("Icon setting failed: %s", e)

    def _setup_ui(self) -> None:
        """UI 구성"""
        # 메인 프레임
        self.main_frame: ttk.Frame = ttk.Frame(self.root, padding=self.MAIN_PADDING)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        # 제목
        self._create_title()
        
        # UI 영역 설정
        self._setup_input_area()
        self._setup_buttons()
        self._setup_output_area()
        self._setup_statusbar()

        # 레이아웃 설정
        self._setup_layout()
        
        # ESC 키 바인딩 (메인 창 종료)
        self.root.bind('<Escape>', self._on_escape_main)
        self.root.bind('<Key-Escape>', self._on_escape_main)

    def _create_title(self) -> None:
        """제목 생성"""
        ttk.Label(self.main_frame, text=self.text['title'], 
                 font=("Arial", 18, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20)
        )

    def _setup_layout(self) -> None:
        """레이아웃 설정"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.rowconfigure(3, weight=1)

    @lru_cache(maxsize=128)
    def _create_text_widget_config(self, **kwargs: Any) -> Dict[str, Any]:
        """텍스트 위젯 설정 캐싱"""
        default_config: Dict[str, Any] = {
            'height': self.TEXT_HEIGHT,
            'width': self.TEXT_WIDTH,
            'wrap': tk.WORD,
            'font': self.TEXT_FONT,
            'undo': True
        }
        default_config.update(kwargs)
        return default_config

    def _create_text_widget(self, parent: tk.Widget, **kwargs: Any) -> scrolledtext.ScrolledText:
        """텍스트 위젯 생성 헬퍼 함수 (최적화됨)"""
        config = self._create_text_widget_config(**kwargs)
        return scrolledtext.ScrolledText(parent, **config)

    def _setup_input_area(self) -> None:
        """입력 영역 설정"""
        input_frame: ttk.LabelFrame = ttk.LabelFrame(self.main_frame, text=self.text['input_label'], 
                                                   padding=self.FRAME_PADDING)
        input_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=0)  # guideline_frame은 고정 크기
        input_frame.rowconfigure(1, weight=1)  # list_frame이 나머지 공간 차지

        # 가이드라인 선택
        self._create_guideline_selector(input_frame)

        # 리스트 입력 영역
        self._create_list_input_area(input_frame)
        
        # 숨겨진 입력 텍스트 영역
        self._create_hidden_input_area(input_frame)

    def _create_guideline_selector(self, parent: tk.Widget) -> None:
        """가이드라인 선택기 생성"""
        guideline_frame: ttk.Frame = ttk.Frame(parent)
        guideline_frame.grid(row=0, column=0, sticky="ew")
        
        ttk.Label(guideline_frame, text=self.text['guideline']).pack(side=tk.LEFT, padx=(0, 5))

        self.guideline_var: tk.StringVar = tk.StringVar()
        self.guideline_combo: ttk.Combobox = ttk.Combobox(
            guideline_frame,
            textvariable=self.guideline_var,
            values=list(self.guidelines.keys()),
            state="readonly",
            width=20
        )
        self.guideline_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.guideline_combo.bind("<<ComboboxSelected>>", self._on_guideline_selected)

        self._update_guideline_combo()

        ttk.Button(guideline_frame, text=self.text['manage_guidelines'], 
                  command=self._manage_guidelines).pack(side=tk.LEFT, padx=5)

    def _create_list_input_area(self, parent: tk.Widget) -> None:
        """리스트 입력 영역 생성"""
        list_frame: ttk.Frame = ttk.Frame(parent)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        
        # 리스트 입력 영역
        self.list_text: scrolledtext.ScrolledText = self._create_text_widget(list_frame)
        self.list_text.grid(row=0, column=0, sticky="nsew")
        
        # 이벤트 바인딩 (디바운스 적용)
        self._bind_list_events()

    def _bind_list_events(self) -> None:
        """리스트 텍스트 위젯 이벤트 바인딩 (디바운스 적용)"""
        self.list_text.bind("<<Paste>>", self._on_list_paste)
        self.list_text.bind("<Control-v>", self._on_list_paste)
        self.list_text.bind("<Command-v>", self._on_list_paste)
        self.list_text.bind("<KeyRelease>", self._debounced_key_release)

    def _debounced_key_release(self, event: Optional[tk.Event] = None) -> None:
        """디바운스된 키 릴리즈 이벤트"""
        if self._debounce_timer:
            self.root.after_cancel(self._debounce_timer)
        
        self._debounce_timer = self.root.after(self.DEBOUNCE_DELAY, self._on_list_key_release)

    def _create_hidden_input_area(self, parent: tk.Widget) -> None:
        """숨겨진 입력 텍스트 영역 생성"""
        self.input_text: scrolledtext.ScrolledText = self._create_text_widget(parent, height=12)
        self.input_text.grid(row=2, column=0, sticky="nsew")
        self.input_text.insert(1.0, self.text['input_hint'])
        self.input_text.bind("<FocusIn>", self._clear_hint)
        self.input_text.bind("<FocusOut>", self._restore_hint)
        
        # 숨김 처리
        self.input_text.grid_remove()

    def _optimize_text_processing(self, text: str) -> str:
        """텍스트 처리 최적화"""
        # 텍스트 길이 제한
        if len(text) > self.MAX_TEXT_LENGTH:
            text = text[:self.MAX_TEXT_LENGTH]
            logging.warning(f"Text truncated to {self.MAX_TEXT_LENGTH} characters")
        
        # 캐시 확인
        cache_key = f"{hash(text)}_{self.current_guideline}"
        if cache_key in self._text_cache:
            logging.info("Using cached result")
            return self._text_cache[cache_key]
        
        return text

    def _batch_process_text(self, text: str) -> List[str]:
        """배치 처리로 텍스트 분할"""
        lines = text.splitlines()
        if len(lines) <= self.BATCH_SIZE:
            return lines
        
        # 배치로 분할
        batches = []
        for i in range(0, len(lines), self.BATCH_SIZE):
            batch = lines[i:i + self.BATCH_SIZE]
            batches.append('\n'.join(batch))
        
        return batches

    def _on_list_paste(self, event=None):
        """리스트에 붙여넣기 - 이미지 자동 OCR 처리 포함"""
        log_user_action("Paste into list")
        logging.info("=== 리스트 붙여넣기 시작 ===")
        
        # 먼저 클립보드에서 이미지 확인
        if self.ocr_processor.is_available():
            clipboard_image = self.ocr_processor.get_clipboard_image()
            if clipboard_image is not None:
                logging.info("클립보드에서 이미지 감지 - OCR 처리 시작")
                self._process_clipboard_image_ocr()
                return "break"
        
        # 이미지가 없으면 기존 텍스트 처리 로직 실행
        try:
            pasted = self.root.clipboard_get()
            logging.info(f"클립보드 내용 길이: {len(pasted)} 문자")
            logging.info(f"클립보드 내용 미리보기: {repr(pasted[:200])}...")
        except Exception as e:
            logging.error(f"클립보드 가져오기 실패: {e}")
            return
        
        if '\t' in pasted or ',' in pasted:
            # 엑셀 데이터를 리스트 형식으로 변환
            logging.info("엑셀 형식 데이터 감지 - 변환 시작")
            converted_data = self._convert_excel_to_list_format(pasted)
            logging.info(f"변환된 데이터 길이: {len(converted_data)} 문자")
            logging.info("변환된 데이터 미리보기:")
            for i, line in enumerate(converted_data.splitlines(), 1):
                if line.strip():
                    logging.info(f"변환 라인 {i}: {repr(line)}")
            
            self.list_text.delete(1.0, tk.END)
            self.list_text.insert(1.0, converted_data)
            logging.info("리스트 텍스트에 변환된 데이터 삽입 완료")
            return "break"
        else:
            logging.info("일반 텍스트 붙여넣기 - 변환 없이 처리")
            # 일반 텍스트는 그대로 붙여넣기 (기본 동작)
            pass

    def _on_list_key_release(self, event=None):
        """리스트 키 입력 시 호출"""
        # 리스트 데이터를 숨겨진 input_text에 저장
        list_data = self.list_text.get(1.0, tk.END).strip()
        if list_data and not list_data.startswith("#"):
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(1.0, list_data)

    def _convert_excel_to_list_format(self, text):
        """엑셀 데이터를 리스트 형식으로 변환"""
        lines = []
        
        for row in text.splitlines():
            if not row.strip():
                continue
                
            # 셀 분리 (탭/쉼표)
            if '\t' in row:
                cells = row.split('\t')
            else:
                cells = row.split(',')
            
            # 3개 컬럼에 맞게 처리
            processed_cells = []
            for i, cell in enumerate(cells[:3]):  # 최대 3개 컬럼만 처리
                cell = cell.strip()
                if not cell:
                    cell = ""
                
                # 첫 번째 컬럼(체크박스) 처리
                if i == 0:
                    cell = self._process_checkbox_value(cell)
                
                # 두 번째 컬럼(숫자) 처리
                elif i == 1:
                    cell = self._process_number_value(cell)
                
                processed_cells.append(cell)
            
            # 빈 셀이 아닌 경우만 라인에 추가
            if any(cell.strip() for cell in processed_cells):
                # 리스트 형식으로 변환 (빈 셀은 공백으로 처리)
                line = " | ".join(processed_cells)
                lines.append(line)
        
        return '\n'.join(lines)

    def _process_checkbox_value(self, value):
        """체크박스 값 처리"""
        value_lower = value.lower().strip()
        # 패턴이 없으면 원본 값 반환
        return value

    def _process_number_value(self, value):
        """숫자 값 처리"""
        import re
        
        # 숫자 패턴 찾기
        number_pattern = r'^(\d+(?:\.\d+)?)'
        match = re.match(number_pattern, value.strip())
        
        if match:
            return match.group(1)
        
        # 숫자가 뒤에 있는 경우
        number_pattern_end = r'(\d+(?:\.\d+)?)$'
        match = re.search(number_pattern_end, value.strip())
        
        if match:
            return match.group(1)
        
        return value

    def _setup_buttons(self) -> None:
        """버튼 영역 설정"""
        button_frame: ttk.Frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        # 버튼 생성 및 배치
        self._create_action_buttons(button_frame)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """액션 버튼들 생성"""
        buttons_config: List[Tuple[str, Callable[[], None], Optional[str]]] = [
            (self.text['clean_btn'], self._clean_text, "Accent.TButton"),
            (self.text['copy_btn'], self._copy_to_clipboard, None),
            (self.text['clear_output_btn'], self._clear_output, None),
            (self.text['ocr_btn'], self._ocr_from_image, None),
            (self.text['manage_guidelines'], self._manage_guidelines, None),
            (self.text['upgrade_btn'], self._upgrade_program, "Accent.TButton")
        ]
        
        for text, command, style in buttons_config:
            if style:
                button = ttk.Button(parent, text=text, command=command, style=style)
            else:
                button = ttk.Button(parent, text=text, command=command)
            button.pack(side=tk.LEFT, padx=self.BUTTON_PADDING)
            
            # 주요 버튼들을 인스턴스 변수로 저장
            if text == self.text['clean_btn']:
                self.clean_button = button
            elif text == self.text['copy_btn']:
                self.copy_button = button
            elif text == self.text['clear_output_btn']:
                self.clear_output_button = button
            elif text == self.text['ocr_btn']:
                self.ocr_button = button
            elif text == self.text['manage_guidelines']:
                self.manage_guidelines_button = button
            elif text == self.text['upgrade_btn']:
                self.upgrade_button = button

    def _setup_output_area(self) -> None:
        """출력 영역 설정"""
        output_frame: ttk.LabelFrame = ttk.LabelFrame(self.main_frame, text=self.text['output_label'], 
                                    padding=self.FRAME_PADDING)
        output_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text: scrolledtext.ScrolledText = self._create_text_widget(output_frame)
        self.output_text.grid(row=0, column=0, sticky="nsew")

    def _setup_statusbar(self) -> None:
        """상태바 설정"""
        self.status_var: tk.StringVar = tk.StringVar()
        self.status_var.set(self.text['status_ready'])
        self.statusbar: ttk.Label = ttk.Label(self.main_frame, textvariable=self.status_var,
                                  relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(15, 0))

    def _update_guideline_combo(self) -> None:
        """가이드라인 콤보박스 업데이트"""
        if self.guidelines:
            guideline_list: List[str] = list(self.guidelines.keys())
            self.guideline_combo['values'] = guideline_list
            self.guideline_combo.set(guideline_list[0])
            self.current_guideline = guideline_list[0]
            self.guideline_combo.config(state="readonly")
        else:
            self.guideline_combo.set("No Guidelines")
            self.guideline_combo.config(state="disabled")
            self.current_guideline = None

    def _clear_hint(self, event: Optional[tk.Event] = None) -> None:
        """힌트 텍스트 지우기"""
        if self.input_text.get(1.0, tk.END).strip() == self.text['input_hint']:
            self.input_text.delete(1.0, tk.END)

    def _restore_hint(self, event: Optional[tk.Event] = None) -> None:
        """힌트 텍스트 복원"""
        if not self.input_text.get(1.0, tk.END).strip():
            self.input_text.insert(1.0, self.text['input_hint'])

    def _on_guideline_selected(self, event: Optional[tk.Event] = None) -> None:
        """가이드라인 선택 이벤트"""
        selected: str = self.guideline_var.get()
        if selected in self.guidelines:
            self.current_guideline = selected
            logging.info("Guideline selected: %s", selected)
            log_user_action("Guideline selected", f"Selected guideline: {selected}")
            self.status_var.set(format_ui_text('select_guideline', name=selected))

    def _clean_text(self) -> None:
        """텍스트 정리 실행 (성능 최적화됨)"""
        log_user_action("Clean Text button clicked")
        
        # 스레드 안전성 확인
        if not self._processing_lock.acquire(blocking=False):
            logging.warning("Processing already in progress")
            log_user_action("Clean Text", "Processing already in progress", False)
            return
            
        try:
            if self.processing:
                logging.warning("Processing already in progress")
                log_user_action("Clean Text", "Processing already in progress", False)
                return
                
            logging.info("Starting text cleaning")
            self._start_processing()
            
            input_content: str = self.input_text.get(1.0, tk.END)
            logging.info("Input text length: %d characters", len(input_content))
            
            # 텍스트 처리 최적화
            input_content = self._optimize_text_processing(input_content)
            
            # 입력 텍스트 상세 로그
            self._log_input_text(input_content)
            
            if not self._validate_input(input_content):
                logging.warning("Input text validation failed")
                log_user_action("Clean Text", "Input validation failed", False)
                return
                
            # 빈 텍스트 처리
            text_length: int = len(input_content.strip())
            if text_length == 0:
                logging.info("Empty text input detected")
                log_user_action("Clean Text", "Empty text input", True)
                # 빈 텍스트의 경우에도 처리 진행 (가이드라인 정보만 표시)
                self._start_processing_thread(input_content)
            else:
                # 사용자 액션 로깅
                log_user_action("Clean Text", f"Text length: {text_length} characters, Guideline: {self.current_guideline}")
                
                # 스레드에서 처리
                self._start_processing_thread(input_content)
            
        except Exception as e:
            self._handle_processing_error(str(e))
        finally:
            self._processing_lock.release()

    def _start_processing(self) -> None:
        """처리 시작 상태 설정"""
        self.processing = True
        self.clean_button.config(state='disabled')
        self.status_var.set("Processing...")
        self.root.update()

    def _log_input_text(self, input_content: str) -> None:
        """입력 텍스트 로깅"""
        logging.info("=== 사용자 입력 텍스트 ===")
        logging.info("입력 텍스트 전체 내용:")
        for i, line in enumerate(input_content.splitlines(), 1):
            if line.strip():
                logging.info(f"라인 {i}: {repr(line)}")

    def _start_processing_thread(self, input_content: str) -> None:
        """처리 스레드 시작"""
        processing_thread: threading.Thread = threading.Thread(
            target=self._process_text_in_thread,
            args=(input_content,)
        )
        processing_thread.daemon = self.THREAD_DAEMON
        processing_thread.start()

    def _handle_processing_error(self, error_msg: str) -> None:
        """처리 오류 처리"""
        full_error_msg: str = f"An error occurred during processing: {error_msg}"
        logging.error(full_error_msg)
        log_user_action("Clean Text", f"Error: {error_msg}", False)
        messagebox.showerror("Error", full_error_msg)
        self.status_var.set("Error occurred")
        self.processing = False
        self.clean_button.config(state='normal')

    def _process_text_in_thread(self, input_content: str) -> None:
        """별도 스레드에서 텍스트 처리 (성능 최적화됨)"""
        try:
            logging.info("Starting text cleaning")
            logging.info(f"Input text length: {len(input_content)} characters")
            
            # 입력 텍스트를 각 행으로 분리하여 로그 기록
            input_lines: List[str] = input_content.splitlines()
            self._log_input_text(input_content)
            
            # 입력 텍스트 미리보기 로그
            logging.info(f"입력 텍스트 미리보기: {repr(input_content[:200])}...")
            
            # 배치 처리 적용
            if len(input_lines) > self.BATCH_SIZE:
                logging.info(f"Large text detected ({len(input_lines)} lines), using batch processing")
                result_text = self._process_large_text(input_content)
            else:
                # 일반 처리
                cleaned_lines: List[str]
                total_youtube_links_removed: int
                cleaned_lines, total_youtube_links_removed = self.text_processor.process_text(input_content)
                result_text = '\n'.join(cleaned_lines)
            
            # 처리 결과 로그
            logging.info(f"Original lines: {len(input_lines)}, Cleaned lines: {len(result_text.splitlines())}")
            
            # 가이드라인 적용
            if self.current_guideline and self.current_guideline in self.guidelines:
                logging.info(f"Applying guideline '{self.current_guideline}'")
                result_text, applied_rules = self._apply_guideline_rules(result_text)
                logging.info(f"Applied rules: {applied_rules}")
            
            # 결과 캐싱
            cache_key = f"{hash(input_content)}_{self.current_guideline}"
            self._text_cache[cache_key] = result_text
            
            # 캐시 크기 제한
            if len(self._text_cache) > 100:
                # 가장 오래된 항목 제거
                oldest_key = next(iter(self._text_cache))
                del self._text_cache[oldest_key]
            
            # 처리된 출력 텍스트 상세 로그
            self._log_output_text(result_text)
            
            self.root.after(0, self._update_gui_with_result, result_text, len(input_lines), 
                          result_text.splitlines(), 0)  # youtube_links_removed는 배치 처리에서 계산 필요
            
        except Exception as e:
            error_msg: str = f"Text processing error: {str(e)}"
            logging.error(error_msg)
            self.root.after(0, self._show_error_and_reset, error_msg)

    def _log_output_text(self, result_text: str) -> None:
        """출력 텍스트 로깅"""
        logging.info("=== 처리된 출력 텍스트 ===")
        logging.info("출력 텍스트 전체 내용:")
        for i, line in enumerate(result_text.splitlines(), 1):
            if line.strip():
                logging.info(f"출력 라인 {i}: {repr(line)}")

    def _filter_lines(self, lines: list) -> tuple:
        """라인 필터링 - TextProcessor 사용"""
        # TextProcessor를 사용하여 텍스트 처리
        input_text = '\n'.join(lines)
        cleaned_lines, total_youtube_links_removed = self.text_processor.process_text(input_text)
        
        return cleaned_lines, total_youtube_links_removed

    def _apply_guideline_rules(self, text: str) -> tuple:
        """가이드라인 규칙 적용"""
        if not self.current_guideline or self.current_guideline not in self.guidelines:
            return text, []
            
        guideline = self.guidelines[self.current_guideline]
        rules = guideline.get("rules", [])
        applied_rules = []
        cleaned_text = text
        
        # 간단한 규칙 적용 (실제로는 더 복잡한 로직 필요)
        for rule_name in rules:
            if "Remove empty lines" in rule_name:
                cleaned_text = "\n".join([line for line in cleaned_text.splitlines() if line.strip()])
                applied_rules.append(rule_name)
                
        return cleaned_text, applied_rules

    def _update_gui_with_result(self, result_text: str, original_lines: int, 
                               cleaned_lines: List[str], youtube_links_removed: int) -> None:
        """GUI 결과 업데이트"""
        try:
            logging.info("Updating output area")
            self.output_text.delete(1.0, tk.END)
            
            # 빈 텍스트 처리
            if not result_text.strip():
                self.output_text.insert(1.0, "입력된 텍스트가 없습니다.\n")
                if self.current_guideline and self.current_guideline in self.guidelines:
                    guideline = self.guidelines[self.current_guideline]
                    info_text = f"\n{'='*3}\nRules to apply:({self.current_guideline})\n"
                    for rule in guideline.get('rules', []):
                        clean_rule = rule.replace('"', '')
                        info_text += f"  • {clean_rule}\n"
                    self.output_text.insert(tk.END, info_text)
                self.status_var.set("빈 텍스트 - 가이드라인 정보만 표시됨")
            else:
                self.output_text.insert(1.0, result_text)
                
                if self.current_guideline and self.current_guideline in self.guidelines:
                    guideline = self.guidelines[self.current_guideline]
                    info_text = f"\n\n{'='*3}\nRules to apply:({self.current_guideline})\n"
                    for rule in guideline.get('rules', []):
                        clean_rule = rule.replace('"', '')
                        info_text += f"  • {clean_rule}\n"
                    self.output_text.insert(tk.END, info_text)
                    
                self._update_status(original_lines, cleaned_lines, youtube_links_removed)
            
            # 사용자 액션 로깅
            result_length = len(result_text)
            log_user_action("Clean Text completed", 
                          f"Original: {original_lines} lines → Result: {len(cleaned_lines)} lines, "
                          f"YouTube links removed: {youtube_links_removed}, "
                          f"Result text length: {result_length} characters")
            
            logging.info("Text cleaning completed")
            
        except Exception as e:
            error_msg = f"An error occurred during GUI update: {str(e)}"
            logging.error(error_msg)
            log_user_action("Clean Text", f"GUI update error: {str(e)}", False)
            self._show_error_and_reset(error_msg)
        finally:
            self.processing = False
            self.clean_button.config(state='normal')
            logging.info("Processing state reset")

    def _update_status(self, original_lines: int, cleaned_lines: List[str], 
                      youtube_links_removed: int = 0) -> None:
        """상태 업데이트"""
        removed_lines: int = original_lines - len(cleaned_lines)
        status_message: str = self._build_status_message(removed_lines, original_lines, 
                                                       len(cleaned_lines), youtube_links_removed)
        self.status_var.set(status_message)

    def _build_status_message(self, removed_lines: int, original_lines: int, 
                            cleaned_lines: int, youtube_links_removed: int) -> str:
        """상태 메시지 생성"""
        status_message: str = f"Completed: {removed_lines} lines removed (Original: {original_lines} lines → Result: {cleaned_lines} lines)"
        if youtube_links_removed > 0:
            status_message += f", YouTube links removed: {youtube_links_removed}"
        if self.current_guideline:
            status_message += f" (Guideline: {self.current_guideline})"
        status_message += ", Text cleaning completed"
        return status_message

    def _show_error_and_reset(self, error_msg: str) -> None:
        """오류 표시 및 상태 리셋"""
        messagebox.showerror("Error", error_msg)
        self.status_var.set("Error occurred")
        self.processing = False
        self.clean_button.config(state='normal')

    def _validate_input(self, text: str) -> bool:
        """입력 검증 - 텍스트가 없어도 허용"""
        # 텍스트가 없어도 정리 기능이 작동하도록 수정
        # 빈 텍스트의 경우에도 정리 프로세스를 진행할 수 있음
        return True

    def _copy_to_clipboard(self) -> None:
        """클립보드 복사 (성능 최적화됨)"""
        log_user_action("Copy to Clipboard button clicked")
        logging.info("Starting clipboard copy")
        
        try:
            output_content: str = self.output_text.get(1.0, tk.END).strip()
            if not output_content:
                self._handle_empty_clipboard_copy()
                return
            
            # 대용량 텍스트 처리 최적화
            if len(output_content) > self.MAX_TEXT_LENGTH:
                logging.warning(f"Large text detected ({len(output_content)} characters)")
                if not messagebox.askyesno("Large Text", 
                                         f"텍스트가 {len(output_content)} 문자로 매우 큽니다. 복사하시겠습니까?"):
                    return
            
            # 복사할 내용 상세 로그
            self._log_clipboard_content(output_content)
            
            # 클립보드에 복사
            self._perform_clipboard_copy(output_content)
            
            # 입력 텍스트 자동 지우기
            self._auto_clear_input_after_copy()
            
        except Exception as e:
            self._handle_clipboard_copy_error(str(e))

    def _handle_empty_clipboard_copy(self) -> None:
        """빈 클립보드 복사 처리"""
        logging.warning("No content to copy")
        log_user_action("Copy to Clipboard", "No content to copy", False)
        messagebox.showwarning("Warning", self.text['warning_no_content'])

    def _log_clipboard_content(self, output_content: str) -> None:
        """클립보드 복사 내용 로깅"""
        logging.info("=== 클립보드 복사 내용 ===")
        logging.info(f"복사할 텍스트 길이: {len(output_content)} 문자")
        logging.info("복사할 텍스트 전체 내용:")
        for i, line in enumerate(output_content.splitlines(), 1):
            if line.strip():
                logging.info(f"복사 라인 {i}: {repr(line)}")

    def _perform_clipboard_copy(self, output_content: str) -> None:
        """클립보드 복사 실행"""
        self.root.clipboard_clear()
        self.root.clipboard_append(output_content)
        
        # 상태 업데이트
        copy_message: str = f"{self.text['clipboard_copied']} ({len(output_content)} 문자)"
        self.status_var.set(copy_message)
        
        # 성공 로그
        log_user_action("Copy to Clipboard", f"Completed: {len(output_content)} characters")
        logging.info(f"Clipboard copy completed: {len(output_content)} characters")

    def _auto_clear_input_after_copy(self) -> None:
        """복사 후 입력 텍스트 자동 지우기"""
        input_content: str = self.list_text.get(1.0, tk.END).strip()
        if input_content and not input_content.startswith("#"):
            logging.info("Clearing input text after clipboard copy")
            self.list_text.delete(1.0, tk.END)
            self.input_text.delete(1.0, tk.END)
            copy_message: str = f"{self.text['clipboard_copied']} - 입력 텍스트 자동 지워짐"
            self.status_var.set(copy_message)
            log_user_action("Clear Input", "Auto-cleared after clipboard copy")
            logging.info("Input text auto-cleared after clipboard copy")
        else:
            logging.info("No input text to clear")

    def _handle_clipboard_copy_error(self, error: str) -> None:
        """클립보드 복사 오류 처리"""
        error_msg: str = f"클립보드 복사 실패: {error}"
        logging.error(error_msg)
        log_user_action("Copy to Clipboard", f"Failed: {error}", False)
        self.status_var.set("Clipboard copy failed")

    def _clear_output(self) -> None:
        """출력 지우기 (성능 최적화됨)"""
        log_user_action("Clear Output button clicked")
        logging.info("Clearing output text")
        
        # 대용량 텍스트 지우기 최적화
        self.output_text.delete(1.0, tk.END)
        
        # 캐시 정리
        self._text_cache.clear()
        
        self.status_var.set(self.text['output_cleared'])
        log_user_action("Clear Output", "Completed")
        logging.info("Output text cleared")

    def _ocr_from_image(self) -> None:
        """이미지에서 텍스트 추출 (성능 최적화됨)"""
        log_user_action("OCR button clicked")
        
        if not self.ocr_processor.is_available():
            self._show_ocr_unavailable_error()
            return
            
        file_path: Optional[str] = self._select_image_file()
        if not file_path:
            log_user_action("OCR", "File selection cancelled", False)
            return
            
        try:
            # 파일 크기 확인
            file_size = Path(file_path).stat().st_size
            if file_size > 10 * 1024 * 1024:  # 10MB
                if not messagebox.askyesno("Large File", 
                                         f"파일 크기가 {file_size // (1024*1024)}MB로 큽니다. 계속하시겠습니까?"):
                    return
            
            self._process_ocr_file(file_path)
        except Exception as e:
            self._handle_ocr_error(str(e))

    def _show_ocr_unavailable_error(self) -> None:
        """OCR 사용 불가 오류 표시"""
        error_msg: str = "OCR functionality is not available. pytesseract or PIL is not installed."
        self.status_var.set(error_msg)
        messagebox.showerror("OCR Error", error_msg)

    def _select_image_file(self) -> Optional[str]:
        """이미지 파일 선택"""
        return filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[
                ("All Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif;*.gif;*.webp"),
                ("PNG Files", "*.png"),
                ("JPEG Files", "*.jpg;*.jpeg"),
                ("All Files", "*.*")
            ]
        )

    def _process_ocr_file(self, file_path: str) -> None:
        """OCR 파일 처리 (성능 최적화됨)"""
        log_user_action("OCR", f"Selected file: {Path(file_path).name}")
        logging.info(f"OCR 처리 시작: {file_path}")
        
        # OCR 처리 (별도 스레드에서 실행)
        def ocr_processing():
            try:
                extracted_text: str = self.ocr_processor.process_image_file(file_path)
                
                # 결과가 너무 크면 경고
                if len(extracted_text) > self.MAX_TEXT_LENGTH:
                    extracted_text = extracted_text[:self.MAX_TEXT_LENGTH]
                    logging.warning(f"OCR result truncated to {self.MAX_TEXT_LENGTH} characters")
                
                # 메인 스레드에서 UI 업데이트
                self.root.after(0, self._update_ocr_result, extracted_text)
                
            except Exception as e:
                self.root.after(0, self._handle_ocr_error, str(e))
        
        # OCR 스레드 시작
        ocr_thread = threading.Thread(target=ocr_processing)
        ocr_thread.daemon = True
        ocr_thread.start()

    def _process_large_text(self, text: str) -> str:
        """대용량 텍스트 배치 처리"""
        batches = self._batch_process_text(text)
        results = []
        
        for i, batch in enumerate(batches):
            logging.info(f"Processing batch {i+1}/{len(batches)}")
            cleaned_lines, _ = self.text_processor.process_text(batch)
            results.extend(cleaned_lines)
        
        return '\n'.join(results)

    def _log_ocr_result(self, extracted_text: str) -> None:
        """OCR 결과 로깅"""
        logging.info("=== OCR 추출 결과 ===")
        logging.info(f"추출된 텍스트 길이: {len(extracted_text)} 문자")
        logging.info("추출된 텍스트 전체 내용:")
        for i, line in enumerate(extracted_text.splitlines(), 1):
            if line.strip():
                logging.info(f"OCR 라인 {i}: {repr(line)}")

    def _update_ocr_result(self, extracted_text: str) -> None:
        """OCR 결과 업데이트"""
        # OCR 결과 상세 로그
        self._log_ocr_result(extracted_text)
        
        # 결과 표시
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, extracted_text)
        
        text_length: int = len(extracted_text)
        log_user_action("OCR completed", f"Extracted text: {text_length} characters")
        self.status_var.set(f"{self.text['ocr_completed']} (이모지 지원)")

    def _handle_ocr_error(self, error: str) -> None:
        """OCR 오류 처리"""
        error_msg: str = f"OCR failed: {error}"
        log_user_action("OCR", f"Error: {error}", False)
        self.status_var.set(error_msg)
        messagebox.showerror("OCR Error", f"Failed to extract text from image: {error}")
    
    def _process_clipboard_image_ocr(self) -> None:
        """클립보드 이미지 자동 OCR 처리"""
        log_user_action("Auto OCR from clipboard image")
        logging.info("=== 클립보드 이미지 자동 OCR 처리 시작 ===")
        
        # UI 상태 업데이트
        self.status_var.set("클립보드 이미지에서 텍스트 추출 중...")
        self.root.update_idletasks()
        
        # 별도 스레드에서 OCR 처리
        def ocr_processing():
            try:
                # 클립보드 이미지에서 텍스트 추출
                extracted_text = self.ocr_processor.process_clipboard_image()
                
                if extracted_text.strip():
                    logging.info(f"OCR 추출 성공: {len(extracted_text)} 문자")
                    logging.info(f"추출된 텍스트 미리보기: {repr(extracted_text[:200])}...")
                    
                    # UI 스레드에서 결과 업데이트
                    self.root.after(0, lambda: self._update_clipboard_ocr_result(extracted_text))
                else:
                    logging.warning("OCR에서 텍스트를 추출할 수 없었습니다")
                    self.root.after(0, lambda: self._handle_clipboard_ocr_no_text())
                    
            except Exception as e:
                error_msg = f"클립보드 이미지 OCR 처리 실패: {e}"
                logging.error(error_msg)
                self.root.after(0, lambda: self._handle_ocr_error(error_msg))
        
        # 백그라운드 스레드에서 실행
        ocr_thread = threading.Thread(target=ocr_processing, daemon=self.THREAD_DAEMON)
        ocr_thread.start()
    
    def _update_clipboard_ocr_result(self, extracted_text: str) -> None:
        """클립보드 OCR 결과를 입력 텍스트에 업데이트"""
        try:
            # 입력 텍스트 영역에 추출된 텍스트 삽입
            self.list_text.delete(1.0, tk.END)
            self.list_text.insert(1.0, extracted_text)
            
            # 숨겨진 입력 텍스트에도 동일하게 삽입
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(1.0, extracted_text)
            
            # 상태 업데이트
            self.status_var.set(f"이미지에서 {len(extracted_text)} 문자 추출 완료")
            
            # 로그 기록
            self._log_ocr_result(extracted_text)
            
            logging.info("클립보드 OCR 결과 입력 텍스트에 업데이트 완료")
            
        except Exception as e:
            error_msg = f"OCR 결과 업데이트 실패: {e}"
            logging.error(error_msg)
            self._handle_ocr_error(error_msg)
    
    def _handle_clipboard_ocr_no_text(self) -> None:
        """클립보드 OCR에서 텍스트를 찾을 수 없는 경우"""
        self.status_var.set("이미지에서 텍스트를 찾을 수 없습니다")
        messagebox.showinfo("OCR 결과", "이미지에서 텍스트를 추출할 수 없었습니다.\n다른 이미지를 시도해보세요.")

    def _upgrade_program(self) -> None:
        """프로그램 업그레이드"""
        log_user_action("Upgrade Program button clicked")
        
        try:
            self._execute_upgrade_manager()
        except Exception as e:
            self._handle_upgrade_error(str(e))

    def _execute_upgrade_manager(self) -> None:
        """업그레이드 매니저 실행"""
        project_root: Path = Path(__file__).parent.parent.parent
        batch_file: Path = project_root / "run_upgrade.bat"
        upgrade_script: Path = project_root / "upgrade_manager.py"
        
        if batch_file.exists():
            cmd: str = f'start cmd /k "cd /d {project_root} && {batch_file}"'
        elif upgrade_script.exists():
            cmd = f'start cmd /k "cd /d {project_root} && py {upgrade_script}"'
        else:
            # 백업 방법: 직접 src/core/upgrade_manager.py 실행
            upgrade_manager_path = project_root / "src" / "core" / "upgrade_manager.py"
            if upgrade_manager_path.exists():
                cmd = f'start cmd /k "cd /d {project_root} && py {upgrade_manager_path} --upgrade-and-restart"'
            else:
                # 최종 백업: 임시 스크립트 파일 생성하여 실행 (개선된 버전)
                temp_script = project_root / "temp_upgrade.py"
                script_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
임시 업그레이드 스크립트
UI에서 업그레이드 매니저를 안전하게 실행하기 위한 임시 파일
"""
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(r"{project_root}")
sys.path.insert(0, str(project_root))

# 로깅 설정
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"temp_upgrade_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

print("[임시 업그레이드 스크립트] 시작...")
logging.info("임시 업그레이드 스크립트 시작")

try:
    from src.core.upgrade_manager import UpgradeManager
    print("[임시 업그레이드 스크립트] 업그레이드 매니저 임포트 성공")
    logging.info("업그레이드 매니저 임포트 성공")
    
    manager = UpgradeManager(None)
    print("[임시 업그레이드 스크립트] 업그레이드 매니저 인스턴스 생성 완료")
    logging.info("업그레이드 매니저 인스턴스 생성 완료")
    
    result = manager.execute_upgrade(auto_upgrade=True)
    print(f"[임시 업그레이드 스크립트] 업그레이드 실행 결과: {{result}}")
    logging.info(f"업그레이드 실행 결과: {{result}}")
    
    if result:
        print("[임시 업그레이드 스크립트] 새 프로그램 실행 시도...")
        launch_result = manager.launch_new_program()
        if launch_result:
            print("[임시 업그레이드 스크립트] 새 프로그램 실행 성공")
            logging.info("새 프로그램 실행 성공")
        else:
            print("[임시 업그레이드 스크립트] 새 프로그램 실행 실패")
            logging.error("새 프로그램 실행 실패")
    else:
        print("[임시 업그레이드 스크립트] 업그레이드 실패")
        logging.error("업그레이드 실패")
        
except Exception as e:
    error_msg = f"업그레이드 실패: {{e}}"
    print(f"[임시 업그레이드 스크립트] {{error_msg}}")
    logging.error(error_msg)
    import traceback
    logging.error(traceback.format_exc())
    
finally:
    print("[임시 업그레이드 스크립트] 종료")
    logging.info("임시 업그레이드 스크립트 종료")
    
    # 임시 파일 삭제
    try:
        os.remove(__file__)
        print("[임시 업그레이드 스크립트] 임시 파일 삭제 완료")
    except Exception as e:
        print(f"[임시 업그레이드 스크립트] 임시 파일 삭제 실패: {{e}}")
'''
                # 임시 스크립트 파일 생성
                with open(temp_script, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                cmd = f'start cmd /k "cd /d {project_root} && py {temp_script}"'
            
        try:
            # 업그레이드 매니저 실행
            subprocess.Popen(cmd, shell=True)
            logging.info("업그레이드 매니저가 새 cmd 창에서 실행되고 현재 창을 닫습니다")
            log_user_action("Upgrade", "업그레이드 매니저 실행됨 (cmd 창)")
            
            # 사용자에게 메시지 표시 (자동으로 닫히도록 설정)
            upgrade_window = messagebox.showinfo("업그레이드", "업그레이드 매니저가 새 창에서 실행됩니다.\n현재 프로그램이 종료됩니다.")
            
            # 1초 후 자동으로 창 닫기 및 프로그램 종료 (더 빠르게)
            self.root.after(1000, self._auto_close_and_exit)
            
        except Exception as e:
            error_msg = f"업그레이드 매니저 실행 실패: {e}"
            logging.error(error_msg)
            log_user_action("Upgrade", f"실행 실패: {error_msg}", False)
            messagebox.showerror("오류", error_msg)

    def _auto_close_and_exit(self) -> None:
        """자동으로 창을 닫고 프로그램 종료"""
        try:
            # 모든 Toplevel 창 닫기
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
            
            # 현재 창 종료
            self.root.destroy()
            
        except Exception as e:
            logging.warning("자동 창 닫기 실패: %s", e)
            # 강제 종료
            try:
                self.root.quit()
            except:
                pass

    def _force_close_upgrade_window(self) -> None:
        """업그레이드 창 강제 닫기"""
        try:
            # 모든 Toplevel 창 닫기
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
        except Exception as e:
            logging.warning("업그레이드 창 강제 닫기 실패: %s", e)

    def _handle_upgrade_error(self, error: str) -> None:
        """업그레이드 오류 처리"""
        logging.error("Upgrade manager execution failed: %s", error)
        log_user_action("Upgrade", f"Execution failed: {error}", False)
        messagebox.showerror("Error", f"Upgrade manager execution failed: {error}")

    def _manage_guidelines(self) -> None:
        """가이드라인 관리 - 편집 창으로 바로 이동"""
        logging.info("Opening guideline editor directly")
        log_user_action("Manage Guidelines", "Guideline editor opened directly")
        
        # 현재 선택된 가이드라인 가져오기
        current_guideline = self.current_guideline or ""
        current_content = ""
        
        # 현재 가이드라인의 내용 가져오기
        if current_guideline and current_guideline in self.guidelines:
            guideline_data = self.guidelines[current_guideline]
            if isinstance(guideline_data, dict):
                rules = guideline_data.get('rules', [])
                current_content = '\n'.join(rules)
        
        # 편집 창으로 바로 이동
        self._show_guideline_editor_with_dropdown("가이드라인 편집", current_guideline, current_content)

    def _create_guideline_management_window(self) -> None:
        """가이드라인 관리 창 생성 (개선된 UX)"""
        # 새 창 생성
        guideline_window = tk.Toplevel(self.root)
        guideline_window.title("가이드라인 관리")
        guideline_window.geometry("700x500")
        guideline_window.resizable(True, True)
        guideline_window.transient(self.root)
        guideline_window.grab_set()
        
        # 메인 프레임
        main_frame = ttk.Frame(guideline_window, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 제목
        title_label = ttk.Label(main_frame, text="가이드라인 관리", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        # 설명
        desc_label = ttk.Label(main_frame, 
                              text="텍스트 정리에 사용할 가이드라인을 관리합니다. 가이드라인은 텍스트 정리 규칙들의 집합입니다.",
                              font=("Arial", 10), foreground="gray")
        desc_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 15))
        
        # 가이드라인 목록 프레임
        list_frame = ttk.LabelFrame(main_frame, text="가이드라인 목록", padding="15")
        list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 20))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 가이드라인 리스트박스 (개선된 스타일)
        self.guideline_listbox = tk.Listbox(
            list_frame, 
            height=12, 
            selectmode=tk.SINGLE,
            font=("Arial", 11),
            activestyle='dotbox',
            selectbackground='#0078d4',
            selectforeground='white'
        )
        self.guideline_listbox.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.guideline_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.guideline_listbox.config(yscrollcommand=scrollbar.set)
        
        # 더블클릭으로 편집
        self.guideline_listbox.bind('<Double-Button-1>', lambda e: self._edit_guideline())
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        # 버튼들 (개선된 스타일)
        new_btn = ttk.Button(button_frame, text="새 가이드라인", 
                            command=self._create_new_guideline, style="Accent.TButton")
        new_btn.pack(side=tk.LEFT, padx=5)
        
        edit_btn = ttk.Button(button_frame, text="편집", 
                             command=self._edit_guideline)
        edit_btn.pack(side=tk.LEFT, padx=5)
        
        delete_btn = ttk.Button(button_frame, text="삭제", 
                               command=self._delete_guideline)
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = ttk.Button(button_frame, text="닫기", 
                              command=guideline_window.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)
        
        # 키보드 단축키
        guideline_window.bind('<Control-n>', lambda e: self._create_new_guideline())
        guideline_window.bind('<Control-e>', lambda e: self._edit_guideline())
        guideline_window.bind('<Delete>', lambda e: self._delete_guideline())
        guideline_window.bind('<Escape>', lambda e: guideline_window.destroy())
        guideline_window.bind('<Key-Escape>', lambda e: guideline_window.destroy())  # 추가 ESC 바인딩
        
        # ESC 키 이벤트를 모든 위젯에 바인딩
        def on_escape(event):
            guideline_window.destroy()
            return "break"
        
        def on_window_close():
            # bind_all 정리
            guideline_window.unbind_all('<Escape>')
            guideline_window.destroy()
        
        guideline_window.bind_all('<Escape>', on_escape)
        self.guideline_listbox.bind('<Escape>', on_escape)
        
        # 창 닫기 이벤트 재정의
        guideline_window.protocol("WM_DELETE_WINDOW", on_window_close)
        
        # 레이아웃 설정
        guideline_window.columnconfigure(0, weight=1)
        guideline_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 가이드라인 목록 로드
        self._load_guideline_list()
        
        # 창 중앙 정렬
        guideline_window.update_idletasks()
        x = (guideline_window.winfo_screenwidth() // 2) - (guideline_window.winfo_width() // 2)
        y = (guideline_window.winfo_screenheight() // 2) - (guideline_window.winfo_height() // 2)
        guideline_window.geometry(f"+{x}+{y}")

    def _load_guideline_list(self) -> None:
        """가이드라인 목록 로드"""
        self.guideline_listbox.delete(0, tk.END)
        for guideline_name in self.guidelines.keys():
            self.guideline_listbox.insert(tk.END, guideline_name)

    def _create_new_guideline(self) -> None:
        """새 가이드라인 생성"""
        self._show_guideline_editor("새 가이드라인", "")

    def _edit_guideline(self) -> None:
        """가이드라인 편집"""
        selection = self.guideline_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "편집할 가이드라인을 선택하세요.")
            return
            
        guideline_name = self.guideline_listbox.get(selection[0])
        guideline_data = self.guidelines.get(guideline_name, {})
        
        # 가이드라인 데이터를 문자열로 변환
        if isinstance(guideline_data, dict):
            rules = guideline_data.get('rules', [])
            guideline_content = '\n'.join(rules)
        else:
            guideline_content = str(guideline_data)
            
        self._show_guideline_editor("가이드라인 편집", guideline_name, guideline_content)

    def _delete_guideline(self) -> None:
        """가이드라인 삭제"""
        selection = self.guideline_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 가이드라인을 선택하세요.")
            return
            
        guideline_name = self.guideline_listbox.get(selection[0])
        
        if messagebox.askyesno("확인", f"가이드라인 '{guideline_name}'을(를) 삭제하시겠습니까?"):
            try:
                self.guideline_manager.delete_guideline(guideline_name)
                self._load_guideline_list()
                self._update_guideline_combo()
                messagebox.showinfo("성공", f"가이드라인 '{guideline_name}'이(가) 삭제되었습니다.")
                log_user_action("Delete Guideline", f"Deleted guideline: {guideline_name}")
            except Exception as e:
                messagebox.showerror("오류", f"가이드라인 삭제 중 오류가 발생했습니다: {e}")

    def _show_guideline_editor(self, title: str, guideline_name: str, content: str = "") -> None:
        """가이드라인 편집기 표시 (개선된 UX)"""
        # 편집 창 생성
        editor_window = tk.Toplevel(self.root)
        editor_window.title(title)
        editor_window.geometry("700x600")
        editor_window.resizable(True, True)
        editor_window.transient(self.root)
        editor_window.grab_set()
        
        # 메인 프레임
        main_frame = ttk.Frame(editor_window, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 제목
        title_label = ttk.Label(main_frame, text=title, font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        # 이름 입력 프레임
        name_frame = ttk.LabelFrame(main_frame, text="가이드라인 이름", padding="10")
        name_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        name_frame.columnconfigure(0, weight=1)
        
        name_var = tk.StringVar(value=guideline_name)
        name_entry = ttk.Entry(name_frame, textvariable=name_var, font=("Arial", 11))
        name_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # 이름 입력 힌트
        name_hint = ttk.Label(name_frame, text="예: 기본 정리, 엄격한 정리, 간단한 정리", 
                             font=("Arial", 9), foreground="gray")
        name_hint.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # 내용 입력 프레임
        content_frame = ttk.LabelFrame(main_frame, text="가이드라인 규칙", padding="10")
        content_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # 내용 입력 영역
        content_text = scrolledtext.ScrolledText(
            content_frame, 
            height=20, 
            width=80,
            font=("Consolas", 10),
            wrap=tk.WORD,
            undo=True
        )
        content_text.grid(row=0, column=0, sticky="nsew")
        
        # 기본 규칙 템플릿
        default_rules = """# 가이드라인 규칙 예시
# 각 줄에 하나의 규칙을 입력하세요
# #으로 시작하는 줄은 주석입니다

Remove empty lines
Remove YouTube links
Trim whitespace
Remove name emojis
Unify date formats
Unify time formats
Convert weekdays
Clean message format
Clean special characters"""
        
        # 내용이 비어있으면 기본 템플릿 표시
        if not content.strip():
            content_text.insert(1.0, default_rules)
            # 기본 템플릿을 힌트로 표시 (회색)
            content_text.tag_configure("hint", foreground="gray")
            content_text.tag_add("hint", "1.0", "end")
        else:
            content_text.insert(1.0, content)
        
        # 내용 입력 힌트
        content_hint = ttk.Label(content_frame, 
                                text="• 각 줄에 하나의 규칙을 입력하세요\n• #으로 시작하는 줄은 주석입니다\n• 규칙은 텍스트 정리 시 순서대로 적용됩니다", 
                                font=("Arial", 9), foreground="gray", justify=tk.LEFT)
        content_hint.grid(row=1, column=0, sticky="w", pady=(10, 0))
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        def clear_hint(event=None):
            """힌트 텍스트 지우기"""
            if content_text.get(1.0, tk.END).strip() == default_rules:
                content_text.delete(1.0, tk.END)
                content_text.config(foreground="black")
        
        def save_guideline():
            new_name = name_var.get().strip()
            new_content = content_text.get(1.0, tk.END).strip()
            
            if not new_name:
                messagebox.showwarning("경고", "가이드라인 이름을 입력하세요.")
                name_entry.focus()
                return
            
            if not new_content or new_content == default_rules:
                messagebox.showwarning("경고", "가이드라인 규칙을 입력하세요.")
                content_text.focus()
                return
                
            try:
                if guideline_name and guideline_name != new_name:
                    # 이름이 변경된 경우 기존 가이드라인 삭제
                    self.guideline_manager.delete_guideline(guideline_name)
                
                # 가이드라인 내용을 규칙 리스트로 변환 (주석 제외)
                lines = new_content.split('\n')
                rules = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        rules.append(line)
                
                if not rules:
                    messagebox.showwarning("경고", "유효한 규칙이 없습니다. 주석이 아닌 규칙을 입력하세요.")
                    content_text.focus()
                    return
                
                # 가이드라인 추가/수정
                if self.guideline_manager.add_guideline(new_name, f"사용자 정의 가이드라인: {new_name}", rules):
                    self.guidelines = self.guideline_manager.guidelines  # 업데이트
                    self._load_guideline_list()
                    self._update_guideline_combo()
                    messagebox.showinfo("성공", f"가이드라인 '{new_name}'이(가) 저장되었습니다.\n\n저장된 규칙: {len(rules)}개")
                    log_user_action("Save Guideline", f"Saved guideline: {new_name} with {len(rules)} rules")
                    editor_window.destroy()
                else:
                    messagebox.showerror("오류", "가이드라인 저장에 실패했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"가이드라인 저장 중 오류가 발생했습니다: {e}")
        
        # 버튼들
        save_btn = ttk.Button(button_frame, text="저장", command=save_guideline, style="Accent.TButton")
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="취소", command=editor_window.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # 키보드 단축키 바인딩
        editor_window.bind('<Control-s>', lambda e: save_guideline())
        editor_window.bind('<Escape>', lambda e: editor_window.destroy())
        editor_window.bind('<Key-Escape>', lambda e: editor_window.destroy())  # 추가 ESC 바인딩
        content_text.bind('<FocusIn>', clear_hint)
        
        # ESC 키 이벤트를 모든 위젯에 바인딩
        def on_escape(event):
            editor_window.destroy()
            return "break"
        
        def on_window_close():
            # bind_all 정리
            editor_window.unbind_all('<Escape>')
            editor_window.destroy()
        
        editor_window.bind_all('<Escape>', on_escape)
        name_entry.bind('<Escape>', on_escape)
        content_text.bind('<Escape>', on_escape)
        
        # 창 닫기 이벤트 재정의
        editor_window.protocol("WM_DELETE_WINDOW", on_window_close)
        
        # 레이아웃 설정
        editor_window.columnconfigure(0, weight=1)
        editor_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 포커스 설정
        if not guideline_name:
            name_entry.focus()
        else:
            content_text.focus()
        
        # 창 중앙 정렬
        editor_window.update_idletasks()
        x = (editor_window.winfo_screenwidth() // 2) - (editor_window.winfo_width() // 2)
        y = (editor_window.winfo_screenheight() // 2) - (editor_window.winfo_height() // 2)
        editor_window.geometry(f"+{x}+{y}")

    def _show_guideline_editor_with_dropdown(self, title: str, guideline_name: str, content: str = "") -> None:
        """가이드라인 편집기 표시 (CRUD 기능 포함)"""
        # 편집 창 생성
        editor_window = tk.Toplevel(self.root)
        editor_window.title(title)
        editor_window.geometry("800x700")
        editor_window.resizable(True, True)
        editor_window.transient(self.root)
        editor_window.grab_set()
        
        # 메인 프레임
        main_frame = ttk.Frame(editor_window, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 제목
        title_label = ttk.Label(main_frame, text=title, font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 20))
        
        # 가이드라인 선택 및 CRUD 프레임
        select_frame = ttk.LabelFrame(main_frame, text="가이드라인 관리", padding="10")
        select_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        select_frame.columnconfigure(1, weight=1)
        
        # 드롭다운
        guideline_var = tk.StringVar(value=guideline_name)
        guideline_combo = ttk.Combobox(
            select_frame,
            textvariable=guideline_var,
            values=list(self.guidelines.keys()) + ["새 가이드라인"],
            state="readonly",
            font=("Arial", 11)
        )
        guideline_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        
        # CRUD 버튼들
        new_btn = ttk.Button(select_frame, text="새로 만들기", command=lambda: on_guideline_selected("새 가이드라인"))
        new_btn.grid(row=0, column=2, padx=(0, 5))
        
        delete_btn = ttk.Button(select_frame, text="삭제", command=lambda: delete_guideline())
        delete_btn.grid(row=0, column=3, padx=(0, 5))
        
        # 내용 입력 프레임
        content_frame = ttk.LabelFrame(main_frame, text="가이드라인 규칙", padding="10")
        content_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 15))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # 내용 입력 영역
        content_text = scrolledtext.ScrolledText(
            content_frame, 
            height=25, 
            width=80,
            font=("Consolas", 10),
            wrap=tk.WORD,
            undo=True
        )
        content_text.grid(row=0, column=0, sticky="nsew")
        
        # 기본 규칙 템플릿
        default_rules = """# 가이드라인 규칙 예시
# 각 줄에 하나의 규칙을 입력하세요
# #으로 시작하는 줄은 주석입니다

Remove empty lines
Remove YouTube links
Trim whitespace
Remove name emojis
Unify date formats
Unify time formats
Convert weekdays
Clean message format
Clean special characters"""
        
        # 내용이 비어있으면 기본 템플릿 표시
        if not content.strip():
            content_text.insert(1.0, default_rules)
            # 기본 템플릿을 힌트로 표시 (회색)
            content_text.tag_configure("hint", foreground="gray")
            content_text.tag_add("hint", "1.0", "end")
        else:
            content_text.insert(1.0, content)
        
        # 내용 입력 힌트
        content_hint = ttk.Label(content_frame, 
                                text="• 각 줄에 하나의 규칙을 입력하세요\n• #으로 시작하는 줄은 주석입니다\n• 규칙은 텍스트 정리 시 순서대로 적용됩니다", 
                                font=("Arial", 9), foreground="gray", justify=tk.LEFT)
        content_hint.grid(row=1, column=0, sticky="w", pady=(10, 0))
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        def clear_hint(event=None):
            """힌트 텍스트 지우기"""
            if content_text.get(1.0, tk.END).strip() == default_rules:
                content_text.delete(1.0, tk.END)
                content_text.config(foreground="black")
        
        def on_guideline_selected(selected=None):
            """가이드라인 선택 이벤트"""
            if selected is None:
                selected = guideline_var.get()
            
            if selected == "새 가이드라인":
                guideline_var.set("새 가이드라인")
                content_text.delete(1.0, tk.END)
                content_text.insert(1.0, default_rules)
                content_text.tag_configure("hint", foreground="gray")
                content_text.tag_add("hint", "1.0", "end")
                delete_btn.config(state="disabled")  # 새 가이드라인은 삭제 불가
            elif selected in self.guidelines:
                guideline_var.set(selected)
                guideline_data = self.guidelines[selected]
                if isinstance(guideline_data, dict):
                    rules = guideline_data.get('rules', [])
                    content_text.delete(1.0, tk.END)
                    content_text.insert(1.0, '\n'.join(rules))
                    content_text.config(foreground="black")
                delete_btn.config(state="normal")  # 기존 가이드라인은 삭제 가능
        
        def delete_guideline():
            """가이드라인 삭제"""
            selected = guideline_var.get()
            if selected == "새 가이드라인" or selected not in self.guidelines:
                messagebox.showwarning("경고", "삭제할 가이드라인을 선택하세요.")
                return
            
            if messagebox.askyesno("확인", f"가이드라인 '{selected}'을(를) 삭제하시겠습니까?"):
                try:
                    self.guideline_manager.delete_guideline(selected)
                    self.guidelines = self.guideline_manager.guidelines
                    self._update_guideline_combo()
                    
                    # 드롭다운 목록 업데이트
                    guideline_combo['values'] = list(self.guidelines.keys()) + ["새 가이드라인"]
                    
                    # 새 가이드라인으로 변경
                    on_guideline_selected("새 가이드라인")
                    
                    messagebox.showinfo("성공", f"가이드라인 '{selected}'이(가) 삭제되었습니다.")
                    log_user_action("Delete Guideline", f"Deleted guideline: {selected}")
                except Exception as e:
                    messagebox.showerror("오류", f"가이드라인 삭제 중 오류가 발생했습니다: {e}")
        
        def save_guideline():
            """가이드라인 저장"""
            selected = guideline_var.get()
            new_content = content_text.get(1.0, tk.END).strip()
            
            if selected == "새 가이드라인":
                # 새 가이드라인 이름 입력 받기
                new_name = self._show_name_input_dialog("새 가이드라인", "가이드라인 이름을 입력하세요:")
                if not new_name:
                    return
                if new_name in self.guidelines:
                    messagebox.showwarning("경고", "이미 존재하는 가이드라인 이름입니다.")
                    return
            else:
                new_name = selected
            
            if not new_content or new_content == default_rules:
                messagebox.showwarning("경고", "가이드라인 규칙을 입력하세요.")
                content_text.focus()
                return
                
            try:
                # 가이드라인 내용을 규칙 리스트로 변환 (주석 제외)
                lines = new_content.split('\n')
                rules = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        rules.append(line)
                
                if not rules:
                    messagebox.showwarning("경고", "유효한 규칙이 없습니다. 주석이 아닌 규칙을 입력하세요.")
                    content_text.focus()
                    return
                
                # 가이드라인 추가/수정
                if self.guideline_manager.add_guideline(new_name, f"사용자 정의 가이드라인: {new_name}", rules):
                    self.guidelines = self.guideline_manager.guidelines  # 업데이트
                    self._update_guideline_combo()  # 메인 창 콤보박스 업데이트
                    
                    # 드롭다운 목록 업데이트
                    guideline_combo['values'] = list(self.guidelines.keys()) + ["새 가이드라인"]
                    guideline_var.set(new_name)
                    
                    messagebox.showinfo("성공", f"가이드라인 '{new_name}'이(가) 저장되었습니다.\n\n저장된 규칙: {len(rules)}개")
                    log_user_action("Save Guideline", f"Saved guideline: {new_name} with {len(rules)} rules")
                else:
                    messagebox.showerror("오류", "가이드라인 저장에 실패했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"가이드라인 저장 중 오류가 발생했습니다: {e}")
        
        # 드롭다운 이벤트 바인딩
        guideline_combo.bind("<<ComboboxSelected>>", lambda e: on_guideline_selected())
        
        # 버튼들
        save_btn = ttk.Button(button_frame, text="저장", command=save_guideline, style="Accent.TButton")
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="취소", command=editor_window.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # 키보드 단축키 바인딩
        editor_window.bind('<Control-s>', lambda e: save_guideline())
        editor_window.bind('<Escape>', lambda e: editor_window.destroy())
        editor_window.bind('<Key-Escape>', lambda e: editor_window.destroy())
        content_text.bind('<FocusIn>', clear_hint)
        
        # ESC 키 이벤트를 모든 위젯에 바인딩
        def on_escape(event):
            editor_window.destroy()
            return "break"
        
        def on_window_close():
            # bind_all 정리
            editor_window.unbind_all('<Escape>')
            editor_window.destroy()
        
        editor_window.bind_all('<Escape>', on_escape)
        content_text.bind('<Escape>', on_escape)
        
        # 창 닫기 이벤트 재정의
        editor_window.protocol("WM_DELETE_WINDOW", on_window_close)
        
        # 레이아웃 설정
        editor_window.columnconfigure(0, weight=1)
        editor_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 포커스 설정
        content_text.focus()
        
        # 초기 상태 설정
        if guideline_name and guideline_name in self.guidelines:
            on_guideline_selected(guideline_name)
        else:
            on_guideline_selected("새 가이드라인")
        
        # 창 중앙 정렬
        editor_window.update_idletasks()
        x = (editor_window.winfo_screenwidth() // 2) - (editor_window.winfo_width() // 2)
        y = (editor_window.winfo_screenheight() // 2) - (editor_window.winfo_height() // 2)
        editor_window.geometry(f"+{x}+{y}")

    def _show_name_input_dialog(self, title: str, message: str) -> Optional[str]:
        """이름 입력 대화상자"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 메인 프레임
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 메시지
        ttk.Label(main_frame, text=message, font=("Arial", 11)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        
        # 입력 필드
        name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=name_var, font=("Arial", 11), width=40)
        name_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        # 버튼들
        ttk.Button(main_frame, text="확인", command=lambda: dialog.quit()).grid(row=2, column=0, padx=(0, 5))
        ttk.Button(main_frame, text="취소", command=lambda: dialog.destroy()).grid(row=2, column=1, padx=(5, 0))
        
        # 레이아웃 설정
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 포커스 설정
        name_entry.focus()
        name_entry.bind('<Return>', lambda e: dialog.quit())
        name_entry.bind('<Escape>', lambda e: dialog.destroy())
        
        # 창 중앙 정렬
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # 대화상자 실행
        dialog.wait_window()
        
        if dialog.winfo_exists():
            result = name_var.get().strip()
            dialog.destroy()
            return result
        return None

    def _on_escape_main(self, event=None) -> None:
        """메인 창 ESC 키 이벤트"""
        logging.info("ESC key pressed in main window")
        self.on_closing()

    def on_closing(self) -> None:
        """프로그램 종료"""
        logging.info("Program termination requested")
        if self.processing:
            if messagebox.askokcancel("Terminate", "Processing in progress. Do you want to terminate?"):
                logging.info("User confirmation for program termination")
                self.root.destroy()
        else:
            logging.info("Program terminated normally")
            self.root.destroy() 

    def _convert_excel_to_list(self, text):
        """엑셀 데이터를 리스트로 변환 (리스트 형식 처리)"""
        lines = []
        
        for row in text.splitlines():
            if not row.strip():
                continue
                
            # 셀 분리 (탭/쉼표)
            if '\t' in row:
                cells = row.split('\t')
            else:
                cells = row.split(',')
            
            # 셀들을 함께 처리
            processed_cells = []
            for cell in cells:
                cell = cell.strip()
                if not cell:
                    continue
                processed_cells.append(cell)
            
            if processed_cells:
                # 셀을 ' | '로 합치기
                line = ' | '.join(processed_cells)
                lines.append(line)
        
        # 자동 번호 매기기
        numbered = [f"{i+1}. {line}" for i, line in enumerate(lines)]
        result = '\n'.join(numbered)
            
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.END, result)

    def _on_paste(self, event=None):
        try:
            pasted = self.root.clipboard_get()
        except Exception:
            return
        if '\t' in pasted or ',' in pasted:
            # 리스트 형식으로 변환
            converted_data = self._convert_excel_to_list_format(pasted)
            self.list_text.delete(1.0, tk.END)
            self.list_text.insert(1.0, converted_data)
            return "break"

    def _on_key_release(self, event=None):
        # 리스트 데이터가 변경되면 자동으로 처리됨
        pass 