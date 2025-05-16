import sys
import trace
from pathlib import Path

class SingleFileTracer:
    def __init__(self, target_file):
        self.target_file = str(Path(target_file).resolve())

    def __call__(self, frame, event, arg):
        # Фильтруем только вызовы из target_file
        if frame.f_code.co_filename == self.target_file:
            print(f"{frame.f_code.co_name}() (line {frame.f_lineno})")
        return self

# Указываем путь к вашему main.py
tracer = SingleFileTracer("main.py")
sys.settrace(tracer)

# Запускаем основной код
from main import main
main()