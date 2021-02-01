from datetime import datetime
import aiohttp
import asyncio
import logging
import sys
import hashlib
import base64
import json
import os
import aiofiles
import cv2
import pickle

# This file is used as test file to test new functions

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("areq")
logging.getLogger("chardet.charsetprober").disabled = True

global loop


async def post(url, payload=None):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as response:
            if response.status != 200:
                print("Status:", response.status)
                print("Request: ", response.url)
            else:
                print("Success: ", response.url)
            result_json = await response.json()
            return result_json['data']['access_token']


async def get(url, payload=None, header=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=payload, headers=header) as response:
            if response.status != 200:
                print("Status:", response.status)
                print("Request: ", response.url)
            else:
                print("Success: ", response.url)
            result_json = await response.json()
            return result_json


def pretty_print(input_json):
    if isinstance(input_json, dict):
        input_json = json.dumps(input_json, indent=4)
    parsed = json.loads(input_json)
    print(json.dumps(parsed, indent=4, sort_keys=True))


def get_task_details(task_json):
    tasks = dict()
    for task in task_json['data']['items']:
        tasks[task['uuid']] = {'dataset_uuid': task['dataset_uuid'], 'status': task['status'],
                               'task_name': task['meta']['taskName'], 'task_username': task['meta']['taskUserName'],
                               'executor_username': task['executor']['username']}

    return tasks


def image_register(image_obj, input_label, height=0, width=0):
    image = {
        "uuid": image_obj['uuid'],
        "filename": image_obj['filename'],
        "url": image_obj['url'],
        "height": height,
        "width": width,
        "label": input_label
    }

    return image


def download_json(result, path, name):
    name = os.path.join(path, name)

    with open(name, 'w') as output:
        json.dump(result, output, indent=4)
        print("Saved to: ", name)


def get_user_info(username, password):
    # Login and get user info including user token and uuid
    auth_url = 'https://aist.feieee.com/api/oauth2/token'
    pwd = password.encode()
    login_payload = {'grant_type': 'password', 'password': hashlib.sha1(pwd).hexdigest(), 'scope': 'USER',
                     'username': username}  # '+86 15536902280'

    user_token = loop.run_until_complete(post(auth_url, login_payload))

    user_info = base64.b64decode(user_token.split('.')[1] + '===').decode('utf-8')
    user_uuid = json.loads(user_info)['uuid']

    return user_uuid, user_token


async def get_nickname(uuid, user_token):
    url = 'https://aist.feieee.com/api/user/' + uuid
    headers = {'Authorization': 'Bearer ' + user_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print("Status:", response.status)
                print("Request: ", response.url)
            else:
                print("Success: ", response.url)

            result_json = await response.json()
            return result_json['data']['username']


def get_task_info(user_uuid, user_token):
    # Get task list
    params = {'page_size': 1000, 'page_index': 1}
    headers = {'Authorization': 'Bearer ' + user_token}
    get_task_url = 'https://aist.feieee.com/api/user/' + user_uuid + '/published_task'
    task_json = loop.run_until_complete(get(get_task_url, params, headers))
    # pretty_print(task_json)

    return task_json


def get_dataset_list(user_token, dataset_uuid):
    headers = {'Authorization': 'Bearer ' + user_token}
    params = {'page_size': 1000, 'page_index': 1}
    get_dataset_list_url = 'https://aist.feieee.com/api/dataset/' + dataset_uuid
    dataset_list = loop.run_until_complete(get(get_dataset_list_url, params, headers))

    return dataset_list


def get_label_info(task_uuid, image_uuid, user_token):
    params = {'page_size': 1000, 'page_index': 1, 'data': image_uuid}
    headers = {'Authorization': 'Bearer ' + user_token}
    get_label_url = 'https://aist.feieee.com/api/task/' + task_uuid + '/label'
    label_json = loop.run_until_complete(get(get_label_url, params, headers))

    return label_json


def download_dataset(username, password):
    user_uuid, user_token = get_user_info(username, password)
    task_json = get_task_info(user_uuid, user_token)

    # Get dataset list and their status
    tasks = get_task_details(task_json)
    # print(tasks)

    accept_status = ['COMMITTED', 'ARCHIVED']
    datasets = dict()

    for k, v in tasks.items():
        if v['status'] in accept_status:
            dataset_list = get_dataset_list(user_token, v['dataset_uuid'])
            label_category_list = dataset_list['data']['self']['label_category']
            label_type = dataset_list['data']['self']['label_type']
            # pretty_print(dataset_list)

            # image uuid and its url, label
            images = []
            for i in dataset_list['data']['items']:
                # Raw image object
                obj = i['obj']

                label_json = get_label_info(task_uuid=k, image_uuid=obj['uuid'], user_token=user_token)
                label = label_json['data']['items'][0]['label']
                image = image_register(image_obj=obj, input_label=label)
                images.append(image)

            result = {
                "label_type": label_type,
                "images": images,
                "label_category": label_category_list
            }

            datasets[v['task_name']] = {'result': result, 'task_username': v['task_username'],
                                        'executor_username': v['executor_username']}

    return datasets


def create_dataset_folder(input_name, input_path):
    new_path = os.path.join(input_path, input_name)
    if not os.path.exists(new_path):
        os.makedirs(new_path)
        print('New path created: ', new_path)
        return new_path
    else:
        print("Already exists")
        return new_path


def save_to_folder(datasets, nickname, path):
    for task_name, data in datasets.items():
        name = task_name + ".json"
        dataset_folder_path = create_dataset_folder(task_name, create_dataset_folder(nickname, path))
        if dataset_folder_path:
            download_json(data['result'], path=dataset_folder_path, name=name)
        else:
            print("Already downloaded")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    Min = ['+86 15137393991', '123456']
    Qing = ['+86 15536902280', 'cike567']

    result_path = './Results_Upgrade'
    username = Min[0]
    pwd = Min[1]

    uuid, token = get_user_info(username=username, password=pwd)
    nickname = loop.run_until_complete(get_nickname(uuid, token))

    # for published tasks which are "COMMITTED' and "ACHIEVED"
    datasets = download_dataset(username=username, password=pwd)
    save_to_folder(datasets, nickname, result_path)

