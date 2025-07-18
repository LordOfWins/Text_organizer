#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텍스트 처리 모듈
text_cleaner의 핵심 텍스트 처리 로직을 담당합니다.
"""

import datetime
import re
from typing import List, Tuple

class TextProcessor:
    """텍스트 처리 클래스"""
    
    def __init__(self):
        self.weekday_map = {
            "월": "Mon", "화": "Tue", "수": "Wed", 
            "목": "Thu", "금": "Fri", "토": "Sat", "일": "Sun"
        }
        
        # 이모지 패턴 통합 (성능 최적화)
        self.emoji_unicode_range = (
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
            r'\U00002702-\U000027B0\U000024C2-\U0001F251\U0001F900-\U0001F9FF\U0001F018-\U0001F270'
            r'\U0001F004\U0001F0CF\U0001F170-\U0001F171\U0001F17E-\U0001F17F\U0001F18E\U0001F191-\U0001F19A'
            r'\U0001F1E6-\U0001F1FF\U0001F201-\U0001F202\U0001F21A\U0001F22F\U0001F232-\U0001F23A'
            r'\U0001F250-\U0001F251\U0001F300-\U0001F321\U0001F324-\U0001F393\U0001F396-\U0001F397'
            r'\U0001F399-\U0001F39B\U0001F39E-\U0001F3F0\U0001F3F3-\U0001F3F5\U0001F3F7-\U0001F3FA'
            r'\U0001F400-\U0001F4FD\U0001F4FF-\U0001F53D\U0001F549-\U0001F54E\U0001F550-\U0001F567'
            r'\U0001F56F-\U0001F570\U0001F573-\U0001F57A\U0001F587\U0001F58A-\U0001F58D\U0001F590'
            r'\U0001F595-\U0001F596\U0001F5A4-\U0001F5A5\U0001F5A8\U0001F5B1-\U0001F5B2\U0001F5BC'
            r'\U0001F5C2-\U0001F5C4\U0001F5D1-\U0001F5D3\U0001F5DC-\U0001F5DE\U0001F5E1\U0001F5E3'
            r'\U0001F5E8\U0001F5EF\U0001F5F3\U0001F5FA-\U0001F64F\U0001F680-\U0001F6C5\U0001F6CB-\U0001F6D2'
            r'\U0001F6D5-\U0001F6D7\U0001F6DD-\U0001F6E5\U0001F6E9\U0001F6EB-\U0001F6EC\U0001F6F0'
            r'\U0001F6F3-\U0001F6F9\U0001F6FB-\U0001F6FC\U0001F7E0-\U0001F7EB\U0001F7F0\U0001F90C-\U0001F93A'
            r'\U0001F93C-\U0001F945\U0001F947-\U0001F970\U0001F973-\U0001F976\U0001F97A\U0001F97C-\U0001F9A2'
            r'\U0001F9B0-\U0001F9B9\U0001F9C0-\U0001F9C2\U0001F9D0-\U0001F9FF\U00002600-\U000026FF'
            r'\U00002B00-\U00002BFF\U00002300-\U000023FF\U00002000-\U0000206F\U0001F000-\U0001F02F'
            r'\U0001F0A0-\U0001F0FF\U0001F100-\U0001F64F\U0001F910-\U0001F96B\U0001F980-\U0001F9E0]'
        )
        
        # 컴파일된 패턴들 (성능 최적화)
        self.name_emoji_pattern = re.compile(
            rf'^([가-힣a-zA-Z0-9]+)({self.emoji_unicode_range}+)'
        )
        
        # 날짜 패턴들 (더 포괄적으로 개선)
        self.date_patterns = [
            # 2025년 6월 2일 → 2025/06/02
            (re.compile(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일'), 
             lambda m: f"{m.group(1)}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"),
            
            # 2025. 6. 2. → 2025/06/02
            (re.compile(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?'), 
             lambda m: f"{m.group(1)}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"),
            
            # 2025.6.2 → 2025/06/02 (공백 없음)
            (re.compile(r'(\d{4})\.(\d{1,2})\.(\d{1,2})'), 
             lambda m: f"{m.group(1)}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"),
            
            # 25. 6. 2 → 2025/06/02 (2자리 연도)
            (re.compile(r'(\d{2})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?'), 
             lambda m: f"20{m.group(1)}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"),
            
            # 25.6.2 → 2025/06/02 (2자리 연도, 공백 없음)
            (re.compile(r'(\d{2})\.(\d{1,2})\.(\d{1,2})'), 
             lambda m: f"20{m.group(1)}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"),
        ]
        
        # 시간 패턴들
        self.time_patterns = [
            # AM/PM이 있는 시간
            re.compile(r'(?<!\d)(\d{1,2}:\d{2}\s*[AP]M)(?!\d)'),
            # 일반 시간
            re.compile(r'(?<!\d)(\d{1,2}:\d{2}(?: ?[AP]M)?)(?!\d)')
        ]
        
        # 요일 시간 → 시간 요일 변환 패턴
        self.weekday_time_pattern = re.compile(r'([월화수목금토일])요일\s*(\d{1,2}:\d{2}\s*[AP]M)')
        
        # 유튜브 링크 패턴
        self.youtube_pattern = re.compile(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+')
        
        # 날짜 슬래시 패턴 (이미 변환된 날짜 확인용)
        self.date_slash_pattern = re.compile(r'\d{4}/\d{2}/\d{2}')

    def process_date_formats(self, text: str) -> str:
        """다양한 날짜 형식을 표준 형식으로 변환"""
        processed_text = text
        
        for pattern, replacement_func in self.date_patterns:
            processed_text = pattern.sub(replacement_func, processed_text)
        
        return processed_text

    def process_time_formats(self, text: str) -> str:
        """시간 형식을 처리하고 오늘 날짜 추가"""
        today_str = datetime.datetime.now().strftime("%Y/%m/%d")
        processed_text = text
        
        # 오전/오후 변환
        processed_text = re.sub(r'오전', 'AM', processed_text)
        processed_text = re.sub(r'오후', 'PM', processed_text)
        
        # 요일 시간 → 시간 요일 변환
        processed_text = self.weekday_time_pattern.sub(
            lambda m: f"{m.group(2)} {self.weekday_map[m.group(1)]}", 
            processed_text
        )
        
        # AM/PM이 있는 시간에 오늘 날짜 추가
        for time_pattern in self.time_patterns:
            if re.search(time_pattern, processed_text) and not self.date_slash_pattern.search(processed_text):
                time_match = re.search(time_pattern, processed_text)
                if time_match:
                    time_part = time_match.group(1)
                    processed_text = re.sub(time_pattern, f"{today_str} {time_part}", processed_text)
        
        return processed_text

    def remove_youtube_links(self, text: str) -> Tuple[str, int]:
        """유튜브 링크 제거"""
        links_removed = len(re.findall(self.youtube_pattern, text))
        cleaned_text = re.sub(self.youtube_pattern, '', text)
        return cleaned_text, links_removed

    def remove_name_emojis(self, text: str) -> str:
        """이름 뒤의 이모지도 포함하여 아무것도 제거하지 않음(이모지 보존)"""
        return text

    def clean_line(self, line: str) -> str:
        """개별 라인 정리"""
        if not line.strip():
            return ""
        
        # 기본 정리
        cleaned_line = re.sub(r'[\[\]\(\)]', '', line)
        
        # 날짜 형식 처리
        cleaned_line = self.process_date_formats(cleaned_line)
        
        # 시간 형식 처리
        cleaned_line = self.process_time_formats(cleaned_line)
        
        # 유튜브 링크 제거
        cleaned_line, _ = self.remove_youtube_links(cleaned_line)
        
        # 이름 이모지 제거
        cleaned_line = self.remove_name_emojis(cleaned_line)
        
        # 추가 정리
        if cleaned_line.strip():
            cleaned_line = re.sub(r' +', ' ', cleaned_line)
            cleaned_line = cleaned_line.replace("보낸 메시지", "나")
            cleaned_line = cleaned_line.replace("이 회원님에게 보낸 답장", "의")
        
        return cleaned_line

    def process_text(self, text: str) -> Tuple[List[str], int]:
        """전체 텍스트 처리"""
        lines = text.splitlines()
        cleaned_lines = []
        total_youtube_links_removed = 0
        
        for line in lines:
            if not line.strip():
                continue
            
            # 유튜브 링크 개수 확인
            _, links_removed = self.remove_youtube_links(line)
            total_youtube_links_removed += links_removed
            
            # 라인 정리
            cleaned_line = self.clean_line(line)
            if cleaned_line.strip():
                cleaned_lines.append(cleaned_line)
        
        return cleaned_lines, total_youtube_links_removed 