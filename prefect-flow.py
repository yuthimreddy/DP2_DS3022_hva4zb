# prefect flow goes here
import boto3
import time
import requests
from prefect import flow, task, get_run_logger

# defining vars:
uva_id = "hva4zb"
total_messages = 21
api_url = "https://j9y2xa0vx0.execute-api.us-east-1.amazonaws.com/api/scatter/hva4zb"
submit_url = "https://sqs.us-east-1.amazonaws.com/440848399208/dp2-submit"

# FIRST TASK: calling the API endpoint and populating queue
@task(retries=3, retry_delay_seconds=5)
def calling_api(url: str) -> str:
    logger = get_run_logger()
    logger.info(f"Calling API Endpoints: {url}")

    try:
        response = requests.post(url)
        response.raise_for_status()
        # Parsing the response JSON:
        payload = response.json()
        my_sqs_url = payload.get('sqs_url') # MY UVA-id

        logger.info(f"Received SQS URL: {my_sqs_url}")
        return my_sqs_url
    # Exception handling:
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Error occurred during API call: {e}")
        raise

# TASK 2: monitoring and receiving messages from SQS -
    # monitors queue by polling and fetching messages until total_messages = 21

@task
def monitor_and_fetch_messages(queue_url: str, total_messages: int) -> list:
    logger = get_run_logger()
    sqs = boto3.client('sqs')
    collected_messages = []

    # Log statement:
    logger.info(f"Fetching messages from {queue_url} until {total_messages} messages are collected.")

    # Polling loop to fetch messages: Keeps running until all messages are collected
    while len(collected_messages) < total_messages:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                MessageAttributeNames=['All'], # retrieve all message attributes, will parse in next step
                WaitTimeSeconds=20
            )    

            # For each message received:
            if 'Messages' in response:
                for msg in response['Messages']:
                    try:
                        # Parsing message body: Collecting order_no and word
                        order_no = int(msg['MessageAttributes']['order_no']['StringValue'])
                        word = msg['MessageAttributes']['word']['StringValue']
                        receipt_handle = msg['ReceiptHandle']

                        # Store the parsed message content in our list:
                        collected_messages.append((order_no, word))
                        logger.info(f"Collected message {order_no}: {word}")

                        # Delete the message immediately after processing:
                        sqs.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=receipt_handle
                        )
                    except Exception as e:
                        logger.warning(f"Error parsing or deleting message: {e}")
            # If no messages were received, wait and retry:
            else:
                logger.info("No messages received in this poll. Waiting and retrying ...")
                time.sleep(10) # retry after ten seconds
        
        except Exception as e:
            logger.error(f"Error receiving messages from SQS: {e}")
            time.sleep(10)
    # Final log statement:
    logger.info(f"Successfully retrieved and deleted {total_messages} messages")
    return collected_messages


# TASK 3: reconstructing the original message from the received parts
@task
def assemble_phrase(messages: list) -> str:
    logger = get_run_logger()
    logger.info("Assembling the final phrase from collected messages.")

    # Sort messages based on order_no
    sorted_messages = sorted(messages, key=lambda x: x[0])

    # Extract words and join them to form the final phrase
    final_phrase = ' '.join([word for order_no, word in sorted_messages])
    logger.info(f"Final assembled phrase: {final_phrase}")

    return final_phrase

# TASK 4: submitting the final phrase to the submit_queue_url
@task
def submit_solution(uva_id: str, final_phrase: str, platform: str, queue_url: str):
    logger = get_run_logger()
    sqs = boto3.client('sqs')

    # Log statement: 
    logger.info(f"Submitting final phrase to {queue_url}...")

    # Making the POST request to submit the final phrase
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody="DP2 Solution Submission for hva4zb:",
            MessageAttributes={
                'uvaid': {
                    'StringValue': uva_id,
                    'DataType': 'String'
                },
                'phrase':{
                    'StringValue': final_phrase,
                    'DataType': 'String'
                },
                'platform': {
                    'StringValue': platform,
                    'DataType': 'String'
                }
            }
        )

        # Checking for HTTP response status (must be 200):
        if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
            logger.info("Final phrase submitted successfully.")
        else:
            logger.error(f"Failed to submit final phrase. Response: {response}")

    except Exception as e:
        logger.error(f"Submission failed: {e}")
        raise

# Defining the main flow to orchestrate the tasks defined:
@flow(name="SQS Message Assembler Flow")
def quote_assembler_flow(uva_id: str = uva_id):
    logger = get_run_logger()
    logger.info("Starting the SQS Message Assembler Flow")

    # Step 1: Call the API to get the SQS queue URL
    my_queue_url = calling_api(api_url)

    # Step 2: Monitor the SQS queue and fetch messages
    messages = monitor_and_fetch_messages(my_queue_url, total_messages)

    # Step 3: Assemble the final phrase from the messages
    final_phrase = assemble_phrase(messages)

    # Step 4: submitting solution
    submit_solution(
        uva_id=uva_id,
        final_phrase=final_phrase,
        platform="prefect",
        queue_url=submit_url
    )

    # Logging:
    logger.info(f"Flow COMPLETED successfully for UVA ID: {uva_id}")


if __name__ == "__main__":
    quote_assembler_flow(uva_id)