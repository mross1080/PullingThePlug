from __future__ import print_function

import serial
from serial import Serial
import serial.tools.list_ports
import time
from timeit import default_timer as timer
from datetime import timedelta
import mido

# this port address is for the serial tx/rx pins on the GPIO header
SERIAL_PORT = '/dev/cu.usbmodem143131'
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



def execute_deletion_of_all_files(service, files, midi_outport):
    print("Beginning deletion of {} files ".format(len(files)))
    period_between_deletions = 4
    for item in files:
        modified_time = item.get('modifiedTime', 'n/a')

        time.sleep(period_between_deletions)
        if period_between_deletions > 2:
            period_between_deletions -= .2
        elif period_between_deletions < 2 and period_between_deletions > 1:
            #print("here")
            period_between_deletions -= .1
        elif period_between_deletions < 1 and period_between_deletions > .18:
            #print("here")
            period_between_deletions -= .05
        file_id = item['id']
        # This is where the magic happens
        if READY_FOR_EXECUTION:
            service.files().delete(fileId=file_id).execute()
        midi_outport.send(mido.Message('note_on', note=44, time=1 ,channel=1))

        print(u'DELETED FILE NAME {0} : last modified {1} : created at {2}'.format(item['name'], modified_time,item.get('createdTime','')))
    midi_outport.send(mido.Message('note_on', note=48, time=1, channel=1))
    pass


def init_serial_connection():
    global ser
    port_name = '/dev/cu.usbmodem143111'
    ports = serial.tools.list_ports.comports()
    print(ports)
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "/dev/cu.usbmodem" in port.device:
            port_name = port.device
            print("using {} for specified port".format(port_name))
    ser = Serial(port_name, 9600)  # Establish the connection on a specific port
    return ser


print("waiting for messages")

def main():
    print("Initiating Pulling the Plug control Script")
    confirmed_stable_sensor_data = False
    detected_possible_pull = False
    initial_wait_time_completed = False
    midi_outport = mido.open_output('To Live Live')

    service = authenticate()
    print('Successfully Authenticated user to Google Drive')
    print("Connected to Drive API to collect files")
    all_files_found_for_deletion = list_files(service)
    start = timer()
    detection_timer_start = timer()
    detection_timer_end = timer()


    if READY_FOR_EXECUTION:
        print("WARNING, EXECUTION FLAG IS ENABLED PULLING THE PLUG WILL PERMANENTLY DELETE YOUR ACCESS TO YOUR DATA")
        execute_deletion_of_all_files(service, all_files_found_for_deletion, midi_outport)
    print("Beginning Setup, will not delete before 10 seconds of sensor stability ")
    ser = init_serial_connection()

    while True:
        # using ser.readline() assumes each line contains a single reading
        # sent using Serial.println() on the Arduino
        reading = int(ser.readline().decode('utf-8'))
        # print("Reading from arduino is ", reading)
        # reading is a string...do whatever you want from here

        # Don't Do Anything Until you have started with the signal that the plug is inserted
        # 2 indicates that plug is out so we want to be recieving the value 1
        if not confirmed_stable_sensor_data:
            if reading == 2:
                print("The plug is reading that it is not inserted, please reconfigure the plug before proceeding")
            else:
                confirmed_stable_sensor_data = True
                print("Beginning Detection for plug pull")
                detection_timer_start = timer()
        if not initial_wait_time_completed:
            end = timer()
            tdelta = int(timedelta(seconds=end - start).seconds)

            if tdelta > 10 and initial_wait_time_completed is False:
                initial_wait_time_completed = True

                print("{} seconds passed.  Ready for plug pull".format(tdelta))

        if confirmed_stable_sensor_data and initial_wait_time_completed:
            # If the Plug is out of the socket
            if reading == 2:
                # If this is the first time we have found the number 2 signal
                if detected_possible_pull is False:
                    # Start the timer for amount of time plug has been out and then look for enough time elapsed
                    detection_timer_start = timer()
                    detected_possible_pull = True
                else:
                    # Reading is 1 and plug is out, check if enough time has passed
                    detection_timer_end = timer()
                    plug_pulled_tdelta = int(timedelta(seconds=detection_timer_end - detection_timer_start).seconds)
                    print("{} seconds passed.  Checking if really a plug pull".format(plug_pulled_tdelta))

                    # Enough Time has Passed So Execute Deletion
                    if plug_pulled_tdelta > 4:

                        try:
                            print("Plug disconnected, fetching all files")
                            execute_deletion_of_all_files(service, all_files_found_for_deletion, midi_outport)
                        except Exception as error:
                            print('An error occurred: %s' % error)
                        print('deleting ')
                        exit()
            else:
                detected_possible_pull = False


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
            #print('Files:')
            for item in items:
                full_set_of_files.append(item)
            #     modified_time = item.get('modifiedTime', 'n/a')
            #     # if "n/a" not in modified_time:
            #     #     modified_year = int(modified_time.split("-")[0])
            #     #     if modified_year < 2019:
            #     time.sleep(.5)
            #     print(u'{0} ({1}) : last modified {2}'.format(item['name'], item['id'], modified_time))
            #     count+=1
        #print('fetching using page token',page_token)

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