import os
import shutil

import requests
from bs4 import BeautifulSoup
import subprocess
import yaml
import main as ble_main


def write_default_commands(file_path):
    default_commands = {
        "syc_dir": "",
        "arg_before": "",
        "arg_after": "",
        'commands_before': [
            {'command': "python main.py --a D8:C9:E8:FB:2D:50 -c 'wifi on'"},
            {'command': "echo 'Executing command before main script'"}
        ],
        'commands_after': [
            {'command': "echo 'Executing command after main script'"},
            {'command': "python main.py --a D8:C9:E8:FB:2D:50 -c 'poweroff'"}
        ]
    }

    with open(file_path, 'w') as file:
        yaml.dump(default_commands, file)


def execute_commands(commands):
    for command_info in commands:
        command = command_info["command"]
        print(f"Executing command: {command}")
        subprocess.run(command, shell=True)


def fetch_files_info(base_url):
    url = f"{base_url}/videos/DCIM/100GOPRO/"
    response = requests.get(url)

    files_info = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all <a> tags within <td> tags
        links = soup.find_all('td')

        for link in links:
            if link.a and "mp4" in link.a.get_text().lower():
                file_name = link.a.get_text()
                file_url = url + file_name
                files_info.append((file_name, file_url))

    return files_info


def download_files(files_info_list, download_dir):
    for file_info in files_info_list:
        file_name, file_url = file_info
        local_path = os.path.join(download_dir, file_name)

        if not os.path.exists(local_path):
            print(f"Downloading {file_name} to {download_dir}")
            response = requests.get(file_url)

            if response.status_code == 200:
                temp = os.path.join(download_dir, "gpvideo.temp")
                with open(temp, 'wb') as file:
                    file.write(response.content)
                    shutil.move(temp, local_path)
                print(f"Downloaded {file_name} successfully")
            else:
                print(f"Failed to download {file_name}. Status code: {response.status_code}")


if __name__ == '__main__':
    config_file_path = 'config/config.yaml'
    config = None  # type: dict
    os.makedirs("config", exist_ok=True)
    if not os.path.exists(config_file_path):
        write_default_commands(config_file_path)
        print("init config and exit")
        exit(0)
    with open(config_file_path, 'r') as file:
        config = yaml.safe_load(file)
    ble_main.mian(config.get('arg_before', ""))
    execute_commands(config.get('commands_before', []))
    # Example usage
    base_url = "http://10.5.5.9"
    files_info_list = fetch_files_info(base_url)
    download_files(files_info_list, config.get("syc_dir"))
    ble_main.mian(config.get('arg_after', ""))
    execute_commands(config.get('commands_after', []))
