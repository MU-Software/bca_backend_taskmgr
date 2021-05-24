import datetime
import json
import logging
import os
import pathlib as pt
import sqlite3
import sys
import tempfile
import traceback
import typing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))

# Dirty flake8 error detection hack
import boto3  # noqa: E402
import redis  # noqa: E402
import sqlalchemy as sql  # noqa: E402
import sqlalchemy.ext.declarative as sqldec  # noqa: E402
import sqlalchemy.orm as sqlorm  # noqa: E402
# This will write temporary files on /tmp,
# so It's fine to use this on AWS lambda

import user_db_table  # noqa: E402


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Constant variables that read from environment
REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_DB = int(os.environ.get('REDIS_DB', 0))

SERVICE_DB = os.environ.get('DB_URL')

SQS_URL: str = os.environ.get('AWS_SQS_URL')
S3_BUCKET_NAME: str = os.environ.get('AWS_S3_BUCKET_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-northeast-2')

# Constant type definition
CHANGELOG_TYPE = typing.Dict[str, typing.Dict[str, typing.Dict[str, typing.Dict[str, typing.Any]]]]

# Reusable resources
# Maybe AWS credentials will be applied automatically, I guess?
s3_client = boto3.client('s3', region_name=AWS_REGION)
sqs_client = boto3.client('sqs', region_name=AWS_REGION)


def get_traceback_msg(err):
    return ''.join(traceback.format_exception(
                   etype=type(err),
                   value=err,
                   tb=err.__traceback__))


def get_service_db_session():
    service_db_engine = sql.create_engine(SERVICE_DB)
    service_db_session = sqlorm.scoped_session(
                                sqlorm.sessionmaker(
                                    autocommit=False,
                                    autoflush=False,
                                    bind=service_db_engine))
    service_db_base = sqldec.declarative_base()

    class Profile(service_db_base):
        __table__ = sql.Table(
            'TB_PROFILE', service_db_base.metadata,
            autoload=True, autoload_with=service_db_engine)

    class Card(service_db_base):
        __table__ = sql.Table(
            'TB_CARD', service_db_base.metadata,
            autoload=True, autoload_with=service_db_engine)

    class CardSubscribed(service_db_base):
        __table__ = sql.Table(
            'TB_CARD_SUBSCRIBED', service_db_base.metadata,
            autoload=True, autoload_with=service_db_engine)

    return {
        'engine': service_db_engine,
        'session': service_db_session,
        'base': service_db_base,
        'tables': {
            'TB_PROFILE': Profile,
            'TB_CARD': Card,
            'TB_CARD_SUBSCRIPTION': CardSubscribed
        }
    }


def apply_changes_on_db(fileobj: typing.IO[bytes], changelog: CHANGELOG_TYPE):
    # Create a temporary file and make a db connection to the tempfile
    temp_user_db_sqlite_conn = sqlite3.connect(fileobj.name)
    temp_user_db_engine = sql.create_engine('sqlite://', creator=lambda: temp_user_db_sqlite_conn)
    temp_user_db_session = sqlorm.scoped_session(
                                sqlorm.sessionmaker(
                                    autocommit=False,
                                    autoflush=False,
                                    bind=temp_user_db_engine))
    temp_user_db_base = sqldec.declarative_base()

    # Create tables
    ProfileTable = type('ProfileTable', (temp_user_db_base, user_db_table.Profile), {})
    CardTable = type('CardTable', (temp_user_db_base, user_db_table.Card), {})
    CardSubscriptionTable = type('CardSubscriptionTable', (temp_user_db_base, user_db_table.CardSubscription), {})

    table_order = ['TB_PROFILE', 'TB_CARD', 'TB_CARD_SUBSCRIPTION']
    table_map = {
        'TB_PROFILE': ProfileTable,
        'TB_CARD': CardTable,
        'TB_CARD_SUBSCRIPTION': CardSubscriptionTable
    }

    for table_name in table_order:
        if table_name in changelog and changelog[table_name]:
            table = table_map[table_name]
            table_changelog = changelog[table_name]

            for uuid, row_data in table_changelog.items():
                uuid = int(uuid)
                action = row_data['action']
                column_value_map = row_data['data']

                # Do modification job
                if action == 'add':
                    is_row_exists = False
                    new_row = table.query.filter(table.uuid == uuid).first()
                    if new_row:
                        # There's a row already inside the User's DB
                        is_row_exists = True
                    else:
                        new_row = table()

                    for column, value in column_value_map.items():
                        if value and column.endswith('_at'):
                            value = datetime.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
                        setattr(new_row, column, value)

                    if not is_row_exists:
                        temp_user_db_session.add(new_row)
                elif action == 'modify':
                    target_row = temp_user_db_session.query(table).filter(table.uuid == uuid).first()
                    if not target_row:
                        # Get this row's whole data from service DB and migrate to User's DB
                        service_db = get_service_db_session()
                        service_db_table = service_db['tables'][table_name]
                        query_result = service_db_table.query.filter(service_db_table.uuid == uuid).first()
                        if not query_result:
                            continue

                        target_row = table()
                        target_columns: list[str] = [
                            (column_tb['name'], column_tb['type'])
                            for column_tb in table.column_descriptions]
                        for column_name, column_type in target_columns:
                            value = getattr(query_result, column_name)
                            if value and column_type == sql.DateTime:
                                value = datetime.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
                            setattr(target_row, column_name, value)
                    else:
                        for column, value in column_value_map.items():
                            if value and column.endswith('_at'):
                                value = datetime.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
                            setattr(target_row, column, value)
                elif action == 'delete':
                    target_row = table.query.filter(table.uuid == uuid).first()
                    if target_row:
                        temp_user_db_session.delete(target_row)
                # Do commit on every row changes to prevent unexpected unique_fail error
                temp_user_db_session.commit()
        # Do this just in case
        temp_user_db_session.commit()

    temp_user_db_session.commit()
    temp_user_db_engine.dispose()  # Disconnect all connections (for safety)
    fileobj.seek(0)


def user_db_modify_worker(events, context):
    logger.info(events)
    for event in events['Records']:
        # Get task message from event
        task_receipt_handle: str = event['receiptHandle']
        task_hash: str = event['md5OfBody']
        task_body: dict = json.loads(event['body'])

        try:
            db_owner_id: int = task_body['db_owner_id']
            changelog: CHANGELOG_TYPE = task_body['changelog']
            redis_lambda_worker_id = 'aws_lambda_userdb_modify_worker='+str(db_owner_id)

            # Redis is used as mutex,
            # to prevent multiple lambda functions editing one user's db file.
            redis_db: redis.StrictRedis = redis.StrictRedis(
                host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB)

            # Check mutex
            redis_mutex = redis_db.get(redis_lambda_worker_id)
            if redis_mutex and redis_mutex != task_hash.encode():
                # There's a running Lambda instance that modifies this user's db file,
                # so delay this task and process another tasks first.
                raise Exception(f'There\'s a task that modifies user {str(db_owner_id)}\'s DB file. '
                                'Retry after 45 seconds')

            # It's safe to modify user db file.
            # Set mutex on redis
            redis_db.set(
                redis_lambda_worker_id, task_hash,
                datetime.timedelta(minutes=6))

            # TODO: WORKER THAT MODIFIES USER DB MUST BE SEPARATED TO ANOTHER LAMBDA INSTANCE
            # Download user db file to modify
            user_db_file: typing.IO[bytes] = tempfile.NamedTemporaryFile('w+b', delete=True)
            s3_client.download_fileobj(
                Bucket=S3_BUCKET_NAME,
                Key=f'user_db/{db_owner_id}/sync_db.sqlite',
                Fileobj=user_db_file)

            # Do a modify tasks
            apply_changes_on_db(user_db_file, changelog)

            # Upload user db file
            user_db_file_pt = pt.Path(user_db_file.name)
            with user_db_file_pt.open('rb') as fp:
                s3_client.upload_fileobj(fp,
                                         S3_BUCKET_NAME,
                                         f'user_db/{db_owner_id}/sync_db.sqlite')

            # Remove mutex on redis
            redis_db.delete(redis_lambda_worker_id)

            # Remove jobs
            sqs_client.delete_message(
                QueueUrl=SQS_URL,
                ReceiptHandle=task_receipt_handle)

        except Exception as err:
            logger.error(get_traceback_msg(err))
            sqs_client.change_message_visibility(
                QueueUrl=SQS_URL,
                ReceiptHandle=task_receipt_handle,
                VisibilityTimeout=45)  # Make this task visible again after 45 seconds

    # Exit this lambda instance as there's no task in queue
    return {
        'statusCode': 200,
        'event': event,
        'body': json.dumps({'message': 'NO_TASK_IN_QUEUE', })
    }

# MUsoftware, /H/Y/P/E/R/I/O/N/ /L/A/B/
