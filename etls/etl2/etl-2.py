from datetime import datetime
from airflow import DAG
from airflow.providers.amazon.aws.transfers.mysql_to_s3 import MySQLToS3Operator
from airflow.providers.amazon.aws.operators.s3_file_transform import S3FileTransformOperator
from airflow.providers.amazon.aws.transfers.s3_to_redshift import S3ToRedshiftOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from udp_dataload_salesforce import UDPDataLoadSalesforce

with DAG(
    # Values set manually in UI
    dag_id="etl-2",
    schedule_interval="@once",
    start_date=datetime(2021,1,1),
    # Values automatically set by default
    concurrency=16,max_active_runs=16,dagrun_timeout=None,orientation="LR",catchup=False,is_paused_upon_creation=False
) as dag:

    task_aurora = MySQLToS3Operator(
        # Values set manually in UI
        query="SELECT PersonID, FirstName, LastName, MiddleName, DateOfBirth, Suffix, Prefix, ActiveFlag, CreateDate, UpdateDate, CreatedBy, UpdatedBy, GenderID FROM PERS_CAP.Person LIMIT 50;",
        s3_bucket="xfusion-poc-etl1",
        s3_key="input/person.csv",
        mysql_conn_id="POC-Aurora",
        aws_conn_id="POC-AWS",
        index=False,
        header=True,
        task_id="task_aurora",
        # Values automatically set by default
        email_on_retry=False,email_on_failure=False,retries=0,retry_exponential_backoff=False,depends_on_past=False,wait_for_downstream=False,priority_weight=1,pool_slots=1,task_concurrency=None,do_xcom_push=False
    )

    task_transform = S3FileTransformOperator(
        # Values set manually in UI
        source_s3_key="s3://xfusion-poc-etl1/input/person.csv",
        dest_s3_key="s3://xfusion-poc-etl1/output/person.csv",
        transform_script="/opt/airflow/dags/transformations/transform-uppercase.py",
        source_aws_conn_id="POC-AWS",
        dest_aws_conn_id="POC-AWS",
        replace=True,
        task_id="task_transform",
        # Values automatically set by default
        email_on_retry=False,email_on_failure=False,retries=0,retry_exponential_backoff=False,depends_on_past=False,wait_for_downstream=False,priority_weight=1,pool_slots=1,task_concurrency=None,do_xcom_push=False
    )

    task_dataload_salesforce = UDPDataLoadSalesforce(
        # Values set manually in UI
        source_s3_key="s3://xfusion-poc-etl1/output/person.csv",
        source_aws_conn_id="POC-AWS",
        replace=True,
        task_id="task_dataload_salesforce",
        # Values automatically set by default
        email_on_retry=False,email_on_failure=False,retries=0,retry_exponential_backoff=False,depends_on_past=False,wait_for_downstream=False,priority_weight=1,pool_slots=1,task_concurrency=None,do_xcom_push=False
    )


    task_aurora >> task_transform >> task_dataload_salesforce
