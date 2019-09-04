from urllib import request,parse
import subprocess
from bs4 import BeautifulSoup
import re
import json
import configparser
import logging
import pygit

config = configparser.ConfigParser()
config.read("../config.ini")

LOG_LEVEL = int(config["logging"]["debug"])
if LOG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)

SDK_BASE_URL = config["nrf-sdk"]["BaseURL"]

def run_shell_command(command):
    return subprocess.run(command, shell=True)

def checkout_or_create_branch(version): 
    return run_shell_command("git checkout {} || git checkout --orphan {} && git rm -rf . > /dev/null".format(version, version))

def add_and_commit():
    return run_shell_command("git add . > /dev/null && git commit -m 'update' > /dev/null").returncode == 0

def get_nrf_sdk_downloads():
    folders_page = BeautifulSoup(request.urlopen(SDK_BASE_URL), features="html.parser")
    folder_links = []

    for a in folders_page.find_all("a", href=True):
        link = a["href"]
        if re.search(r"SDK_v\d+\.x\.x", link, re.IGNORECASE):
            folder_links.append(link)
    
    downloads = dict()
    for link in folder_links:
        folder_url = parse.urljoin(SDK_BASE_URL, link)
        folder_page = BeautifulSoup(request.urlopen(folder_url), features="html.parser")
        for a in folder_page.find_all("a", href=True):
            l = a["href"]
            match = re.search(r"SDK_([\d\.]+)_[a-z0-9]{7}\.zip", l, re.IGNORECASE) or re.search(r"sdk_v([\d_]+)_[a-z0-9]{5}\.zip", l, re.IGNORECASE)
            if match:
                version = match.group(1).strip("_").replace("_", ".")
                download_link = parse.urljoin(folder_url, l)
                downloads[version] = download_link
    
    logging.info("Found {} versions of nrf sdk available".format(len(downloads)))

    return downloads

def main():
    sdk_downloads = get_nrf_sdk_downloads()

    logging.info("Found following versions of nrf sdk:\n{}".format(" ".join(sdk_downloads.keys())))


    for version in sdk_downloads:
        logging.info("Downloading {}".format(version))

        file_name = "../downloads/{}.zip".format(version)
        run_shell_command("wget -q -O {} {} ".format(file_name, sdk_downloads[version]))

        logging.info("Switching git repo to {} branch".format(version))
        checkout_or_create_branch(version)

        unzip_cmd = "unzip -qq -o -d . {}".format(file_name)
        logging.info("Running {}".format(unzip_cmd))
        run_shell_command(unzip_cmd)

        if add_and_commit():
            logging.info("Version {} has changed. Staging and commiting changes.".format(version))
        else:
            logging.info("Version {} unchanged".format(version))



main()
