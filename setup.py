import sys
from cx_Freeze import setup, Executable

""" To build on windows: python.exe setup.py bdist_msi """

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup( name = "Checkout",
       version = "1.1",
       description = "A simple library checkout system that interfaces with goodreads.com",
       options = {"build_exe" : {"includes": "atexit"}},
       executables = [Executable("checkout.py", base=base)])
