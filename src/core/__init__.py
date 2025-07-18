"""
Core business logic package
핵심 비즈니스 로직 모듈들
"""

try:
    from .text_processor import TextProcessor
except ImportError as e:
    raise ImportError("Failed to import TextProcessor from text_processor module. Please ensure 'src/core/text_processor.py' exists and is error-free.") from e

try:
    from .guideline_manager import GuidelineManager
except ImportError as e:
    raise ImportError("Failed to import GuidelineManager from guideline_manager module. Please ensure 'src/core/guideline_manager.py' exists and is error-free.") from e

try:
    from .upgrade_manager import UpgradeManager
except ImportError as e:
    raise ImportError("Failed to import UpgradeManager from upgrade_manager module. Please ensure 'src/core/upgrade_manager.py' exists and is error-free.") from e

__all__ = ['TextProcessor', 'GuidelineManager', 'UpgradeManager']