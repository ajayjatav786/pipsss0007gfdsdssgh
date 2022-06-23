# Create our image based on Python 3.8
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-alpine3.10

# Tell Python to not generate .pyc
ENV PYTHONDONTWRITEBYTECODE 1

# Turn off buffering
ENV PYTHONUNBUFFERED 1

# Install requirements using pip
ADD requirements.txt .

RUN \
  pip install --upgrade pip && \
  apk update && \
  apk add --no-cache build-base curl sudo git make gcc musl-dev libffi-dev && \
  rm -rf /var/cache/apk/* && \
  pip install -r requirements.txt && \
  apk del build-base make gcc musl-dev libffi-dev

# Set working directory
WORKDIR /app

# Copy files
ADD ./api /app
ADD ./pytest.ini /app

EXPOSE 80
