from airflow.models import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models.param import Param
from datetime import timedelta
import time
from pathlib import Path
import os
from pydotenvs import load_env
import boto3
import openai

#load local environment
load_env()
#define global variables
openai.api_key = os.environ.get('OPENAI_KEY')
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY')
aws_secret_access_key = os.environ.get('AWS_SECRET_KEY')
aws_log_key = os.environ.get('AWS_LOG_ACCESS_KEY')
aws_log_secret = os.environ.get('AWS_LOG_SECRET_KEY')
user_bucket = os.environ.get('USER_BUCKET_NAME')

#authenticate S3 resource with your user credentials that are stored in your .env config file
s3resource = boto3.resource('s3',
                    region_name='us-east-1',
                    aws_access_key_id = aws_access_key_id,
                    aws_secret_access_key = aws_secret_access_key
                    )

#authenticate S3 client for logging with your user credentials that are stored in your .env config file
clientLogs = boto3.client('logs',
                        region_name='us-east-1',
                        aws_access_key_id = os.environ.get('AWS_LOG_ACCESS_KEY'),
                        aws_secret_access_key = os.environ.get('AWS_LOG_SECRET_KEY')
                        )

def download_latest_audio_file():

    """Function for Airflow DAG to traverse through all files within the S3 bucket's batch-folder folder and download it 
    locally to enable further processing.
    -----
    Input parameters:
    None
    -----
    Returns:
    None
    """

    i=0 #being used to check for first object, could also use a boolean flag
    for objects in s3resource.Bucket(user_bucket).objects.filter(Prefix='batch-folder/'):   #traverse through the files found on the S3 bucket batch folder
        if(i==0):
            pass    #since the first object is the root directory object, we do not need this so pass
        else:
            audio_file_path = './files/downloads/batch-files/'  #local path to audio file batch folder
            audio_file_path = audio_file_path + objects.key.split('/')[-1] #append audio file path with file name
            s3resource.Bucket(user_bucket).download_file(objects.key, audio_file_path)   #download the latest audio file from S3 bucket into local folder
        i+=1    #being used to check for first object, could also use a boolean flag
    
    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow batch DAG: Task 1 (download files from S3 bucket) executed"
                }
            ]
    )

def transcribe_audio_file():

    """Function for Airflow DAG to transcribe all audio files from local folder leveraging OpenAI's Whisper API for speech to 
    text conversion. The transcribed text is stored into a .txt file locally.
    -----
    Input parameters:
    None
    -----
    Returns:
    None
    """

    # Convert the MP3 file to WAV format
    # sound = AudioSegment.from_mp3(audio_file_path)
    # sound.export('./audio.wav', format='wav')
    pathlist = Path('./files/downloads/batch-files/').glob('**/*.*')    #local path to audio file batch folder
    for path in pathlist:   #travesing through each file inside this local folder
        audio_file = str(path)  #because path is object not string
        #read the audio file and pass it to OpenAI's Whisper API for transcribing
        with open(audio_file, 'rb') as f:
            transcription = openai.Audio.transcribe(api_key=openai.api_key,
                                                    model='whisper-1', 
                                                    file=f, 
                                                    response_format='text')
        transcription_file_path = './files/processed-files/batch-files/' + audio_file.split('/')[3].split('.')[0] + '.txt'  #set up complete path for transcribed batch folder for current file
        #write the transcription got from OpenAI's Whisper API to transcription file (.txt)
        with open(transcription_file_path, 'w') as f:
            f.write(transcription)

    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow batch DAG: Task 2 (transcribe audio files) executed"
                }
            ]
    )

def upload_transcribed_text_file_to_s3():

    """Function for Airflow DAG to upload the all transcribed .txt file to S3 bucket's processed-text folder.
    -----
    Input parameters:
    None
    -----
    Returns:
    None
    """

    pathlist = Path('./files/processed-files/batch-files/').glob('**/*.*')  #local path to transcribed file batch folder
    for path in pathlist:   #travesing through each file inside this local folder
        processed_file = str(path)  #because path is object not string
        s3_file_path = 'processed-text-folder/batch-files/' + processed_file.split('/')[3]  #defined path of S3 folder
        s3resource.meta.client.upload_file(processed_file, user_bucket, s3_file_path)   #upload the file to the S3 bucket folder

    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow batch DAG: Task 3 (upload audio transcription to S3 bucket) executed"
                }
            ]
    )

def answer_default_questions():

    """Function for Airflow DAG which answers the general questions for all the audio files provided in the batch-folder. 
    It fetches all the transcribed .txt files for each audio file that is locally stored in the previous task. After reading 
    the text from each transcribed file it calls OpenAI's ChatGPT API to answer the 4 general questions. The responses to each 
    of these questions provided by the ChatGPT API are stored in a new text file inside. This new text file contains each of 
    the 4 question prompts and their recieved answers. This txt file is then transferred to S3 bucket's 
    processed-text-folder/default-questions/batch-files/ folder. This file will be later used as a context when the user wants 
    to each new questions about a meeting.
    -----
    Input parameters:
    None
    -----
    Returns:
    None
    """

    pathlist = Path('./files/processed-files/batch-files/').glob('**/*.*')  #local path to transcribed file batch folder
    for path in pathlist:   #travesing through each file inside this local folder
        transcription_file_path = str(path) #because path is object not string
        #read the transcription got from OpenAI's Whisper API which was stored in a .txt file
        with open(transcription_file_path, 'r') as f:
            text = f.read()
            text = text.split("\n")[:-1]    #remove the new line character at the end of the txt file
            text = text[0]  #select only the string of the text from text list obtained

            #system prompt to the ChapGPT model
            system_prompt = "You are meeting intelligence tool which helps provide answers to the meeting transcript provided to you. You will help answer questions as concisely as possible"
            #defining prompts for each of the 4 general questions
            question1 = f"Here is the meeting text:{text}\nSummarise this meeting"  #the context with the entire meeting's transcribed text is only contained in the first prompt
            question2 = "How many people were talking in this meeting and what were their names?"   #general question 2
            question3 = "Is this meeting a generic discussion or focused on a specific project?"    #general question 3
            question4 = "What were the topics discussed during this meeting?"   #general question 4
            
            #ChatGPT API response for question 1
            response1 = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[
                                                    {"role": "system", "content": system_prompt},
                                                    {"role": "user", "content": question1}
                                                ],
                                                temperature=0.7,
                                                max_tokens=500,
                                                top_p=1,
                                                frequency_penalty=0,
                                                presence_penalty=0)

            #ChatGPT API response for question 2
            response2 = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[
                                                    {"role": "system", "content": system_prompt},
                                                    {"role": "user", "content": f"Here is the meeting text:{text}. {question2}"}
                                                ],
                                                temperature=0.7,
                                                max_tokens=50,
                                                top_p=1,
                                                frequency_penalty=0,
                                                presence_penalty=0)

            #ChatGPT API response for question 3
            response3 = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[
                                                    {"role": "system", "content": system_prompt},
                                                    {"role": "user", "content": f"Here is the meeting text:{text}. {question3}"}
                                                ],
                                                temperature=0.7,
                                                max_tokens=200,
                                                top_p=1,
                                                frequency_penalty=0,
                                                presence_penalty=0)

            #ChatGPT API response for question 4
            response4 = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[
                                                    {"role": "system", "content": system_prompt},
                                                    {"role": "user", "content": f"Here is the meeting text:{text}. {question4}"}
                                                ],
                                                temperature=0.7,
                                                max_tokens=500,
                                                top_p=1,
                                                frequency_penalty=0,
                                                presence_penalty=0)

            #store each of the responses from ChapGPT as strings
            response_1 = response1.choices[0].message.content.strip()
            response_2 = response2.choices[0].message.content.strip()
            response_3 = response3.choices[0].message.content.strip()
            response_4 = response4.choices[0].message.content.strip()
    
        default_questions_file_path = './files/processed-files/default-questions/batch-files/' + transcription_file_path.split('/')[3]  #set up complete path for default questions batch folder for current file
        #save this chat-type conversation into a .txt file: only the first question has the context of the whole meeting transcript, then the remaining questions do not have the transcript
        #this file stores the question and answer one after other, similar to a chatbot. This chat file will be used as context for the meeting when use wants to ask new questions
        with open(default_questions_file_path, 'w') as f:
            f.write(question1+"\n"+response_1+"\n"+question2+"\n"+response_2+"\n"+question3+"\n"+response_3+"\n"+question4+"\n"+response_4+"\n")
        
        #finally store this chat type file with the answers to the default questions into the S3 bucket
        s3_file_path = 'processed-text-folder/default-questions/batch-files/' + transcription_file_path.split('/')[3] #defined path of S3 folder
        s3resource.meta.client.upload_file(default_questions_file_path, user_bucket, s3_file_path)  #upload the file to the S3 bucket folder

    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow batch DAG: Task 4 (answer default questions) executed"
                }
            ]
    )

#defining the DAG
with DAG(
    dag_id="batch-dag_v3",
    schedule="0 0 * * *",   #run daily - at midnight
    start_date=days_ago(0),
    catchup=False,
    tags=["damg7245", "meeting-intelligence-tools", "batch-process", "working"],
) as dag:

    download_latest_audio_file = PythonOperator(
        task_id = 'task_get_audio_file',
        python_callable = download_latest_audio_file
    )

    transcribe_audio_file = PythonOperator(
        task_id = 'task_transcribe_audio_file',
        python_callable = transcribe_audio_file
    )

    upload_transcribed_text_file_to_s3 = PythonOperator(
        task_id = 'task_upload_transcribed_text_file_to_s3',
        python_callable = upload_transcribed_text_file_to_s3
    )

    answer_default_questions = PythonOperator(
        task_id = 'task_answer_default_questions',
        python_callable = answer_default_questions
    )
    
    #the 4 tasks for this DAG
    download_latest_audio_file >> transcribe_audio_file >> upload_transcribed_text_file_to_s3 >> answer_default_questions