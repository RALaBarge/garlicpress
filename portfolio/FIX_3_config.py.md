# Fix #3: Validate prompts_dir

**File:** `config.py`  
**Description:** Check that prompts directory exists at config load time  
**Generated:** April 8, 2026  
**Analysis Method:** 8-Model Review

---

## Model Responses


### Trinity Large Thinking

**Status:** ❌ Backend Error

### GPT-5.4-Nano

```
```python
# garlicpress/config.py

import os

prompts_dir = os.getenv("PROMPTS_DIR", "")
if not prompts_dir or not os.path.isdir(prompts_dir):
    raise NotADirectoryError(f"prompts_dir does not exist or is not a directory: {prompts_dir!r}")

config["prompts_dir"] = prompts_dir
```

**Explanation:** Ensures `prompts_dir` from `PROMPTS_DIR` points to an existing directory before using it.  

**Risk if unfixed:** Code may proceed with an invalid/empty path, causing runtime failures or misbehavior when loading prompts.
```

### Gemini 3.1 Flash Lite

```
### 1. Fixed Code Snippet
```python
prompts_dir = os.getenv('PROMPTS_DIR', 'prompts')
if not os.path.isdir(prompts_dir):
    raise NotADirectoryError(f"The prompts directory '{prompts_dir}' does not exist or is not a directory.")
config['prompts_dir'] = prompts_dir
```

### 2. Explanation
This ensures the application fails fast with a descriptive error if the configured prompts directory is missing or invalid, preventing downstream runtime crashes.

### 3. Risk if unfixed
The application will fail silently or throw cryptic FileNotFoundError exceptions during execution when attempting to load template files, complicating debugging and potentially causing partial system failures.
```

### GLM-5v-Turbo

```
### 1. Fixed Code Snippet

```python
import os

# Retrieve and validate configuration
prompts_dir = os.getenv('PROMPTS_DIR')

if not os.path.isdir(prompts_dir):
    raise NotADirectoryError(f"Configuration Error: The specified prompts directory does not exist: {prompts_dir}")

config['prompts_dir'] = prompts_dir
```

### 2. Explanation
Enforces immediate validation of the environment variable to ensure the target directory is accessible before the application proceeds, failing fast with a specific error message.

### 3. Risk if Unfixed
The application will encounter cryptic `FileNotFoundError` exceptions or silent data corruption later in the execution lifecycle when attempting to access non-existent prompt files.
```

### GPT-OSS-120b

```
**Fixed code snippet (garlicpress/config.py)**
```python
import os

# Retrieve prompts directory from environment
prompts_dir = os.getenv("PROMPTS_DIR")
if not prompts_dir:
    raise EnvironmentError("The PROMPTS_DIR environment variable is not set.")

# Validate that the directory exists and is a directory
if not os.path.isdir(prompts_dir):
    raise NotADirectoryError(f"Prompts directory does not exist or is not a directory: {prompts_dir}")

# Store validated path in config
config['prompts_dir'] = prompts_dir
```

**Explanation:**  
Adds explicit checks to ensure `PROMPTS_DIR` is set and points to an existing directory, raising clear errors otherwise.

**Risk if unfixed:**  
The application could silently use an invalid or missing path, leading to runtime file‑not‑found errors, corrupted data handling, or security issues when loading prompts
```

### Qwen 3.2 235B

```
```python
config['prompts_dir'] = os.getenv('PROMPTS_DIR')
if not os.path.isdir(config['prompts_dir']):
    raise NotADirectoryError(f"Prompts directory does not exist: {config['prompts_dir']}")
```
Validates existence and type of prompts directory to prevent runtime errors.  
Risk if unfixed: Causes silent failures or crashes when accessing prompts, leading to unreliable behavior and potential security issues via path injection.
```

### GPT-4o Mini

```
```python
prompts_dir = os.getenv('PROMPTS_DIR')
if not prompts_dir or not os.path.isdir(prompts_dir):
    raise NotADirectoryError(f"Configured prompts directory '{prompts_dir}' is invalid or does not exist.")
```
Validates that the prompts directory exists and raises an error if it does not.  
Risk: If unfixed, the application may attempt to access a non-existent directory, leading to runtime errors and potential crashes.
```

### Gemini 2.0 Flash

```
```python
--- a/garlicpress/config.py
+++ b/garlicpress/config.py
@@ -14,6 +14,7 @@
     config['anthropic_api_key'] = os.getenv('ANTHROPIC_API_KEY')
 
     prompts_dir = os.getenv('GARLICPRESS_PROMPTS_DIR', 'prompts')
+    if not os.path.isdir(prompts_dir): raise NotADirectoryError(f"Prompts directory '{prompts_dir}' does not exist.")
     config['prompts_dir'] = prompts_dir
 
     config['port'] = int(os.getenv('GARLICPRESS_PORT', 5000))

```

Ensure `prompts_dir` exists, raising an exception if not.
Risk: Application crashes or unpredictable behavior if `prompts_dir` doesn't exist.
```
