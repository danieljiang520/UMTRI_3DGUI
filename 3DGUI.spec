# -*- mode: python ; coding: utf-8 -*-

from os import path
site_packages = 'venv/lib/python3.9/site-packages'
block_cipher = None


a = Analysis(['main.py'],
             pathex=[site_packages, '.'],
             binaries=[],
             datas=[(path.join(site_packages,"vtkmodules"), "vtkmodules"),
                    (path.join(site_packages,"vedo"), "vedo")],
             hiddenimports=['vtkmodules'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

##### include mydir in distribution #######
def extra_datas(mydir):
    def rec_glob(p, files):
        import os
        import glob
        for d in glob.glob(p):
            if os.path.isfile(d):
                files.append(d)
            rec_glob("%s/*" % d, files)
    files = []
    rec_glob("%s/*" % mydir, files)
    extra_datas = []
    for f in files:
        extra_datas.append((f, f, 'DATA'))

    return extra_datas
###########################################

# append the 'data' dir
a.datas += extra_datas('fonts')
a.datas += extra_datas('res')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='3DGUI',
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
    icon='logo.png',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='3DGUI',
)
app = BUNDLE(
    coll,
    name='3DGUI.app',
    icon='logo.png',
    bundle_identifier=None,
)
