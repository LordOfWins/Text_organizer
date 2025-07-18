#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 기능 테스트 스크립트
"""

import os
import sys
from pathlib import Path

# PIL과 pytesseract import 확인
try:
    from PIL import Image, ImageDraw, ImageFont
    import pytesseract
    print("✓ PIL과 pytesseract 모듈이 정상적으로 import되었습니다.")
except ImportError as e:
    print(f"✗ 모듈 import 실패: {e}")
    sys.exit(1)

def create_test_image():
    """테스트용 이미지 생성"""
    try:
        # 400x200 크기의 흰색 이미지 생성
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # 간단한 텍스트 추가
        test_text = "Hello World\n안녕하세요\n테스트 텍스트"
        
        # 기본 폰트 사용 (폰트가 없는 경우를 대비)
        try:
            # Windows 기본 폰트 시도
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            try:
                # 대체 폰트 시도
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
            except:
                # 기본 폰트 사용
                font = ImageFont.load_default()
        
        # 텍스트 그리기
        draw.text((20, 20), test_text, fill='black', font=font)
        
        # 이미지 저장
        test_image_path = "test_ocr_image.png"
        img.save(test_image_path)
        print(f"✓ 테스트 이미지가 생성되었습니다: {test_image_path}")
        return test_image_path
        
    except Exception as e:
        print(f"✗ 테스트 이미지 생성 실패: {e}")
        return None

def test_ocr(image_path):
    """OCR 테스트"""
    try:
        print(f"OCR 테스트 시작: {image_path}")
        
        # 이미지 로드
        image = Image.open(image_path)
        print(f"이미지 크기: {image.size}")
        print(f"이미지 모드: {image.mode}")
        
        # Tesseract 경로 설정
        tesseract_paths = [
            r"C:\Users\Administrator\Tesseract-OCR\tesseract.exe",
            "tesseract"
        ]
        
        tesseract_found = False
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✓ Tesseract 경로 설정: {path}")
                tesseract_found = True
                break
        
        if not tesseract_found:
            print("✗ Tesseract를 찾을 수 없습니다.")
            return False
        
        # OCR 실행
        print("OCR 실행 중...")
        text = pytesseract.image_to_string(image, lang='kor+eng', config='--psm 6')
        
        print("=" * 50)
        print("OCR 결과:")
        print(text)
        print("=" * 50)
        
        if text.strip():
            print("✓ OCR 성공: 텍스트가 추출되었습니다.")
            return True
        else:
            print("✗ OCR 실패: 텍스트가 추출되지 않았습니다.")
            return False
            
    except Exception as e:
        print(f"✗ OCR 테스트 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("OCR 기능 테스트 시작")
    print("=" * 50)
    
    # 테스트 이미지 생성
    image_path = create_test_image()
    if not image_path:
        return
    
    # OCR 테스트
    success = test_ocr(image_path)
    
    # 결과 정리
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"✓ 테스트 이미지 삭제: {image_path}")
    except:
        pass
    
    if success:
        print("\n✓ OCR 기능이 정상적으로 작동합니다!")
    else:
        print("\n✗ OCR 기능에 문제가 있습니다.")

if __name__ == "__main__":
    main() 