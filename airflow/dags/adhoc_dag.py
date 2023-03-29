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
audio_file_path = './files/downloads/adhoc-files/'  #local path to audio file adhoc folder
transcription_file_path = './files/processed-files/adhoc-files/'    #local path to transcription file adhoc folder
default_questions_file_path = './files/processed-files/default-questions/adhoc-files/'  #local path to default questions adhoc folder

#authenticate S3 client with your user credentials that are stored in your .env config file
s3client = boto3.client('s3',
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

def download_latest_audio_file(ti):

    """Function for Airflow DAG to find the latest uploaded file within the S3 bucket's adhoc-folder folder and download it 
    locally to enable further processing. This function pushes variables to Airflow's xcom so that the variables can 
    later be used in the upcoming DAG tasks, where necessary.
    -----
    Input parameters:
    ti - to enable interacting with xcom in airflow
    -----
    Returns:
    None
    """

    global audio_file_path, transcription_file_path #use the global variables
    response = s3client.list_objects_v2(Bucket=user_bucket, Prefix='adhoc-folder/') #list objects within specified folder in S3 bucket   
    latest_object = max(response['Contents'], key=lambda x: x['LastModified'])  #get the last modified object (latest uploaded)
    audio_file_path = audio_file_path + latest_object['Key'].split('/')[-1] #append audio file path with file name
    transcribed_file_name = os.path.splitext(latest_object['Key'].split('/')[-1])[0] + '.txt'   #transcribed file name is file namefile.txt
    transcription_file_path = transcription_file_path + transcribed_file_name   #append transcribed file path with transcribed file name
    s3client.download_file(user_bucket, latest_object['Key'], audio_file_path)   #download the latest audio file from S3 bucket into local folder
    ti.xcom_push(key="audio_file_path", value=audio_file_path)  #push audio file path for current file to xcom, to use in the next task in DAG
    ti.xcom_push(key="transcribed_file_name", value=transcribed_file_name)  #push transcirbed file name for current file to xcom, to use in the next task in DAG
    ti.xcom_push(key="transcription_file_path", value=transcription_file_path)  #push transcribed file path for current file to xcom, to use in the next task in DAG

    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow adhoc DAG: Task 1 (download files from S3 bucket) executed"
                }
            ]
    )

def transcribe_audio_file(ti):

    """Function for Airflow DAG to transcribe audio file from local folder leveraging OpenAI's Whisper API for speech to text
    conversion. The transcribed text is stored into a .txt file locally. This function pulls variables from Airflow's xcom
    that were pushed by a previous task using its task id.
    -----
    Input parameters:
    ti - to enable interacting with xcom in airflow
    -----
    Returns:
    None
    """

    # Convert the MP3 file to WAV format
    # sound = AudioSegment.from_mp3(audio_file_path)
    # sound.export('./audio.wav', format='wav')
    audio_file_path = ti.xcom_pull(key="audio_file_path", task_ids="task_get_audio_file")   #fetch the audio file path through xcom using task id of first task
    transcription_file_path = ti.xcom_pull(key="transcription_file_path", task_ids="task_get_audio_file")   #fetch the transcribed file path through xcom using task id of first task
    
    #read the audio file and pass it to OpenAI's Whisper API for transcribing
    with open(audio_file_path, 'rb') as audio_file:
        transcription = openai.Audio.transcribe(api_key=openai.api_key,
                                                model='whisper-1', 
                                                file=audio_file, 
                                                response_format='text')
    #write the transcription got from OpenAI's Whisper API to transcription file (.txt)
    with open(transcription_file_path, 'w') as f:
        f.write(transcription)

    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow adhoc DAG: Task 2 (transcribe audio files) executed"
                }
            ]
    )

def upload_transcribed_text_file_to_s3(ti):

    """Function for Airflow DAG to upload the transcribed .txt file to S3 bucket's processed-text folder. This function pulls 
    variables from Airflow's xcom that were pushed by a previous task using its task id.
    -----
    Input parameters:
    ti - to enable interacting with xcom in airflow
    -----
    Returns:
    None
    """

    transcribed_file_name = ti.xcom_pull(key="transcribed_file_name", task_ids="task_get_audio_file")   #fetch the transcribed file name through xcom using task id of first task
    transcription_file_path = ti.xcom_pull(key="transcription_file_path", task_ids="task_get_audio_file")   #fetch the transcribed file path through xcom using task id of first task
    s3_file_path = 'processed-text-folder/adhoc-files/' + transcribed_file_name #defined path of S3 folder
    s3client.put_object(Body=open(transcription_file_path, 'rb'), Bucket=user_bucket, Key=s3_file_path) #upload the file to the S3 bucket folder

    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow adhoc DAG: Task 3 (upload audio transcription to S3 bucket) executed"
                }
            ]
    )

def answer_default_questions(ti):

    """Function for Airflow DAG which answers the general questions for the given aduio file meeting. It fetches the transcribed
    .txt file that is locally stored in the previous task. After reading the text from the transcribed file it calls OpenAI's
    ChatGPT API to answer the 4 general questions. The responses to each of these questions provided by the ChatGPT API are
    stored in a new text file inside. This new text file contains each of the 4 question prompts and their recieved answers.
    This txt file is then transferred to S3 bucket's processed-text-folder/default-questions/adhoc-files/ folder. This file 
    will be later used as a context when the user wants to each new questions about a meeting. This function pulls variables 
    from Airflow's xcom that were pushed by a previous task using its task id.
    -----
    Input parameters:
    ti - to enable interacting with xcom in airflow
    -----
    Returns:
    None
    """

    global default_questions_file_path
    transcribed_file_name = ti.xcom_pull(key="transcribed_file_name", task_ids="task_get_audio_file")   #fetch the transcribed file name through xcom using task id of first task
    transcription_file_path = ti.xcom_pull(key="transcription_file_path", task_ids="task_get_audio_file")   #fetch the transcribed file path through xcom using task id of first task
    default_questions_file_path = default_questions_file_path + transcribed_file_name   #append the default questions file path to add the file name

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
                                            max_tokens=200,
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
                                            max_tokens=100,
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
                                            max_tokens=200,
                                            top_p=1,
                                            frequency_penalty=0,
                                            presence_penalty=0)

        #store each of the responses from ChapGPT as strings
        response_1 = response1.choices[0].message.content.strip()
        response_2 = response2.choices[0].message.content.strip()
        response_3 = response3.choices[0].message.content.strip()
        response_4 = response4.choices[0].message.content.strip()

    #save this chat-type conversation into a .txt file: only the first question has the context of the whole meeting transcript, then the remaining questions do not have the transcript
    #this file stores the question and answer one after other, similar to a chatbot. This chat file will be used as context for the meeting when use wants to ask new questions
    with open(default_questions_file_path, 'w') as f:
        f.write(question1+"\n"+response_1+"\n"+question2+"\n"+response_2+"\n"+question3+"\n"+response_3+"\n"+question4+"\n"+response_4+"\n")

    #finally store this chat type file with the answers to the default questions into the S3 bucket
    s3_file_path = 'processed-text-folder/default-questions/adhoc-files/' + transcribed_file_name #defined path of S3 folder
    s3client.put_object(Body=open(default_questions_file_path, 'rb'), Bucket=user_bucket, Key=s3_file_path) #upload the file to the S3 bucket folder

    clientLogs.put_log_events(      #logging to AWS CloudWatch logs
            logGroupName = "assignment-04",
            logStreamName = "airflow",
            logEvents = [
                {
                'timestamp' : int(time.time() * 1e3),
                'message' : "Airflow adhoc DAG: Task 4 (answer default questions) executed"
                }
            ]
    )

#defining the DAG
with DAG(
    dag_id="adhoc-dag_v3",
    start_date=days_ago(0),
    catchup=False,
    tags=["damg7245", "meeting-intelligence-tools", "adhoc-process", "working"],
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