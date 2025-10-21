# ds3022-data-project-2

Your assignment is to write a Prefect data pipeline that will retrieve a number of messages from an SQS queue, parse their contents, and reassemble a message made up of the fragments from each message.

Your pipeline can run a single time to produce a complete result, or it can run on a schedule to produce a complete result.

You can run your pipeline as many times as you like for testing.

## Task 1 - Populate your SQS Queue

Using your UVA computing ID, append it to this API endpoint:

```
https://j9y2xa0vx0.execute-api.us-east-1.amazonaws.com/api/scatter/<UVA_ID>
```

You must call this URL by way of an HTTP `POST` request. To do this using the `requests` library in python:

```
import requests

url = "https://j9y2xa0vx0.execute-api.us-east-1.amazonaws.com/api/scatter/nem2p"

payload = requests.post(url).json
```

The `payload` object contains your SQS URL:

```
>>> payload
{'hello': 'mst3k', 'sqs_url': 'https://sqs.us-east-1.amazonaws.com/440848399208/mst3k'}
```

Meanwhile, exactly XX messages have now been sent to your SQS queue. These have been sent with a variety of random `DelaySeconds` values ranging from 10 to 900 seconds.

Keep these delays in mind as you proceed to the next task.

**NOTE** This step should not be repeated if your pipeline needs to run more than once - it will clear your queue and repopulate all messages each time.

## Task 2 - Observe Your Queue and Collect Messages

Devise a way for your pipeline to track how many messages are available for pickup. As it gets attributes about your queue, notice that there are three values that count messages:

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

Store the values you fetch for each message. There are a variety of ways to store them.

Some notes:

- Recall that even though the `order_no` value will appear as if it is an integer, Python will see it as a string by default.
- You must also fetch the `ReceiptHandle` for each message and delete it after storing its data.
- Your pipeline must receive, parse, and delete ALL messages completely when run.

## Task 3 - Reassemble the Message and Submit

Using the two fields collected from each message, now reassemble the complete message into a single phrase by ordering them using the `order_no` value.

Your completed phrase should now become the message attributes for a new message that you send to a separate SQS queue.

Send to this queue URL:
```
xxxxxx
```

To send