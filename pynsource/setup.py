from distutils.core import setup
import py2exe
setup(
    options = {
        "py2exe": {
            "dll_excludes": ["MSVCP90.dll"]
        }
    },
    console=['pynsourcegui.py', 'pynsource.py']
)

