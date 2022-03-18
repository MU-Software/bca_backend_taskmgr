![B.Ca title image](./.github/readme/title.png)
# THIS REPOSITORY IS DEPRECATED!
Task scheduler was migrated and re-writed to Celery, and merged to the [Main API Server Repository](https://github.com/MU-Software/bca_backend).  
This repository remains a record of what was used for my graduation project in the past and is no longer working.  
The information below is based on historical information and may not apply today.  

# B.Ca Task Scheduler repository
B.Ca is a communication messenger project focusing on business card, which was conducted as a graduation work.  
This repository contains the task scheduler code written in Python.  

# Project structure
The project consists of an Android client, this API server, and a task scheduler.  
* Android client: The title says all.  
* API backend server: This handles all HTTP REST requests.  
* Task scheduler: This repository, Task scheduler handles some batch tasks that can take much time, like user db file modifications. This runs on AWS SQS and Lambda.

### AWS dependencies
This project uses some services of AWS. For example, This API server was written assuming that it would run on an AWS EC2 instance. The table below shows which services are used in the project backend.  
Service Name | Required | Usage
|   :----:   |  :----:  | :----
EC2          |   | Compute instance for API server.  
S3           | O | File storage for user-db files. User-uploaded files will be saved on API server.  
RDS          |   | API server natively supports PostgreSQL or SQLite3, but maybe it can handle MySQL/MariaDB, too (not tested tho). You don't need this if you use SQLite3.  
ElastiCache  | O | Redis, not to mention long.  
SQS          | O | Used for message queues in the task scheduler. One lambda instance is triggered per task job.  
Lambda       | O | Used as task scheduler's worker instances.  
SES          |   | Used to send mail on account-related matters such as account registration, password change, etc. This function can be off completely on `env_collection`.  
