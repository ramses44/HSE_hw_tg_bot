FROM ubuntu:latest

RUN apt-get update
RUN apt-get install -y python3.10
RUN apt-get install -y python3-pip
RUN apt install -y myspell-ru
RUN apt-get -y install enchant-2

CMD ["pip", "install", "-r", "project/requirements.txt"]
