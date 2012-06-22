import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup( name = "Checkout",
       version = "0.1",
       description = "A simple library checkout system that interfaces with goodreads.com",
       options = {"build_exe" : {"includes": "atexit"}},
       executables = [Executable("checkout.py", base=base)])
