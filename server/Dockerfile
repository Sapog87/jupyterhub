FROM ubuntu:22.04

ENV TZ=Europe/Moscow
ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU:ru
ENV LC_ALL=ru_RU.UTF-8
ENV NVM_DIR=/home/node/.nvm
ENV NODE_VERSION=18.17.2
ENV NODE_PATH=/usr/local/lib/node_modules

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        systemd \
        systemd-sysv \
        dbus \
        locales \
        tzdata \
        curl \
        gnupg \
        python3-pip \
        mono-complete && \
    locale-gen ru_RU.UTF-8 && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g configurable-http-proxy && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Установка Python-библиотек
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
        jupyterlab \
        jupyterhub \
        psycopg2-binary \
        jupyterlab-language-pack-ru-RU \
        jupyter-resource-usage \
        jupyterhub-systemdspawner \
        jupyterhub-nativeauthenticator \
        jupyterhub-idle-culler \
        posix-ipc 

# Удаление стандартного Python ядра (если есть)
RUN jupyter kernelspec remove -y python3 && \
    jupyter labextension disable --level=system "@jupyterlab/apputils-extension:announcements"

WORKDIR /app
COPY pabc_kernel_master.zip .
RUN pip3 install --no-cache-dir pabc_kernel_master.zip && \
    python3 -m pabc_kernel.install

# Перевод интерфейса
# COPY /translation/plugin.json /usr/local/share/jupyter/lab/schemas/@jupyterlab/translation-extension/plugin.json

# Шаблоны интерфейса
# RUN mkdir -p /app/templates
# COPY ./templates /app/templates

# Публичная директория
RUN mkdir -p /srv/public

EXPOSE 8000

COPY jupyterhub.service jupyterhub.slice /etc/systemd/system
RUN systemctl enable jupyterhub.service

# COPY jupyterhub_config.py .

CMD ["/sbin/init"]

# CMD ["jupyterhub", "--config", "/app/jupyterhub_config.py"]
