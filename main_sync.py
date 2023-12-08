import argparse
import json
import os
import shutil
import time

import requests
from bs4 import BeautifulSoup
import subprocess
import yaml
# from mtpy.core import MTP
import main as ble_main


class GoProData:
    def __init__(self) -> None:
        self.config_file = None
        self.config = {}
        self.copied_store_file = None
        self.copied_store = {}

    def __del__(self):
        """保存字典到文件"""
        self.save_to_file(self.config_file, self.config)
        self.save_to_file(self.copied_store_file, self.copied_store)

    def do_init(self):
        """
        读取文件到字典"""
        self.config = self.load_from_file(self.config_file)
        self.copied_store = self.load_from_file(self.copied_store_file)
        self.write_default_commands()

    def save_to_file(self, file_path, data):
        """将字典保存到文件"""
        with open(file_path, 'w') as json_file:
            yaml.dump(data, json_file)

    def load_from_file(self, file_path):
        """从文件加载字典"""
        try:
            with open(file_path, 'r') as json_file:
                return yaml.safe_load(json_file)
        except FileNotFoundError:
            return {}

    def write_default_commands(self):
        if os.path.exists(self.config_file):
            return
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        default_commands = {
            "syc_dir": "",
            "device_name": "",
            "arg_before": "",
            "arg_after": "",
            'commands_before': [
                {'command': "echo before main script"}
            ],
            'commands_after': [
                {'command': "echo after script"}
            ]
        }

        with open(self.config_file, 'w') as file:
            yaml.dump(default_commands, file)

    def execute_commands(self, commands):
        for command_info in commands:
            command = command_info["command"]
            print(f"Executing command: {command}")
            subprocess.run(command, shell=True)

    def fetch_files_info(self, ):
        url = "http://10.5.5.9/videos/DCIM/100GOPRO/"
        response = requests.get(url + "?dd", timeout=10)

        files_info = []

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all <a> tags within <td> tags
            links = soup.find_all('td')

            for link in links:
                name = link.a.get_text().lower() if link.a else None
                if link.a and name and name.startswith("g") and "lrv" not in name and "thm" not in name:
                    file_name = link.a.get_text()
                    file_url = url + file_name
                    files_info.append((file_name, file_url))
        return files_info

    def download_files(self, files_info_list, download_dir):
        start_len = len(self.copied_store)
        for file_info in files_info_list:
            file_name, file_url = file_info
            local_path = os.path.join(download_dir, file_name)

            if not os.path.exists(local_path) and file_name not in self.copied_store:
                print(f"Downloading {file_name} to {download_dir}")
                response = requests.get(file_url)

                if response.status_code == 200:
                    temp = os.path.join(download_dir, "gpvideo.temp")
                    with open(temp, 'wb') as file:
                        file.write(response.content)
                    shutil.move(temp, local_path)
                    print(f"Downloaded {file_name} successfully")
                    self.copied_store[file_name] = 1
                else:
                    print(f"Failed to download {file_name}. Status code: {response.status_code}")
        print(f"copid {len(self.copied_store) - start_len}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', "-t", dest='type', help="run type: main", required=False, type=str)
    args = parser.parse_args()

    start = time.time()
    config_file_path = 'config/config_gopro_down.yaml'
    config_store_path = 'config/gopro_down.yaml'
    go = GoProData()
    go.config_file = config_file_path
    go.copied_store_file = config_store_path
    go.do_init()
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            if args.type == "main":
                ble_main.main("")
                go.execute_commands(go.config.get('commands_before', []))
                print(f"done")
                exit(0)
            ble_main.main(go.config.get('arg_before', ""))
            go.execute_commands(go.config.get('commands_before', []))
            files_info_list = go.fetch_files_info()
            go.download_files(files_info_list, go.config.get("syc_dir"))
            ble_main.main(go.config.get('arg_after', ""))
            go.execute_commands(go.config.get('commands_after', []))
            go.__del__()
            break  # 如果成功运行，跳出循环
        except Exception as e:
            print(f"Error occurred: {e}")
            if attempt < max_retries:
                print(f"Retrying... (Attempt {attempt}/{max_retries})")
                time.sleep(1)  # 等待一秒后重试
            else:
                print(f"Max retries reached. Exiting.")
                exit(1)

    print(f"use {time.time() - start}s")
    print(f"done")
