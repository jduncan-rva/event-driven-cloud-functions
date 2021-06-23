import requests
import json
import secrets
import os
from zipfile import ZipFile
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession, Request
from google.cloud import firestore
from google.cloud import storage
import apache_beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import StandardOptions
from apache_beam.options.pipeline_options import SetupOptions
from apache_beam.io import WriteToText


scopes=[
  "https://www.googleapis.com/auth/cloud-platform",
  "https://www.googleapis.com/auth/userinfo.email"]

credentials = service_account.Credentials.from_service_account_file(
  'cloudfunctions.json',
  scopes=scopes)

authed_session = AuthorizedSession(credentials)
request = Request()
credentials.refresh(request)
bearer_token = credentials.token

def event_decompressor(event, context):
  """Background Cloud Function to be triggered by Cloud Storage file creation.
  This triggers a dataflow pipeline to de-compress zip files.
  """
  
  bucket = event['bucket']
  out_bucket = os.environ['DATA_OUT_BKT']
  filename = event['name']
  project = os.environ['PROJECT_ID']
  region = os.environ['REGION']
  file_handle = filename.split('.')[0]
  
  site_id = secrets.token_hex(nbytes=4)
  session_id = "{}_{}".format(file_handle, site_id)
  
  pipeline_args = [
        '--runner=DataflowRunner',
        '--project={}'.format(project),
        '--region={}'.format(region),
        '--staging_location=gs://dz-dropzone/staging',
        '--temp_location=gs://dz-dropzone/tmp',
        '--job_name=cf-decompressor'
  ]
  
  pipeline_options = PipelineOptions(pipeline_args)
  pipeline_options.view_as(SetupOptions).save_main_session = False
  pipeline_options.view_as(StandardOptions).streaming = False
  
  with apache_beam.Pipeline(options=pipeline_options) as p:
      
    print('Processing file gs://{}/{}'.format(bucket,filename))
    
    with apache_beam.io.gcp.gcsio.GcsIO().open('gs://{}/{}'.format(bucket,filename), 'r') as zipped_file, ZipFile(zipped_file, 'r') as z:
          
      for zip_content in z.namelist():        
        rawdata = (
            p  | 'load {}'.format(zip_content) >> apache_beam.Create( [z.read(zip_content).decode('utf-8')] )
        )

        rawdata | f'write {zip_content} to gcs' >> WriteToText( f'gs://{out_bucket}/{zip_content}', num_shards=1, shard_name_template='' )
  
  print('Event ID: {}'.format(context.event_id))
  print('Event type: {}'.format(context.event_type))
  print('File: {}'.format(event['name']))
  print('Content Type: {}'.format(content_type))
  print('Created: {}'.format(event['timeCreated']))  

def video_transcode(event, context):
  """Background Cloud Function called when a video file is uploaded. Triggers an
  automatic transcode event via the Transcoder API
  """

  video_file = event['name']
  filename = video_file.split('.')[0]
  content_type = event['contentType']
  bucket = event['bucket']
  bucket_out = os.environ['VIDEO_OUT_BKT']
  project = "jduncan-asensus-video"

  if content_type == 'video/mp4':

    transcode_json = dict()
    transcode_json['inputUri'] = "gs://{}/{}".format(bucket, video_file)
    transcode_json['outputUri'] = "gs://{}/{}/".format(bucket_out, filename)
    
    transcode_data = json.dumps(transcode_json)
    
    headers = {
      'Authorization': 'Bearer {}'.format(bearer_token),
      'Content-Type': 'application/json; charset=utf-8'
    }

    transcode_url = 'https://transcoder.googleapis.com/v1beta1/projects/{}/locations/us-central1/jobs'.format(project)
    
    data = requests.post(transcode_url, headers=headers, data=transcode_data)

    print('Event ID: {}'.format(context.event_id))
    print('Event type: {}'.format(context.event_type))
    print('File: {}'.format(event['name']))
    print('Content-Type: {}'.format(content_type))
    print('Created: {}'.format(event['timeCreated']))
    print('Transcode Response Code: {}'.format(data.status_code))

  else:
    print('Event ID: {}'.format(context.event_id))
    print('Event type: {}'.format(context.event_type))
    print('File: {}'.format(event['name']))
    print('Content-Type: {}'.format(content_type))
    print('Unable to Transcode: Not a supported content type')

def firestore_ingest(event, context):
  """Backgound Cloud Functiona called when a dataset is decompressed and uploads
  the file into Firestore"""

  db = firestore.Client()
  storage_client = storage.Client()

  filename = event['name']
  bucket = event['bucket']
  event_name = filename.split('.')[0]
  filetype = event['contentType']

  bkt = storage_client.get_bucket(bucket)
  blob = bkt.blob(filename)
  d_blob = blob.download_as_string()

  data = json.loads(d_blob)

  doc_ref = db.collection(u'senhance').document(event_name)
  doc_ref.set(data)

  print('Event ID: {}'.format(context.event_id))
  print('Event type: {}'.format(context.event_type))
  print('File: {}'.format(event['name']))
  print('Content-Type: {}'.format(filetype))
  print('Created: {}'.format(event['timeCreated']))
  print('JSON Upload: {}'.format(data))
