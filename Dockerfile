FROM    mindersturmoil/verbose-waffle:1
MAINTAINER zp5njqlfex@gmail.com

COPY . /opt/project/

EXPOSE 64550
CMD python3 /opt/project/verbose-waffle/main.py