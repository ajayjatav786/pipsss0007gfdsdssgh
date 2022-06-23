from .validator import validate_file


def test_base():
    assert validate_file("../airflow/airflow/operators/bash.py") == True
    assert validate_file("../airflow/airflow/operators/branch.py") == True
    assert validate_file("../airflow/airflow/secrets/local_filesystem.py") == True
    assert validate_file("../airflow/airflow/secrets/metastore.py") == True
    assert validate_file("../airflow/airflow/sensors/base.py") == True
    assert validate_file("../airflow/airflow/providers/airbyte/hooks/airbyte.py") == True
    assert validate_file("../airflow/airflow/providers/yandex/operators/yandexcloud_dataproc.py") == True
    assert validate_file("../airflow/airflow/providers/zendesk/hooks/zendesk.py") == True
    assert validate_file("../airflow/airflow/utils/log/colored_log.py") == True
    assert validate_file("../airflow/airflow/hooks/base.py") == True
    assert validate_file("../airflow/airflow/hooks/webhdfs_hook.py") == False
    assert validate_file("../airflow/airflow/hooks/zendesk_hook.py") == False
    assert validate_file("../airflow/airflow/operators/bash_operator.py") == False
    assert validate_file("../airflow/airflow/contrib/sensors/wasb_sensor.py") == False
    assert validate_file("../airflow/airflow/contrib/sensors/weekday_sensor.py") == False
    assert validate_file("../airflow/airflow/contrib/utils/log/task_handler_with_custom_formatter.py") == False
    assert validate_file("../airflow/airflow/sensors/base_sensor_operator.py") == False
    assert validate_file("../airflow/airflow/utils/log/cloudwatch_task_handler.py") == False
