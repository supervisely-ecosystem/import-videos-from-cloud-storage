import io
import google.api_core.exceptions as google_exceptions
from google.cloud import storage
from google.resumable_media.requests import ChunkedDownload
import google.auth.transport.requests as tr_requests
from google.oauth2 import service_account
import supervisely_lib as sly

_client = None
_credentials = None
_transport = None


def init(cred_path):
    global _client, _credentials, _transport
    _client = storage.Client.from_service_account_json(cred_path)
    _credentials = service_account.Credentials.from_service_account_file(cred_path)
    _transport = tr_requests.AuthorizedSession(_credentials)


def list_blobs(bucket_name):
    #bucket = _client.bucket(bucket_name)
    blobs = _client.list_blobs(bucket_name)
    return blobs


def download(bucket_name, blob_path, save_path):
    bucket = _client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(save_path)


# https://googleapis.dev/python/google-resumable-media/latest/resumable_media/requests.html#chunked-downloads
def streaming_download(bucket_name, blob_name, save_path):
    bucket = _client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url_template = u'https://www.googleapis.com/download/storage/v1/b/{bucket}/o/{blob_name}?alt=media'
    media_url = url_template.format(bucket=bucket, blob_name=blob_name)

    stream = io.BytesIO()
    chunk_size = 5 * 1024 * 1024
    download = ChunkedDownload(media_url, chunk_size, stream)

    sly.fs.ensure_base_path(save_path)
    with open(save_path, 'wb') as fd:
        while not download.finished:
            response = download.consume_next_chunk(_transport)
            fd.write(response.data)
            # if progress_cb is not None:
            #     progress_cb(len(chunk))