FROM python:3.11.15-bookworm
LABEL maintainer="zp5njqlfex@gmail.com"

EXPOSE 64550
VOLUME /etc/letsencrypt/live/kksoft.kr/
ENV DEBIAN_FRONTEND=noninteractive
RUN mkdir -p /opt/project

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        cups \
        cups-bsd \
        cups-filters \
        libcups2-dev \
        tar \
    && usermod --append --groups lpadmin root \
    && rm -rf /var/lib/apt/lists/*

COPY linux-UFRII-drv-v620-m17n-20.tar.gz /tmp/canon-ufr2/ufr2.tar.gz
RUN set -eux; \
    mkdir -p /tmp/canon-ufr2; \
    tar -xzf /tmp/canon-ufr2/ufr2.tar.gz -C /tmp/canon-ufr2; \
    cd /tmp/canon-ufr2/linux-UFRII-drv-v620-m17n; \
    yes y | bash install.sh; \
    test -x /usr/lib/cups/filter/pdftopdf; \
    test -x /usr/lib/cups/filter/rastertoufr2; \
    test -f /usr/share/cups/model/CNRCUPSIRADV45453ZK.ppd; \
    test -f /usr/lib/libcanonufr2r.so.1; \
    rm -rf /tmp/canon-ufr2
COPY cups-files.conf /etc/cups/cups-files.conf
COPY docker-entrypoint.sh /usr/local/bin/verbose-waffle-entrypoint
RUN grep -qx '#!/bin/sh' /usr/local/bin/verbose-waffle-entrypoint \
    && /bin/sh -n /usr/local/bin/verbose-waffle-entrypoint \
    && chmod 0755 /usr/local/bin/verbose-waffle-entrypoint

COPY requirements.txt /opt/project/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /opt/project/requirements.txt
COPY ./verbose-waffle /opt/project/verbose-waffle

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD lpstat -r >/dev/null 2>&1 \
        && python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:64550/openapi.json', timeout=3).read(1)"
ENTRYPOINT ["/usr/local/bin/verbose-waffle-entrypoint"]
CMD ["python3", "/opt/project/verbose-waffle/main.py"]
