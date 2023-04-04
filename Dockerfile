FROM python:3.9

WORKDIR /app
COPY ./requirements.txt .
RUN pip install --no-cache -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["./scripts/entrypoint.sh"]

