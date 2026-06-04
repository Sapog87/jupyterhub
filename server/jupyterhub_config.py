import os, posix_ipc, sys, pwd, subprocess

sys.path.insert(0, os.path.dirname(__file__))

from customnativeauthenticator.customnativeauthenticator import CustomNativeAuthenticator
import customnativeauthenticator


# ---------------------------------------
# Конфигурация
# ---------------------------------------
c = get_config()

# ---------------------------------------
# Аутентификация
# ---------------------------------------
c.Authenticator.allow_all = True
c.Authenticator.admin_users = {'admin'}
c.Authenticator.username_pattern = r'^[a-zA-Z0-9_]{1,64}$'
c.JupyterHub.authenticator_class = CustomNativeAuthenticator
c.JupyterHub.load_roles = [
    {
        "name": "jupyterhub-idle-culler",
        "scopes": [
            "list:users",
            "read:users:activity",
            "read:servers",
            "delete:servers",
        ],
        "services": ["jupyterhub-idle-culler-service"],
    },
    {
        "name": "teacher",
        "scopes": [
            "admin-ui",
            "list:users",
            "read:users",
            "read:groups",
            "list:groups",
            "read:servers",
            "read:hub",
        ],
        "groups": ["teachers"]
    }
]


# ---------------------------------------
# Шаблоны
# ---------------------------------------
c.JupyterHub.template_paths = [
        f"{os.path.dirname(customnativeauthenticator.customnativeauthenticator.__file__)}/templates/", 
        "/app/templates/"
    ]


# ---------------------------------------
# Подключение к базе данных
# ---------------------------------------
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

c.JupyterHub.db_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
       

# ---------------------------------------
# Найстройка лимита запущенных серверов
# ---------------------------------------
c.JupyterHub.active_server_limit = 50


# ---------------------------------------
# Найстройка спавнера
# ---------------------------------------
public_dir = "/srv/public"
teacher_group = "teachers"

try: 
    subprocess.run(["getent", "group", teacher_group], check=True)
except subprocess.CalledProcessError: 
    subprocess.run(["groupadd", teacher_group], check=True)
    
if not os.path.exists(public_dir): 
    os.makedirs(public_dir, exist_ok=True)
    
subprocess.run(['chown', '-R', f":{teacher_group}", public_dir], check=True)
subprocess.run(['chmod', '3775', public_dir], check=True)
    
        
def pre_spawn_hook(spawner):
    user = spawner.user
    username = user.name

    # Создание пользователя в системе, если не существует
    try: 
        pwd.getpwnam(username)
    except KeyError: 
        subprocess.check_call(['useradd', '-ms', '/bin/bash', username])

    # Добавить в группу при необходимости
    if (teacher_group in map(lambda g: g.name, user.groups)):
        try: 
            subprocess.run(['usermod', '-aG', teacher_group, username], check=True)
        except subprocess.CalledProcessError: 
            pass  # Игнорируем, если группа не существует

    # Символическая ссылка ~/repository -> /srv/public
    user_home = os.path.join("/home", username)
    repository_link = os.path.join(user_home, "repository")
    if not os.path.exists(repository_link):
        try: 
            os.symlink(public_dir, repository_link)
        except FileExistsError: 
            pass

c.JupyterHub.spawner_class = "systemd"
c.SystemdSpawner.user_workingdir = '/home/{USERNAME}'
c.SystemdSpawner.username_template = '{USERNAME}'
c.SystemdSpawner.cpu_limit = 0.5
c.SystemdSpawner.mem_limit = '0.5G'
c.SystemdSpawner.isolate_tmp = True
c.SystemdSpawner.unit_extra_properties = {}
c.SystemdSpawner.slice = "jupyterhub.slice"
c.Spawner.pre_spawn_hook = pre_spawn_hook
c.Spawner.args = [
        "--KernelSpecManager.ensure_native_kernel=False", 
        "--NotebookApp.terminals_enabled=False", 
        "--NotebookApp.iopub_msg_rate_limit=100",
    ]
c.Spawner.environment = {
  'IP': os.environ.get('IP'),
  'PORT': os.environ.get('PORT'),
  'JUPYTERLAB_ENABLE_TELEMETRY': 'false',
}


# ---------------------------------------
# Найстройка сервисов
# ---------------------------------------
c.JupyterHub.services = [
    {
        "name": "jupyterhub-idle-culler-service",
        "command": [
            sys.executable, 
            "-m", "jupyterhub_idle_culler",
            "--timeout=300"
        ],
    }
]


# ---------------------------------------
# Семофор
# ---------------------------------------
try: 
    os.remove("/dev/shm/sem.my_semaphore")
except FileNotFoundError: 
    pass
posix_ipc.Semaphore("/my_semaphore", flags=posix_ipc.O_CREAT, initial_value=4, mode=0o777)
os.chmod("/dev/shm/sem.my_semaphore", 0o777)