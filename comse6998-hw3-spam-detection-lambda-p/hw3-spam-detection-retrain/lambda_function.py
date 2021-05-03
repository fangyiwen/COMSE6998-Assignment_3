import json
import boto3
import time
import requests
import websocket

def lambda_handler(event, context):
    sm_client = boto3.client('sagemaker')
    notebook_instance_name = 'hw3-spam-detection-retrain'
    url = sm_client.create_presigned_notebook_instance_url(NotebookInstanceName=notebook_instance_name)['AuthorizedUrl']

    url_tokens = url.split('/')
    http_proto = url_tokens[0]
    http_hn = url_tokens[2].split('?')[0].split('#')[0]

    s = requests.Session()
    s.get(url)
    cookies = "; ".join(key + "=" + value for key, value in s.cookies.items())

    ws = websocket.create_connection(
        "wss://{}/terminals/websocket/1".format(http_hn),
        cookie=cookies,
        host=http_hn,
        origin=http_proto + "//" + http_hn
    )

    ws.send("""[ "stdin", "cd ~/anaconda3/envs\\r" ]""")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)

    ws.send("""[ "stdin", "source activate JupyterSystemEnv\\r" ]""")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)

    ws.send("""[ "stdin", "pip uninstall sagemaker\\r" ]""")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)

    ws.send("""[ "stdin", "y\\r" ]""")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)

    ws.send("""[ "stdin", "pip install sagemaker===1.19.0\\r" ]""")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)

    ws.send("""[ "stdin", "jupyter nbconvert --execute --to notebook --inplace /home/ec2-user/SageMaker/smlambdaworkshop/training/sms_spam_classifier_mxnet.ipynb --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=-1\\r" ]""")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)

    time.sleep(1)
    ws.close()

    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
