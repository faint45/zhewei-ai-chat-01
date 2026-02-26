# Zhewei Brain Startup Diagnostics

This script performs system diagnostics before starting Zhewei Brain.

## Usage

### Python Script
```bash
python startup_diagnostics.py
```

### Batch Script (Recommended)
```bash
run_diagnostics.bat
```

### Full Startup with Diagnostics
```bash
啟動_築未科技大腦_完整版.bat
```

## Checks Performed

1. **Z Drive (Cloud Storage)** - Checks if Google Drive is mounted
2. **Vision Environment** - Checks if Python 3.12 vision environment exists
3. **GPU Acceleration (CUDA)** - Checks if CUDA is available for AI vision
4. **Python Environment** - Verifies Python installation
5. **Required Files** - Checks for brain_server.py, ai_service.py, website_server.py
6. **Optional Directories** - Checks for input/, processed/, models/ directories

## Exit Codes

- `0` - All checks passed, system ready
- `1` - One or more required checks failed

## Integration

The diagnostics can be integrated into startup scripts:

```python
import sys
from startup_diagnostics import run_diagnostics

if not run_diagnostics():
    sys.exit(1)
```
