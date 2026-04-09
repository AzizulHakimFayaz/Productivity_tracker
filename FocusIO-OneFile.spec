# -*- mode: python ; coding: utf-8 -*-
import os
import site

# ── Locate onnxruntime DLLs ──────────────────────────────────────────────────
# PyInstaller cannot auto-detect native C-extension DLLs inside onnxruntime.
# We collect them explicitly so FastEmbed works inside the EXE.
def _find_onnxruntime_binaries():
    bins = []
    for sp in site.getsitepackages():
        capi = os.path.join(sp, 'onnxruntime', 'capi')
        if os.path.isdir(capi):
            for f in os.listdir(capi):
                if f.endswith('.dll') or f.endswith('.pyd'):
                    src = os.path.join(capi, f)
                    bins.append((src, 'onnxruntime/capi'))
    return bins

def _find_fastembed_data():
    datas = []
    for sp in site.getsitepackages():
        fe_dir = os.path.join(sp, 'fastembed')
        if os.path.isdir(fe_dir):
            datas.append((fe_dir, 'fastembed'))
    return datas

ONNX_BINS  = _find_onnxruntime_binaries()
FE_DATAS   = _find_fastembed_data()

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
        'fastembed.text_embedding',
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
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FocusIO-OneFile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
