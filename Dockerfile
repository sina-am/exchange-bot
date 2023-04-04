FROM python:3.9

RUN apt-get update && apt-get install -y libgl1-mesa-glx 

WORKDIR /app
COPY ./requirements.txt .
RUN pip install --no-cache -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["/app/scripts/entrypoint.sh"]

