node {
  def app
  def ecsCluster = 'dev-xaqua-api-cluster'
  def ecsService = 'data-pipeline-api-py'
  def region = 'us-west-2'
  def mvnHome = tool name: 'maven3', type: 'maven'
  def mvnCMD = "${mvnHome}/bin/mvn"


  try{
      //notify('Started')

      stage 'SCM Checkout'
        git branch: 'develop', credentialsId: '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', url: 'https://github.com/xFusionTech/xaqua-data-pipeline-api-py.git'

      //stage 'Maven build'
        //sh label: '', script: 'mvn -B -DskipTests -f Student/csac-student/pom.xml clean package'
        //sh "${mvnCMD} -B -DskipTests -f pom.xml clean package"
		
//	  stage 'Running SonarQube Code Analysis'
//        withSonarQubeEnv('sonarQube-server') {
//        sh "${mvnCMD} -B -f pom.xml sonar:sonar"   
//      }

      stage 'Docker build for commercial cloud'
            app = docker.build('dev-xaqua-data-pipeline-api-py')

      stage 'Docker push for commercial cloud'
           docker.withRegistry('https://834352307282.dkr.ecr.us-west-2.amazonaws.com', 'ecr:us-west-2:xf-aws-system-user') {
          app.push('latest')
          app.push("jenkins-${env.JOB_NAME}-${env.BUILD_ID}")
        }

      //stage 'Waiting for user input'
        //input 'Do you want to go ahead and deploy the code?'

      stage 'Deploy in aws'
        //EC2 instance must have IAM role attached in order to run AWS cli commands
        //sh label: '', script: "aws ecs list-tasks --service ${ecsService} --cluster ${ecsCluster} --region ${region}"
        def taskID = sh(script: "aws ecs list-tasks --service ${ecsService} --cluster ${ecsCluster} --region ${region} | grep ecs", returnStdout: true)
        echo taskID
        sh label: '', script: "aws ecs stop-task --cluster ${ecsCluster} --region ${region} --task ${taskID}"
      
	//  stage 'Run integration test?'
      //  input 'Do you want to run the integration test?'
	  
     // stage 'SCM Checkout of Integration Test scripts'
     //   git branch: 'develop', credentialsId: 'GIT-repo-dev', url: 'https://github.com/xFusionTech/xaqua-data-pipeline-api.git'
	  
	 // stage 'Compiling Test scripts'
     //   sh "${mvnCMD} -B -DskipTests -f pom.xml clean compile"
	
	 // stage 'Pausing for 90s'
     //   sh 'sleep 90'
		
	 // stage 'Running Automation Test'
	 //   sh "${mvnCMD} -DpropertiesFile=resources/dev/Dev.properties exec:java -Dexec.mainClass='com.csac.gdsm.automate.RunInstitutionTests'"
              
   //   notify('Success')

  } catch(err) {
      //  notify("Error ${err}")
       currentBuild.result = 'FAILURE'

  }
}

// def notify(status){
//      emailext (
//       to: "m.mulla@xfusiontech.com",
//       subject: "${status}: Jenkins Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
//       body: """<p>${status}: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]':</p>
//         <p>Check console output at <a href='${env.BUILD_URL}'>${env.JOB_NAME} [${env.BUILD_NUMBER}]</a></p>""",
//     )
//}
