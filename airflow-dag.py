# airflow DAG goes here

# importing necessary libraries:
import boto3
import httpx
import time
import logging
from datetime import datetime

# importing airflow decorators:
from airflow.decorators import dag, task

# --- CONFIGURATION ---

# Defining constants/variables: 
uva_id = "hva4zb" 
total_messages = 21
api_url = f"https://j9y2xa0vx0.execute-api.us-east-1.amazonaws.com/api/scatter/{uva_id}"
submission_sqs_url = "https://sqs.us-east-1.amazonaws.com/440848399208/dp2-submit"

# Logging configuration
log = logging.getLogger(__name__)

# First DAG: Quote Assembler DAG
@dag(
    dag_id="quote_assembler_dag",
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,  # This DAG is manually triggered
    catchup=False,
    tags=['dp2', 'sqs', 'assignment']
)
def quote_assembler_dag():
    """
    4 Tasks (like Prefect flow): 
    
    1. Call API to populate queue.
    2. Monitor and fetch all messages.
    3. Assemble the phrase.
    4. Submit the solution.
    """

    # Task 1: calling api to retrieve messages and populate SQS queue
    @task
    def call_api_to_populate_queue() -> str:
        # Log statement:
        log.info(f"Calling API endpoint: {api_url}")
        try:
            response = httpx.post(api_url)
            response.raise_for_status()
            
            payload = response.json()
            my_sqs_url = payload.get('sqs_url')
            
            log.info(f"API call successful: Messages populating in: {my_sqs_url}")
            return my_sqs_url
        # Exception handling:
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP error calling API: {e}")
            raise
        except Exception as e:
            log.error(f"An error occurred during API call: {e}")
            raise

    # Task 2: monitoring and fetching messages from SQS queue, same as Prefect flow
    @task
    def monitor_and_fetch_messages(queue_url: str) -> list:
        """
        Monitors the queue by polling and fetches all messages.
        This task will run for as long as it takes to get all 21 messages.
        """
        sqs = boto3.client('sqs')
        collected_messages = []
        
        # Log statement
        log.info(f"Starting to monitor and fetch {total_messages} messages from {queue_url}...")
        
        # Polling loop: Keep running until all messages are collected
        while len(collected_messages) < total_messages:
            try:
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    MessageAttributeNames=['All'],
                    WaitTimeSeconds=20
                )
                # For each message received:
                # - Parse order_no and word, store in list, delete from queue
                if 'Messages' in response:
                    for msg in response['Messages']:
                        try:
                            order_no = int(msg['MessageAttributes']['order_no']['StringValue'])
                            word = msg['MessageAttributes']['word']['StringValue']
                            receipt_handle = msg['ReceiptHandle']
                            
                            # storing the requested tuple:
                            collected_messages.append((order_no, word))
                            log.info(f"Collected message {len(collected_messages)}/{total_messages}: ({order_no}, '{word}')")
                            
                            # deleting message immediately after processing:
                            sqs.delete_message(
                                QueueUrl=queue_url,
                                ReceiptHandle=receipt_handle
                            )
                        
                        except Exception as e:
                            log.warning(f"Error parsing or deleting a message: {e}. Skipping.")
                            
                else:
                    log.info("No messages found in this poll. Waiting and retrying...")
                    time.sleep(20)
                    
            except Exception as e:
                log.error(f"Error receiving messages: {e}")
                time.sleep(10)

        # Final log statement:        
        log.info("Successfully fetched and deleted all messages.")
        return collected_messages

    # Task 3: assembling the final phrase
    @task
    def assemble_phrase(messages: list) -> str:
        
        # Log statement:
        log.info("Assembling final phrase...")
        sorted_messages = sorted(messages, key=lambda x: x[0])
        final_phrase = " ".join([word for order, word in sorted_messages])
        log.info(f"Assembled phrase: {final_phrase}")
        return final_phrase
    
    # Task 4: submitting the final solution
    #@task
    #def submit_solution(phrase: str):
        sqs = boto3.client('sqs')
        
        # Log statement:
        log.info(f"Submitting solution to {submission_sqs_url}...")
        
        try:
            response = sqs.send_message(
                QueueUrl=submission_sqs_url,
                MessageBody="DP2 Solution Submission (Airflow)",
                # Including necessary message attributes:
                MessageAttributes={
                    'uvaid': {
                        'DataType': 'String',
                        'StringValue': uva_id
                    },
                    'phrase': {
                        'DataType': 'String',
                        'StringValue': phrase
                    },
                    'platform': {
                        'DataType': 'String',
                        'StringValue': "airflow" # <-- Key change for bonus
                    }
                }
            )
            # Log success message:
            log.info(f"Solution submitted! MessageID: {response.get('MessageId')}")
            
        except Exception as e:
            log.error(f"Error submitting solution: {e}")
            raise

    # Define Task Dependencies:
    my_queue_url = call_api_to_populate_queue()
    messages = monitor_and_fetch_messages(my_queue_url)
    final_phrase = assemble_phrase(messages)
    #submit_solution(final_phrase)

# Instantiating DAG
quote_assembler_dag()