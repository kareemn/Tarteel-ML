#!/usr/bin/env python3
import csv
import requests
import os
import webrtcvad
import wave

from urllib.parse import urlparse
from argparse import ArgumentParser

parser = ArgumentParser(description='Tarteel Audio Downloader')
parser.add_argument('--csv_url', type=str, default='https://www.tarteel.io/download-full-dataset-csv')
parser.add_argument('--local_csv_cache', type=str, default='.cache/local.csv')
parser.add_argument('--local_download_dir', type=str, default='.audio')
parser.add_argument('--vad_check', type=str, default=True)
args = parser.parse_args()

def downloadCSVDataset():
    print("Downloading CSV from", args.csv_url)
    with requests.Session() as s:
        download = s.get(args.csv_url)

        os.makedirs(os.path.dirname(args.local_csv_cache))
        decoded_content = download.content.decode('utf-8')
        file = open(args.local_csv_cache, "w")
        file.write(decoded_content)
        file.close()
        print ("Done downloading CSV.")

def parseCSV():
    file = open(args.local_csv_cache, "r")
    content = file.read()
    cr = csv.reader(content.splitlines(), delimiter=',')
    rows = list(cr)
    return rows

def cachedCSVExists():
    return os.path.isfile(args.local_csv_cache)

def downloadAudio(row):
    surah_number = row[0]
    ayah_number = row[1]
    url = "http://" + row[2]
    parsed_url = urlparse(url)
    wav_filename = os.path.basename(parsed_url.path)
    local_download_path = os.path.join(args.local_download_dir, surah_number, ayah_number, wav_filename)
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
        wav_bytes = wf.readframes(wf.getnframes())
        sample_rate = wf.getframerate()
        num_channels = wf.getnchannels()
        wf.close()
        # The webrtc VAD engine only works on certain sample rates.
        if args.vad_check and sample_rate in (8000, 16000, 320000, 48000) and not hasSpeech(wav_bytes, sample_rate, num_channels):
            print("Audio file", local_download_path, "does not have speech according to VAD. Removing.")
            os.remove(local_download_path)
    except wave.Error:
        print("Invalid wave header found", local_download_path, ", removing.")
        os.remove(local_download_path)

def hasSpeech(wav_bytes, sample_rate, num_channels):
    # Use webrtc's VAD with the lowest level of aggressiveness.
    mono_channel_bytes = wav_bytes
    if num_channels == 2:
        # just take the left channel for simplicity purposes.
        # We're just trying to get a quick sanity check, no need
        # to mix the two channels.
        mono_channel_bytes = b"".join([wav_bytes[i:i+2] for i in range(0, len(wav_bytes), 4)])
    vad = webrtcvad.Vad(1)
    frame_duration = 10  # ms
    bytes_per_sample = 2 # assuming 16-bit PCM.
    samples_per_vaded_chunk = (sample_rate * frame_duration / 1000)
    bytes_per_vaded_chunk = int(samples_per_vaded_chunk*bytes_per_sample)
    num_speech_frames = 0
    num_non_speech_frames = 0
    for i in range(0, len(mono_channel_bytes)-bytes_per_vaded_chunk, bytes_per_vaded_chunk):
        chunk_to_vad = mono_channel_bytes[i:i+bytes_per_vaded_chunk]
        if webrtcvad.valid_rate_and_frame_length(sample_rate, int(len(chunk_to_vad) / bytes_per_sample)) and vad.is_speech(chunk_to_vad, sample_rate):
            num_speech_frames += 1
        else:
            num_non_speech_frames += 1
    emptyAudio = (num_speech_frames == 0 or (num_speech_frames and num_non_speech_frames == 0))
    percentage_non_speech = (float(num_non_speech_frames) / float(num_non_speech_frames+num_speech_frames))
    print ("percentage non-speech:", percentage_non_speech, "num_speech_frames", num_speech_frames, "num_non_speech_frames", num_non_speech_frames)
    return not emptyAudio and percentage_non_speech < 0.5

if __name__ == "__main__":
    if not cachedCSVExists():
        downloadCSVDataset()
    else:
        print("Using cached copy of csv at", args.local_csv_cache)
    rows = parseCSV()
    for row in rows:
        if row[0] == '1':
            downloadAudio(row)