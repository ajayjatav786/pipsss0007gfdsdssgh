#from hello_operator import HelloOperator
from airflow import DAG
from datetime import timedelta
from textwrap import dedent
from airflow.utils.dates import days_ago
from udp_transformation_operator import UDPTransformationOperator
from udp_dataload_operator import UDPDataLoadOperator
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}

with DAG(
        'etl-3',
    default_args=default_args,
    schedule_interval=timedelta(days=1),
    start_date=days_ago(2),
    tags=['operator'],
) as dag:
    #hello_task = HelloOperator(task_id='sample-task', name='foo_bar')
    a3_persistence=UDPTransformationOperator(
        task_id='UDP_Transformation_Operator',
        source_s3_key="s3://xfusion-poc-etl1/input/testing1.csv",
        dest_s3_key="s3://xfusion-poc-etl1/output/testingjson.json",
        source_aws_conn_id="POC-AWS",
        replace=True
    )

    s3_operator2=UDPDataLoadOperator(
        task_id='UDP_Data_Load_Operator',
        source_s3_key="s3://xfusion-poc-etl1/output/testingjson.json",
        source_aws_conn_id="POC-AWS",
        replace=True
    )
    a3_persistence >> s3_operator2