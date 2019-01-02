#!/usr/bin/env python3
import csv
import requests
import os
from urllib.parse import urlparse
import wave

CSV_URL = 'https://www.tarteel.io/download-full-dataset-csv'
LOCAL_CSV_LOCATION = ".cache/local.csv"
AUDIO_DIR = ".audio/"

def downloadCSVDataset():
    print("Downloading CSV from", CSV_URL)
    with requests.Session() as s:
        download = s.get(CSV_URL)

        os.makedirs(os.path.dirname(LOCAL_CSV_LOCATION))
        decoded_content = download.content.decode('utf-8')
        file = open(LOCAL_CSV_LOCATION, "w")
        file.write(decoded_content)
        file.close()
        print ("Done downloading CSV.")

def parseCSV():
    file = open(LOCAL_CSV_LOCATION, "r")
    content = file.read()
    cr = csv.reader(content.splitlines(), delimiter=',')
    rows = list(cr)
    return rows

def cachedCSVExists():
    return os.path.isfile(LOCAL_CSV_LOCATION)

def downloadAudio(row):
    surah_number = row[0]
    ayah_number = row[1]
    url = "http://" + row[2]
    parsed_url = urlparse(url)
    wav_filename = os.path.basename(parsed_url.path)
    local_download_path = os.path.join(AUDIO_DIR, surah_number, ayah_number, wav_filename)
    with requests.Session() as s:
        print("Downloading", url, "to", local_download_path)
        download = s.get(url)
        dirname = os.path.dirname(local_download_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        file = open(local_download_path, "wb")
        file.write(download.content)
        file.close()
    # Check for valid WAVE header.
    try :
        wf = wave.open(local_download_path, "rb")
        wf.close()
    except wave.Error:
        print("Invalid wave header found", local_download_path, ", removing.")
        os.remove(local_download_path)

if __name__ == "__main__":
    if not cachedCSVExists():
        downloadCSVDataset()
    else:
        print("Using cached copy of csv at", LOCAL_CSV_LOCATION)
    rows = parseCSV()
    for row in rows:
        if row[0] == '1':
            downloadAudio(row)