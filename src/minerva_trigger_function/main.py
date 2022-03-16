from google.auth.transport.requests import AuthorizedSession
from os import getenv
import requests
import google.auth
import json


def trigger_dag(data, context=None):
    send_request(data, auth_request)

def send_request(data, request):
    print(f'Event: {data}')
    data_attributes = data['attributes']
    path = data_attributes['objectId'].split('/')
    if path[-1].endswith('.parquet'):
        json_data = {
            'conf': {
                'id': data_attributes['objectGeneration'],
                'bucket': data_attributes['bucketId'],
                'file': data_attributes['objectId'],
                'pipeline': 'minerva'
            }
        }
        print("Below configuration is being sent to the composer dag:")
        print(json.dumps(json_data))

        response = request(json_data)
        if response.status_code == 403:
            raise requests.HTTPError("You do not have a permission to perform this operation."
                                     f"{response.headers} / {response.text}")
        elif response.status_code != 200:
            response.raise_for_status()
        else:
            return response.text

def auth_request(payload)-> google.auth.transport.Response:
    webserver = getenv("AIRFLOW_URI")
    dag_id = getenv("DAG_ID")

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    endpoint = f"api/v1/dags/{dag_id}/dagRuns"
    api_url = f"{webserver}/{endpoint}"

    authed_session = AuthorizedSession(credentials)
    return authed_session.request('POST', api_url, timeout = 90, json = payload)

