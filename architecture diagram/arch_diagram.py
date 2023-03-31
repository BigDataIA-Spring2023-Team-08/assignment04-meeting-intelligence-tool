from cProfile import label
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
            whisper_api = Custom("Whisper API", "./whisper-icon.png")
            chat_api = Custom("Chat API", "./chatgpt-icon.png")


        with Cluster("Storage"):
            s3 = S3("Audio Files")


    with Cluster("User"):
        user = User("User")

    # with Cluster("Machine"):
    #     audio_conversion = Python("Audio Conversion")


    user >> Edge(label = "Access Echonotes application") >> streamlit_app
    user  >> chat_api #>> Edge(label = "User asks a new question")
    s3 >> Edge(label = "Fetches general questionnaire file from S3") >> chat_api
    # audio_conversion >> chat_api
    streamlit_app >> Edge(label = "Triggers Adhoc Process and Uploads audio file") >> dag_adhoc
    dag_adhoc >> Edge(label = "Calls Whisper API to generate transcript") >> whisper_api
    # audio_conversion << whisper_api
    # audio_conversion >> chat_api
    #whisper_api >> Edge(label = "Store transcribed file to S3") >> s3
    dag_batch >> Edge(label = "Runs every midnight and Stores files in S3") >> s3
