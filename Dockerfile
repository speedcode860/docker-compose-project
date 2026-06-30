#use a base image

FROM python:3.12-slim

#set the working directory

WORKDIR /app

#copy files from the host to the container

COPY api/ .

#install dependencies

RUN pip install --no-cache-dir -r requirements.txt

#Expose ports

EXPOSE 5000

#define the command to run the application

CMD ["python", "app.py"]
