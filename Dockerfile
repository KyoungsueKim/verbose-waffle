FROM python:3.11.2
LABEL maintainer="zp5njqlfex@gmail.com"

EXPOSE 64550
VOLUME /etc/letsencrypt/live/kksoft.kr/
RUN mkdir -p /opt/project
COPY requirements.txt /opt/project/requirements.txt
COPY ./verbose-waffle /opt/project/verbose-waffle

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        cups \
        cups-bsd \
        libcups2-dev \
        tar \
    && rm -rf /var/lib/apt/lists/*

COPY linux-UFRII-drv-v620-m17n-20.tar.gz /tmp/canon-ufr2/ufr2.tar.gz
RUN set -eux; \
    mkdir -p /tmp/canon-ufr2; \
    tar -xzf /tmp/canon-ufr2/ufr2.tar.gz -C /tmp/canon-ufr2; \
    cd /tmp/canon-ufr2/linux-UFRII-drv-v620-m17n; \
    yes y | bash install.sh; \
    test -x /usr/lib/cups/filter/rastertoufr2; \
    test -f /usr/lib/libcanonufr2r.so.1; \
    rm -rf /tmp/canon-ufr2
COPY cups-files.conf /etc/cups/cups-files.conf

ENV DEBIAN_FRONTEND=noninteractive

RUN pip install --no-cache-dir --upgrade -r /opt/project/requirements.txt
CMD ["sh", "-c", "service cups restart >/tmp/cups-restart.log 2>&1 || true; exec python3 /opt/project/verbose-waffle/main.py"]
