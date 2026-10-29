import argparse
from pathlib import Path
import shutil
import subprocess
import sys


root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("command", choices=["backend", "frontend", "seed", "test", "build"])
command = parser.parse_args().command
npm = shutil.which("npm")
commands = {
    "backend": ([sys.executable, "-m", "uvicorn", "app.main:app", "--reload"], "backend"),
    "frontend": ([npm, "run", "dev"], "frontend"),
    "seed": ([sys.executable, "-m", "app.seed"], "backend"),
    "test": ([sys.executable, "-m", "pytest"], "backend"),
    "build": ([npm, "run", "build"], "frontend"),
}
arguments, directory = commands[command]
if arguments[0] is None:
    parser.error("Install Node.js and npm before running this command")
sys.exit(subprocess.run(arguments, cwd=root / directory).returncode)
