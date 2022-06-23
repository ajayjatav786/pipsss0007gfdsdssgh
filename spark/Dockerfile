FROM bitnami/spark:latest

USER root

RUN pip install delta-spark
RUN pip install pymysql
RUN curl https://repo1.maven.org/maven2/io/delta/delta-core_2.12/1.0.0/delta-core_2.12-1.0.0.jar --output ${SPARK_HOME}/jars/delta-core_2.12-1.0.0.jar
RUN curl https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.1/hadoop-aws-3.3.1.jar --output ${SPARK_HOME}/jars/hadoop-aws-3.3.1.jar
RUN curl https://repo1.maven.org/maven2/mysql/mysql-connector-java/8.0.25/mysql-connector-java-8.0.25.jar  --output ${SPARK_HOME}/jars/mysql-connector-java-8.0.25.jar
RUN curl https://repo1.maven.org/maven2/org/postgresql/postgresql/42.2.23/postgresql-42.2.23.jar  --output ${SPARK_HOME}/jars/postgresql-42.2.23.jar
RUN curl https://repo1.maven.org/maven2/com/crealytics/spark-excel_2.12/0.13.7/spark-excel_2.12-0.13.7.jar  --output ${SPARK_HOME}/jars/spark-excel_2.12-0.13.7.jar   