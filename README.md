# EchoNotes: A Meeting Intelligence Application

![Webinar-pana](https://user-images.githubusercontent.com/46862684/229015820-c303a49e-dd60-4381-a77a-165e0f9aa562.svg)

----- 

> ✅ Active status <br>
> [🚀 Application link](http://34.73.90.193:8082) <br>
> [⏱ Airflow](http://34.73.90.193:8081) <br>
> [🎬 Codelab Slides](https://codelabs-preview.appspot.com/?file_id=10g_VR_sg49wRqfq8tMtr2pbBg80EHSgA2Rqd8R1MaiI#0) <br>
> 🐳 Docker Hub Images: [Airflow](https://hub.docker.com/repository/docker/mashruwalav/echonotes_airflow_v2/general), [Streamlit](https://hub.docker.com/repository/docker/mashruwalav/echonotes_streamlitapp_v2/general) <br>
> [📽️ Application Demo/Presentation](tba)

----- 

## Index
  - [Objective 🎯](#objective)
  - [Abstract 📝](#abstract)
  - [Architecture Diagram 🏗](#architecture-diagram)
  - [Project Components 💽](#project-components)
    - [APIs](#apis)
    - [Streamlit](#streamlit)
    - [Airflow](#airflow)
  - [How to run the application 💻](#how-to-run-the-application-locally)
----- 

## Objective
Build a Meeting Intelligence tool using generative AI APIs such as **Whisper** and **GPT 3.5** APIs, integrated with [Streamlit](https://streamlit.iohttps://streamlit.io) for its user interface to illustrate application workflow illustration as well as [Airflow](https://airflow.apache.org/docs/) for automation.


## Abstract
The task involves building a decoupled architecture for the meeting intelligence application:

- View meeting insights such a summaries, quick conclusions etc about a meeting without having to listen to the entire meeting audio
- Use the audio file and provide it to OpenAI’s Whisper API to transcribe this audio file. The transcription is stored on a S3 bucket
- Use the transcription file to call GPT 3.5 API to answer 4 general questions about the meeting. This answer & questionnaire file is then stored into S3
- Give the user details about these general questions & provide option for users to ask any additional questions. When a user asks any new question, the GPT 3.5 API is called again
- Access the application through Streamlit which pulls a Docker image of the application
- Backend processes are handled through Airflow which again uses a Docker image of the Airflow instance

The 4 general questions asked for each meeting are: 

1. Provide meeting summary
2. How many speakers were there?
3. Is this meeting a generic discussion or focused on a specific project?
4. What were the topics discussed during this meeting?


## Architecture Diagram
![Architecture](https://github.com/BigDataIA-Spring2023-Team-08/assignment04-meeting-intelligence-tool/blob/main/architecture%20diagram/whisper_and_chat_api_architecture.png?raw=true)


## Project Components

### APIs
**Whisper API:** API for [Whisper](https://openai.com/research/whisper) speech-to-text open-source model which provides two endpoints for transcriptions and translations and accepts variety of formats (m4a, mp3, mp4, mpeg, mpga, wav, webm). For the purpose of this assignment, Whisper API has been implemented to transcribe audio from test meeting recordings and user uploaded audio files in mp3 format.

**GPT 3.5 API:** API for [ChatGPT 3.5](https://openai.com/research/whisper) model which takes sequence of messages coupled with metadata as tokens to generate text completion which can either be natural language or code. For the purpose of this assignment, GPT 3.5 API has been implemented to build a query engine complemented by the transcripts generated by Whisper as well as generate transcript questionnaire.

### Streamlit
Python library [Streamlit](https://streamlit.iohttps://streamlit.io) has been implemented in this application for its user interface. Streamlit offers user friendly experience to assist users in :

>  Upload audio files to S3 bucket 

>  Select meetings from a list

>  Generate general questionnaire from the selected meeting

>  Ask questions related to meeting using the query engine

### Airflow
Airflow is an open-source platform for data orchestration, through which data workflows can be scheduled, monitored and managed. In this application, Airflow is integrated to automate the workflow of the application with the help of following DAG's (Directed Acyclic Graphs):

1) **Adhoc Dags** - Dags which can be triggered using REST API calls.

> `Task 1`: Audio files of meeting uploaded by users are stored in `Adhoc` folder inside S3 bucket which is read by the Dag.

> `Task 2`: Audio file is sent to Whisper AI to generate transcriptions

> `Task 3`: Transcripts are written in `Processed` folder inside S3 bucket

> `Task 4`: ChatGPT API is called for querying questions

2) **Batch Dags** - Dags which are scheduled using cron.

> `Task 1`: Read audio files stored in `Batch` folder inside S3 bucket.

> `Task 2`: Audio file is sent to Whisper AI to generate transcriptions

> `Task 3`: Transcripts are written in `Processed` folder inside S3 bucket

> `Task 4`: ChatGPT API is called for querying questions



## How to run the application locally

1. Clone the repo to get all the source code on your machine

2. Within the [airflow folder](https://github.com/BigDataIA-Spring2023-Team-08/assignment04-meeting-intelligence-tool/tree/main/airflow), create a `.env` file with just the following line: 

        AIRFLOW_UID=1001
        
Note: no need to add your credentials in this .env file since the credentials for the airflow app are to be added as said in the next point

3. Edit lines 66-71 in the [`docker-compose.yml`](https://github.com/BigDataIA-Spring2023-Team-08/assignment04-meeting-intelligence-tool/blob/main/airflow/docker-compose.yaml) found within the airflow folder to add your API keys

4. Once done, create a virtual environment and install all requirements from the [`requirements.txt`](https://github.com/BigDataIA-Spring2023-Team-08/assignment04-meeting-intelligence-tool/blob/main/airflow/requirements.txt) file present

5. Finally, execute following line to get airflow running: 

        docker compose up

Lets us get the streamlit frontend running now:

6. Within the [streamlit-app folder](https://github.com/BigDataIA-Spring2023-Team-08/assignment04-meeting-intelligence-tool/tree/main/streamlit-app), create a `.env` file with following variables and your key: 

        ACCESS_KEY=yourkey
        AWS_SECRET_KEY=yourkey
        USER_BUCKET_NAME=meeting-intelligence-tool
        OPENAI_KEY=yourkey
        AIRFLOW_URL=http://34.73.90.193:8081/

Note: airflow URL should be the URL you just got after doing docker compose up

7. Once done, create a virtual environment and install all requirements from the [`requirements.txt`](https://github.com/BigDataIA-Spring2023-Team-08/assignment04-meeting-intelligence-tool/blob/main/streamlit-app/requirements.txt) file present 

8. Finally, execute following line to get streamlit running: 

        docker compose up

9. Access application through the port you just opened by running docker compose up for Streamlit

-----
> WE ATTEST THAT WE HAVEN’T USED ANY OTHER STUDENTS’ WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK.
> 
> Vraj: 25%, Poojitha: 25%, Merwin: 25%, Anushka: 25%
-----
