import os
import requests
import argparse
from github import Github
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates, serialize_key_and_certificates
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption
from cryptography.hazmat.backends import default_backend
import time
import string
from itertools import product
from concurrent.futures import ThreadPoolExecutor

# Placeholders for configuration (user should replace these)
WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"  # Set your Discord webhook URL here
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"  # Set your GitHub token here
REPO_NAME = "YOUR_USERNAME/YOUR_REPO_NAME_HERE"  # Set your GitHub repository name here
BRANCH_NAME = "main"  # Set your GitHub branch name here
MAX_LENGTH = 8  # Set maximum password length (default is 8)
CUSTOM_PASSCODES = ['1', '12', '123', '1234', '12345', '123456', '1234567', '12345678', '123456789', '1234567890', 
                    'AppleP12.com', 'nabzclan.vip', 'regionoftech', 'applep12', 'AppleP12', 'applep12.com']  # Custom passcodes to test

def parse_args():
    parser = argparse.ArgumentParser(description="Brute Force P12 Password Cracker")
    parser.add_argument('--num-workers', type=int, required=True, help="Number of workers to run")
    return parser.parse_args()

def download_file(file_link):
    try:
        response = requests.get(file_link, stream=True)
        if response.status_code == 200 and response.content:
            return response.content
        else:
            print(f"Failed to download the file: {file_link}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
        return None

def brute_force_worker(file_data, file_link, file_number, lock, found_password):
    # Here you should implement the brute force logic, testing the passcodes
    for password in CUSTOM_PASSCODES:
        try:
            # Try loading the P12 file with the password
            key, cert, additional_certificates = load_key_and_certificates(file_data, password.encode(), backend=default_backend())

            # If password is correct, break out of the loop
            print(f"Password found for File {file_number}: {password}")
            found_password.append(password)
            break
        except Exception as e:
            continue  # Ignore any errors if the password is wrong
    return found_password

def send_to_webhook(file_number, old_password, new_password, old_file_link, new_file_link):
    """Send data to the webhook"""
    payload = {
        'content': f'Password found for File {file_number}!\nOld Password: {old_password}\nNew Password: {new_password}\nOld file download link: {old_file_link}\nNew file download link: {new_file_link}'
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print(f"Password and file links sent to webhook for File {file_number}")
        else:
            print(f"Failed to send to webhook. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending to webhook: {e}")

def main():
    args = parse_args()
    num_workers = args.num_workers
    file_links = [
        'https://example.com/yourfile.p12'  # Replace with the actual file link
    ]

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for idx, file_link in enumerate(file_links, start=1):
            file_data = download_file(file_link)
            if file_data:
                futures.append(executor.submit(brute_force_worker, file_data, file_link, idx, lock, found_password))

        for future in futures:
            future.result()

if __name__ == '__main__':
    main()