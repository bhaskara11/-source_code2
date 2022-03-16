from airflow.models import Variable
from airflow import models
from airflow.providers.google.cloud.operators import dataproc
from airflow.utils import trigger_rule
import datetime
import logging

dag_config = Variable.get("common_dag_variables", deserialize_json=True)

with models.DAG(
        dag_config['DAG_ID'],
        start_date=datetime.datetime(2022, 1, 1),
        schedule_interval=None,
        default_args={
            'project_id': dag_config['GCP_PROJECT'],
            'location': dag_config['GCE_REGION'],
        }) as dag:
    unique_cluster_name = dag_config['CLUSTER_NAME'] + '-{{ dag_run.conf["id"] }}'
    create_dataproc_cluster = dataproc.DataprocCreateClusterOperator(
        task_id='create_dataproc_cluster',
        cluster_name=unique_cluster_name,
        cluster_config={
            'master_config': {
                'num_instances': dag_config['MASTER_NUM_INSTANCES'],
                'machine_type_uri': dag_config['MASTER_MACHINE_TYPE_URI']
            },
            'worker_config': {
                'num_instances': dag_config['WORKER_NUM_INSTANCES'],
                'machine_type_uri': dag_config['WORKER_MACHINE_TYPE_URI']
            },
            'gce_cluster_config': {
                'subnetwork_uri': dag_config['SUBNETWORK_URI']
            }
        },
        region=dag_config['GCE_REGION'])

    run_dataproc_spark = dataproc.DataprocSubmitJobOperator(
        task_id='run_dataproc_spark',
        job={
            'reference': {'project_id': dag_config['GCP_PROJECT']},
            'placement': {'cluster_name': unique_cluster_name},
            'pyspark_job': {
                'main_python_file_uri': dag_config['GCS_CODE'] + "/" + dag_config['SPARK_JOB_FILE'],
                'args': [
                    '{{ dag_run.conf["bucket"] }}',
                    '{{ dag_run.conf["file"] }}',
                    '{{ dag_run.conf["pipeline"] }}',
                    dag_config['OUTPUT_BUCKET_PREFIX']
                ]
            }
        },
        region=dag_config['GCE_REGION'],
        project_id=dag_config['GCP_PROJECT'])

    delete_dataproc_cluster = dataproc.DataprocDeleteClusterOperator(
        task_id='delete_dataproc_cluster',
        cluster_name=unique_cluster_name,
        region=dag_config['GCE_REGION'],
        trigger_rule=trigger_rule.TriggerRule.ALL_DONE)

    create_dataproc_cluster >> run_dataproc_spark >> delete_dataproc_cluster
