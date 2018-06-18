from __future__ import print_function
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import os
import json
import boto3

def process(event, context):

    # Set Region
    region = os.environ['AWS_REGION']

    # Set AWS Client
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
    
    event["@timestamp"] = event["time"]
    event["eventSource"] = event["source"].split(".")[0]
    event["type"] = event["guardduty"]
    
    ############# Add additional metadata to event #############
            
    # Example: Add AWS Account type
    event["accountType"] = "Production" 

    ############################################################
    
    data = json.dumps(event)
    print(data)
           
    event_date = event["time"].split("T")[0].replace("-", ".")
           
    url = 'https://' + endpoint + '/logstash-' + event_date + '/cloudtrail/'
    index = 'logs-' + event_date
    res = es.index(index=index, doc_type='aws', id=event['id'], body=data)
    print(res)

    return 'Success'