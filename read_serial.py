from __future__ import print_function
from art import *
import argparse
import subprocess
from random import random, randint
import logging
import serial
from beautifultable import BeautifulTable
from serial import Serial
import serial.tools.list_ports
import time
from timeit import default_timer as timer
from datetime import timedelta
import mido
from termcolor import colored
import logging
logging.basicConfig()
from pulling_the_plug import get_file_names_from_drive, display_files_from_drive
logging.getLogger().setLevel(logging.INFO)
urllib3_logger = logging.getLogger('googleapiclient')
urllib3_logger.setLevel(logging.CRITICAL)
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



READY_FOR_EXECUTION = True


def display_files_in_table(items):
    count = 0
    for item in items:
        count+=1
        display_table = BeautifulTable(max_width=160)
        display_table.column_headers = ["File Number", "File Name", "Last Modified Time", "Last Viewed Time"]

        modified_time = item.get('modifiedTime', 'n/a')

        display_table.append_row([colored(count, 'magenta'), colored(item['name'], 'green'), colored(
            modified_time ,
            'red'), colored(item.get('viewedByMeTime'),'blue')])
        print(display_table)
        time.sleep(.3)
    count+=1



def execute_deletion_of_all_files(service, files, midi_outport):
    delete_msg = text2art("Beginning deletion of {} files ".format(len(files)), font='small')
    print(delete_msg)
    # logging.info("Beginning deletion of {} files ".format(len(files)))
    count = 0
    period_between_deletions = 4


    for item in files:
        display_table = BeautifulTable(max_width=160)
        display_table.column_headers = ["File Number", "File Name", "Last Modified Time", "Last Viewed Time"]
        modified_time = item.get('modifiedTime', 'n/a')
        count+=1
        time.sleep(period_between_deletions)
        if period_between_deletions > 2:
            period_between_deletions -= .2
        elif period_between_deletions < 2 and period_between_deletions > 1:

            period_between_deletions -= .1
        elif period_between_deletions < 1 and period_between_deletions > .18:

            period_between_deletions -= .05
        file_id = item['id']
        # This is where the magic happens
        if READY_FOR_EXECUTION:
            service.files().delete(fileId=file_id).execute()
        midi_outport.send(mido.Message('note_on', note=44, time=1 ,channel=1))

        # print("DELETING")
        # print(u'DELETED FILE NAME {0} : last modified {1} : created at {2}'.format(item['name'], modified_time,item.get('createdTime','')))
        display_table.append_row([colored(count, 'magenta'), colored(item['name'], 'green'), colored(
            modified_time,
            'red'), colored(item.get('viewedByMeTime'), 'blue')])
        print("DELETED" + str(display_table))

    midi_outport.send(mido.Message('note_on', note=48, time=1, channel=1))
    pass


def init_serial_connection():
    global ser
    port_name = '/dev/cu.usbmodem143111'
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "/dev/cu.usbmodem" in port.device:
            port_name = port.device
    ser = Serial(port_name, 9600)  # Establish the connection on a specific port
    return ser




def main(args):
    main_title = text2art("Pull The Plug")
    print(main_title)
    logging.info("Initiating Pulling the Plug control Script")
    confirmed_stable_sensor_data = False
    detected_possible_pull = False
    initial_wait_time_completed = False
    midi_outport = mido.open_output('To Live Live')

    service = authenticate()
    logging.info('Successfully Authenticated user to Google Drive')
    time.sleep(2)

    # all_files_found_for_deletion = list_files(service)
    about_metadata = service.about().get(fields="*").execute()

    page_token = None
    permission_id = about_metadata['user']['permissionId']
    timescale = "18 months"
    all_files_found_for_deletion = get_file_names_from_drive(service,permission_id,timescale)

    print("A Total of {} files have not been looked at in over 18 months".format(len(all_files_found_for_deletion)))
    if args.list_all:
        display_files_in_table(all_files_found_for_deletion)
    if args.single_file:
        print("\n\n\nRandomly Selecting A Single File For Deletion")
        time.sleep(4)
        all_files_found_for_deletion = [all_files_found_for_deletion[randint(0, len(all_files_found_for_deletion))-1]]
        file_to_delete = text2art("File To Delete Is ...",font='small')
        print(file_to_delete)
        # logging.info("Your Randomly Selected File For Deletion is ....")
        display_files_in_table(all_files_found_for_deletion)

    start = timer()
    detection_timer_start = timer()
    detection_timer_end = timer()


    if READY_FOR_EXECUTION:
        logging.info("\n\nWARNING, EXECUTION FLAG IS ENABLED PULLING THE PLUG WILL PERMANENTLY DELETE YOUR ACCESS TO YOUR DATA\n\n")
    else:
        logging.info("Ready for execution flag is not enabled, deletion will not occur")

    logging.info("Beginning Setup, calibrating plug stability.  Please wait 5 seconds ...")
    ser = init_serial_connection()

    while True:
        # using ser.readline() assumes each line contains a single reading
        # sent using Serial.println() on the Arduino
        reading = int(ser.readline().decode('utf-8'))
        # logging.info("Reading from arduino is ", reading)
        # reading is a string...do whatever you want from here

        # Don't Do Anything Until you have started with the signal that the plug is inserted
        # 2 indicates that plug is out so we want to be recieving the value 1
        if not confirmed_stable_sensor_data:
            if reading == 2:
                logging.info("The plug is reading that it is not inserted, please reconfigure the plug before proceeding")
            else:
                print("\n\n\n")
                confirmed_stable_sensor_data = True
                detection_timer_start = timer()
        if not initial_wait_time_completed:
            end = timer()
            tdelta = int(timedelta(seconds=end - start).seconds)

            if tdelta > 5 and initial_wait_time_completed is False:
                initial_wait_time_completed = True

                #print("{} seconds passed.  Ready for plug pull".format(tdelta))
                ready = text2art("Pull The Plug When You Are Ready", font='small')
                print(ready)
                print("Deletion will occur after plug is removed for 6 seconds ")

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
                    midi_outport.send(mido.Message('note_on', note=52, channel=2))

                    print("{} seconds passed since plug pulled".format(plug_pulled_tdelta))

                    # Enough Time has Passed So Execute Deletion
                    if plug_pulled_tdelta > 6:

                        try:
                            midi_outport.send(mido.Message('note_off', note=52, time=1, channel=2))

                            execute_deletion_of_all_files(service, all_files_found_for_deletion, midi_outport)
                        except Exception as error:
                            print('An error occurred: %s' % error)
                            print("Script Encountered Error --- Deleting Local Credentials File")

                        print("Completed Script and Deleted Local Credentials File")
                        # DELETE LOCAL CREDENTIALS FILE FOR USER
                        subprocess.call(['rm', 'token.pickle'])
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
    parser = argparse.ArgumentParser(description='Options For Running Analysis ')

    parser.add_argument('--single_file', metavar='-a', default=False, type=bool,
                        help='Flag Indicating if only a single file should be choosen for deletion', )
    parser.add_argument('--list_all', metavar='-a', default=False, type=bool,
                        help='Flag to Use Ableton for Translation', )
    parser.add_argument('--enable_deletion', metavar='-a', default=False, type=bool,
                        help='Flag to Enable Deletion ', )

    args = parser.parse_args()

    main(args)