from flask import Flask, request, send_file, jsonify
import psutil
import threading
import subprocess
import tempfile
import os
import signal
import atexit
import re

app = Flask(__name__)

compilers = []
pids = []
locks = []
n = int(os.environ.get('PROCESSES'))
MAX_MEMORY_MB = 200
compiler_path = "./PascalABCNETLinux/pabcnetc.exe"

def cleanup():
    for proc in compilers:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
            
atexit.register(cleanup)

def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    cleanup()
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def restart_compiler(index):
    if (compilers[index] is not None):
        compilers[index].kill()
        
    compilers[index] = subprocess.Popen(
        ["mono", compiler_path], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True
    )
    
    pid = compilers[index].pid
    pids[index] = psutil.Process(pid)
    compilers[index].stdin.write("Language=0\n")
    compilers[index].stdin.write("Debug=0\n")
    compilers[index].stdin.write("cd /tmp\n")
    compilers[index].stdin.flush()

    for _ in range(47):
        compilers[index].stdout.readline()

for i in range(n):
    locks.append(threading.Lock())
    compilers.append(None)
    pids.append(None)
    restart_compiler(i)
    pids[i] = psutil.Process(compilers[i].pid)
    
class AtomicInteger:
    def __init__(self, initial=0):
        self.value = initial
        self._lock = threading.Lock()

    def getAndIncrement(self):
        with self._lock:
            temp = self.value
            self.value = (self.value + 1) % n
            return temp
            
rr = AtomicInteger(0)

files = []         
            
def compile_file(source_file):
    i = rr.getAndIncrement()
    lock = locks[i]
    
    with lock:
        if(pids[i].memory_info().rss / 1024 /1024 > MAX_MEMORY_MB):
            restart_compiler(i)

        stdout = []
        compilers[i].stdin.write(
            f'{os.path.basename(source_file.name)}\n'
        )
        compilers[i].stdin.flush()
        
        while True:
            output = compilers[i].stdout.readline()

            if output == "\n":
                break

            stdout.append(output)

        return stdout

def new_temp_file(**kwargs):
    kwargs['mode'] = 'w'
    return tempfile.NamedTemporaryFile(**kwargs)

USES_LINE = "uses __RedirectIOMode;"

def has_real_code(line: str) -> bool:
    s = line.strip()

    if not s:
        return False

    # убираем префиксы ### / ##
    s = re.sub(r'^#+\s*', '', s)

    return bool(s)


def inject_redirect(code: str) -> str:
    if "__RedirectIOMode" in code:
        return code

    # Ищем existing uses
    uses_match = re.search(
        r'^\s*uses\s+([^;]+);',
        code,
        re.IGNORECASE | re.MULTILINE
    )

    if uses_match:
        uses_content = uses_match.group(1)

        if "__RedirectIOMode" not in uses_content:
            new_uses = uses_content.rstrip() + ", __RedirectIOMode"

            code = (
                code[:uses_match.start(1)] +
                new_uses +
                code[uses_match.end(1):]
            )

        return code

    lines = code.splitlines()

    insert_index = 0

    for i, line in enumerate(lines):
        if has_real_code(line):
            insert_index = i
            break

    lines.insert(insert_index, USES_LINE)

    return "\n".join(lines)

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.json
    code = data.get('code')
    
    code = inject_redirect(code)
    
    with new_temp_file(suffix='.pas') as source_file:
        source_file.write(code)
        source_file.flush()
        
        stdout = compile_file(source_file)
        
        if len(stdout) != 1:
            return jsonify({ 'err' : stdout }), 400
        else:
            file_name, _ = os.path.splitext(source_file.name)
            exe = f'{file_name}.exe'
            
            while (not os.access(exe, os.X_OK)):
                pass
            
            try:
                return send_file(exe, as_attachment=True) ,200
            finally:
                os.remove(exe)
        
    return code

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)