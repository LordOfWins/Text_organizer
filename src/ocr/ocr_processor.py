#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 처리 모듈
이미지에서 텍스트 추출 기능을 담당합니다.
타입 안전성과 오류 처리를 강화했습니다.
"""

import logging
from typing import Optional, List, Union, Any
from pathlib import Path

try:
    import pytesseract  # type: ignore
    PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False
    logging.warning("pytesseract module is not installed. OCR functionality is disabled.")

try:
    from PIL import Image, ImageGrab, ImageEnhance, ImageFilter  # type: ignore
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore
    ImageGrab = None  # type: ignore
    PIL_AVAILABLE = False
    logging.warning("PIL module is not installed. Image processing functionality is disabled.")

# OpenCV와 numpy를 조건부로 import
OPENCV_AVAILABLE = False
cv2_module = None
np_module = None

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    OPENCV_AVAILABLE = True
    cv2_module = cv2
    np_module = np
except ImportError:
    logging.warning("OpenCV module is not installed. Advanced image processing is disabled.")


class OCRProcessor:
    """OCR 처리 클래스 - 타입 안전성 강화"""
    
    def __init__(self):
        self.emoji_chars = self._generate_emoji_chars()
        self.char_whitelist = self._generate_char_whitelist()
        self.config_options = self._generate_config_options()
    
    def _generate_emoji_chars(self) -> str:
        """이모지 문자 범위 생성"""
        emoji_ranges = [
            range(0x1F600, 0x1F650),  # 기본 이모지
            range(0x2600, 0x2700),    # 기상 이모지
            range(0x1F300, 0x1F400),  # 기타 이모지
        ]
        return "".join([chr(i) for r in emoji_ranges for i in r])
    
    def _generate_char_whitelist(self) -> str:
        """문자 화이트리스트 생성"""
        return f"가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9!@#$%^&*()_+-=[]{{}}|;':\",./<>?`~ {self.emoji_chars}"
    
    def _generate_config_options(self) -> List[str]:
        """Tesseract 설정 옵션 생성"""
        return [
            f'--oem 1 --psm 6 -c tessedit_char_whitelist="{self.char_whitelist}" --preserve_interword_spaces=1',
            f'--oem 1 --psm 3 -c tessedit_char_whitelist="{self.char_whitelist}" --preserve_interword_spaces=1',
            f'--oem 1 --psm 11 -c tessedit_char_whitelist="{self.char_whitelist}" --preserve_interword_spaces=1',
            f'--oem 3 --psm 6 -c tessedit_char_whitelist="{self.char_whitelist}" --preserve_interword_spaces=1',
            f'--oem 3 --psm 3 -c tessedit_char_whitelist="{self.char_whitelist}" --preserve_interword_spaces=1'
        ]
    
    def is_available(self) -> bool:
        """OCR 기능 사용 가능 여부 확인"""
        return PYTESSERACT_AVAILABLE and PIL_AVAILABLE
    
    def get_clipboard_image(self) -> Optional[PILImage.Image]:
        """클립보드에서 이미지 가져오기"""
        if not PIL_AVAILABLE or ImageGrab is None:
            return None
        
        try:
            image = ImageGrab.grabclipboard()
            if isinstance(image, PILImage.Image):
                return image
            return None
        except Exception as e:
            logging.error(f"클립보드 이미지 가져오기 실패: {e}")
            return None
    
    def preprocess_image(self, image: PILImage.Image) -> List[PILImage.Image]:
        """이미지 전처리 - 타입 안전성 강화"""
        if not isinstance(image, PILImage.Image):
            return []
        
        img_list: List[PILImage.Image] = []
        
        # 원본 이미지 추가
        img_list.append(image)
        
        # 그레이스케일 변환
        try:
            img_gray = image.convert('L')
            img_list.append(img_gray)
        except Exception as e:
            logging.warning(f"그레이스케일 변환 실패: {e}")
            return img_list

        # OpenCV 이진화 (타입 안전성 강화)
        if OPENCV_AVAILABLE and (cv2_module is not None) and (np_module is not None):
            try:
                img_bin = self._opencv_binarization(img_gray)
                if img_bin is not None and isinstance(img_bin, PILImage.Image):
                    img_list.append(img_bin)
            except Exception as e:
                logging.warning(f"OpenCV 이진화 실패: {e}")
        
        # PIL 기반 이진화 (fallback)
        try:
            img_bin_pil = self._pil_binarization(img_gray)
            if img_bin_pil is not None:
                img_list.append(img_bin_pil)
        except Exception as e:
            logging.warning(f"PIL 이진화 실패: {e}")
        
        # 이미지 향상
        try:
            img_enhanced = self._enhance_image(img_gray)
            if img_enhanced is not None:
                img_list.append(img_enhanced)
        except Exception as e:
            logging.warning(f"이미지 향상 실패: {e}")
        
        # 크기 조정
        img_list = self._resize_images(img_list)
        
        return img_list
    
    def _opencv_binarization(self, img_gray: PILImage.Image) -> Optional[PILImage.Image]:
        """OpenCV를 사용한 이진화 - 타입 안전성 강화"""
        if not OPENCV_AVAILABLE or cv2_module is None or np_module is None:
            return None
        
        try:
            # numpy 배열로 변환
            img_array = np_module.array(img_gray)
            
            # OpenCV 함수들을 안전하게 호출
            if hasattr(cv2_module, 'cvtColor') and hasattr(cv2_module, 'COLOR_GRAY2BGR'):
                img_cv = cv2_module.cvtColor(img_array, cv2_module.COLOR_GRAY2BGR)
            else:
                # OpenCV 함수가 없으면 직접 변환
                img_cv = np_module.stack([img_array] * 3, axis=-1)
            
            if hasattr(cv2_module, 'cvtColor') and hasattr(cv2_module, 'COLOR_BGR2GRAY'):
                img_cv_gray = cv2_module.cvtColor(img_cv, cv2_module.COLOR_BGR2GRAY)
            else:
                img_cv_gray = img_array
            
            # 이진화
            if hasattr(cv2_module, 'threshold'):
                threshold_flag = 0
                if hasattr(cv2_module, 'THRESH_BINARY'):
                    threshold_flag |= cv2_module.THRESH_BINARY
                if hasattr(cv2_module, 'THRESH_OTSU'):
                    threshold_flag |= cv2_module.THRESH_OTSU
                
                _, img_bin = cv2_module.threshold(img_cv_gray, 0, 255, threshold_flag)
                return PILImage.fromarray(img_bin)
            
        except Exception as e:
            logging.warning(f"OpenCV 이진화 처리 중 오류: {e}")
        
        return None
    
    def _pil_binarization(self, img_gray: PILImage.Image) -> Optional[PILImage.Image]:
        """PIL을 사용한 이진화"""
        try:
            if np_module is not None:
                arr = np_module.array(img_gray)
                arr_bin = (arr < 128).astype('uint8') * 255
                return PILImage.fromarray(arr_bin)
        except Exception as e:
            logging.warning(f"PIL 이진화 처리 중 오류: {e}")
        
        return None
    
    def _enhance_image(self, img_gray: PILImage.Image) -> Optional[PILImage.Image]:
        """이미지 향상 처리"""
        try:
            # 대비 향상
            enhancer = ImageEnhance.Contrast(img_gray)
            img_enhanced = enhancer.enhance(2.5)
            
            # 밝기 향상
            brightness_enhancer = ImageEnhance.Brightness(img_enhanced)
            img_bright = brightness_enhancer.enhance(1.3)
            
            # 선명도 향상
            sharpness_enhancer = ImageEnhance.Sharpness(img_bright)
            img_sharp = sharpness_enhancer.enhance(2.0)
            
            # 노이즈 제거
            img_denoised = img_sharp.filter(ImageFilter.MedianFilter(size=3))
            
            return img_denoised
        except Exception as e:
            logging.warning(f"이미지 향상 처리 중 오류: {e}")
            return None
    
    def _resize_images(self, img_list: List[PILImage.Image]) -> List[PILImage.Image]:
        """이미지 크기 조정"""
        resized_list: List[PILImage.Image] = []
        
        for img in img_list:
            try:
                if hasattr(img, 'size') and (img.size[0] < 200 or img.size[1] < 200):
                    scale_factor = max(2, 300 // min(img.size))
                    new_size = (img.size[0] * scale_factor, img.size[1] * scale_factor)
                    resample = getattr(PILImage, 'LANCZOS', getattr(PILImage, 'ANTIALIAS', 1))
                    resized_img = img.resize(new_size, resample)
                    resized_list.append(resized_img)
                else:
                    resized_list.append(img)
            except Exception as e:
                logging.warning(f"이미지 크기 조정 중 오류: {e}")
                resized_list.append(img)
        
        return resized_list
    
    def extract_text_from_images(self, img_list: List[PILImage.Image]) -> str:
        """이미지 리스트에서 텍스트 추출"""
        if not PYTESSERACT_AVAILABLE or pytesseract is None:
            return ""
        
        results: List[str] = []
        
        for img in img_list:
            if not isinstance(img, PILImage.Image):
                continue
            
            for config in self.config_options:
                try:
                    text = pytesseract.image_to_string(
                        img, 
                        lang='kor+eng', 
                        config=config
                    )
                    if text.strip():
                        results.append(text.strip())
                except Exception as e:
                    logging.warning(f"OCR 처리 실패 (config: {config[:50]}...): {e}")
        
        # 가장 긴 결과 반환
        if results:
            return max(results, key=len)
        
        return ""
    
    def process_clipboard_image(self) -> str:
        """클립보드 이미지 처리"""
        if not self.is_available():
            return ""
        
        # 클립보드에서 이미지 가져오기
        image = self.get_clipboard_image()
        if image is None:
            return ""
        
        # 이미지 전처리
        img_list = self.preprocess_image(image)
        if not img_list:
            return ""
        
        # 텍스트 추출
        return self.extract_text_from_images(img_list)
    
    def process_image_file(self, file_path: Union[str, Path]) -> str:
        """이미지 파일 처리"""
        if not self.is_available():
            return ""
        
        try:
            # 이미지 파일 로드
            if Image is None:
                return ""
            image = Image.open(str(file_path))
            if not isinstance(image, PILImage.Image):
                return ""
            
            # 이미지 전처리
            img_list = self.preprocess_image(image)
            if not img_list:
                return ""
            
            # 텍스트 추출
            return self.extract_text_from_images(img_list)
            
        except Exception as e:
            logging.error(f"이미지 파일 처리 실패: {e}")
            return "" 