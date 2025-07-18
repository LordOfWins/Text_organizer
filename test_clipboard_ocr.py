#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
클립보드 OCR 기능 테스트 스크립트
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.ocr.ocr_processor import OCRProcessor
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_clipboard_ocr():
    """클립보드 OCR 기능 테스트"""
    print("=== 클립보드 OCR 기능 테스트 ===")
    
    # OCR 프로세서 초기화
    ocr = OCRProcessor()
    
    if not ocr.is_available():
        print("❌ OCR 기능을 사용할 수 없습니다.")
        print("필요한 라이브러리: pytesseract, PIL")
        return
    
    print("✅ OCR 기능 사용 가능")
    
    # 클립보드에서 이미지 확인
    print("\n📋 클립보드에서 이미지 확인 중...")
    image = ocr.get_clipboard_image()
    
    if image is None:
        print("❌ 클립보드에 이미지가 없습니다.")
        print("💡 이미지를 복사한 후 다시 실행하세요.")
        return
    
    print(f"✅ 이미지 감지됨: {image.size[0]}x{image.size[1]} 픽셀")
    
    # OCR 처리
    print("\n🔍 OCR 처리 중...")
    extracted_text = ocr.process_clipboard_image()
    
    if extracted_text.strip():
        print("✅ 텍스트 추출 성공!")
        print(f"📝 추출된 텍스트 ({len(extracted_text)} 문자):")
        print("-" * 50)
        print(extracted_text)
        print("-" * 50)
    else:
        print("❌ 텍스트를 추출할 수 없었습니다.")
        print("💡 다른 이미지를 시도해보세요.")

if __name__ == "__main__":
    test_clipboard_ocr() 