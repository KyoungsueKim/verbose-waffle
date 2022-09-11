FROM    ubuntu:latest
MAINTAINER zp5njqlfex@gmail.com

# Pre-setup
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Python 3.9
RUN apt update
RUN apt install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt -y install python3.9

# Install prerequisites
RUN apt install -y python3-pip
RUN pip install 'fastapi[all]'
RUN pip install PyPDF2

# Install CUPS
RUN apt install -y cups

# Install Cannon Printer Driver
COPY . /opt/project/
# RUN tar -xvf /opt/project/linux-UFRII-drv-v560-m17n-08.tar
RUN ["/bin/bash", "-c", "/opt/project/linux-UFRII-drv-v560-m17n/install.sh"]

# EXPOSE 64550
# CMD python3 /opt/project/verbose-waffle/main.py