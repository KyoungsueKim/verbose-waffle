FROM    mindersturmoil/verbose-waffle:3
MAINTAINER zp5njqlfex@gmail.com

COPY . /opt/project/

EXPOSE 80
CMD python3 /opt/project/verbose-waffle/main.py