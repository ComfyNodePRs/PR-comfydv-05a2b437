import os
import sys
import subprocess


if sys.argv[0] == 'install.py':
    sys.path.append('.')   # for portable version

comfy_path = os.environ.get('COMFYUI_PATH')
if comfy_path is None:
    print(f"\n[bold yellow]WARN: The `COMFYUI_PATH` environment variable is not set. Assuming `{os.path.dirname(__file__)}/../../` as the ComfyUI path.[/bold yellow]", file=sys.stderr)
    comfy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

subprocess.check_output(executable=sys.executable, args=['-m', 'pip', 'install', '.'])