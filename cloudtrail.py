from __future__ import print_function
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import os
import json
import boto3
import urllib
import gzip

def process(event, context):

    # Set Region
    region = os.environ['AWS_REGION']

    # Set AWS Clients
    s3 = boto3.client('s3', region_name=region)
    es = boto3.client('es', region_name=region)

    # Retrieve Elasticsearch Domain Endpoint
    domain = es.describe_elasticsearch_domain(
        DomainName=os.environ['ES_DOMAIN_NAME']
    )
    endpoint = domain['DomainStatus']['Endpoint']

    # Set Auth
    auth = AWS4Auth(
        os.environ['AWS_ACCESS_KEY_ID'],
        os.environ['AWS_SECRET_ACCESS_KEY'],
        region,
        'es',
        session_token=os.environ['AWS_SESSION_TOKEN']
    )

    # Client Authentication
    es = Elasticsearch(
        hosts=[{'host': endpoint, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    # Load SNS message from event
    message = json.loads(event['Records'][0]['Sns']['Message'])

    # Retrieve bucket name and key from event
    bucket = message['s3Bucket']
    key = urllib.unquote_plus(message['s3ObjectKey'][0]).decode('utf8')

    # Ignore Digest Events
    if 'Digest' in key:
        return "Cloudtrail Digest File - Not Processing"

    # Download gzip file and store events
    path = '/tmp/ctlog.gz'
    s3.download_file(bucket, key, path)
    gzfile = gzip.open(path, "r")
    events = json.loads(gzfile.readlines()[0])["Records"]

    # Iterate through events and push to Elasticsearch domain
    for i in events:
        if 'Describe' not in i["eventName"]:
            i["@timestamp"] = i["eventTime"]
            i["eventSource"] = i["eventSource"].split(".")[0]

            ############# Add additional metadata to event #############
            
            # Example: Add AWS Account type
            i["accountType"] = "Production" 

            ############################################################

            data = json.dumps(i)
            print(data)
           
            event_date = i["eventTime"].split("T")[0].replace("-", ".")
           
            url = 'https://' + endpoint + '/logstash-' + event_date + '/cloudtrail/'
            index = 'logs-' + event_date
            res = es.index(index=index, doc_type='cloudtrail', id=i['eventID'], body=data)
            print(res)

        else:
            print("CloudTrail Describe Event - Not Processing")
  
    return 'Success'