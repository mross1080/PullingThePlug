from __future__ import print_function
import pickle
import os.path
import subprocess

import time
from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']
# SCOPES = []
from apiclient import errors
from apiclient import http
# ...
from termcolor import colored, cprint


from beautifultable import BeautifulTable

def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    # from selenium import webdriver
    # from selenium.webdriver.common.keys import Keys
    # import time
    # driver = webdriver.Firefox(
    #     executable_path='/Users/mattross/webdriver/gecko/v0.26.0/geckodriver-v0.26.0-macos/geckodriver')
    # driver.get("https://docs.google.com/document/d/1iExEioauDvg96boSVS7Us4CiDBFPKiaJeFXUeiU4mtY/edit")
    # # time.sleep(25)
    # # assert "Python" in driver.title
    # # elem = driver.find_element_by_name("q")
    # # elem.clear()
    # # elem.send_keys("pycon")
    # # elem.send_keys(Keys.RETURN)
    # # assert "No results found." not in driver.page_source
    # driver.close()

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
            creds = flow.run_local_server(port=0,open_browser=True)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    about_metadata = service.about().get(fields="*").execute()

    page_token = None
    permission_id = about_metadata['user']['permissionId']

    print("Permission ID is ", permission_id)
    timescale = "12 months"

    get_file_names_from_drive(service,permission_id,timescale)
    # DELETE LOCAL CREDENTIALS FILE FOR USER
    #subprocess.call(['rm', 'token.pickle'])

def get_file_names_from_drive(service, permission_id, timescale):
    # Call the Drive v3 API
    count =0
    full_set_of_files = []
    if timescale == "12 months":
        modified_time = '2018-12-29T12:00:00'

    if timescale == "18 months":
        modified_time = '2018-6-29T12:00:00'

    if timescale == "3 years":
        modified_time = '2015-6-29T12:00:00'
    print("\n\n\n\nRetrieving all documents modified before\n", modified_time)
    time.sleep(4)



    documents_to_retrieve = " and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.google-apps.presentation' or mimeType='application/vnd.google-apps.spreadsheet')"
    q = "'{}' in owners and modifiedTime < '{}' ".format(permission_id, modified_time)
    q += documents_to_retrieve

    results = service.files().list(q=q,
        pageSize=40, fields="*").execute()
    items = results.get('files', [])
    for item in items:
        full_set_of_files.append(item)
    #count = display_files_from_drive(count,full_set_of_files)
    page_token = results.get('nextPageToken')
    while page_token is not None:
        new_page_token = results.get('nextPageToken')
        #count = display_files_from_drive(count, results)
        print('fetching using page token',page_token)

        results = service.files().list(q=q,
                                       pageSize=40,
                                       fields="*"
                                       , pageToken=page_token).execute()
        items = results.get('files', [])
        for item in items:
            full_set_of_files.append(item)
        #count = display_files_from_drive(count, results)
        page_token = results.get('nextPageToken')
    return full_set_of_files



def display_files_from_drive(count, items):
    # items = results.get('files', [])
    file_names = []
    modified_times = []
    counts = []
    table = BeautifulTable(max_width=160)

    table.column_headers = ["File Number", "File Name", "Last Modified Time"]


    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            modified_time = item.get('modifiedTime', 'n/a')
            file_names.append(item['name'])
            modified_times.append(modified_time)
            #print(u'{0} ({1}) : last modified {2} \n \n'.format(item['name'], item['id'], modified_time))
            table.append_row([colored(count,'magenta'), colored(item['name'] + "                 ",'green'), colored(modified_time + "                                                                                                   ",'red')])

            count += 1

            print(table)
            del table[-1]
            time.sleep(.3)
    return count


#https://drive.google.com/file/d/0BxJ-sEJ9u5hQTDREZGJJVzVobUk/view?usp=sharing
# https://drive.google.com/file/d/0BxJ-sEJ9u5hQdENsNjhNQUkxQlU/view?usp=sharing
if __name__ == '__main__':
    main()