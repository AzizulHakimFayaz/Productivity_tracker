# -*- mode: python ; coding: utf-8 -*-
import os
import importlib.util

# ── Locate onnxruntime DLLs ──────────────────────────────────────────────────
# PyInstaller cannot auto-detect native C-extension DLLs inside onnxruntime.
# We use importlib.util.find_spec() which reliably finds the actual package
# location regardless of how Python was installed (site.getsitepackages()
# can return the base prefix instead of Lib\site-packages on some installs).
def _find_onnxruntime_binaries():
    spec = importlib.util.find_spec('onnxruntime')
    if spec is None or spec.origin is None:
        print('WARNING: onnxruntime not found — DLLs will NOT be bundled!')
        return []
    onnx_dir = os.path.dirname(spec.origin)
    capi = os.path.join(onnx_dir, 'capi')
    bins = []
    if os.path.isdir(capi):
        for f in os.listdir(capi):
            if f.endswith('.dll') or f.endswith('.pyd'):
                bins.append((os.path.join(capi, f), 'onnxruntime/capi'))
    else:
        print(f'WARNING: onnxruntime/capi not found at {capi}')
    print(f'[spec] onnxruntime DLLs found: {[b[0] for b in bins]}')
    return bins

def _find_fastembed_data():
    spec = importlib.util.find_spec('fastembed')
    if spec is None or spec.origin is None:
        print('WARNING: fastembed not found — data will NOT be bundled!')
        return []
    fe_dir = os.path.dirname(spec.origin)
    print(f'[spec] fastembed dir: {fe_dir}')
    return [(fe_dir, 'fastembed')]

ONNX_BINS  = _find_onnxruntime_binaries()
FE_DATAS   = _find_fastembed_data()

# UPX must NOT compress these — it corrupts native extension binaries
# and causes "DLL initialization routine failed" at runtime.
UPX_EXCLUDE = [
    'onnxruntime.dll',
    'onnxruntime_providers_shared.dll',
    'onnxruntime_pybind11_state.pyd',
    'tokenizers.pyd',
    'tokenizers.dll',
    # wildcard patterns PyInstaller also accepts
    'vcruntime*.dll',
    'msvcp*.dll',
    'api-ms-*.dll',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ONNX_BINS,
    datas=[('classifier_data', 'classifier_data')] + FE_DATAS,
    hiddenimports=[
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        'fastembed',
        'fastembed.text',
        'fastembed.text.text_embedding',
        'fastembed.sparse',
        'fastembed.image',
        'fastembed.late_interaction',
        'fastembed.late_interaction_multimodal',
        'fastembed.common',
        'fastembed.common.model_management',
        'scipy.special._cdflib',
        'huggingface_hub',
        'tokenizers',
        'numpy',
        'sklearn',
        'sklearn.feature_extraction',
        'sklearn.feature_extraction.text',
        'sklearn.metrics.pairwise',
        'scipy.sparse',
        'scipy.sparse._csr',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_onnx.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FocusIO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=UPX_EXCLUDE,
    name='FocusIO',
)
