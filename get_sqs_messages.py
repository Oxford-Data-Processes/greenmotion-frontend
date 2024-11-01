import os
from aws_utils import iam

iam_instance = iam.IAM(stage=os.environ["STAGE"])
iam.AWSCredentials.get_aws_credentials(
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID_ADMIN"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY_ADMIN"],
    iam_instance=iam_instance,
)

import os
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict


class SQSHandler:
    def __init__(self) -> None:
        """
        Initializes the SQSHandler by creating an SQS client using AWS credentials
        from environment variables.
        """
        self.sqs_client = boto3.client(
            "sqs",
            region_name=os.environ["AWS_REGION"],
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=os.environ["AWS_SESSION_TOKEN"],
        )

    def get_all_sqs_messages(self, queue_url: str) -> List[Dict[str, str]]:
        """
        Retrieves all messages from the specified SQS queue.

        Args:
            queue_url (str): The URL of the SQS queue from which to retrieve messages.

        Returns:
            List[Dict[str, str]]: A list of messages from the SQS queue.
        """
        messages: List[Dict[str, str]] = []
        while True:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,
                VisibilityTimeout=30,
            )
            if "Messages" in response:
                messages.extend(response["Messages"])
            else:
                break
        return messages

    def delete_all_sqs_messages(self, queue_url: str) -> None:
        """
        Deletes all messages from the specified SQS queue.

        Args:
            queue_url (str): The URL of the SQS queue from which to delete messages.
        """
        all_messages: List[Dict[str, str]] = self.get_all_sqs_messages(queue_url)
        for message in all_messages:
            try:
                self.sqs_client.delete_message(
                    QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
                )
            except ClientError as e:
                raise Exception(f"Error deleting message {message['MessageId']}: {e}")


sqs_handler = SQSHandler()
queue_url = "greenmotion-lambda-queue"
sqs_handler.delete_all_sqs_messages(queue_url)
messages = sqs_handler.get_all_sqs_messages(queue_url)
print(messages)
