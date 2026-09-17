FROM python:3.14

WORKDIR /app

COPY requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code

EXPOSE 8000

CMD ["python", "-m", "app.main"]