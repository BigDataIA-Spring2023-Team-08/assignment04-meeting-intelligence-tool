from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB
from diagrams.aws.storage import S3
from diagrams.programming.language import Python
from diagrams.onprem.client import User
from diagrams.onprem.ci import Jenkins
from diagrams.onprem.container import Docker
from diagrams.onprem.workflow import Airflow
#from diagrams.onprem.chat import Slack
from diagrams.onprem.iac import Terraform
from diagrams.onprem.vcs import Github

from diagrams import Cluster, Diagram
from diagrams.custom import Custom
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3
#from diagrams.docker.web import Docker
from diagrams.onprem.client import User
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python
#from diagrams.programming.flowchart import Streamlit
from diagrams.onprem.workflow import Airflow

with Diagram("Whisper and Chat API Architecture", show=False, direction = "LR"):
    with Cluster("Cloud"):
        with Cluster("Airflow"):
               dag_adhoc = Airflow("Adhoc Process")
               dag_batch = Airflow("Batch Process")

               with Cluster("Docker"):
                airflow_docker = Docker("Airflow")

        with Cluster("Streamlit"):
            with Cluster("Docker"):
                streamlit_docker = Docker("Streamlit")
            streamlit_app = Custom("Streamlit", "./streamlit-icon.png")

        with Cluster("API"):
            with Cluster("Docker"):
                whisper_api_docker = Docker("Whisper API")
                chat_api_docker = Docker("Chat API")
            whisper_api = Custom("Whisper API", "./whisper-icon.png")
            chat_api = Custom("Chat API", "./chatgpt-icon.png")


        with Cluster("Storage"):
            audio_files = S3("Audio Files")


    with Cluster("User"):
        user = User("User")

    with Cluster("Machine"):
        audio_conversion = Python("Audio Conversion")

    # user >> streamlit_docker >> streamlit_app
    # streamlit_app >> dag_adhoc >> airflow_docker
    # dag_adhoc >> whisper_api_docker >> whisper_api >> audio_conversion >> audio_files
    # # audio_conversion >> chat_api_docker >> chat_api >> message_queue
    # dag_batch >> audio_conversion
    # audio_files >> audio_conversion
    # # audio_conversion >> db_instance
    # # message_queue >> chat_api
    # whisper_api >> audio_conversion
    # streamlit_app >> whisper_api
    # whisper_api >> chat_api


    user >> Edge(label="Uploads audio file") >> streamlit_app
    streamlit_app >> Edge(label="Triggers Adhoc Process") >> dag_adhoc
    dag_adhoc >> Edge(label="Calls Whisper API to generate transcript") >> whisper_api
    whisper_api >> Edge(label="Transcript file") >> audio_conversion
    audio_conversion >> Edge(label="Processes transcript with ChatGPT API") >> chat_api
    chat_api >> Edge(label="Answered questions file") >> audio_conversion
    audio_conversion >> Edge(label="Stores files in S3") >> audio_files
    dag_batch >> Edge(label="Runs every midnight") >> audio_conversion
    chat_api << Edge(label="User asks a new question") << user
