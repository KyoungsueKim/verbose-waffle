"""테스트에서 하이픈이 포함된 소스 디렉터리를 import할 수 있게 준비한다."""

from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "verbose-waffle"
sys.path.insert(0, str(SOURCE_ROOT))
