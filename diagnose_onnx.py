"""
Diagnostic script — run from within dist/FocusIO/ to see exactly
what happens when onnxruntime tries to load.
"""
import sys, os, ctypes, ctypes.wintypes

print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print(f"Frozen: {getattr(sys, 'frozen', False)}")
print(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'NOT SET')}")
print()

base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
print(f"Base dir: {base}")

# Check where onnxruntime capi DLLs are
for candidate in [base, os.path.join(base, "_internal")]:
    capi = os.path.join(candidate, "onnxruntime", "capi")
    print(f"  Checking {capi} ... exists={os.path.isdir(capi)}")
    if os.path.isdir(capi):
        for f in os.listdir(capi):
            full = os.path.join(capi, f)
            sz = os.path.getsize(full) if os.path.isfile(full) else "DIR"
            print(f"    {f}  ({sz})")
        
        # Try to add DLL directory
        try:
            os.add_dll_directory(capi)
            print(f"  ✅ add_dll_directory({capi}) succeeded")
        except Exception as e:
            print(f"  ❌ add_dll_directory failed: {e}")
        
        # Also try loading the DLL directly with ctypes
        dll_path = os.path.join(capi, "onnxruntime.dll")
        if os.path.isfile(dll_path):
            try:
                ctypes.CDLL(dll_path)
                print(f"  ✅ ctypes.CDLL(onnxruntime.dll) succeeded")
            except Exception as e:
                print(f"  ❌ ctypes.CDLL(onnxruntime.dll) failed: {e}")

        pyd_path = os.path.join(capi, "onnxruntime_pybind11_state.pyd")
        if os.path.isfile(pyd_path):
            try:
                ctypes.CDLL(pyd_path)
                print(f"  ✅ ctypes.CDLL(pybind11_state.pyd) succeeded")
            except Exception as e:
                print(f"  ❌ ctypes.CDLL(pybind11_state.pyd) failed: {e}")

# Check for MSVC runtime
print("\n--- MSVC Runtime check ---")
for dll_name in ["vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll"]:
    try:
        ctypes.CDLL(dll_name)
        print(f"  ✅ {dll_name} loadable")
    except Exception as e:
        print(f"  ❌ {dll_name} NOT loadable: {e}")

# Now try the actual import
print("\n--- Attempting onnxruntime import ---")
try:
    import onnxruntime
    print(f"✅ onnxruntime imported! Version: {onnxruntime.__version__}")
except Exception as e:
    print(f"❌ onnxruntime import failed: {e}")
    
    # Try a more detailed import
    print("\n--- Detailed import attempt ---")
    try:
        import onnxruntime.capi
        print("  onnxruntime.capi imported OK")
    except Exception as e2:
        print(f"  onnxruntime.capi failed: {e2}")
    
    try:
        import onnxruntime.capi._pybind_state
        print("  _pybind_state imported OK")
    except Exception as e3:
        print(f"  _pybind_state failed: {e3}")

input("\nPress Enter to exit...")
