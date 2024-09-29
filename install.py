import os
import sys
import subprocess

comfydv_path: str = os.path.abspath(os.path.dirname(__file__))
print(f"ComfyDV path: {comfydv_path}")

if sys.argv[0] == 'install.py':
    sys.path.append('.')   # for portable version

comfy_path = os.environ.get('COMFYUI_PATH')
if comfy_path is None:
    print(f"\n[bold yellow]WARN: The `COMFYUI_PATH` environment variable is not set. Assuming `{os.path.dirname(__file__)}/../../` as the ComfyUI path.[/bold yellow]", file=sys.stderr)
    comfy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def install():
    print(f"Using {sys.executable} to install ComfyDV nodes")
    subprocess.check_output(executable=sys.executable, args=['python', '-m', 'pip', 'install', comfydv_path], cwd=comfydv_path)

install()