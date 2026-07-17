#!/bin/sh
set -eu

# 웹 API가 출력 요청을 받기 전에 CUPS 관리자 소켓이 준비되어야 한다.
if ! service cups start >/tmp/cups-start.log 2>&1; then
    cat /tmp/cups-start.log >&2
    exit 1
fi

if ! lpstat -r >/tmp/cups-readiness.log 2>&1; then
    cat /tmp/cups-readiness.log >&2
    exit 1
fi

exec "$@"
