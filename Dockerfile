FROM python:3.11.2
MAINTAINER zp5njqlfex@gmail.com

EXPOSE 64550
COPY ./verbose-waffle /opt/project/verbose-waffle
COPY requirements.txt /opt/project

RUN apt-get update && apt-get install -y cups libcups2-dev
RUN service cups start

RUN pip install --no-cache-dir --upgrade -r /opt/project/requirements.txt

CMD python3 /opt/project/verbose-waffle/core/printers.py
