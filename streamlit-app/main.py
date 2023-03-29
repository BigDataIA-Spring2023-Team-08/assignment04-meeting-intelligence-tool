from pkg_resources import load_entry_point
import streamlit as st
import boto3
from botocore.exceptions import NoCredentialsError
import os 
from pydotenvs import load_env
import codecs
import openai
import requests
import json
import time
#load local environment
load_env()

#define global variables
openai.api_key = os.environ.get('OPENAI_KEY')
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY')
aws_secret_access_key = os.environ.get('AWS_SECRET_KEY')
user_bucket = os.environ.get('USER_BUCKET_NAME')
airflow_url = os.environ.get('AIRFLOW_URL')

#authenticate S3 client with your user credentials that are stored in your .env config file
s3client = boto3.client('s3',
                        region_name='us-east-1',
                        aws_access_key_id = aws_access_key_id,
                        aws_secret_access_key = aws_secret_access_key
                        )

#authenticate S3 resource with your user credentials that are stored in your .env config file
s3resource = boto3.resource('s3',
                        region_name='us-east-1',
                        aws_access_key_id = aws_access_key_id,
                        aws_secret_access_key = aws_secret_access_key
                        )

def upload_to_aws(file):

    """Function that takes in the file user uploaded using Streamlit UI and then uploads it to S3 bucket's adhoc-folder/.
    -----
    Input parameters:
    file: UploadFile
        This is the uploaded file through streamlit
    -----
    Returns:
    None
    """

    try:
        s3_filename = 'adhoc-folder/'+file.name  #s3 bucket filepath for new file, to be uploaded in adhoc-folder
        s3client.upload_fileobj(file, user_bucket, s3_filename) 
        st.success("File uploaded!")    #display success message
    except FileNotFoundError:
        st.error("The file was not found.")
    except NoCredentialsError:
        st.error("Credentials not available.")

#set up streamlit app
st.markdown("<h1 style='color: #1E90FF;'>EchoNotes</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color: #1E90FF;'>Generate Insights from your Meetings</h3>", unsafe_allow_html=True)

#display upload audio file button with supported types
audio_file = st.file_uploader("Upload audio file", type=['mp3', 'wav', 'm4a'])

#display upload and cancel buttons after audio file is uploaded
if audio_file is not None:

    st.write('File uploaded successfully! Click below to upload to S3 bucket or click Cancel to upload a different file.')
    upload_btn = st.button("Upload file")   #button to upload file to S3
    cancel_btn = st.button("Cancel")

    if upload_btn:

        upload_to_aws(audio_file) #on clicking upload button, upload the file to the S3 bucket's adhoc-folder
        
        #trigger Airflow's adhoc DAG to transcribe this audio file & storing the general questions responses got from OpenAI's ChatGPT API into the processed-text-files folder
        dag_id = 'adhoc-dag_v3' #DAG id for the adhoc dag already defined on airflow
        dag_run_id = "triggered_using_app_" + str(time.time() * 1e3)    #unique run id for each dag run using current time
        
        #call the Airflow API to trigger a DAG run
        response = requests.post(url=f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns",
                                headers={"Authorization": "Basic YWlyZmxvdy1nY3A6YWlyZmxvd2djcA=="},    #base 64 encoded value of username:password for Airflow instance
                                json = {"dag_run_id": dag_run_id}   #payload data in json
                            )

        resp_json = response.json() #get the response json of the API call done

        #wait until the DAG run finishes
        with st.spinner('Generating meeting insights...'):  #waiting for adhoc dag run to finish, might take a minute
            while(True):    #check status of the DAG run just executed recursively to check when it is successfully completed
                #call the Airflow API to get the dag run we just executed above
                response_dag_status = requests.get(url=f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}",
                            headers={"Authorization": "Basic YWlyZmxvdy1nY3A6YWlyZmxvd2djcA=="},    #base 64 encoded
                            )
                resp_json1 = response_dag_status.json() #get the response json
                if(resp_json1['state'] == 'success'):   #if the 'state' of this dag run is 'success', it has executed
                    break   #break spinner once dag executed
    elif cancel_btn:
        audio_file = None

#list all audio files currently in S3 bucket processed text folder
st.write('Processed audio list')
list_of_files = []  #this will store all the files available in the S3 bucket

#traverse through the objects within S3 bucket's default questions folder's batch files folder
for objects in s3resource.Bucket(user_bucket).objects.filter(Prefix='processed-text-folder/default-questions/batch-files/'):
    file_path = objects.key
    file_path = file_path.split('/')    #get file name
    list_of_files.append(file_path[-1]) #append the filename to display in Procesed audio files dropdown on UI

first_flag = True   #because the first object is the root directory, blank filename which we want to skip
#traverse through the objects within S3 bucket's default questions folder's batch files folder
for objects in s3resource.Bucket(user_bucket).objects.filter(Prefix='processed-text-folder/default-questions/adhoc-files/'):
    if (first_flag):
        pass    #if this is the first object then it is the root directory which can be ignored
    else:
        file_path = objects.key
        file_path = file_path.split('/')    #get file name
        list_of_files.append(file_path[-1]) #append the filename to display in Procesed audio files dropdown on UI
    first_flag = False

#display all the processed files available as a dropdown
processed_audio = st.selectbox('Select processed audio', list_of_files)
if (processed_audio != ''): #if some file is selected
    
    #if the processed file selected is a batch file
    if (processed_audio == 'batch1.txt' or processed_audio == 'batch2.txt' or processed_audio == 'batch3.txt'):
        file_path = 'processed-text-folder/default-questions/batch-files/' + processed_audio    #set filepath from the S3 bucket
    
    #else when the processed file selected is the new adhoc file just uploaded
    else:
        file_path = 'processed-text-folder/default-questions/adhoc-files/' + processed_audio    #set filepath from the S3 bucket

    #list of the default questions already asked to processed meetings
    questions = ['-Please select-','Provide meeting summary', 'How many speakers were there?', 'Is this meeting a generic discussion or focused on a specific project?', 'What were the topics discussed during this meeting?']
    selected_question = st.selectbox('Select question', questions)  #dropdown for the general questions

    #text box displaying all text relevant to selected question (ChatGPT's answer to the question)
    st.write('Text box')
    text = 'This is the text relevant to the selected question.'    #initial placeholder text for the text answer box
    line_stream = codecs.getreader("utf-8")
    chat_convo = [] #to store the conversation extracted from the already processed general questions files
    
    #open the processed file user selected directly on the S3 location WITHOUT downloading anything on streamlit
    for line in line_stream(s3resource.Object(user_bucket, file_path).get()['Body']):
        chat_convo.append(line) #add every line read into the chat_convo list
    #next, get answer that ChatGPT provided for the general question that user has selected
    if(selected_question == questions[1]):
        text = chat_convo[2]    #select the answer as per question selected
    elif(selected_question == questions[2]):
        text = chat_convo[4]    #select the answer as per question selected
    elif(selected_question == questions[3]):
        text = chat_convo[6]    #select the answer as per question selected
    elif(selected_question == questions[4]):
        text = chat_convo[8]    #select the answer as per question selected

    st.text_area(selected_question, value=text, height=300) #text area to display answers

    #input textbox to ask any other question
    st.write('Ask a question')
    other_question = st.text_input('Enter your question')   #user can ask new questions
    ask_btn = st.button('Ask')
    if (other_question != ''):  #if user asks some question, i.e. some text entered
        if ask_btn:
            st.write('You asked:', other_question)
            system_prompt = system_prompt = "You are a meeting intelligence tool which helps provide answers to the meeting transcript provided to you. You will help answer questions as concisely as possible"
            
            #call ChatGPT API to answer new questions that user asks, the model needs to be provided with context of the meeting & previous conversation
            #chat_convo variable in our case stores the chat convo that the user and model previously had while answering general questions of the meeting
            new_response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                    messages=[
                                                        {"role": "system", "content": system_prompt},
                                                        {"role": "user", "content": chat_convo[0]+chat_convo[1]},
                                                        {"role": "assistant", "content": chat_convo[2]},
                                                        {"role": "user", "content": chat_convo[3]},
                                                        {"role": "assistant", "content": chat_convo[4]},
                                                        # {"role": "user", "content": all_lines[5]},
                                                        # {"role": "assistant", "content": all_lines[6]},
                                                        {"role": "user", "content": other_question} #finally provide the new question user just asked on streamlit
                                                        ],
                                                    temperature=0.7,
                                                    max_tokens=200,
                                                    top_p=1,
                                                    frequency_penalty=0,
                                                    presence_penalty=0)

            new_response = new_response.choices[0].message.content.strip()  #store model's response
            st.write(new_response)  #display the response on streamlit
