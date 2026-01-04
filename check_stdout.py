import sys
original_stdout = sys.stdout
import kss
if sys.stdout != original_stdout:
    print(f"KSS replaced sys.stdout with {sys.stdout}")
else:
    print("KSS did not replace sys.stdout")
