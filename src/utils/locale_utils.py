#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다국어 지원 유틸리티
UI 텍스트 및 로케일 관리를 담당합니다.
"""

import locale
from typing import Dict, Any, Optional


# 다국어 UI 리소스
UI_TEXT: Dict[str, Dict[str, str]] = {
    'ko': {
        'title': '텍스트 클리너 v2.0',
        'clean_btn': '텍스트 정리',
        'copy_btn': '클립보드 복사',
        'clear_btn': '입력 지우기',
        'clear_output_btn': '출력 지우기',
        'ocr_btn': '이미지에서 텍스트 추출',
        'upgrade_btn': '프로그램 업그레이드',
        'input_hint': '여기에 정리할 텍스트를 입력하세요...',
        'status_ready': '준비됨 - 텍스트 입력 후 "텍스트 정리" 클릭',
        'manage_guidelines': '가이드라인 관리',
        'guideline': '가이드라인:',
        'output_label': '정리된 출력 텍스트',
        'input_label': '입력 텍스트',
        'warning_no_text': '입력할 텍스트가 없습니다.',
        'warning_no_content': '복사할 내용이 없습니다.',
        'success_guideline_save': "가이드라인 '{name}'이(가) 저장되었습니다.",
        'success_guideline_delete': "가이드라인 '{name}'이(가) 삭제되었습니다.",
        'confirm_delete_guideline': "정말로 가이드라인 '{name}'을(를) 삭제하시겠습니까?",
        'select_guideline': "가이드라인 '{name}'이(가) 선택되었습니다.",
        'ocr_completed': 'OCR 완료: 텍스트 추출됨',
        'clipboard_copied': '클립보드에 복사되었습니다.',
        'input_cleared': '입력 텍스트가 지워졌습니다.',
        'output_cleared': '출력 텍스트가 지워졌습니다.',
        'error': '오류',
        'warning': '경고',
        'success': '성공',
        'close': '닫기',
    },
    'en': {
        'title': 'Text Cleaner v2.0',
        'clean_btn': 'Clean Text',
        'copy_btn': 'Copy to Clipboard',
        'clear_btn': 'Clear Input',
        'clear_output_btn': 'Clear Output',
        'ocr_btn': 'Extract Text from Image',
        'upgrade_btn': 'Upgrade Program',
        'input_hint': 'Enter the text to clean here...',
        'status_ready': 'Ready - Enter text and click "Clean Text"',
        'manage_guidelines': 'Manage Guidelines',
        'guideline': 'Guideline:',
        'output_label': 'Cleaned Output Text',
        'input_label': 'Input Text',
        'warning_no_text': 'No text to input.',
        'warning_no_content': 'No content to copy.',
        'success_guideline_save': "Guideline '{name}' saved.",
        'success_guideline_delete': "Guideline '{name}' deleted.",
        'confirm_delete_guideline': "Are you sure you want to delete guideline '{name}'?",
        'select_guideline': "Guideline '{name}' selected.",
        'ocr_completed': 'OCR completed: Text extracted',
        'clipboard_copied': 'Text copied to clipboard',
        'input_cleared': 'Input text cleared',
        'output_cleared': 'Output text cleared',
        'error': 'Error',
        'warning': 'Warning',
        'success': 'Success',
        'close': 'Close',
    }
}


def get_system_language() -> str:
    """시스템 언어 감지"""
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang.startswith('en'):
            return 'en'
        else:
            return 'ko'
    except Exception:
        # locale 모듈 오류 시 기본값 반환
        return 'ko'


def get_ui_text(lang: Optional[str] = None) -> Dict[str, str]:
    """UI 텍스트 반환"""
    if lang is None:
        lang = get_system_language()
    
    return UI_TEXT.get(lang, UI_TEXT['ko'])


def format_ui_text(key: str, **kwargs: Any) -> str:
    """UI 텍스트 포맷팅"""
    lang = get_system_language()
    text = UI_TEXT.get(lang, UI_TEXT['ko']).get(key, key)
    
    try:
        return text.format(**kwargs)
    except (KeyError, ValueError):
        return text 