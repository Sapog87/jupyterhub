FROM ubuntu:22.04

ENV TZ=Europe/Moscow

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        mono-complete \
        p7zip-full \
        wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
        flask \
        psutil

WORKDIR /app
RUN wget https://pascalabc.net/downloads/PascalABCNETLinux.zip && \
    7z x PascalABCNETLinux.zip "PascalABCNETLinux" && \
    rm PascalABCNETLinux.zip

COPY ./__RedirectIOMode.pcu ./graph ./PascalABCNETLinux/Lib

EXPOSE 5000

COPY compiler.py .
CMD [ "python3", "compiler.py" ]