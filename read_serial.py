from __future__ import print_function

import serial

import time
from timeit import default_timer as timer
from datetime import timedelta


# this port address is for the serial tx/rx pins on the GPIO header
SERIAL_PORT = '/dev/cu.usbmodem141131'
# be sure to set this to the same rate used on the Arduino
SERIAL_RATE = 9600
import pickle
import os.path

from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive']
READY_FOR_EXECUTION = False

def execute_deletion_of_all_files(service, files):
    print("Beginning deletion of {} files ".format(len(files)))
    for item in files:
        modified_time = item.get('modifiedTime', 'n/a')

        time.sleep(5)
        file_id = item['id']
        # This is where the magic happens
        # if READY_FOR_EXECUTION:
        #     service.files().delete(fileId=file_id).execute()

        print(u'DELETED FILE NAME {0} : last modified {1}'.format(item['name'], modified_time))

    pass

def main():
    detectedPossiblePull = False
    ready_for_pull = False

    service = authenticate()
    all_files_found_for_deletion = list_files(service)
    start = timer()
    detectionTimerStart = timer()
    detectionTimerEnd = timer()

    print('authenticated looking for plug pull')
    print("Beginning Setup, will not delete before 10 seconds of sensor stability ")
    ser = serial.Serial(SERIAL_PORT, SERIAL_RATE)

    while True:
        # using ser.readline() assumes each line contains a single reading
        # sent using Serial.println() on the Arduino
        reading = int(ser.readline().decode('utf-8'))
        # reading is a string...do whatever you want from here
        print("Recieved from arduino over serial : ", reading)
        if reading == 2 and ready_for_pull:
            if detectedPossiblePull is False:
                detectionTimerStart = timer()
                detectedPossiblePull = True
            else:
                detectionTimerEnd = timer()
                plug_pulled_tdelta = int(timedelta(seconds=detectionTimerEnd - detectionTimerStart).seconds)
                print("{} seconds passed.  Checking if really a plug pull".format(plug_pulled_tdelta))

                if plug_pulled_tdelta > 2:

                    try:
                        print("Plug disconnected, fetching all files")
                        execute_deletion_of_all_files(service, all_files_found_for_deletion)
                    except Exception as error:
                        print('An error occurred: %s' % error)
                    print('deleting ')
                    exit()
        else:
            detectedPossiblePull = False
            end = timer()
            tdelta = int(timedelta(seconds=end - start).seconds)

            if tdelta > 10 and ready_for_pull is False:
                ready_for_pull = True

                print("{} seconds passed.  Ready for plug pull".format(tdelta))


        time.sleep(.1)

def list_files(service):
    # Call the Drive v3 API
    count =0
    full_set_of_files = []
    q = "(mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.google-apps.presentation' or mimeType='application/vnd.google-apps.spreadsheet')	 and modifiedTime < '2017-12-12T12:00:00' and '16520467830139767599' in owners"
    results = service.files().list(q=q,
        pageSize=40, fields="*").execute()
    page_token = results.get('nextPageToken')
    while page_token is not None:
        new_page_token = results.get('nextPageToken')
        items = results.get('files', [])
        count+= len(items)
        if not items:
            print('No files found.')
        else:
            print('Files:')
            for item in items:
                full_set_of_files.append(item)
            #     modified_time = item.get('modifiedTime', 'n/a')
            #     # if "n/a" not in modified_time:
            #     #     modified_year = int(modified_time.split("-")[0])
            #     #     if modified_year < 2019:
            #     time.sleep(.5)
            #     print(u'{0} ({1}) : last modified {2}'.format(item['name'], item['id'], modified_time))
            #     count+=1
        print('fetching using page token',page_token)

        results = service.files().list(q=q,
                                       pageSize=40,
                                       fields="nextPageToken, files(id, name)"
                                       , pageToken=page_token).execute()
        page_token = results.get('nextPageToken')
    print("Done, collected {} files from Google Drive ".format(count))
    return full_set_of_files


def authenticate():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:

            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:

            creds.refresh(Request())
        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
    return service


if __name__ == "__main__":
    main()