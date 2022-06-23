"""
GitHub Connector

Connect to a GitHub account to:

- Create repositories
- Read contents of a repository (branches, files and versions)
- Create branches inside a repository
- Commit changes to a file

"""


from typing import List
from github import Github
import github
import requests
import difflib as dl
from fastapi import UploadFile
from zipfile import ZipFile
import os
import tempfile
import json
import ast
from pathlib import Path
import shutil
import time

CUSTOM_OPERATORS_REPO = "custom-operators"

EXT_ALLOWED = (".py",".json", ".csv", ".txt", ".scala", ".sql")

class GitHubConnector:
    """Implements the connection to a GitHub account"""


    def __init__(self, token: str):
        # Check token
        if not token:
            raise Exception(f"Invalid Access Token")
        self.token = token
        self.g = Github(token)


    def get_user(self):
        return self.g.get_user().login


    def get_tree(self):
        """Returns a tree with repositories, branches and versions from a GitHub account"""
        repos = self.g.get_user().get_repos()
        tree = {}
        for repo in repos:
            print(f"repo: {repo.name}")
            tree[repo.name] = {}
            for branch in repo.get_branches():
                print(f"branch: {branch.name}")
                tree[repo.name][branch.name] = {}
                for commit in repo.get_commits(sha=branch.name):
                    tree[repo.name][branch.name][commit.sha] = {}
                    print(f"commit: {commit.commit.message}")
                    for file in commit.files:
                        print(f"file: {file.filename}")
                        tree[repo.name][branch.name][commit.sha][commit.commit.message] = file.filename
        # json_object = json.dumps(tree, indent=4)
        return tree


    def create_repo(self, repo_name: str):
        """Creates a new repository in a GitHub account"""
        name_repo = repo_name
        description = repo_name
        organization = self.g.get_user()
        organization.create_repo(
            name_repo,
            allow_rebase_merge=True,
            auto_init=True,
            description=description,
            has_issues=True,
            has_projects=False,
            has_wiki=False,
            private=True,
        )


    def create_branch(self, repo_name: str, source_branch: str, target_branch: str,source_commit: str = None):
        """Creates a new branch in the repository from a source branch"""
        repo = self.g.get_user().get_repo(repo_name)
        sb = repo.get_branch(source_branch)
        if source_commit is None:
            source_commit=sb.commit.sha
        repo.create_git_ref(ref=f"refs/heads/{target_branch}", sha=source_commit)


    def upsert_file(
        self,
        repo_name: str,
        branch: str,
        filename: str,
        filecontent: str,
        current_version: str
    ):
        """Inserts or updates (if exists) a file inside a branch of the repository"""
        #if (
            #filename != "dagworkflow.json"
            #and filename != "generatedDAG/GEN_dag.py"
            #and filename != "editedDAG/uedit_dag.py"
        #):
            #raise Exception(
                #'Unrecognized filename "{}". Should be one of: dagworkflow.json, generatedDAG/GEN_dag.py or editedDAG/uedit_dag.py'
            #)
        # git_prefix = ""
        # if filename == "GEN_dag.py":
        #     git_prefix = "generatedDAG/"
        # elif filename == "uedit_dag.py​":
        #     git_prefix = "editedDAG/"
        # git_file = git_prefix + filename
        repo = self.g.get_user().get_repo(repo_name)
        try:
            contents = repo.get_contents(filename, ref=branch)
            fileExists = True
            # print(contents)
            # git_content = contents.decoded_content.decode()
            # print(filecontent)
            # differences = [diff for diff in dl.context_diff(git_content, filecontent)]
            # if len(differences):
            #   => UPDATE
            # else:
            #   => Nothing, the file hasn't changed
        except:
            # NOT FOUND
            fileExists = False
        if filename.lower().endswith(".py"):
            version = current_version
        else:
            if fileExists:
                n = self.get_last_commit_in_branch(
                    login=self.g.get_user().login, repository=repo_name, branch=branch
                )
                if n["message"] == "Initial commit":
                    last_version = 0
                else:
                    last_version = int(float(n["message"].split(sep=" ")[1]))
                version = f"VERSION {last_version + 1}"
            else:
                version = "VERSION 1"
        # print(f"fileExists? {fileExists}")
        # print(f"version? {version}")
        # Upsert
        if fileExists:
            repo.update_file(filename, version, filecontent, contents.sha, branch=branch)
            print(f"{filename} UPDATED")
        else:
            repo.create_file(filename, version, filecontent, branch=branch)
            print(f"{filename} CREATED")

    # def upsert_file_from_path(self, repo_name: str, branch: str, filesource: str, filename: str):
    #     """Inserts or updates (if exists) a file (from path) inside a branch of the repository"""
    #     repo = self.g.get_user().get_repo(repo_name)
    #     all_files = []
    #     contents = repo.get_contents("")
    #     while contents:
    #         file_content = contents.pop(0)
    #         if file_content.type == "dir":
    #             contents.extend(repo.get_contents(file_content.path))
    #         else:
    #             file = file_content
    #             all_files.append(str(file).replace('ContentFile(path="', "").replace('")', ""))
    #     with open(filesource, "r") as file:
    #         content = file.read()
    #     # Upload to github
    #     git_prefix = ""
    #     git_file = git_prefix + filename
    #     if git_file in all_files:
    #         contents = repo.get_contents(git_file)
    #         # contents.sha
    #         repo.update_file(contents.path, "committing files", content, contents.sha, branch=branch)
    #         print(f"{git_file} UPDATED")
    #     else:
    #         repo.create_file(git_file, "Version 1", content, branch=branch)
    #         print(f"{git_file} CREATED")


    # return {
    #     "name": search_operator_name(files),
    #     "filenames": [file.filename for file in files]
    # }

    def upload_operator(
        self,
        version: str,
        files: List[UploadFile]
    ):
        # 1) Read CUSTOM_OPERATORS_REPO repository
        repo_name = f"{CUSTOM_OPERATORS_REPO}"
        repo = None
        try:
            repo = self.g.get_user().get_repo(repo_name)
        except Exception as ex:
            # Failed reading repo_name repository
            # raise Exception(f"Failed reading {repo_name}: {ex}")
            pass
        if not repo:
            try:
                self.create_repo(repo_name)
                repo = self.g.get_user().get_repo(repo_name)
            except Exception as ex:
                raise Exception(f"Failed creating {repo_name}: {ex}")
        print(repo)
        # 2) Read contents in {repo_name}/{version}
        current_files = []
        try:            
            for f in repo.get_contents(f"{version}"):
                current_files.append(f.name)
        except:
            # Failed reading contents in {repo_name}/{version}"
            pass
        
        
        # Temp folder to uncompress zip
        tmp_dir = tempfile.TemporaryDirectory(suffix='_temp')
        print('created temporary directory', tmp_dir.name)
            
        for file in files:
            with open(os.path.join(tmp_dir.name, file.filename), "wb+") as f:
                f.write(file.file.read())
        
        uploaded_files = []
        for root, subdirs, files_downloaded in os.walk(tmp_dir.name):
            for filename in files_downloaded:
                file_path = os.path.join(root, filename) 
                print(f'file path uploaded -> {file_path}')
                uploaded_files.append(file_path)
        
        if not uploaded_files:
            pass
        
        # How do I push new files to GitHub?
        # https://www.py4u.net/discuss/22051
        # Full example of commit multiple file
        # https://github.com/PyGithub/PyGithub/issues/1628
        # you can read file content into blob, here just use str for example
        elements = list()
        print(f'Uploaded files -> {uploaded_files}')
        files_allowed, errors_found = self.filter_files(uploaded_files)        
        if len(errors_found) == 0:        
            for file in files_allowed:
                #path = f"{version}/{file.filename}"
                #print(f'Path Operator {path}')
                file_parsed_path = file.split('/') # split path to avoid temp folder names
                if file_parsed_path[-1].startswith("."): # Avoid hidden files
                    print("Hidden file not readed: ", file_parsed_path[-1])
                else:
                    file_basename = '/'.join(file_parsed_path[3:]) # rebuild path without temp folders
                    path = f"{version}/{file_basename}"
                    print(f'Path Operator -> {path}')
                # Read Uploaded file content
                try:
                    with open(file, 'r') as fileUploaded:
                        file_content = fileUploaded.read()
                        blob = repo.create_git_blob(file_content, "utf-8")
                        element = github.InputGitTreeElement(path=path, mode="100644", type="blob", sha=blob.sha)
                        elements.append(element)
                except:  # Skip binary files to avoid encoding errors
                    print('Binary file skipped: ', file_parsed_path[-1])
                    pass
        else:
            print(f'Errors found in Upload Operator -> {errors_found}')
            tmp_dir.cleanup()
            raise Exception(errors_found)  # -> [{},{},{}]
        
        commit_message = f"Upload custom operator/s"   
        head_sha = repo.get_branch("main").commit.sha
        base_tree = repo.get_git_tree(sha=head_sha)
        tree = repo.create_git_tree(elements, base_tree)
        parent = repo.get_git_commit(sha=head_sha)
        commit = repo.create_git_commit(commit_message, tree, [parent])
        master_ref = repo.get_git_ref('heads/main')
        master_ref.edit(sha=commit.sha)
        tmp_dir.cleanup()
        return len(files)
    
    #upload_zip
    def upload_zip(
        self,
        version: str,
        file: UploadFile
    ):
        # 1) Read CUSTOM_OPERATORS_REPO repository
        repo_name = f"{CUSTOM_OPERATORS_REPO}"
        repo = None
        try:
            repo = self.g.get_user().get_repo(repo_name)
        except Exception as ex:
            # Failed reading repo_name repository
            # raise Exception(f"Failed reading {repo_name}: {ex}")
            pass
        if not repo:
            try:
                repo = self.create_repo(repo_name)
            except Exception as ex:
                raise Exception(f"Failed creating {repo_name}: {ex}")
        print(f'Repo -> {repo}')
        
        # 2) Read contents in {repo_name}/{version}
        #current_files = []
        #try:            
        #    for f in repo.get_contents(f"{version}"):
        #        current_files.append(f.name)
        #except:
        #    # Failed reading contents in {repo_name}/{version}"
        #    pass
        #print(f"* current files: {current_files}")
        
        #######################
        # Decompress operation
        #######################
        print(f'Descomprimiendo {file.filename}...') 
        
        # Temp zip file at filesystem
        tmp = tempfile.NamedTemporaryFile()
        # Writing
        with open(tmp.name, "wb+") as f:
            f.write(file.file.read())

        # Temp folder to uncompress zip
        with tempfile.TemporaryDirectory(suffix='_temp') as tmp_dir:
            print('created temporary directory', tmp_dir)

        with ZipFile(tmp.file, 'r') as zipObj:
            # Extract all the contents of zip file in temp directory
            zipObj.extractall(tmp_dir)

        unzip_files = []
        for root, subdirs, files in os.walk(tmp_dir):
            for filename in files:
                file_path = os.path.join(root, filename) 
                print(f'file path unzip -> {file_path}')
                unzip_files.append(file_path)
        if not unzip_files:
            pass

        # How do I push new files to GitHub?
        # https://www.py4u.net/discuss/22051
        # Full example of commit multiple file
        # https://github.com/PyGithub/PyGithub/issues/1628
        # you can read file content into blob, here just use str for example
        elements = list()
        print(f'Unziped files -> {unzip_files}')
        if len(unzip_files) == 0:
            print(f'Errors found in Upload Zip -> Empty folder')
            raise Exception([{"error": "Empty folder"}])
        
        files_allowed, errors_found = self.filter_files(unzip_files)
        if len(errors_found) == 0:
            for file_unzip in files_allowed:                 # SV: Acá se hace el filtrado del Upload Operator
                file_parsed_path = file_unzip.split('/') # split path to avoid temp folder names
                if file_parsed_path[-1].startswith("."): # Avoid hidden files
                    print("Hidden file not readed: ", file_parsed_path[-1])
                else:
                    file_basename = '/'.join(file_parsed_path[3:]) # rebuild path without temp folders
                    path = f"{version}/{file_basename}"
                    print(f'Path Zip -> {path}')
                # Read unzipped file content
                try: 
                    with open(file_unzip, 'r') as fileUnzip:
                        file_content = fileUnzip.read()
                        blob = repo.create_git_blob(file_content, "utf-8")
                        element = github.InputGitTreeElement(path=path, mode="100644", type="blob", sha=blob.sha)
                        elements.append(element)
                except: # Skip binary files to avoid encoding errors
                    print('Binary file skipped: ', file_parsed_path[-1])
                    pass
        else:
            print(f'Errors found in Upload Zip -> {errors_found}')
            raise Exception(errors_found)  # -> [{},{},{}]

                        
        commit_message = f"Upload {file.filename}"
        head_sha = repo.get_branch("main").commit.sha
        base_tree = repo.get_git_tree(sha=head_sha)
        tree = repo.create_git_tree(elements, base_tree)
        parent = repo.get_git_commit(sha=head_sha)
        commit = repo.create_git_commit(commit_message, tree, [parent])
        master_ref = repo.get_git_ref('heads/main')
        master_ref.edit(sha=commit.sha)
        return len(files)

    def filter_files(self, filenames: list):
        ''' Filter files by allowed extension'''
        files_allowed = []
        errors = []
        for filename in filenames:    
            if filename.endswith(EXT_ALLOWED) and not filename.startswith('.'):
                files_allowed.append(filename)
                # .py
                if filename.endswith(".py"):
                    with open(filename, "rb") as fin:
                                contents = fin.read()
                    try:
                        tree = ast.parse(contents) # SV: Esto lanza la Excepción
                    except Exception as ex:
                        file_with_error = filename
                        error_dict = self.record_file_error(file_with_error, ex)
                        errors.append(error_dict)
                # .json                        
                elif filename.endswith(".json"):
                    try:
                        with open(filename, "rb") as json_file:
                                json_contents = json_file.read()
                        json.loads(json_contents)
                    except Exception as ex:
                        file_with_error = filename
                        error_dict = self.record_file_error(file_with_error, ex)
                        errors.append(error_dict)
                #print(f'Allowed: {f_allowed}')
                #print(f'Errors : {errors}')
            else:
                # extensions NOT ALLOWED
                p = Path(filename)
                file_with_error = p.name
                # NOT ALLOWED - Hidden files -> pass
                if file_with_error.startswith("."):
                    pass
                else:    
                    # Register NOT ALLOWED as Error
                    errors.append({"file": file_with_error, "error": "File extension not allowed"})
                    pass
        return files_allowed, errors


    def record_file_error(self, filepath: str, ex_msg: str):
        try:
            p = Path(filepath)
            file_with_error = p.name
        except Exception as ex:
            pass
        print(f'Parsing Error - file: {file_with_error}: {ex_msg}')
        return {"file":file_with_error, "error": str(ex_msg)}



    def get_contents_of_file(self, repository: str, filename: str, sha: str):
        """Get contents of file inside an specific branch of the repository"""
        repo = self.g.get_user().get_repo(repository)
        file_content = repo.get_contents(filename, ref=sha)
        return file_content.decoded_content


    def run_query(self, query, headers):
        # An example on using the Github GraphQL API with Python 3
        # https://gist.github.com/gbaman/b3137e18c739e0cf98539bf4ec4366ad
        request = requests.post("https://api.github.com/graphql", json={"query": query}, headers=headers)
        if request.status_code == 200:
            return request.json()
        else:
            raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

    def get_tree_graphql(self, login: str, commit_qty: str = '1'):
        """Get last commit in branch or N commit in branch"""
        # https://gist.github.com/Hollywood/75a0569285e673280422e552631e29fd
        # https://docs.github.com/en/graphql/overview/explorer
        headers = {"Authorization": f"Bearer {self.token}"}
        # https://gist.github.com/MichaelCurrin/6777b91e6374cdb5662b64b8249070ea
        # One level down
        # object {
        #     ... on Tree {
        #         entries {
        #             name
        #         }
        #     }
        # }
        # TODO Verify files that really changed in a version
        # For example, the DAG script appears in v2
        # even though it only changed in version 1.
        
        #on Commit {
        #    history(first: 25)  <------------- history is ordered from the new to the older commits, hence first:1 returns the latest commit.
        #
        # https://github.community/t/how-to-use-graphql-api-to-get-the-latest-commit-date-of-a-specific-file/13999
        query = """
        query {
            repositoryOwner (login: "{{login}}") {
                repositories(first:100) {
                    totalCount
                    nodes {
                        name
                        refs(first: 100, refPrefix: "refs/heads/") {
                            edges {
                                node {
                                    name
                                    target {
                                        ... on Commit {
                                            history(first: {{commit_qty}}) {
                                                totalCount
                                                nodes {
                                                    message
                                                    committedDate
                                                    oid
                                                    tree {
                                                        entries {
                                                            name
                                                            type
                                                            object{
                                                                ...on Tree{
                                                                    entries{
                                                                        name
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """.replace(
            "{{login}}", login
        ).replace(
            "{{commit_qty}}", commit_qty 
        )
        result = self.run_query(query, headers)
        repos = []
        if not "data" in result:
            print(result)
            # {'errors': [{'type': 'RATE_LIMITED', 'message': 'API rate limit exceeded for user ID 89102445.'}]}
            if "errors" in result and len(result["errors"]) > 0 and "type" in result["errors"][0] and result["errors"][0]["type"] == "RATE_LIMITED":
                raise Exception(f"GitHub API rate limit exceeded")
            raise Exception(f"Error trying to connect to GitHub")       
        for repo in result["data"]["repositoryOwner"]["repositories"]["nodes"]:
            #if repo["name"].startswith("DP-"):
            branches = []
            for edge in repo["refs"]["edges"]:
                branch = edge["node"]
                versions = []
                versions_set = set()
                for version in branch["target"]["history"]["nodes"]:
                    version_name = version["message"]
                    if version_name.startswith("VERSION "):
                        if version_name not in versions_set:
                            versions_set.add(version_name)
                            filesfolder=[]
                            for files in version["tree"]["entries"]:
                                folder=""
                                if files["type"] =="tree":
                                    folder=files["name"]
                                    for files2 in files["object"]["entries"]:
                                        if ".json" in files2["name"] or ".py" in files2["name"]:
                                            filesfolder.append(
                                                {
                                                    "filename": folder+"/"+files2["name"],
                                                    "sha": version["oid"]
                                                }
                                            )
                                else:
                                    if ".json" in files["name"] or ".py" in files["name"]:
                                        filesfolder.append(
                                            {
                                                "filename": files["name"],
                                                "sha": version["oid"]
                                            }
                                        )
                            versions.append(
                                {
                                    "name": version_name,
                                    "files": filesfolder,
                                }
                                            )
                branches.append({"name": branch["name"], "versions": versions})
            repos.append({"name": repo["name"], "branches": branches})
        return {"repositories": repos}


    def complete_filename(self, filename: str):
        # Valid filenames:
        # dagworkflow.json
        # generatedDAG/GEN_dag.py
        # editedDAG/uedit_dag.py        
        if filename == "generatedDAG":
            return "generatedDAG/GEN_dag.py"
        if filename == "editedDAG":
            return "editedDAG/uedit_dag.py"
        return filename


    def get_last_commit_in_branch(self, login: str, repository: str, branch: str):
        # https://stackoverflow.com/questions/57229005/use-github-api-to-get-the-last-commit-of-all-repositorys
        # return self.g.get_user().get_repo(repository).get_branch(branch).commit.commit.message
        """Get last commit in branch"""
        headers = {"Authorization": f"Bearer {self.token}"}
        query = (
            """
        {
            repository(name: "{{repository}}", owner: "{{login}}") {
                ref(qualifiedName: "{{branch}}") {
                    target {
                        ... on Commit {
                            history(first: 1) {
                                edges {
                                    node {
                                        message
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """.replace(
                "{{login}}", login
            )
            .replace("{{repository}}", repository)
            .replace("{{branch}}", branch)
        )
        result = self.run_query(query, headers)
        return result["data"]["repository"]["ref"]["target"]["history"]["edges"][0]["node"]

    # get old repo info
    def get_repoo(self,old_repo: str):
        try:
            repo = self.g.get_user().get_repo(str(old_repo))
            return repo
        except Exception as e:
            if str(e).split(' ')[0] == '404':
                print('Repo not Exist')
                exit()

    # creating new repo
    def create_neww_repo(self,new_repo: str):
        try:
            self.g.get_user().create_repo(str(new_repo))
        except Exception as e:
            if str(e).split(' ')[0] == '422':
                print('Repository already Exist please try again')
                exit()

    # get all files from repo
    def gett_files_from_old(self,repo: str):
        all_files = []
        contents = repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                file = file_content
                all_files.append(str(file).replace('ContentFile(path="', '').replace('")', ''))
        return all_files

    # Upload to github
    def update_to_new(self,repo: str, new_repo: str, all_files):
        nrepo = self.g.get_user().get_repo(str(new_repo))
        for file in all_files:
            content = repo.get_contents(str(file))
            nrepo.create_file(file, "committing files", content.decoded_content.decode(), branch="master")
            print(str(new_repo) + '/' + file + ' CREATED')


