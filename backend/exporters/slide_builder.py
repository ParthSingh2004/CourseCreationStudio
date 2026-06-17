"""
slide_builder.py
================
Python entry-point that delegates to slide_builder.js (PptxGenJS).
 
The public API is unchanged:
    build_slides(course: GeneratedCourse) -> str   # returns output path
 
Why a JS backend?
-----------------
python-pptx's low-level OOXML manipulation (custom Part objects, direct XML
injection for audio timing, transparent-PNG image hacks) produced structurally
invalid .pptx files that PowerPoint refused to open.
 
PptxGenJS (Node.js) generates spec-compliant OOXML natively; we post-process
the file with JSZip only for the narrow case of injecting auto-play timing XML
into slides that have embedded audio — a surgical, well-scoped change.
"""
 
import json
import os
import subprocess
import sys
import tempfile
 
from models.schemas import GeneratedCourse
from config import Config
 
# Absolute path to the JS builder (same directory as this file)
_JS_BUILDER = os.path.join(os.path.dirname(__file__), "slide_builder.js")
 
 
def build_slides(course: GeneratedCourse) -> str:
    """
    Build a .pptx for *course* and return the output file path.
 
    Serialises the course to a temporary JSON file, calls Node.js, then
    cleans up.  Raises RuntimeError if the Node process exits non-zero.
    """
    print(f"\n[slide_builder] ═══ Building slides for course '{course.course_id}' ═══")
 
    # ── Serialise course to a temp JSON file ──────────────────────────────
    course_dict = course.model_dump()   # Pydantic v2; use .dict() for v1
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(course_dict, tmp, default=str)
        tmp_json_path = tmp.name
 
    output_path = os.path.join(Config.SLIDES_OUTPUT_DIR, f"{course.course_id}.pptx")
    os.makedirs(Config.SLIDES_OUTPUT_DIR, exist_ok=True)
 
    try:
        # ── Invoke Node.js builder ─────────────────────────────────────────
        cmd = [
            "node",
            _JS_BUILDER,
            tmp_json_path,
            output_path,
            Config.IMAGE_OUTPUT_DIR,   # imageDir argument
        ]
        print(f"[slide_builder] Running: {' '.join(cmd)}")
 
        result = subprocess.run(
            cmd,
            capture_output=False,   # let Node's stdout/stderr pass through
            text=True,
        )
 
        if result.returncode != 0:
            raise RuntimeError(
                f"slide_builder.js exited with code {result.returncode}"
            )
 
        if not os.path.exists(output_path):
            raise RuntimeError(f"Output file not found after build: {output_path}")
 
        print(f"[slide_builder] ✓ Saved to {output_path}\n")
        return output_path
 
    finally:
        try:
            os.unlink(tmp_json_path)
        except OSError:
            pass
 