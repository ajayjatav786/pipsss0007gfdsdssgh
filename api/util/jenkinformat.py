def get_jenkin_job_config(repository, branch, credentials_id, script_path):
    start_part =  '''<?xml version="1.0" encoding="UTF-8"?>
<flow-definition plugin="workflow-job@2.38">
   <actions>
      <org.jenkinsci.plugins.pipeline.modeldefinition.actions.DeclarativeJobAction plugin="pipeline-model-definition@1.6.0" />
      <org.jenkinsci.plugins.pipeline.modeldefinition.actions.DeclarativeJobPropertyTrackerAction plugin="pipeline-model-definition@1.6.0">
         <jobProperties />
         <triggers />
         <parameters />
         <options />
      </org.jenkinsci.plugins.pipeline.modeldefinition.actions.DeclarativeJobPropertyTrackerAction>
   </actions>
   <description />
   <keepDependencies>false</keepDependencies>
   <properties>
      <hudson.plugins.throttleconcurrents.ThrottleJobProperty plugin="throttle-concurrents@2.2">
         <maxConcurrentPerNode>0</maxConcurrentPerNode>
         <maxConcurrentTotal>0</maxConcurrentTotal>
         <categories class="java.util.concurrent.CopyOnWriteArrayList">
            <string>CSACThrottlePolicyforBuilds</string>
         </categories>
         <throttleEnabled>false</throttleEnabled>
         <throttleOption>category</throttleOption>
         <limitOneJobWithMatchingParams>false</limitOneJobWithMatchingParams>
         <paramsToUseForLimit />
      </hudson.plugins.throttleconcurrents.ThrottleJobProperty>
      <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
         <triggers />
      </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
   </properties>
   <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps@2.80">
      <scm class="hudson.plugins.git.GitSCM" plugin="git@4.2.2">
         <configVersion>2</configVersion>
         <userRemoteConfigs>
            <hudson.plugins.git.UserRemoteConfig>
                '''
    git_url = f'<url>{repository}</url>\n' \
              f'<credentialsId>{credentials_id}</credentialsId>'.format(repository, credentials_id)

    middle_part = '''
            </hudson.plugins.git.UserRemoteConfig>
         </userRemoteConfigs>
         <branches>
            <hudson.plugins.git.BranchSpec>
               '''
    branch_part = f'<name>*/{branch}</name>'.format(branch)
    middle_part2 ='''
            </hudson.plugins.git.BranchSpec>
         </branches>
         <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
         <submoduleCfg class="list" />
         <extensions />
      </scm>
      '''
    script = f'<scriptPath>{script_path}</scriptPath>'.format(script_path)
    end_part = ''' <lightweight>true</lightweight>
   </definition>
   <triggers />
   <disabled>false</disabled>
</flow-definition>'''
    print( start_part + git_url + middle_part + branch_part + middle_part2 + script + end_part)
    return start_part + git_url + middle_part + branch_part + middle_part2 + script + end_part
