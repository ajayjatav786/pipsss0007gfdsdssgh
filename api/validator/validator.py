import re


def validate_file(filename):
    try:
        with open(filename, encoding="utf8") as f_obj:
            contents = f_obj.read()
    except FileNotFoundError:
        msg = f"The file {filename} does not exists!"
        print(msg)
        return False
    else:
        matches = re.findall(r"\w*This module is deprecated\w*", contents)
        num_words = len(matches)
        matches1 = re.findall(r"\w*import BaseOperator\w*", contents)
        num_words1 = len(matches1)
        matches2 = re.findall(r"\w*import BaseHook\w*", contents)
        num_words2 = len(matches2)
        matches3 = re.findall(r"\w*import BaseSecretsBackend\w*", contents)
        num_words3 = len(matches3)
        matches4 = re.findall(r"\w*import BaseSensorOperator\w*", contents)
        num_words4 = len(matches4)
        matches5 = re.findall(r"\w*import FileTaskHandler\w*", contents)
        num_words5 = len(matches5)

        if num_words >= 1:
            # print(f"{filename} = 0")
            # invalid
            return False
        if num_words1 >= 1 or num_words2 >= 1 or num_words3 >= 1 or num_words4 >= 1 or num_words5 >= 1:
            # print(f"{filename} = 2")
            # valid by inheriting
            return True
        # valid
        # print(f"{filename} = 1")
        return True


def find_words(filename):
    try:
        with open(filename) as f_obj:
            contents = f_obj.read()
    except FileNotFoundError:
        msg = "The file " + filename + " does not exists"
        print(msg)
    else:
        matches = re.findall(r"\w*This module is deprecated\w*", contents)
        num_words = len(matches)
        matches1 = re.findall(r"\w*import BaseOperator\w*", contents)
        num_words1 = len(matches1)
        matches2 = re.findall(r"\w*import BaseHook\w*", contents)
        num_words2 = len(matches2)
        matches3 = re.findall(r"\w*import BaseSecretsBackend\w*", contents)
        num_words3 = len(matches3)
        matches4 = re.findall(r"\w*import BaseSensorOperator\w*", contents)
        num_words4 = len(matches4)
        matches5 = re.findall(r"\w*import FileTaskHandler\w*", contents)
        num_words5 = len(matches5)

        if num_words >= 1:
            print(filename + " = 0")  # invalid
        else:
            if num_words1 >= 1 or num_words2 >= 1 or num_words3 >= 1 or num_words4 >= 1 or num_words5 >= 1:
                print(filename + " = 2")  # valid by inheriting
            else:
                print(filename + " = 1")  # valid


if __name__ == "__main__":
    # filenames = ['base.py', 'base_hook.py', 'dbapi.py', 'dbapi_hook.py', 'desktop.ini',
    # 'docker_hook.py', 'druid_hook.py', 'filesystem.py', 'hdfs_hook.py', 'hive_hooks.py',
    # 'http_hook.py', 'jdbc_hook.py', 'mssql_hook.py', 'mysql_hook.py', 'oracle_hook.py',
    # 'pig_hook.py', 'postgres_hook.py', 'presto_hook.py', 'README.md', 'S3_hook.py',
    # 'samba_hook.py', 'slack_hook.py', 'sqlite_hook.py', 'subprocess.py', 'webhdfs_hook.py',
    # 'zendesk_hook.py', '__init__.py','gasgf.txt']
    filenames = [
        "../airflow/airflow/operators/bash.py",
        "../airflow/airflow/operators/branch.py",
        "../airflow/airflow/secrets/local_filesystem.py",
        "../airflow/airflow/secrets/metastore.py",
        "../airflow/airflow/sensors/base.py",
        "../airflow/airflow/providers/airbyte/hooks/airbyte.py",
        "../airflow/airflow/providers/yandex/operators/yandexcloud_dataproc.py",
        "../airflow/airflow/providers/zendesk/hooks/zendesk.py",
        "../airflow/airflow/utils/log/colored_log.py",
        "../airflow/airflow/hooks/base.py",
        "../airflow/airflow/hooks/webhdfs_hook.py",
        "../airflow/airflow/hooks/zendesk_hook.py",
        "../airflow/airflow/operators/bash_operator.py",
        "../airflow/airflow/contrib/sensors/wasb_sensor.py",
        "../airflow/airflow/contrib/sensors/weekday_sensor.py",
        "../airflow/airflow/contrib/utils/log/task_handler_with_custom_formatter.py",
        "../airflow/airflow/sensors/base_sensor_operator.py",
        "../airflow/airflow/utils/log/cloudwatch_task_handler.py",
    ]
    # for filename in filenames:
    #     find_words(filename)
    for filename in filenames:
        print(f"{validate_file(filename)} => {filename}")
