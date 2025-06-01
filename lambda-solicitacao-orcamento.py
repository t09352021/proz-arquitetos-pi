import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
from boto3.dynamodb.conditions import Key
import logging
import uuid
import os

# Configuração do logger para que os logs apareçam no CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
dynamodb_table = dynamodb.Table('proz-arquitetos-pi-form-soliciteorcamento')

#Sns topic env
sns_client = boto3.client('sns', region_name='sa-east-1')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')


status_check_path = '/status'
solicitacao_orcamento_path = '/solicitacao-orcamento'

def lambda_handler(event, context):
    print('Request event: ', event)
    response = None
   

    try:
        http_method = event.get('httpMethod')
        path = event.get('path')

        logger.info(f"HTTP Method: {http_method}, Path: {path}")
        
        if http_method == 'POST' and path == solicitacao_orcamento_path:
            response = save_request(json.loads(event['body']))
        else:
            response = build_response(404, '404 Not Found')

    except Exception as e:
        print('Error:', e)
        response = build_response(400, 'Error processing request')
   
    return response

def scan_dynamo_records(scan_params, item_array):
    response = dynamodb_table.scan(**scan_params)
    item_array.extend(response.get('Items', []))
   
    if 'LastEvaluatedKey' in response:
        scan_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
        return scan_dynamo_records(scan_params, item_array)
    else:
        return {'request': item_array}

def save_request(request_body):
    try:
        request_body['id'] = str(uuid.uuid4())

        # Publica notificação no SNS
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='Nova Solicitação de Orçamento',
            Message=f"Nova solicitação recebida:\n\n{json.dumps(request_body, indent=2)}"
        )
        logger.info(f"SNS_TOPIC_ARN: {SNS_TOPIC_ARN}")

        dynamodb_table.put_item(Item=request_body)
        body = {
            'Operation': 'SAVE',
            'Message': 'SUCCESS',
            'Item': request_body
        }
        return build_response(200, body)
    except ClientError as e:
        print('Error:', e)
        return build_response(400, e.response['Error']['Message'])


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Check if it's an int or a float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        # Let the base class default method raise the TypeError
        return super(DecimalEncoder, self).default(obj)

def build_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }