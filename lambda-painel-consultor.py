import boto3
import json
import os
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def build_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',

        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }

dynamodb = boto3.resource('dynamodb')
table_name = os.getenv('TABLE_NAME', 'proz-arquitetos-pi-form-soliciteorcamento')
sns_topic_arn = os.getenv('SNS_TOPIC_ARN')  

def lambda_handler(event, context):
    http_method = event['httpMethod']
    path = event.get('resource', '')

    table = dynamodb.Table(table_name)

    # Listar todas as solicitações
    if http_method == 'GET' and path == '/solicitacoes':
        response = table.scan()
        return build_response(200, response['Items'])

    # Arquivar uma solicitação
    elif http_method == 'DELETE' and path == '/solicitacoes/{id}':
        item_id = event['pathParameters']['id']
        table.delete_item(Key={'id': item_id})
        return build_response(200, {'message': 'Solicitação arquivada'})

    # Responder ao cliente (via SNS)
    elif http_method == 'POST' and path == '/solicitacoes/responder':
        body = json.loads(event['body'])
        send_email(body['email'], body['nome'])
        return build_response(200, {'message': 'E-mail enviado'})

    return build_response(400, {'error': 'Requisição inválida'})

def send_email(email, nome):
    sns = boto3.client('sns')
    try:
        message = f"Olá, {nome}! Sua solicitação foi recebida pelo nosso time de cloud e em breve entraremos em contato."
        sns.publish(
            TopicArn= sns_topic_arn,
            Message=message,
            Subject='Confirmação de Solicitação Recebida'
        )
    except Exception as e:
        print("Erro ao enviar SNS:", str(e))
        raise