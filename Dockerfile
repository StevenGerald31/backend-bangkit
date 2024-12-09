from python:3.11-bookworm

ENV PYTHONUNBUFFERED TRUE
ENV APP_HOME /back-end
WORKDIR $APP_HOME
COPY . ./

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD exec gunicorn --bind :$PORT --workers 3 --threads 4 --timeout 120 run:app
