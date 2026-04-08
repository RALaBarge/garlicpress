# Fix #1: Thread-Safe File Collection

**File:** `queue.py`  
**Description:** Add threading.Lock to protect shared all_files list  
**Generated:** April 8, 2026  
**Analysis Method:** 8-Model Review

---

## Model Responses


### Trinity Large Thinking

**Status:** ❌ Backend Error

### GPT-5.4-Nano

```
```python
# garlicpress/queue.py

# ... existing imports ...
import threading

# ... existing code ...

all_files_lock = threading.Lock()

# ... existing code ...

def collect_source_files(*args, **kwargs):
    # ... existing code that computes files_to_add ...
    files_to_add = []

    # ... existing logic populating files_to_add ...

    with all_files_lock:
        all_files.extend(files_to_add)

    # ... existing code ...
```

Add a shared threading.Lock to serialize updates to the shared `all_files` list during concurrent `collect_source_files` calls.

If unfixed, concurrent `all_files.extend()` calls can race, leading to missing/duplicated entries or corrupted list state under heavy parallelism.
```

### Gemini 3.1 Flash Lite

```
### 1. Fixed code snippet
```python
import threading

# Initialize lock in the module scope or class instance
all_files_lock = threading.Lock()

# ... inside collect_source_files method:
with all_files_lock:
    all_files.extend(new_files)
```

### 2. One-line explanation
Wrapping the `.extend()` call in a `threading.Lock` prevents race conditions and potential data corruption when multiple threads attempt to modify the shared `all_files` list simultaneously.

### 3. Risk if unfixed
Concurrent calls to `.extend()` can lead to non-atomic list updates, resulting in lost data, inconsistent list state, or `RuntimeError` exceptions during iteration.
```

### GLM-5v-Turbo

**Status:** ❌ Backend Error

### GPT-OSS-120b

```
**Fixed code snippet (garlicpress/queue.py)**  
```python
import threading                     # ← added
# ... other existing imports ...

# Global lock protecting the shared `all_files` list
_all_files_lock = threading.Lock()    # ← added

def collect_source_files(...):
    # ... existing logic that builds `new_files` ...

    # Safely extend the shared list under lock
    with _all_files_lock:              # ← added
        all_files.extend(new_files)    # ← unchanged, now protected
```

**One‑line explanation**  
A module‑level `threading.Lock` (`_all_files_lock`) now guards every `all_files.extend(...)` to prevent race conditions during concurrent `collect_source_files` calls.

**Risk if unfixed**  
Without the lock, simultaneous extensions can corrupt the shared list, leading to lost or duplicated file entries and unpredictable downstream processing failures.
```

### Qwen 3.2 235B

```
```python
# garlicpress/queue.py
all_files_lock = threading.Lock()

def collect_source_files():
    all_files = []
    # ... (other code)
    with all_files_lock:
        all_files.extend(new_files)
    # ... (other code)
```

Ensures thread-safe updates to shared `all_files` list during concurrent execution.  
Risk if unfixed: Race conditions causing data corruption or lost files in `all_files` under high concurrency.
```

### GPT-4o Mini

```
```python
import threading

all_files_lock = threading.Lock()
all_files = []

def collect_source_files():
    global all_files
    # ... other code ...
    with all_files_lock:
        all_files.extend(new_files)
```

This code snippet adds a threading lock to protect the shared `all_files` list during concurrent `collect_source_files` calls. 

Risk if unfixed: Concurrent modifications to `all_files` could lead to data corruption or missed entries.
```

### Gemini 2.0 Flash

```
```python
--- a/garlicpress/queue.py
+++ b/garlicpress/queue.py
@@ -34,6 +34,7 @@
 
     all_files = []
     all_filters = []
+    all_files_lock = threading.Lock()
 
     def __init__(self, config, include=None, exclude=None):
         self.config = config
@@ -66,7 +67,8 @@
             for f in files:
                 f = os.path.normpath(os.path.join(self.config.project_root, f))
                 source_files.append(f)
-        all_files.extend(source_files)
+        with all_files_lock:
+            all_files.extend(source_files)
 
     def collect_static_files(self):
         """Collects all static files.

```
Add threading.Lock to protect shared `all_files` list during concurrent `collect_source_files` calls.
Risk if unfixed: Race condition leading to data corruption or incomplete file lists, potentially causing build failures or incorrect deployments.
```
