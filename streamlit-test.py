from pkg_resources import load_entry_point
import streamlit as st
import boto3
from botocore.exceptions import NoCredentialsError
import os 
from pydotenvs import load_env


#load local environment
load_env()

# Set up AWS S3 credentials
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY')
aws_secret_access_key = os.environ.get('AWS_SECRET_KEY')
aws_log_key = os.environ.get('AWS_LOG_ACCESS_KEY')
aws_log_secret = os.environ.get('AWS_LOG_SECRET_KEY')
user_bucket = os.environ.get('USER_BUCKET_NAME')

s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

# Set up Streamlit app
#st.title('Meeting Insights')


st.markdown("<h1 style='color: #1E90FF;'>EchoNotes</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color: #1E90FF;'>Generate Insights from your Meetings</h3>", unsafe_allow_html=True)


# Upload audio file to S3 bucket
def upload_to_aws(file, bucket, s3_filename):
    try:
        s3.upload_file(file, bucket, s3_filename)
        st.success("File uploaded to S3!")
    except FileNotFoundError:
        st.error("The file was not found.")
    except NoCredentialsError:
        st.error("Credentials not available.")

# Display upload audio file button
audio_file = st.file_uploader("Upload audio file", type=['mp3', 'wav'])

# Display upload and cancel buttons after audio file is uploaded
if audio_file is not None:
    st.write('File uploaded successfully! Click below to upload to S3 bucket or click Cancel to upload a different file.')
    upload_btn = st.button("Upload file")
    cancel_btn = st.button("Cancel")
    if upload_btn:
        upload_to_aws(audio_file.name, user_bucket, audio_file.name)
    elif cancel_btn:
        audio_file = None

# List all audio files currently in S3 bucket
st.write('Processed audio list')
list_of_files = []
for obj in s3.list_objects(Bucket=user_bucket)['Contents']:
    list_of_files.append(obj['Key'])
processed_audio = st.selectbox('Select processed audio', list_of_files)

# List of questions to ask
questions = ['Meeting summary', 'How many speakers were there', 'What was the general consensus of the meeting']
selected_question = st.selectbox('Select question', questions)

# Text box displaying all text relevant to selected question
st.write('Text box')
text = 'This is the text relevant to the selected question.'
st.text_area(selected_question, value=text, height=300)

# Input textbox to ask any other question
st.write('Ask a question')
other_question = st.text_input('Enter your question')
ask_btn = st.button('Ask')
if ask_btn:
    st.write('You asked:', other_question)
