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

# 1. Login and get a user token
# 2. Use this user token, to get a uuid
# 3. This user may have many published task and assigned task, we only take published task
# 4. Use that user uuid to get a list of his tasks
# 5. Each task contains 3 important info, its dataset uuid, its own uuid and its status
# 6. Only "COMMITTED" tasks have labels on dataset
# 7.
#         for each tasks
#             if it is COMMITTED
#                 use /dataset/{dataset_uuid} to get its dataset info
#                 for image in dataset
#                     use image_uuid, task_uuid to get label to this image

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
            print("Status:", response.status)
            result_json = await response.json()
            return result_json['data']['access_token']


async def get(url, payload=None, header=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=payload, headers=header) as response:
            print("Status:", response.status)
            result_json = await response.json()
            return result_json


def pretty_print(input_json):
    if isinstance(input_json, dict):
        input_json = json.dumps(input_json, indent=4)
    parsed = json.loads(input_json)
    print(json.dumps(parsed, indent=4, sort_keys=True))


def get_taskUUID_datasetUUI_taskStatus(task_json):
    tasks = dict()
    for task in task_json['data']['items']:
        tasks[task['uuid']] = {'dataset_uuid': task['dataset_uuid'], 'status': task['status']}

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


def get_task_info(user_uuid, user_token):
    # Get task list
    params = {'page_size': 1000, 'page_index': 1}
    headers = {'Authorization': 'Bearer ' + user_token}
    get_task_url = 'https://aist.feieee.com/api/user/' + user_uuid + '/published_task'
    task_json = loop.run_until_complete(get(get_task_url, params, headers))

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
    tasks = get_taskUUID_datasetUUI_taskStatus(task_json)

    # one item in tasks: {task_uuid: {task_status, dataset_uuid}}
    for k, v in tasks.items():
        if v['status'] == 'COMMITTED':
            dataset_list = get_dataset_list(user_token, v['dataset_uuid'])
            label_category_list = dataset_list['data']['self']['label_category']
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
                "images": images,
                "label_category": label_category_list
            }

            name = 'result' + '-' + datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".json"
            download_json(result, path=r'/home/xunjie/PycharmProjects/TransferDataset/results/', name=name)


async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open('./results/test.jpg', mode='wb')
                await f.write(await resp.read())
                await f.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # url = "http://data.vsais.com/197ec0f6-0bd8-42bc-8c9c-29fd4f956c5e/20210121031628318933902.jpg?e=1611839106&token=kMwTtMsmCVtbGgI-l9gw1de9fmoaDO4nj67cFw3l:MnKRds01pyXa5p7Of6dp741Q6cs="
    # loop.run_until_complete(download_image(url))
    image = cv2.imread('./results/test.jpg', 0)
    # (width, high)
    print(image.shape)

    # download_dataset(username='+86 15536902280', password='cike567')
    # download_image('http://data.vsais.com/197ec0f6-0bd8-42bc-8c9c-29fd4f956c5e/20210121031628318933902.jpg?e=1611839106&token=kMwTtMsmCVtbGgI-l9gw1de9fmoaDO4nj67cFw3l:MnKRds01pyXa5p7Of6dp741Q6cs=')
