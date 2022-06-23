from starlette.testclient import TestClient
from main import app, do_init_airflow_folder
import pytest


# xfusion Test Repo
XF_REPO_ACCOUNT = "xfusiontest01"
XF_REPO_TOKEN = "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"
XF_FILENAME_TEST = "generatedDAG/GEN_dag.py"
XF_REPO_TEST = "Test"
XF_FILE_SHA = "5afc324a34dc6850cd6892d2abfe509dd8d31667"

client = TestClient(app)


def test_github_get_tree_graphql_ok():
    response = client.get(f"/github/tree/graphql?token={XF_REPO_TOKEN}&login={XF_REPO_ACCOUNT}")
    assert response.status_code == 200
    repositories =[elem["name"] for elem in response.json()["repositories"]]
    assert XF_REPO_ACCOUNT in repositories

def test_github_get_tree_graphql_bad():
    response = client.get(f"/github/tree/graphql?token={XF_REPO_TOKEN}&login=bad_account")
    assert response.status_code == 503
    
def test_github_get_content_of_file_ok():
    response = client.get(f"/github/files?token={XF_REPO_TOKEN}&repository={XF_REPO_TEST}&filename={XF_FILENAME_TEST}&sha={XF_FILE_SHA}")
    assert response.status_code == 200
    assert "from airflow import DAG" in response.text


def test_v2_airflow_operators():
    response = client.get("/stats/v2")
    assert response.status_code == 200
    assert response.json()[0]["total"] == 35


def test_v2_providers_operators():
    response = client.get("/stats/v2")
    assert response.status_code == 200
    assert response.json()[1]["total"] == 700


def test_v2_modules():
    response = client.get("/modules/v2")
    assert response.status_code == 200
    assert "airflow.operators.bash" in response.json()


def test_v2_types():
    response = client.get("/types/v2")
    assert response.status_code == 200
    assert len(response.json()) == 162


def test_v2_operators_base_operator():
    response = client.get("/operators/v2")
    assert response.status_code == 200
    assert response.json()[0]["operators"][4]["name"] == "BashSensor"


def test_v2_operators_airbyte():
    response = client.get("/operators/v2")
    assert response.status_code == 200
    assert response.json()[1]["subcategory"][0]["operators"][0]["name"] == "AirbyteHook"


def test_v2_operators_aws_athena():
    response = client.get("/operators/v2")
    assert response.status_code == 200
    assert response.json()[1]["subcategory"][1]["operators"][1]["name"] == "AWSAthenaOperator"


def test_v2_operator_bash():
    response = client.get("/operators/v2/airflow.operators.bash")
    assert response.status_code == 200
    assert response.json()["name"] == "BashOperator"


def test_v2_operator_bash_parameter_bash_command():
    response = client.get("/operators/v2/airflow.operators.bash")
    assert response.status_code == 200
    assert response.json()["parameters"][0]["id"] == "bash_command"
    assert response.json()["parameters"][0]["type"] == "str"
    assert response.json()["parameters"][0]["typeCategory"] == "elem"


def test_v2_operator_bash_parameter_env():
    response = client.get("/operators/v2/airflow.operators.bash")
    assert response.status_code == 200
    assert response.json()["parameters"][1]["id"] == "env"
    assert response.json()["parameters"][1]["type"] == "Dict[str,str]"
    assert response.json()["parameters"][1]["typeCategory"] == "dict"


def test_v2_operator_bash_parameter_email():
    response = client.get("/operators/v2/airflow.operators.bash")
    assert response.status_code == 200
    assert response.json()["parameters"][6]["id"] == "email"
    assert response.json()["parameters"][6]["type"] == "Union[str,Iterable[str]]"
    assert response.json()["parameters"][6]["typeCategory"] == "union"


def test_v2_operator_bash_parameter_dag():
    response = client.get("/operators/v2/airflow.operators.bash")
    assert response.status_code == 200
    assert response.json()["parameters"][17]["id"] == "dag"
    assert response.json()["parameters"][17]["type"] == "airflow.models.DAG"
    assert response.json()["parameters"][17]["typeCategory"] == "complex"


def test_get_operator_version_ok():
    response = client.get("/operators/v2")
    sources_in_version =[elem["name"] for elem in response.json()]
    assert "airflow" in sources_in_version
    assert response.status_code == 200
    #assert response.json()[0]["source"] == "airflow"


def test_get_operator_v2_search_ok():
    response = client.get("/operators/v2/search?text=airflow")
    assert response.status_code == 200
    assert response.json()[0]["source"] == "airflow"

def test_get_operator_v2_search_bad():
    response = client.get("/operators/v2/search")
    assert response.status_code == 400
    assert response.json()["detail"] == "Url should contains => search?text=(part of desired data type)"


def test_get_operator_v2_by_name():
    response = client.get("/operators/v2/BashOperator")
    assert response.status_code == 200
    assert response.json()["name"] == "BashOperator"


def test_get_operator_v2_by_name_not_found():
    response = client.get("/operators/v2/NonexistentOperator")
    assert response.status_code == 404
    assert response.json() ["detail"]  == "Operator v2.NonexistentOperator not found."


def test_get_operator_v2_tree():
    response = client.get("/operators/v2/PythonOperator/tree")
    assert response.status_code == 200
    assert response.json() == ["PythonOperator", "--BaseOperator"]


def test_get_operator_v2_tree_not_found():
    response = client.get("/operators/v2/NonexistentOperator/tree")
    assert response.status_code == 404
    assert response.json()["detail"] == "Operator v2.NonexistentOperator not found."


def test_post_catalog():
    response = client.post("/catalog/v2/airflow")
    assert response.status_code == 200
    assert "successfully" and "documents inserted" in response.json()["detail"]


def test_post_catalog_bad_source():
    response = client.post("/catalog/v2/bad_source")
    assert response.status_code == 400
    assert response.json()["detail"] == "Source should be 1 of: airflow | providers | udp"


def test_post_catalog_bad_version_airflow():
    response = client.post("/catalog/v10/airflow")
    assert response.status_code == 404
    assert response.json()["detail"] == "Error, airflow version's folder v10 not found."


def test_post_catalog_bad_version_udp():
    response = client.post("/catalog/v8/udp")
    assert response.status_code == 404
    assert response.json()["detail"] == "Error, udp version's folder v8 not found."


def test_delete_catalog_v2_bad_source():
    response = client.delete("/catalog/v2/bad_source")
    assert response.json()["detail"] == "Source should be: airflow | providers | udp"


def test_delete_catalog_bad_version_udp():
    response = client.delete("/catalog/v10/udp")
    assert response.json()["detail"] == "0 documents deleted in catalog.operators.v10.udp"


def test_post_catalog_init():
    response = client.post("/catalog/init")
    if response.status_code == 200:  # Success
        assert response.json()["detail"] == "Operator Catalog initialized successfully."
    elif response.status_code == 500:  # Error
        assert "Failed to create parser:" in response.json()["detail"]
