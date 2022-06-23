def get_jenkinfile_content(branch, user, repository, credentials_id):
    front_part  =  '''node {
  def app
  def ecsService = 'is-wso2'
  def ecsCluster = 'DEV-gdsm-webapp'
  def region = 'us-west-2'
  
  try{
      
      //notify('Started')
        
      stage 'SCM Checkout'
        '''
    jenkinfile_content =   f"git branch: '{branch}', credentialsId: '{credentials_id}'," \
                           f" url: 'https://github.com/{user}/{repository}.git'".format(branch, credentials_id, user, repository)

    end_part = '''
      stage 'DAGs backup, transfer'
        sshPublisher(publishers: [sshPublisherDesc(configName: 'dev-airflow', transfers: [sshTransfer(cleanRemote: true, excludes: '', execCommand: 'tar -cvf /tmp/airflow-dags-backup-`date +%d-%m-%Y_%H%M%S`.tar /home/ec2-user/xf-airflow-docker/dags/; sudo \\\\cp -r /var/tmp/xaqua-airflow-config/generatedDAG/* /home/ec2-user/xf-airflow-docker/dags/', execTimeout: 120000, flatten: false, makeEmptyDirs: true, noDefaultExcludes: false, patternSeparator: '[, ]+', remoteDirectory: 'xaqua-airflow-config', remoteDirectorySDF: false, removePrefix: '', sourceFiles: 'generatedDAG/**')], usePromotionTimestamp: false, useWorkspaceInPromotion: false, verbose: false)])


  } catch(err) {
      notify("Error ${err}")
      currentBuild.result = 'FAILURE'
  }
}
'''

    return front_part + jenkinfile_content + end_part

