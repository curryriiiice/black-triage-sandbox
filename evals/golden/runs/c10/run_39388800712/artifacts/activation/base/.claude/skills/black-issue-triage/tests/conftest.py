import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parent.parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
