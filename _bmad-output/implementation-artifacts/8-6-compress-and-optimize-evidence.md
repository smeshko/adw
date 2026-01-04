# Story 8.6: Compress and Optimize Evidence

Status: ready-for-dev
Linear Issue: not-configured
Epic: 8 - Evidence Gathering
Created: 2026-01-03

---

## Story

As a developer,
I want captured evidence compressed,
so that storage and transfer are efficient.

## Acceptance Criteria

**Given** evidence directory with screenshots
**When** optimization runs
**Then** images are compressed (lossy acceptable for screenshots)

**Given** large terminal outputs
**When** optimization runs
**Then** they're truncated or summarized if over threshold

**Given** all evidence
**When** run completes
**Then** total size is logged for monitoring

**Given** evidence optimization
**When** configured
**Then** max sizes are respected per file type

## Tasks / Subtasks

### Task 1: Create Optimization Models (models/evidence.py)
- [x] Create `OptimizationConfig` model with max sizes per type
- [x] Create `OptimizationResult` model with before/after sizes
- [x] Create `FileOptimization` model for individual file results
- [x] Export from `models/__init__.py`

### Task 2: Implement Image Compression (evidence/optimizer.py)
- [x] Create `EvidenceOptimizer` class
- [x] Implement PNG compression using Pillow
- [x] Support quality settings (lossy acceptable)
- [x] Handle missing Pillow gracefully (skip optimization)

### Task 3: Implement Text Truncation
- [x] Implement truncation for CLI output files
- [x] Preserve head and tail of truncated files
- [x] Add truncation marker with original size
- [x] Configurable max size threshold (default: 100KB)

### Task 4: Implement JSON Minification
- [x] Minify JSON files (remove whitespace)
- [x] Option to keep pretty-printed manifest
- [x] Calculate size savings

### Task 5: Implement Size Monitoring
- [x] Calculate total evidence directory size
- [x] Calculate per-type size breakdown
- [x] Log summary to console via LogManager
- [x] Emit warning if over configurable threshold

### Task 6: Implement Config-Based Settings
- [x] Read optimization config from `.adw/project.yaml`
- [x] Support configuration format:
  ```yaml
  evidence:
    optimization:
      enabled: true
      max_image_size_kb: 500
      max_text_size_kb: 100
      image_quality: 80
      compress_json: true
      warn_total_size_mb: 10
  ```
- [x] Apply sensible defaults when not configured

### Task 7: Integrate with Verify Phase
- [ ] Run optimization after manifest generation
- [ ] Update manifest with optimized file sizes
- [ ] Store optimization results in RunContext
- [ ] Log total size and savings summary

### Task 8: Write Unit Tests
- [ ] Test image compression (mock Pillow)
- [ ] Test text truncation logic
- [ ] Test JSON minification
- [ ] Test size calculation
- [ ] Test config loading and defaults
- [ ] Test warning threshold

---

## Relevant Feature Documentation

**From Architecture (Evidence Gathering):**
Evidence files (screenshots, API responses, logs) can grow large. Compression ensures efficient storage and transfer while maintaining usability.

---

## Developer Context

### Technical Requirements

**From Epic 8.6 Acceptance Criteria:**
- Images compressed (lossy acceptable for screenshots)
- Large text files truncated or summarized
- Total size logged for monitoring
- Max sizes configurable per file type

**From NFR Requirements:**
- NFR3: Non-blocking artifact writes (optimization can be async)
- NFR14: Keep logs/evidence under reasonable size limits

### Architecture Compliance

**Module Location:** `src/adw/evidence/`

**Files to Create/Modify:**
```
src/adw/evidence/
├── __init__.py          # Package exports (update)
├── detector.py          # From Story 8.1
├── cli_capture.py       # From Story 8.2
├── web_capture.py       # From Story 8.3
├── api_capture.py       # From Story 8.4
├── manifest.py          # From Story 8.5
└── optimizer.py         # Evidence optimization (NEW)

src/adw/models/
└── evidence.py          # Add optimization models (MODIFY)
```

**Evidence Structure After Optimization:**
```
.adw/runs/<run_id>/
└── evidence/
    ├── cli/
    │   ├── version.txt          # Possibly truncated
    │   └── summary.json         # Minified
    ├── screenshots/
    │   ├── home_desktop.png     # Compressed
    │   └── metadata.json        # Minified
    ├── api/
    │   ├── health.json          # Minified
    │   └── summary.json         # Minified
    ├── manifest.json            # Pretty-printed (kept readable)
    └── optimization_report.json # NEW: Optimization results
```

**Dependencies:**
- Pillow (optional) for image compression
- pathlib for file operations (stdlib)
- json for JSON handling (stdlib)

**Integration Points:**
- Runs after manifest generation (Story 8.5)
- Updates file sizes in manifest
- Logs summary via LogManager (Epic 7)

### Library & Framework Requirements

**Pillow Image Compression:**
```python
# Optional import with graceful fallback
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

def compress_image(
    input_path: Path,
    output_path: Path | None = None,
    quality: int = 80,
    max_size_kb: int = 500,
) -> FileOptimization:
    """Compress PNG/JPEG image.

    Args:
        input_path: Path to source image
        output_path: Path for compressed image (default: overwrite input)
        quality: JPEG quality (1-100), or PNG compression level
        max_size_kb: Target maximum size in KB

    Returns:
        FileOptimization with before/after sizes
    """
    if not PILLOW_AVAILABLE:
        return FileOptimization(
            path=str(input_path),
            optimized=False,
            reason="Pillow not installed",
        )

    output_path = output_path or input_path
    original_size = input_path.stat().st_size

    with Image.open(input_path) as img:
        # Convert RGBA to RGB for JPEG compression
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        # Save with compression
        img.save(output_path, optimize=True, quality=quality)

    new_size = output_path.stat().st_size

    return FileOptimization(
        path=str(input_path),
        optimized=True,
        original_size=original_size,
        optimized_size=new_size,
        savings_bytes=original_size - new_size,
        savings_percent=round((1 - new_size / original_size) * 100, 1),
    )
```

**Text Truncation:**
```python
def truncate_text_file(
    path: Path,
    max_size_kb: int = 100,
    keep_head_lines: int = 500,
    keep_tail_lines: int = 500,
) -> FileOptimization:
    """Truncate large text files, preserving head and tail.

    Args:
        path: Path to text file
        max_size_kb: Maximum file size in KB
        keep_head_lines: Number of lines to keep from start
        keep_tail_lines: Number of lines to keep from end

    Returns:
        FileOptimization with details
    """
    original_size = path.stat().st_size
    max_size_bytes = max_size_kb * 1024

    if original_size <= max_size_bytes:
        return FileOptimization(
            path=str(path),
            optimized=False,
            reason="Under size threshold",
            original_size=original_size,
        )

    content = path.read_text()
    lines = content.split('\n')
    total_lines = len(lines)

    if total_lines <= keep_head_lines + keep_tail_lines:
        return FileOptimization(
            path=str(path),
            optimized=False,
            reason="Not enough lines to truncate",
            original_size=original_size,
        )

    # Build truncated content
    head = '\n'.join(lines[:keep_head_lines])
    tail = '\n'.join(lines[-keep_tail_lines:])
    truncated_count = total_lines - keep_head_lines - keep_tail_lines

    truncated_content = f"""{head}

... [{truncated_count} lines truncated - original size: {original_size:,} bytes] ...

{tail}"""

    path.write_text(truncated_content)
    new_size = path.stat().st_size

    return FileOptimization(
        path=str(path),
        optimized=True,
        original_size=original_size,
        optimized_size=new_size,
        savings_bytes=original_size - new_size,
        truncated_lines=truncated_count,
    )
```

**JSON Minification:**
```python
import json

def minify_json_file(path: Path) -> FileOptimization:
    """Minify JSON file by removing whitespace."""
    original_size = path.stat().st_size

    with open(path) as f:
        data = json.load(f)

    minified = json.dumps(data, separators=(',', ':'))
    path.write_text(minified)

    new_size = path.stat().st_size

    return FileOptimization(
        path=str(path),
        optimized=True,
        original_size=original_size,
        optimized_size=new_size,
        savings_bytes=original_size - new_size,
    )
```

**Pydantic Models:**
```python
from pydantic import BaseModel, Field
from datetime import datetime

class OptimizationConfig(BaseModel):
    """Configuration for evidence optimization."""
    enabled: bool = True
    max_image_size_kb: int = 500
    max_text_size_kb: int = 100
    image_quality: int = 80
    compress_json: bool = True
    keep_manifest_pretty: bool = True
    warn_total_size_mb: int = 10

class FileOptimization(BaseModel):
    """Result of optimizing a single file."""
    path: str
    optimized: bool
    reason: str | None = None
    original_size: int | None = None
    optimized_size: int | None = None
    savings_bytes: int | None = None
    savings_percent: float | None = None
    truncated_lines: int | None = None

class OptimizationReport(BaseModel):
    """Complete optimization report for a run."""
    run_id: str
    optimized_at: datetime = Field(default_factory=datetime.now)

    # Summary statistics
    total_files: int
    files_optimized: int
    files_skipped: int

    # Size metrics
    original_total_bytes: int
    optimized_total_bytes: int
    total_savings_bytes: int
    total_savings_percent: float

    # Breakdown by type
    image_optimization: list[FileOptimization] = Field(default_factory=list)
    text_optimization: list[FileOptimization] = Field(default_factory=list)
    json_optimization: list[FileOptimization] = Field(default_factory=list)

    # Warnings
    size_warning: bool = False
    warning_threshold_mb: int | None = None
```

### File Structure Requirements

**Optimization Report Format (optimization_report.json):**
```json
{
  "run_id": "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
  "optimized_at": "2026-01-03T10:31:00Z",

  "total_files": 12,
  "files_optimized": 8,
  "files_skipped": 4,

  "original_total_bytes": 5242880,
  "optimized_total_bytes": 2097152,
  "total_savings_bytes": 3145728,
  "total_savings_percent": 60.0,

  "image_optimization": [
    {
      "path": "screenshots/home_desktop.png",
      "optimized": true,
      "original_size": 1048576,
      "optimized_size": 262144,
      "savings_bytes": 786432,
      "savings_percent": 75.0
    }
  ],

  "text_optimization": [
    {
      "path": "cli/large_output.txt",
      "optimized": true,
      "original_size": 524288,
      "optimized_size": 102400,
      "truncated_lines": 5000
    }
  ],

  "json_optimization": [
    {
      "path": "api/health.json",
      "optimized": true,
      "original_size": 2048,
      "optimized_size": 512,
      "savings_bytes": 1536
    }
  ],

  "size_warning": false
}
```

**Truncated Text Format:**
```
[First 500 lines preserved]

... [12,345 lines truncated - original size: 5,242,880 bytes] ...

[Last 500 lines preserved]
```

### Testing Requirements

**Test File Structure:**
```
tests/unit/evidence/
├── __init__.py
├── test_detector.py
├── test_cli_capture.py
├── test_web_capture.py
├── test_api_capture.py
├── test_manifest.py
├── test_optimizer.py      # Optimization tests (NEW)
└── fixtures/
    ├── large_text.txt     # Test truncation
    ├── sample_image.png   # Test compression
    └── sample.json        # Test minification
```

**Testing Patterns:**
- Test image compression (mock Pillow if needed)
- Test text truncation with various sizes
- Test JSON minification
- Test size calculation and warnings
- Use `tmp_path` for test files
- Test Pillow-not-installed fallback

**Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 8.5 (Manifest):**
- Manifest lists all evidence files
- Use manifest to iterate files for optimization
- Update manifest with optimized sizes

**From Story 8.2-8.4 (Evidence Capture):**
- CLI: Text files may need truncation
- Web: Screenshots need compression
- API: JSON files need minification

**From Epic 7 (Observability & Logging):**
- Use LogManager for optimization summary logging
- Log total size, savings, warnings

---

## Git Intelligence

Recent commits show patterns for:
- Optional dependency handling (try/import)
- File operations with pathlib
- Size calculation and formatting

---

## Latest Technical Information

**Pillow 10.2+ (Latest):**
```python
from PIL import Image

# PNG optimization
img.save(path, format='PNG', optimize=True)

# JPEG with quality
img.save(path, format='JPEG', quality=80, optimize=True)

# WebP (modern, smaller)
img.save(path, format='WEBP', quality=80)
```

**File Size Formatting:**
```python
def format_size(bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(bytes) < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/` - NO exceptions
- Use structured logging with context fields
- Full type annotations required
- Graceful degradation for optional dependencies

---

## Dev Notes

- Pillow is OPTIONAL - gracefully skip image optimization if not installed
- Don't optimize manifest.json - keep it human-readable
- Truncation should preserve diagnostic value (head + tail)
- Log warnings for unexpectedly large evidence directories
- Consider async optimization for non-blocking behavior

### Project Structure Notes

- Add `optimizer.py` to `evidence/` package
- Update `evidence.py` models with optimization types
- Optimization report saved alongside manifest
- Consider adding `[optimization]` optional dependency group

### References

- [Source: _bmad-output/architecture.md] - NFR requirements
- [Source: _bmad-output/epics/epic-8-evidence-gathering.md#Story-8.6] - Story definition
- [Source: _bmad-output/project-context.md] - Implementation rules
- [Source: https://pillow.readthedocs.io/] - Pillow documentation

---

## Dependencies

- **Depends On:** Story 8.2, Story 8.3, Story 8.4, Story 8.5
- **Blocks:** None (final story in epic)
- **Can Parallel With:** None

### Dependency Rationale
- Requires all evidence files to exist before optimization
- Requires manifest (8.5) for file inventory
- Final story in epic - blocks nothing

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

