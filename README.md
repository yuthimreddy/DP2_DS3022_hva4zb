# DS3022 Data Project 2

This data project is a puzzle. Your goal is to put the pieces back together.

Your assignment is to write a Prefect data pipeline that retrieves a number of messages from an SQS queue, parses their contents, and reassembles a complete phrase made up of the fragments from each single message.

Your pipeline can run a single time to produce a complete result, or it can run on a schedule to produce a complete result. Design your workflow however you see fit.

You can run your pipeline as many times as you like for testing. There is no penalty for running it multiple times.

## Task 1 - Populate your SQS Queue

Using your UVA computing ID, append it to this API endpoint:

```
https://j9y2xa0vx0.execute-api.us-east-1.amazonaws.com/api/scatter/<UVA_ID>
```

Your pipeline must call this URL by way of an HTTP `POST` request. To do this using the `requests` library in python:

```
import requests

url = "https://j9y2xa0vx0.execute-api.us-east-1.amazonaws.com/api/scatter/nem2p"

payload = requests.post(url).json
```

The `payload` object returns your SQS URL:

```
>>> payload
{'hello': 'mst3k', 'sqs_url': 'https://sqs.us-east-1.amazonaws.com/440848399208/mst3k'}
```

Your POST to this API will send exactly **21** messages to your SQS queue. These have been sent with a variety of random `DelaySeconds` values ranging from 30 to 900 seconds.

Keep these delays in mind as your pipeline proceeds to the next task.

**NOTE** This step (sending a `POST` request to the API) should not be repeated if your pipeline needs to run more than once, i.e. on a cron timer, to gather all messages - it clears your queue of all previous messages and repopulates all 21 messages each time.

## Task 2 - Monitor Your Queue then Collect Messages

Next, devise a way for your pipeline to track how many messages are available for pickup using the `get_queue_attributes()` method. As it gets attributes about your queue, notice that there are three values that count messages:

- `ApproximateNumberOfMessages`
- `ApproximateNumberOfMessagesNotVisible`
- `ApproximateNumberOfMessagesDelayed`

Together, these make up the total count of messages in your queue.

You should determine a strategy for how/when to pick up messages, and code according to that strategy.

When receiving messages, each has a `MessageBody` that contains the same word (i.e. meaningless content). The meaningful content of each message is contained within the `['MessageAttributes']` segment of each message, and that you must parse into each attribute and get out its `['StringValue']`.

To get these values:

```
# order number:
['Messages'][0]['MessageAttributes']['order_no']['StringValue']

# word:
['Messages'][0]['MessageAttributes']['word']['StringValue']
```

Store the values you fetch for each message and keep them paired together. There are a variety of ways to store them.

Some notes:

- Recall that even though the `order_no` value will appear as if it is an integer, Python will see it as a string by default.
- You must also fetch the `ReceiptHandle` for each message and delete it after storing its data.
- Your pipeline must receive, parse, and delete ALL messages completely when run. Do not leave "dangling" messages that have been read but not deleted.
- Take care that when you request a message using the boto3 `receive_message` method that you handle errors gracefully without throwing an error and breaking your pipeline. If there are messages but they are invisible or delayed, and you try to poll for it, the returned response will not match the format of a successful message request.

## Task 3 - Reassemble the Messages and Submit Your Answer via SQS

Using the two fields collected from each message, now reassemble the words into a single phrase by ordering them using the `order_no` value.

Take this example:

```
order_no         word
---------------------------------------
3                brown
2                quick
4                fox.
1                The
```

would result in "This quick brown fox."

There are a variety of ways to sort lists or key-value pairs in both Python and SQL.

You may run and observe your pipeline multiple times if you care to, but in the end your code must fetch and reassemble all messages in order without human intervention. You may not receive messages or sort the fragments manually.

Your completed phrase should now be submitted as a message attribute for a new message that you send to a separate SQS queue, along with your computing ID.

Send to this queue URL:
```
https://sqs.us-east-1.amazonaws.com/440848399208/dp2-submit
```

To send a message with attributes, use this syntax:

```
def send_solution(uvaid, phrase)
    try:
        response = sqs.send_message(
            QueueUrl=url,
            MessageBody=message,
            MessageAttributes={
                'uvaid': {
                    'DataType': 'String',
                    'StringValue': uvaid
                },
                'phrase': {
                    'DataType': 'String',
                    'StringValue': phrase
                }
            }
        )
        print(f"Response: {response}")

    . . .
```
Be sure that your response returns a `200` HTTP response message, indicating that it has been received.

### Other Submission Notes

1. Be sure to fork this repository and commit/push your code back to it for grading.
2. Your Prefect flow should be saved to a file named `prefect.py`.
3. If you attempt to write an Airflow DAG that should be saved to a file named `airflow.py`.
4. Your code should log using the built-in logging methods for either Prefect or Airflow. You do not need to use a separate logging package. Do not save or commit log files.
5. Do not save or commit any data or database files.

## Reference

- [Working with SQS - Practical Examples](https://github.com/nmagee/learn-sqs)
- [`boto3` - SQS Client Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html)
- Prefect 
- Airflow