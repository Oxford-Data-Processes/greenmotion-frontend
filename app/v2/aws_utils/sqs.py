import boto3
import json
from typing import List, Dict, Optional


class SQSHandler:
    def __init__(self) -> None:
        """
        Initializes the SQSHandler by creating an SQS client using AWS credentials
        from environment variables.
        """
        self.sqs_client = None  # type: Optional[boto3.client]

    @staticmethod
    def extract_datetime_from_sns_message(message: str) -> Optional[str]:
        """
        Extracts a datetime string from the given SNS message.

        Args:
            message (str): The SNS message from which to extract the datetime.

        Returns:
            Optional[str]: The extracted datetime string if found, otherwise None.
        """
        return None

    def delete_all_sqs_messages(self, queue_url: str) -> None:
        """
        Deletes all messages from the specified SQS queue.

        Args:
            queue_url (str): The URL of the SQS queue from which to delete messages.
        """
        pass

    def get_all_sqs_messages(self, queue_url: str) -> List[Dict[str, Optional[str]]]:
        """
        Retrieves all messages from the specified SQS queue.

        Args:
            queue_url (str): The URL of the SQS queue from which to retrieve messages.

        Returns:
            List[Dict[str, Optional[str]]]: A list of dictionaries containing the
            timestamp and message body for each message.
        """
        queue_name = queue_url.split("/")[-1]
        file_path = f"mocks/sqs/{queue_name}/sqsmessage.json"
        with open(file_path) as f:
            messages = json.load(f)
        return [{"timestamp": msg["timestamp"], "message": msg["message"]} for msg in messages]
