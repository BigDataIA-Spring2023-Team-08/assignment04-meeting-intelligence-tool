FROM --platform=linux/amd64 python:3.8.10
#pull the base docker image with tag 3.8.10 since thats the version in my venv
#now you are inside the container

WORKDIR /app
#change the working dir inside the container 

#copy your local files into the container 
ADD . /app

#install dependencies
RUN pip install -r requirements.txt

#### container env same as local at this point
EXPOSE 8082

CMD ["streamlit", "run", "main.py", "--server.port", "8082"]