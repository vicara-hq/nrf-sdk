from urllib import request,parse
import subprocess
from bs4 import BeautifulSoup
import re
import json
import configparser
import logging

config = configparser.ConfigParser()
config.read("config.ini")

LOG_LEVEL = int(config["logging"]["debug"])
if LOG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)

SDK_BASE_URL = config["nrf-sdk"]["BaseURL"]
SDK_DOCKER_REPO = config["nrf-sdk"]["DockerRepo"]

LIST_TAGS_URL = "https://registry.hub.docker.com/v1/repositories/{}/tags"

def run_shell_command(command):
    subprocess.run(command, shell=True, check=True)

def build_docker_image(name, download_url):
    logging.info("Building {}".format(name))
    run_shell_command("docker build --build-arg download_url=\"{}\" -t \"{}\" .".format(download_url, name))

def publish_docker_image(image):
    logging.info("Publishing {}".format(image))
    run_shell_command("docker push {}".format(image))

def delete_docker_image(image):
    logging.info("Deleting {}".format(image))
    run_shell_command("docker rmi -f {}".format(image))

def list_repo_tags(image):
    url = LIST_TAGS_URL.format(image)
    tags_obj = json.load(request.urlopen(url))
    logging.info("{} tags built in {} repo".format(len(tags_obj), image))
    return list(map(lambda tag:tag["name"], tags_obj))

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
    sdk_built_tags = list_repo_tags(SDK_DOCKER_REPO)

    sdk_downloads = get_nrf_sdk_downloads()

    sdk_build_tags = list(set(sdk_downloads.keys()) - set(sdk_built_tags))
    if len(sdk_build_tags):
        logging.info("nrf sdk tags to build:\n{}".format(" ".join(sdk_build_tags)))

    finished_builds = []

    for tag in sdk_build_tags:
        build_tag = "{}:{}".format(SDK_DOCKER_REPO, tag)
        build_docker_image(build_tag, sdk_downloads[tag])
        publish_docker_image(build_tag)
        finished_builds.append(build_tag)
    
    map(delete_docker_image, finished_builds)

# main()