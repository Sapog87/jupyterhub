from ipykernel.kernelbase import Kernel
from threading import Thread
import subprocess
import tempfile
import posix_ipc
import requests
import os

class PabcKernel(Kernel):
    implementation = 'PascalABC.NET'
    implementation_version = '1.0'
    language = 'pascal'
    language_version = '3.8'
    language_info = {
        'name': 'pascal',
        'mimetype': 'text/pascal',
        'file_extension': '.pas',
    }
    banner = "PascalABC.NET kernel"

    semaphore = None
    ip = None
    port = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ip = os.environ.get('IP')
        self.port = os.environ.get('PORT')
        self.semaphore = posix_ipc.Semaphore("/my_semaphore")
        self._allow_stdin=True

    def create_popen(self, cmd):
        return subprocess.Popen(
            ["mono", cmd], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            stdin=subprocess.PIPE, 
            text=True
        )
        
    def out(self, proc):
        html = False
        html_buffer = ""
        for line in iter(proc.stdout.readline, ''):
            output = line.replace('\ufeff', '')
            if output != '':
                if output == '[HTMLSTART]':
                    html = True
                    continue
                if output == '[HTMLEND]':
                    self.send_response(self.iopub_socket,'display_data',{'data':{'text/html':html_buffer},'metadata':{},'transient':{}})
                    html_buffer = ""
                    html = False
                    continue
                if not html:
                    self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': output})
                else:
                    html_buffer += output

    def err(self, proc):
        for line in iter(proc.stderr.readline, ''):
            err = line.replace('\   ', '')
            if err == '[READLNSIGNAL]\n':
                self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': ''})
                value = self.raw_input()
                proc.stdin.write(f'{value}\n')
                proc.stdin.flush()
            else:
                if err != '' and err != '\n':
                    self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': err})
    
    def run_exe(self, exe):
        with self.create_popen(exe) as proc:
            stdout_t = Thread(target=self.out, args=(proc,))
            stderr_t = Thread(target=self.err, args=(proc,))
            stdout_t.start()
            stderr_t.start()
            stdout_t.join(3)
            proc.kill()
    
    def do_execute(self, code, silent, store_history, user_expressions, allow_stdin):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': 'Запрос поставлен в очередь'})
        self.send_response(self.iopub_socket, 'clear_output', {'wait': True})
        try:
            self.log.info('Отправка кода')
            response = requests.post(f"http://{self.ip}:{self.port}/compile", json={'user': 'user1', 'code': code})
            if (response.status_code == 400):
                stdout = response.json().get('err')
                self.send_response(self.iopub_socket, 'clear_output', {'wait': False})
                self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': ''.join(stdout)})
            elif (response.status_code == 200):
                self.log.info('Пришел exe')
                with tempfile.NamedTemporaryFile(suffix='.exe', mode='wb') as exe:
                    exe.write(response.content)
                
                    self.semaphore.acquire()
                    self.send_response(self.iopub_socket, 'clear_output', {'wait': False})
                    self.run_exe(exe.name)
            else:
                self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': 'Упс..., какие-то проблемы'})
                self.log.error('Неожиданный ответ')

        except BaseException as e:
            # self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': f'Kernel Error {str(e)}'})
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': 'Упс..., какие-то проблемы'})
            self.log.error('Подание в ходе выполнения кода', exc_info=True)
            raise
        
        finally:
            self.semaphore.release()
        
        return {'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
                }