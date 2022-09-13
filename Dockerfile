FROM    mindersturmoil/verbose-waffle:5
MAINTAINER zp5njqlfex@gmail.com

EXPOSE 64550
COPY . /opt/project/
CMD python3 /opt/project/verbose-waffle/main.py