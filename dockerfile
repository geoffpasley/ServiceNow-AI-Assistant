FROM python:latest
WORKDIR /usr/app/src
COPY code /usr/app/src
COPY config.ini /usr/app/src
COPY dependency.ini /usr/app/src
RUN pip install --no-cache-dir --progress-bar=off requests
RUN pip install --no-cache-dir --progress-bar=off requests docker
CMD [ "python", "-u", "/usr/app/src/main.py"]