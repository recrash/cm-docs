"""
로깅 설정 모듈

구조화된 로깅 시스템을 제공합니다.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from .config_loader import get_config


def setup_logger(
    name: str = "ts_cli",
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    console_output: bool = True,
) -> logging.Logger:
    """
    로거 설정

    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로
        console_output: 콘솔 출력 여부

    Returns:
        설정된 로거 인스턴스
    """
    logger = logging.getLogger(name)

    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()

    # 설정에서 로그 레벨과 포맷 가져오기
    try:
        config = get_config()
        if level is None:
            level = config.get("logging", "level", "INFO")
        log_format = config.get(
            "logging", "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_enabled = config.get("logging", "file_enabled", False, bool)
        if log_file is None and file_enabled:
            log_file_path = config.get("logging", "file_path", "ts-cli.log")
            log_file = Path(log_file_path)
    except Exception:
        # 설정 로드 실패시 기본값 사용
        level = level or "INFO"
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        file_enabled = False

    # 로그 레벨 설정
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # 포매터 생성
    formatter = logging.Formatter(log_format)

    # 콘솔 핸들러 설정
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)

        # 콘솔용 컬러 포매터 (rich가 있는 경우)
        try:
            from rich.logging import RichHandler

            rich_handler = RichHandler(
                show_time=True, show_path=False, enable_link_path=False, markup=True
            )
            rich_handler.setLevel(numeric_level)
            logger.addHandler(rich_handler)
        except ImportError:
            # rich가 없으면 기본 핸들러 사용
            logger.addHandler(console_handler)

    # 파일 핸들러 설정
    if log_file:
        try:
            # 로그 디렉토리 생성
            log_file.parent.mkdir(parents=True, exist_ok=True)

            # 회전 파일 핸들러 사용 (최대 10MB, 5개 파일)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            # 파일 핸들러 설정 실패시 경고 출력
            logger.warning(f"파일 로그 핸들러 설정 실패: {e}")

    return logger


def get_logger(name: str = "ts_cli") -> logging.Logger:
    """
    로거 인스턴스 반환

    Args:
        name: 로거 이름

    Returns:
        로거 인스턴스
    """
    logger = logging.getLogger(name)

    # 로거가 아직 설정되지 않았으면 기본 설정 적용
    if not logger.handlers:
        return setup_logger(name)

    return logger


def set_log_level(level: str, logger_name: str = "ts_cli") -> None:
    """
    로그 레벨 동적 변경

    Args:
        level: 새로운 로그 레벨
        logger_name: 로거 이름
    """
    logger = logging.getLogger(logger_name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(numeric_level)

    # 모든 핸들러의 레벨도 변경
    for handler in logger.handlers:
        handler.setLevel(numeric_level)


class LoggerMixin:
    """
    로거 믹스인 클래스

    클래스에서 쉽게 로깅을 사용할 수 있도록 하는 믹스인입니다.
    """

    @property
    def logger(self) -> logging.Logger:
        """로거 인스턴스 반환"""
        return get_logger(f"{__package__}.{self.__class__.__name__}")


def configure_third_party_loggers() -> None:
    """
    서드파티 라이브러리 로거 설정

    httpx, urllib3 등의 서드파티 라이브러리 로그 레벨을 조정합니다.
    """
    # HTTP 관련 로거들의 레벨을 WARNING으로 설정 (너무 verbose하지 않도록)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Git 관련 명령어 출력은 DEBUG 레벨로
    logging.getLogger("subprocess").setLevel(logging.WARNING)


# 모듈 로드시 서드파티 로거 설정
configure_third_party_loggers()
