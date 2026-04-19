"""
PyInstaller runtime hook — executed before any app code.

Ensures the onnxruntime native DLLs are loadable on Windows inside
the frozen bundle.  Three mechanisms are used (belt-and-suspenders):

  1. os.add_dll_directory()           — modern Win10+ search path
  2. Prepend to os.environ["PATH"]    — legacy DLL search fallback
  3. ctypes.CDLL() pre-load           — forces the DLLs into process
                                        memory in the right order
"""
import os
import sys

if sys.platform == "win32":
    # Determine the base directory of the frozen bundle
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))

    # Locate onnxruntime/capi inside the bundle
    onnx_capi = None
    for candidate in [base, os.path.join(base, "_internal")]:
        path = os.path.join(candidate, "onnxruntime", "capi")
        if os.path.isdir(path):
            onnx_capi = path
            break

    if onnx_capi:
        # 1) Modern DLL search directory (Windows 10 1607+)
        try:
            os.add_dll_directory(onnx_capi)
        except (OSError, AttributeError):
            pass

        # 2) Legacy PATH-based search — some DLL loaders still rely on this
        os.environ["PATH"] = onnx_capi + os.pathsep + os.environ.get("PATH", "")

        # 3) Explicitly pre-load the native binaries in dependency order.
        #    This is the most reliable approach: once a DLL is in the
        #    process address space, the .pyd import will find it there
        #    regardless of search-path quirks.
        import ctypes
        for dll_name in [
            "onnxruntime_providers_shared.dll",
            "onnxruntime.dll",
        ]:
            dll_path = os.path.join(onnx_capi, dll_name)
            if os.path.isfile(dll_path):
                try:
                    ctypes.CDLL(dll_path)
                except Exception:
                    pass

    # Also add the base/_internal dir itself to PATH so that any other
    # loose DLLs (VC runtime, tokenizers, etc.) can be found.
    internal = os.path.join(base, "_internal") if os.path.isdir(os.path.join(base, "_internal")) else base
    if internal not in os.environ.get("PATH", ""):
        os.environ["PATH"] = internal + os.pathsep + os.environ.get("PATH", "")
