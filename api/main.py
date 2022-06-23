from fastapi import FastAPI, HTTPException, Query, File, Form, UploadFile, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from pymongo.common import validate_non_negative_int_or_basestring
import uvicorn
import requests
import os
import json
import datetime
from typing import List, Optional
from parser import *
from dotenv import load_dotenv

from githubconnector.githubconnector import GitHubConnector

import jenkins
from typing import Optional

from githubconnector.jenkinfile import *
from util.jenkinformat import *
from pickle import APPEND
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
# from werkzeug.security import safe_str_cmp
from werkzeug.datastructures import FileStorage
from boto.s3.connection import S3Connection
from boto.gs.connection import GSConnection
from io import BytesIO
from google.cloud import storage
import boto3, json, os
from botocore.exceptions import NoCredentialsError
from github import Github

TITLE = "xFusion Operator Catalog API"
VERSION = "1.5.0 - [12-13-2021]"

# Root folder inside Docker container
ROOT_FOLDER = "./repo/"

load_dotenv()

app = FastAPI(
    title=TITLE,
    description="xFusion Operator Catalog API for xFusion UDP Platform",
    version=VERSION
)

# app.config['UPLOAD_FOLDER'] = os.getcwd()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# MongoDB connection string, defined in ENVIRONMENT variables
mongodb_conn = (
    # During DEV
    f'mongodb://{os.environ.get("MONGODB_USER")}:{os.environ.get("MONGODB_PASS")}@{os.environ.get("MONGODB_HOST")}'
    # During PROD
    # f'mongodb://{"xfadmin"}:{"admin123#"}@{"10.200.10.250"}:{"28050"}'
)


class GitHubNewRepoRequest(BaseModel):
    token: str
    name: str


class GitHubNewBranchRequest(BaseModel):
    token: str
    repository: str
    source_branch: str
    target_branch: str
    source_commit: Optional[str] = None


class UserDataSessionRequest(BaseModel):
    action: str
    previewFlag: str
    numRecordsForPreview: str
    dataAssetID: str
    dataAssetType: str
    userID: str
    customerID: str
    sessionKey: str
    createNewSession: str
    includeDataProfileInformation: str
    dtWorkflow: str
    paginationParam: str
    maxReturnRecordCount: str
    dataExportFormat: str


# @app.get("/userDataSession")
# async def user_data_session(payload: UserDataSessionRequest):
#     userdatasessiondata = UserDataSession(payload)
#     res = userdatasessiondata.get_login_session()
#     return res


@app.on_event("startup")
def startup_event():
    do_init_airflow_folder(starting=True)


# @app.get("/userDataSession")
# async def user_data_session(payload: UserDataSessionRequest):
#     userdatasessiondata = UserDataSession(payload)
#     res = userdatasessiondata.get_login_session()
#     return res


@app.get("/github/tree")
async def github_get_tree(token: str):
    """Returns a tree with repositories, branches and versions from a GitHub account"""
    github = GitHubConnector(token)
    res = github.get_tree()
    return res


@app.get("/github/test_api")
async def test_api(token: str):
    """Returns a tree with repositories, branches and versions from a GitHub account"""
    github = GitHubConnector(token)
    res = github.test_py_pi()
    return res


@app.get("/github/tree/graphql")
async def github_get_tree_graphql(token: str, login: str, commit_qty: Optional[str] = '1'):
    """Returns a tree with repositories, branches and last version (commit) from a GitHub account """
    try:
        github = GitHubConnector(token)
        res = github.get_tree_graphql(login, commit_qty)
    except Exception as ex:
        raise HTTPException(status_code=503, detail=str(ex))
    return res


@app.post("/github/repositories")
async def github_create_repo(data: GitHubNewRepoRequest):
    """Creates a new repository in a GitHub account"""
    github = GitHubConnector(data.token)
    github.create_repo(repo_name=data.name)
    return {"detail": f"Repository {data.name} created successfully."}


@app.post("/github/branches")
async def github_create_branch(data: GitHubNewBranchRequest):
    """Creates a new branch in the repository from a source branch"""
    github = GitHubConnector(data.token)
    github.create_branch(
        repo_name=data.repository,
        source_branch=data.source_branch,
        target_branch=data.target_branch,
        source_commit=data.source_commit,
    )
    return {"detail": f"Branch {data.target_branch} created successfully inside {data.repository}."}


@app.post("/github/files")
async def github_upsert_file(
        token: str = Form(...),
        repository: str = Form(...),
        branch: str = Form(...),
        current_version: str = Form(...),
        filename: str = Form(...),
        filecontent: UploadFile = File(...),
):
    """Inserts or updates (if exists) a file (from path) inside a branch of the repository"""
    contents = filecontent.file.read()
    github = GitHubConnector(token)
    github.upsert_file(
        repo_name=repository,
        branch=branch,
        filename=filename,
        filecontent=contents,
        current_version=current_version
    )
    return {"detail": f"File {filename} updated successfully inside {repository} » {branch}"}


@app.post("/github/clone")
def github_clone_repo(
        token: str = Form(...),
        old_repository: str = Form(...),
        new_repository: str = Form(...),
):
    """Clone exisiting repository and create new"""
    github = GitHubConnector(token)

    # Entering old repo and get info of that repo
    old_repo = old_repository
    repo = github.get_repoo(old_repo)
    print(repo)

    # Entering new Repo and creating it
    new_repo = new_repository
    github.create_neww_repo(new_repo)

    # getting files from old repository
    all_files = github.gett_files_from_old(repo)

    # adding files from old repository to new repo
    github.update_to_new(repo, new_repo, all_files)
    return {"detail": f"Successfully cloned {new_repo} repository from {old_repo}"}


@app.post("/github/upload/operator/{version}")
async def github_upload_operator(
        version: str,
        token: str = Form(...),
        customer_id: str = Form(...),
        files: List[UploadFile] = File(...)
):
    # Validate if valid file/s
    if len(files) > 0 and not files[0].filename:
        msg = f"A valid file or files must be provided."
        raise HTTPException(status_code=400, detail=msg)
    # 1) Upload to GitHub
    github = GitHubConnector(token)
    # print(f'files -> {files}')
    try:
        # Upload ZIP file
        if len(files) == 1 and files[0].filename.endswith(".zip"):
            res = github.upload_zip(
                version=version,
                file=files[0]
            )
            # Imprecise if subfolder
            res = "All"
        else:
            # Upload Operator
            res = github.upload_operator(
                version=version,
                files=files
            )
    except Exception as ex:  # Filter files exceptions
        print(ex)
        msg = f"Error in Upload Operator - {ex}"
        # exception object to str
        ex_str = str(ex).replace('\'', '"')
        errors_list_dict = json.loads(ex_str)
        response = {}
        response["message"] = "Error in Upload Operator"
        response["errors_found"] = errors_list_dict
        raise HTTPException(status_code=422, detail=response)

    # 2) Parse file into DB
    parser = create_parser(verbose=False)
    # parser.delete_catalog_by_customer("catalog", "operators", version, source, customer_id)
    source = "custom"
    try:
        result = parser.scan_custom(version=version, source=source, customer_id=customer_id, token=token)
        scanned_ok_files = result[0]
        errors_found_repo_list = result[1]
    except Exception as ex:
        msg = f"Error in  parsing after Upload Operator: {ex}"
        raise HTTPException(status_code=500, detail=msg)
        pass
    response = {}
    response["detail"] = {}
    response["detail"]["message"] = f"{res} - files uploaded successfully inside custom-operators/{version}"
    if len(errors_found_repo_list) != 0:
        response["detail"]["errors_found_at_repo"] = errors_found_repo_list
    return response


@app.post("/github/addjenkinfile")
async def github_add_jenkin_file(
        token: str = Form(...),
        repository: str = Form(...),
        branch: str = Form(...),
        current_version: str = Form(...),
        credentials_id: str = Form(...),
        filename: str = Form(...)
):
    github = GitHubConnector(token)
    contents = get_jenkinfile_content(branch, github.get_user(), repository, credentials_id)
    print(contents)
    github.upsert_file(
        repo_name=repository, branch=branch, filename=filename, filecontent=contents, current_version=current_version
    )
    return {"detail": f"File {filename} updated successfully inside {repository} » {branch}"}


@app.get("/github/files", response_class=HTMLResponse)
async def github_get_contents_of_file(
        token: str = Query(None, title="Access Token for GitHub account"),
        repository: str = Query(None, title="Name of existing repository"),
        filename: str = Query(None, title="Name of existing file"),
        sha: str = Query(None, title="SHA of the file"),
):
    """Get contents of file inside an specific branch of the repository"""
    github = GitHubConnector(token)
    return github.get_contents_of_file(repository=repository, filename=filename, sha=sha)


@app.get("/github/versions/last")
async def get_last_commit_in_branch(
        token: str = Query(None, title="Access Token for GitHub account"),
        login: str = Query(None, title="Name of the GitHub account"),
        repository: str = Query(None, title="Name of existing repository"),
        branch: str = Query(None, title="Name of existing branch"),
):
    """ "Get last commit in branch"""
    github = GitHubConnector(token)
    return github.get_last_commit_in_branch(login=login, repository=repository, branch=branch)


@app.get("/stats")
@app.get("/stats/{version}")
async def get_stats(version: Optional[str] = None):
    """Return stats about the Catalog"""
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    stats = parser.get_stats(version)
    return stats


@app.get("/data/{version}")
async def get_data(version: str):
    """Return stats about the data in specific version of Catalog"""
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    stats = parser.validate_data_in_version(version)
    return stats


@app.get("/modules/{version}")
async def modules(version: str):
    """Returns a list with the available modules"""
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    parser.validate_data_in_version(version)
    modules = parser.get_distinct_modules(version)
    return modules


@app.get("/types/{version}")
async def types(version: str):
    """Returns a list with the distinct types"""
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    parser.validate_data_in_version(version)
    types = parser.get_distinct_types(version)
    return types


@app.get("/operators/{version}")
async def get_operators(version: str, customer_id: Optional[str] = None, mode: Optional[str] = None):
    """Return full listing of Operators"""
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    parser.validate_data_in_version(version)
    # if mode == "list":
    #    operators = parser.get_operators_list(version)
    # elif mode == "original-lite":
    #    operators = parser.get_operators_list_original(version, mode="lite")
    # elif mode == "original-full":
    #    operators = parser.get_operators_list_original(version, mode="full")
    # elif mode == "nested":
    #    operators = parser.get_operators_nested(version)
    # elif mode == "treev2":
    #    operators = parser.get_operators_tree_v2(version)
    # else:  # "tree" - Default
    operators = parser.get_operators_tree(version, customer_id)
    return operators


# ui refresh button
@app.post("/operators/{version}/refresh_custom")
async def get_operators(version: str, token: str = Form(...), customer_id: str = Form(...), mode: Optional[str] = None):
    """Return full listing of Operators"""

    # 2) Parse file into DB
    parser = create_parser(verbose=False)
    print(f'root folder = {parser.root_folder}')
    print(f'customer_id = {customer_id}')
    # parser.delete_catalog_by_customer("catalog", "operators", version, source, customer_id)
    source = "custom"
    try:
        result = parser.scan_custom(version=version, source=source, customer_id=customer_id, token=token)
        print(result)
        scanned_ok_files = result[0]
        errors_found_repo_list = result[1]
    except Exception as ex:
        msg = f"Error in  parsing after Upload Operator: {ex}"
        raise HTTPException(status_code=500, detail=msg)
        pass

    response = {}
    response["detail"] = {}
    response["detail"]["message"] = f"{scanned_ok_files} successfully inside custom-operators/{version}"
    if len(errors_found_repo_list) != 0:
        response["detail"]["errors_found_at_repo"] = errors_found_repo_list
    return response


@app.get("/operators/{version}/search")
async def get_operators_search(version: str, text: Optional[str] = None):
    """Return full listing of Operators with parameters of specif types"""
    if not text:
        msg = f"Url should contains => search?text=(part of desired data type)"
        raise HTTPException(status_code=400, detail=msg)
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    parser.validate_data_in_version(version)
    operators = parser.get_operators_search_parameters_type(version, text)
    return operators


@app.get("/operators/{version}/{operator_id}")
async def get_operator(version: str, operator_id: str, debug: Optional[str] = None):
    """Returns individual Operator"""
    debugging = debug is not None
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    parser.validate_data_in_version(version)
    operator = parser.get_operator(version, operator_id, debugging)
    if not operator:
        msg = f"Operator {version}.{operator_id} not found."
        raise HTTPException(status_code=404, detail=msg)
    return operator


@app.get("/operators/{version}/{operator_id}/tree")
async def get_operator_tree(version: str, operator_id: str):
    """Returns individual Operator"""
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    parser.validate_data_in_version(version)
    operator = parser.get_operator_tree(version, operator_id)
    if not operator:
        msg = f"Operator {version}.{operator_id} not found."
        raise HTTPException(status_code=404, detail=msg)
    return operator


@app.post("/catalog/{version}/{source}")
async def post_catalog(version: str, source: str):
    """Parse Operators from Airflow, Providers, UDP and Customer"""
    # print(f'post_catalog(version: "{version}", source: "{source}")')
    source = source.lower()
    if source not in ["airflow", "providers", "udp"]:
        msg = f"Source should be 1 of: airflow | providers | udp"
        raise HTTPException(status_code=400, detail=msg)
    parser = create_parser(verbose=False)
    parser.delete_catalog_by_source("catalog", "operators", version, source)
    if source == "udp":
        response = parser.scan_udp(version=version, source=source)
    else:
        if source == "providers":  # SV: providers está dentro de repo/airflow/v2/airflow/providers
            source = source.replace("providers", "airflow")
        response = parser.scan(version=version, source=source)
    if 'Error' in response:
        msg = response
        raise HTTPException(status_code=404, detail=msg)
    return {"detail": f"{source} {version} operators parsed successfully. {response}"}


@app.delete("/catalog")
@app.delete("/catalog/{version}")
async def delete_all(version: Optional[str] = None):
    """Deletes all operators in Catalog"""
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    res = parser.delete_catalog("catalog", "operators", version)
    return {"detail": res}


@app.delete("/catalog/{version}/{source}")
async def delete_airflow(version: str, source: str):
    """Deletes operators from Airflow/Providers/UDP"""
    source = source.lower()
    if source not in ["airflow", "providers", "udp"]:
        msg = f"Source should be: airflow | providers | udp"
        raise HTTPException(status_code=400, detail=msg)
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    res = parser.delete_catalog_by_source("catalog", "operators", version, source)
    return {"detail": res}


@app.post("/catalog/init")
async def init_airflow_folder():
    """Initializes Airflow folders with defined major versions"""
    res = do_init_airflow_folder()
    if res == "":
        return {"detail": "Operator Catalog initialized successfully."}
    raise HTTPException(status_code=500, detail=res)


def do_init_airflow_folder(starting: bool = False) -> str:
    """Updates Airflow folders with defined major versions"""
    parser = create_parser(on_error_abort=False)
    if type(parser) is str:
        print(parser)
    else:
        try:
            parser.init_airflow_folder(starting)
        except Exception as ex:
            msg = f"Failed to create parser: {ex}"
            print(msg)
            return msg
    return ""


def create_parser(verbose: bool = False, on_error_abort: bool = True):
    parser = None
    try:
        parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=verbose)
    except Exception as ex:
        msg = f"Failed to create parser: {ex}"
        if on_error_abort:
            print(msg)
            raise HTTPException(status_code=500, detail=msg)
        return msg
    return parser


class JenkinsReq(BaseModel):
    jobId: Optional[str] = None
    buildId: Optional[int] = None
    queueId: Optional[int] = None
    jobName: Optional[str] = None
    repositoryURL: Optional[str] = None
    branch: Optional[str] = None
    jenkinScriptPath: Optional[str] = None
    credentialsIdOfSourceCode: Optional[str] = None


# Private Jenkins URL

def get_jenkin_server_obj():
    jenkins_url = "http://10.200.10.200:8080"
    jenkins_username = "apiadmin"
    jenkins_password = "115db2032bf2da1adbee3fdd39fdd18100"
    server = jenkins.Jenkins(jenkins_url, username=jenkins_username, password=jenkins_password)
    return server


@app.post("/getjobinfo")
def get_job_info(request_data: JenkinsReq):
    print(request_data)
    try:
        server = get_jenkin_server_obj()
        job = server.get_job_info(request_data.jobId)
        print("Job", job)
        return job
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.post("/getjobs")
def get_jobs(request_data: JenkinsReq):
    try:
        server = get_jenkin_server_obj()
        return server.get_jobs()
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.delete("/deletejob")
def delete_job(request_data: JenkinsReq):
    try:
        server = get_jenkin_server_obj()
        return server.delete_job(request_data.jobId)
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.post("/build_invoke")
def build_invoke(request_data: JenkinsReq, request: Request):
    print(request_data)
    print("", request.client.host)
    try:
        server = get_jenkin_server_obj()
        queue_id = server.build_job(request_data.jobId)
        return {"queueId": queue_id}
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.post("/build_queue_info")
def build_queue_info(request_data: JenkinsReq):
    print(request_data)
    try:
        server = get_jenkin_server_obj()
        return server.get_queue_item(request_data.queueId)
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.get("/checkcrumb")
def checkcrumb():
    request = requests.Request("GET", "/")
    try:
        server = get_jenkin_server_obj()
        server.maybe_add_crumb(request)
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg
    return request.headers


@app.post("/build_info")
def build_info(request_data: JenkinsReq):
    print(request_data)
    try:
        server = get_jenkin_server_obj()
        return server.get_build_info(request_data.jobId, request_data.buildId)
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.post("/getjobconfig")
def get_job_info(request_data: JenkinsReq):
    try:
        server = get_jenkin_server_obj()
        return server.get_job_config(request_data.jobId)
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.post("/createjob")
def create_job(request_data: JenkinsReq):
    try:
        config_xml = get_jenkin_job_config(request_data.repositoryURL,
                                           request_data.branch,
                                           request_data.credentialsIdOfSourceCode,
                                           request_data.jenkinScriptPath
                                           )
        server = get_jenkin_server_obj()
        return server.create_job(request_data.jobName, config_xml)
    except Exception as e:
        msg = f"Failed to make request: {e}"
        return msg


@app.get("/", response_class=HTMLResponse)
async def root():
    return f"""
    <html>
        <head>
            <title>{TITLE}</title>
            <style>
            body {{
              color: #fff;
              background-color: #666;
              font-family: 'Courier new', 'sans-serif';
            }}
            .centered {{
              position: fixed;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              background-color: #666;
              padding: 50px;
            }}
            </style>
        </head>
        <body>
            <h1 class="centered">{TITLE} {VERSION}</h1>
        </body>
    </html>
    """


@app.post('/s3-upload-file')
# Uploads file from local to S3 bucket
# API call to this route needs: bucket_name, region and selecting the file to be uploaded

def uploadFile(
        bucket_name: str = Form(...),
        s3_id: str = Form(...),
        s3_sk: str = Form(...),
        file_upload: UploadFile = File(...),
):
    # bucket_name = request.form['bucket_name']
    # file_upload =  request.files['upload_file']
    # s3_id = request.form['s3_id']
    # s3_sk = request.form['s3_secret_key']
    print(file_upload.filename)

    print(s3_sk)
    print(s3_id)
    print(bucket_name)
    # return "ok"

    file_upload.write(secure_filename(file_upload.filename))
    s3 = boto3.client('s3', aws_access_key_id=s3_id, aws_secret_access_key=s3_sk)
    s3.upload_file(os.getcwd() + "/" + file_upload.filename, bucket_name, file_upload.filename)
    return jsonify({"Status": "File uploaded successfully"})


@app.delete('/s3-delete-file')
# Deletes a file in the S3 bucket
# API call to this route needs: bucket_name and name of the file to be deleted, including the file extention

def deleteFile(
        bucket_name: str, file_name: str, s3_id: str, s3_sk: str
):
    # bucket_name = request.form['bucket_name']
    # file_name = request.form['file_name']
    # s3_id = request.form['s3_id']
    # s3_sk = request.form['s3_secret_key']

    s3 = boto3.client('s3', aws_access_key_id=s3_id, aws_secret_access_key=s3_sk)
    s3.delete_object(Bucket=bucket_name, Key=file_name)
    return "File Deleted Successfully"


# Lists the objects in specified S3 buckets
# API call requires bucket_name, access key id and secret acccess key
@app.get('/s3-list-objects')
def listObjects(s3_secret_key: str, s3_id: str, bucket_name: str):
    # bucket_name = request.form['bucket_name']
    # s3_id = request.form['s3_id']
    # s3_sk = request.form['s3_secret_key']

    s3 = boto3.client('s3', aws_access_key_id=s3_id, aws_secret_access_key=s3_secret_key)
    response = s3.list_objects(Bucket=bucket_name)
    return response


@app.route('/gcs-to-s3', methods=['POST'])
# Moves a file from GCS to S3
# API call requires the bucket names at the source and destination, name of the file
# and the access credentials for GCS and S3.

# Here we are asking the user to provide S3 creds as well, although we can use
# the config files to import the credentials too, as we did for the other API calls in this script

def gcs_to_s3():
    gcs_bucket_name = request.form['gcs_bucket']
    s3_bucket_name = request.form['s3_bucket']
    file_name = request.form['file_name']
    gs_id = request.form['gs_id']
    gs_sk = request.form['gs_secret_key']
    s3_id = request.form['s3_id']
    s3_sk = request.form['s3_secret_key']
    gs_bucket = GSConnection(gs_id, gs_sk).get_bucket(gcs_bucket_name)
    s3_bucket = S3Connection(s3_id, s3_sk).get_bucket(s3_bucket_name)

    io = BytesIO()
    try:
        gs_bucket.get_key(file_name).get_file(io)
        io.seek(0)
        key = s3_bucket.new_key(key_name=file_name)
        key.set_contents_from_file(io, replace=True)
    finally:
        io.close()

    return "Success"


@app.route('/gcs_list_objects', methods=['POST'])
# Returns list of files in the GCS bucket to the console
# Uses credentials from the config file
def gcs_list_objects(self):
    credential_path = '/Users/amolkhade/Documents/Python/aws_api/radiant-striker-345721-04a014275ac7.json'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
    client = storage.Client()
    bucket_name = request.form['bucket_name']
    blobs = client.list_blobs(bucket_name)
    items = ""
    for blob in blobs:
        print(blob.name)
    return "Check console"


@app.get('/s3-list-buckets')
def s3_list_buckets(s3_secret_key: str, s3_id: str):
    print('list of buckets')
    # Retrieve the list of existing buckets
    # s3_id = request.form['s3_id']
    # s3_sk = request.form['s3_secret_key']
    s3 = boto3.client('s3', aws_access_key_id=s3_id, aws_secret_access_key=s3_secret_key)
    response = s3.list_buckets()
    return response


if __name__ == "__main__":
    port = os.environ.get("XFUSION_API_PORT")
    uvicorn.run("main:app", port=int(port))