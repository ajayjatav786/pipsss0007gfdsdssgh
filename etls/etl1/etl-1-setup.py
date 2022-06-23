from datetime import datetime
from airflow import DAG
from airflow.providers.amazon.aws.operators.s3_delete_objects import S3DeleteObjectsOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.amazon.aws.transfers.s3_to_redshift import S3ToRedshiftOperator

with DAG(
    # Values set manually in UI
    dag_id="etl-1-setup",
    schedule_interval="@once",
    start_date=datetime(2021,1,1),
    # Values automatically set by default
    concurrency=16,max_active_runs=16,dagrun_timeout=None,orientation="LR",catchup=False,is_paused_upon_creation=False
) as dag:

    task_delete_input = S3DeleteObjectsOperator(
        # Values set manually in UI     
        bucket="xfusion-poc-etl1",
        keys="input/person.csv",
        aws_conn_id="POC-AWS",
        task_id='task_delete_input',
        # Values automatically set by default
        email_on_retry=False,email_on_failure=False,retries=0,retry_exponential_backoff=False,depends_on_past=False,wait_for_downstream=False,priority_weight=1,pool_slots=1,task_concurrency=None,do_xcom_push=False        
    )

    task_postgres = PostgresOperator(
        # Values set manually in UI
        sql="TRUNCATE table staging.person;",
        postgres_conn_id="POC-Redshift",
        database="dev",
        task_id="task_postgres",
        # Values automatically set by default
        autocommit=False,email_on_retry=False,email_on_failure=False,retries=0,retry_exponential_backoff=False,depends_on_past=False,wait_for_downstream=False,priority_weight=1,pool_slots=1,task_concurrency=None,do_xcom_push=False
    )

    task_redshift = S3ToRedshiftOperator(
        # Values set manually in UI
        schema="dev.prod",
        table="person",
        s3_bucket="xfusion-poc-etl1",
        s3_key="Person_Aurora_original.csv",
        redshift_conn_id="POC-Redshift",
        aws_conn_id="POC-AWS",
        truncate_table=True,
        copy_options=['csv','IGNOREHEADER 1'],
        task_id="task_redshift",
        # Values automatically set by default
        email_on_retry=False,email_on_failure=False,retries=0,retry_exponential_backoff=False,depends_on_past=False,wait_for_downstream=False,priority_weight=1,pool_slots=1,task_concurrency=None,do_xcom_push=False
    )

    task_delete_input >> task_postgres >> task_redshift
