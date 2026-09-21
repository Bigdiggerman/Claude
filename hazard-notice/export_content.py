"""Dump content.py to content.json so build_docx.js reads the same wording."""
import json
from pathlib import Path

import content as C

data = {k: getattr(C, k) for k in dir(C) if k.isupper()}
out = Path(__file__).resolve().parent / "content.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("JSON ->", out)
