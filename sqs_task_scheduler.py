import boto3
import datetime
import json
import os
import redis


class UserDBHandler:
    sqs_client = None
    sqs_url: str = ''
    lambda_client = None

    redis_db: redis.StrictRedis = None

    def __init__(self, event, context):
        self.sqs_url = os.environ.get('AWS_SQS_URL')
        self.aws_region = os.environ.get('AWS_REGION')

        # Maybe AWS credentials will be automatically applied, I think?
        self.sqs_client = boto3.resource(service_name='sqs', region_name=self.aws_region)
        self.lambda_client = boto3.resource(service_name='lambda', region_name=self.aws_region)

        # Redis is used as mutex,
        # to prevent multiple lambda functions editing one user's db file.
        self.redis_db = redis.StrictRedis(
            host=os.environ.get('REDIS_HOST'),
            port=os.environ.get('REDIS_PORT'),
            password=os.environ.get('REDIS_PASSWORD'),
            db=os.environ.get('REDIS_DB'))

        while True:
            # Pull SQS Messages
            sqs_task_response = json.loads(self.sqs_client.receive_message(
                QueueUrl=self.sqs_url,
                MaxNumberOfMessages=10,  # Maximum is 10
                AttributeNames=['All', ]))

            if not sqs_task_response.get('Messages', None):
                # If there's no task on queue, then exit this lambda.
                return {
                    'statusCode': 200,
                    'event': event,
                    'body': json.dumps({'message': 'NO_TASK_IN_QUEUE', })
                }

            for task_message in sqs_task_response:
                # Get task data
                db_owner_id = task_message['Body']['db_owner_id']
                task_hash = task_message['MD5OfBody']
                task_receipt_handle = task_message['ReceiptHandle']
                redis_lambda_worker_id = 'aws_lambda_worker='+str(db_owner_id)

                # Check mutex
                redis_mutex = self.redis_db.get(redis_lambda_worker_id)
                if redis_mutex:
                    # User db file is modified by another Lambda, so make this message visible after 45secs
                    self.sqs_client.change_message_visibility(
                        QueueUrl=self.sqs_url,
                        ReceiptHandle=task_receipt_handle,
                        VisibilityTimeout=45)

                # If it's safe to modify user db, then register mutex and run lambda
                self.redis_db.set(
                    redis_lambda_worker_id, task_hash,
                    datetime.timedelta(minutes=10))

                self.lambda_client.invoke(
                    FunctionName=os.environ.get('AWS_LAMBDA_USERDB_HANDLER_NAME'),
                    InvocationType='Event',
                    Payload=json.dumps({
                    'queueUrl': self.sqs_url,
                    'message': task_message,
                }))

                # Delete message as we are processing it
                self.sqs_client.delete_message(
                    QueueUrl=self.sqs_url,
                    ReceiptHandle=task_receipt_handle)
