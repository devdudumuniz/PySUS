## 2024-08-29 - Command Injection in Native Directory Picker

**Vulnerability:** A command injection vulnerability existed in `pysus/web/pages/1_client.py` within the `_native_dir_picker` function. When opening a directory picker on Windows or macOS (Darwin), user-provided strings (`title` and `initialdir`) were directly formatted into PowerShell and AppleScript strings without any escaping.

**Learning:** When using Python's `subprocess.run` to execute scripts that dynamically construct logic via format strings (f-strings) inside platforms like PowerShell or `osascript`, quoting strings within those formats is insufficient if the external platform is processing the final string payload. Even though `shell=True` was not used, the script engines evaluated the unescaped inputs as code.

**Prevention:** Always escape data embedded inside dynamically generated scripts being passed to an interpreter like PowerShell (`'` to `''`) or AppleScript (`\` to `\\`, `"` to `\"`), or pass the data as parameters/arguments to the script rather than embedding them directly in the script source.
