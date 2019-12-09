from __future__ import print_function
import pickle
import os.path

from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

from apiclient import errors
from apiclient import http
# ...





def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            print('a')
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("AAA")
            creds.refresh(Request())
        else:
            print('h')
            flow = InstalledAppFlow.from_client_secrets_file(
                '/Users/mattross/workspace/googleit/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    about_metadata = service.about().get(fields="*").execute()

    page_token = None
    permission_id = about_metadata['user']['permissionId']

    print("Permission ID is ", permission_id)
    timescale = "12 months"
    list_files(service,permission_id,timescale)

def list_files(service, permission_id, timescale):
    # Call the Drive v3 API
    count =0

    if timescale == "12 months":
        modified_time = '2018-12-29T12:00:00'

    if timescale == "18 months":
        modified_time = '2018-6-29T12:00:00'

    if timescale == "3 years":
        modified_time = '2015-6-29T12:00:00'
    print("Retrieving all documents modified before", modified_time)
    documents_to_retrieve = " and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.google-apps.presentation' or mimeType='application/vnd.google-apps.spreadsheet')"
    #q = "and modifiedTime < '2019-12-12T12:00:00' and '16520467830139767599' in owners"
    q = "'{}' in owners and modifiedTime < '{}' ".format(permission_id, modified_time)
    q += documents_to_retrieve

    results = service.files().list(q=q,
        pageSize=40, fields="*").execute()
    count = display_files_from_drive(count,results)
    page_token = results.get('nextPageToken')
    while page_token is not None:
        new_page_token = results.get('nextPageToken')
        count = display_files_from_drive(count, results)
        print('fetching using page token',page_token)

        results = service.files().list(q=q,
                                       pageSize=40,
                                       fields="*"
                                       , pageToken=page_token).execute()
        page_token = results.get('nextPageToken')
    print("Done, collected {} files".format(count))


def display_files_from_drive(count, results):
    items = results.get('files', [])
    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            modified_time = item.get('modifiedTime', 'n/a')
            print(u'{0} ({1}) : last modified {2}'.format(item['name'], item['id'], modified_time))
            count += 1
    return count


#https://drive.google.com/file/d/0BxJ-sEJ9u5hQTDREZGJJVzVobUk/view?usp=sharing
# https://drive.google.com/file/d/0BxJ-sEJ9u5hQdENsNjhNQUkxQlU/view?usp=sharing
if __name__ == '__main__':
    main()