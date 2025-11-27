# Agent Guidelines for Secret Santa Project

## Build/Run Commands
- **Install dependencies**: `pip install -r requirements.txt`
- **Run script**: `python3 secret-santa.py`
- **No tests**: This project has no test suite

## Code Style

### General
- Python 3 script using shebang `#!/usr/bin/env python3`
- Simple, procedural style (no classes/modules)

### Imports
- Standard library first, third-party after (csv, boto3, random, logging)
- No relative imports needed (single file)

### Variables & Naming
- Use `snake_case` for variables and functions
- UPPERCASE for constants (AWS_ACCESS_KEY, AWS_SECRET_KEY, FILE)
- Descriptive names (secret_santas, sms_to_send, not_found)

### Error Handling
- Use logging module (DEBUG level writes to results.log)
- Exit with specific codes on errors (exit(2), exit(3))
- Log errors with logging.error() before exiting
