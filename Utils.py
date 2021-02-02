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

# Download options:
# 1. Download all and overwrite all
# 2. Download optional
# 3. Selective download, chose which dataset

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("areq")
logging.getLogger("chardet.charsetprober").disabled = True


def update_json(json_path, filename, shape):
    with open(json_path) as json_file:
        j = json.load(json_file)


async def download_image(url, image_path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(image_path, mode='wb')
                await f.write(await resp.read())
                await f.close()


def create_dataset_folder(input_name, input_path):
    new_path = os.path.join(input_path, input_name)
    if not os.path.exists(new_path):
        os.makedirs(new_path)
        print('New path created: ', new_path)
        return new_path
    else:
        print("Already exists")
        return new_path


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


def get_task_details(task_json):
    tasks = dict()
    for task in task_json['data']['items']:
        tasks[task['uuid']] = {'dataset_uuid': task['dataset_uuid'], 'status': task['status'],
                               'task_name': task['meta']['taskName'], 'task_username': task['meta']['taskUserName'],
                               'executor_username': task['executor']['username']}

    return tasks


def pretty_print(input_json):
    if isinstance(input_json, dict):
        input_json = json.dumps(input_json, indent=4)
    parsed = json.loads(input_json)
    print(json.dumps(parsed, indent=4, sort_keys=True))


def download_json(result, path, name):
    name = os.path.join(path, name)

    with open(name, 'w') as output:
        json.dump(result, output, indent=4)
        print("Saved to: ", name)


class Utils:
    def __init__(self, username, pwd, result_path):
        self.loop = asyncio.get_event_loop()
        self.username = username
        self.pwd = pwd
        self.result_path = result_path  # ./results
        self.user_result_path = None  # ./results/Sam
        self.nickname = None
        self.user_uuid = None
        self.user_token = None
        self.task_json = None
        self.valid_dataset = []
        self.downloaded_dataset = set()
        self.accept_status = {'COMMITTED', 'ARCHIVED'}
        # k = ./results/小齐/
        # v = ./results/小齐/无锡电梯超员_24899_2021_01_04/xxx.json
        self.json_path = dict()

    def update_downloaded_dataset(self):
        pass

    def set_nickname(self, input_name):
        self.nickname = input_name

    def set_user_result_path(self, input_name=None):
        self.user_result_path = os.path.join(result_path, self.nickname if input_name is None else input_name)

    def update_json_path(self):
        result = dict()
        try:
            for directory in os.listdir(self.user_result_path):
                abs_path = os.path.join(self.user_result_path, directory)
                for f in os.listdir(abs_path):
                    if f.split('.')[-1] == 'json':
                        result[abs_path] = os.path.join(abs_path, f)
        except FileNotFoundError:
            print("Cannot read the user_result_path, reasons could be following: ")
            print("1. Nothing is downloaded, so user_result_path is empty")
            print("2. The nickname and user_result_path is set manually, but not create this folder yet")
            print("Json path would be set to None")

        self.json_path = result

    def set_accept_status(self, input_status_list):
        self.accept_status = input_status_list

    def add_accept_status(self, input_status):
        self.accept_status.add(input_status)

    async def post(self, url, payload=None):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload) as response:
                if response.status != 200:
                    print("Status:", response.status)
                    print("Request: ", response.url)
                else:
                    print("Success: ", response.url)
                result_json = await response.json()
                return result_json['data']['access_token']

    async def get(self, url, payload=None, header=None):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=payload, headers=header) as response:
                if response.status != 200:
                    print("Status:", response.status)
                    print("Request: ", response.url)
                else:
                    print("Success: ", response.url)
                result_json = await response.json()
                return result_json

    def get_user_info(self):
        # Login and get user info including user token and uuid
        auth_url = 'https://aist.feieee.com/api/oauth2/token'
        pwd = self.pwd.encode()
        login_payload = {'grant_type': 'password', 'password': hashlib.sha1(pwd).hexdigest(), 'scope': 'USER',
                         'username': self.username}  # '+86 15536902280'

        user_token = self.loop.run_until_complete(self.post(auth_url, login_payload))

        user_info = base64.b64decode(user_token.split('.')[1] + '===').decode('utf-8')
        user_uuid = json.loads(user_info)['uuid']

        return user_uuid, user_token

    def update_user_info(self):
        self.user_uuid, self.user_token = self.get_user_info()

    async def get_nickname(self):
        url = 'https://aist.feieee.com/api/user/' + self.user_uuid
        headers = {'Authorization': 'Bearer ' + self.user_token}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    print("Status:", response.status)
                    print("Request: ", response.url)
                else:
                    print("Success: ", response.url)

                result_json = await response.json()
                return result_json['data']['username']

    def get_task_info(self):
        # Get task list
        params = {'page_size': 1000, 'page_index': 1}
        headers = {'Authorization': 'Bearer ' + self.user_token}
        get_task_url = 'https://aist.feieee.com/api/user/' + self.user_uuid + '/published_task'
        task_json = self.loop.run_until_complete(self.get(get_task_url, params, headers))
        # pretty_print(task_json)

        return task_json

    def get_dataset_list(self, dataset_uuid):
        headers = {'Authorization': 'Bearer ' + self.user_token}
        params = {'page_size': 1000, 'page_index': 1}
        get_dataset_list_url = 'https://aist.feieee.com/api/dataset/' + dataset_uuid
        dataset_list = self.loop.run_until_complete(self.get(get_dataset_list_url, params, headers))

        return dataset_list

    def get_label_info(self, task_uuid, image_uuid, user_token):
        params = {'page_size': 1000, 'page_index': 1, 'data': image_uuid}
        headers = {'Authorization': 'Bearer ' + user_token}
        get_label_url = 'https://aist.feieee.com/api/task/' + task_uuid + '/label'
        label_json = self.loop.run_until_complete(self.get(get_label_url, params, headers))

        return label_json

    def get_dataset(self, option, which_task):
        self.user_uuid, self.user_token = self.get_user_info()
        task_json = self.get_task_info()

        # Get dataset list and their status
        tasks = get_task_details(task_json)
        self.task_json = tasks

        accept_status = ['COMMITTED', 'ARCHIVED']
        datasets = dict()

        # k: task uuid
        # v: task
        for k, v in tasks.items():
            # if this taks is not which task we want to download
            # jump to the next one
            # if which_task is None, just download everything
            if which_task is not None:
                if v['task_name'] != which_task:
                    continue
            # Only acceptable tasks will be read
            if v['status'] in accept_status:
                # dataset_list actually is a image list with their label info
                dataset_list = self.get_dataset_list(v['dataset_uuid'])
                label_category_list = dataset_list['data']['self']['label_category']
                label_type = dataset_list['data']['self']['label_type']
                # pretty_print(dataset_list)

                # image uuid and its url, label
                images = []
                for i in dataset_list['data']['items']:
                    # Raw image object
                    obj = i['obj']

                    label_json = self.get_label_info(task_uuid=k, image_uuid=obj['uuid'], user_token=self.user_token)
                    label = label_json['data']['items'][0]['label']
                    if option == 1:
                        if len(label) == 0:
                            print("No labels: ", obj['filename'])
                            continue
                    image = image_register(image_obj=obj, input_label=label)
                    images.append(image)

                result = {
                    "label_type": label_type,
                    "images": images,
                    "label_category": label_category_list
                }

                datasets[v['task_name']] = {'result': result, 'task_username': v['task_username'],
                                            'executor_username': v['executor_username']}

        if len(datasets) == 0 and which_task is not None:
            print("This task does not exist")

        return datasets

    def save_to_folder(self, datasets):
        if len(datasets) == 0:
            print("Nothing to save")
            return

        for task_name, data in datasets.items():
            self.valid_dataset.append(task_name)
            name = task_name + ".json"
            dataset_folder_path = create_dataset_folder(task_name,
                                                        create_dataset_folder(self.nickname, self.result_path))
            if dataset_folder_path:
                # k = ./results/小齐/
                # v = ./results/小齐/xxx.json
                self.json_path[dataset_folder_path] = os.path.join(dataset_folder_path, name)
                download_json(data['result'], path=dataset_folder_path, name=name)
            else:
                print("Already downloaded")

    def download_dataset(self, option=None, which_task=None):
        # for published tasks which are "COMMITTED' and "ACHIEVED"
        if option is None:
            pass
        elif option == 1:
            print("Download option: download images with labels")
        elif option == 2:
            print("Download option: download all images, with or without labels")
        else:
            print("Not open it yet")
            return
        datasets = self.get_dataset(option, which_task)
        nickname = self.loop.run_until_complete(self.get_nickname())
        self.nickname = nickname
        self.user_result_path = os.path.join(self.result_path, self.nickname)
        self.save_to_folder(datasets)

        print("JSON downloaded")

    def get_update_list(self, imagePath_imageURL_dict):
        # k = ./results/小齐/无锡电梯超员_24899_2021_01_04/20210104114539.jpg
        # v = url
        current_json_path = None
        current_directory = None
        update_list = dict()
        for k, v in imagePath_imageURL_dict.items():
            # update current_directory and current_json_dict when changing directory
            if (not current_json_path) or (current_directory != os.path.dirname(k)):
                current_directory = os.path.dirname(k)
                # i = ./results/小齐/无锡电梯超员_24899_2021_01_04/xxx.json
                for i in self.json_path.values():
                    if os.path.dirname(i) == current_directory:
                        current_json_path = i
            # ./results/小齐/无锡电梯超员_24899_2021_01_04/20210104114539.jpg -> 无锡电梯超员_24899_2021_01_04
            self.downloaded_dataset.add(k.split('/')[-2])
            print("Downloading: ", k.split('/')[-1])
            self.loop.run_until_complete(download_image(v, k))
            shape = cv2.imread(k, 0).shape

            update_info = {v: shape}

            if current_json_path not in update_list.keys():
                update_list[current_json_path] = dict()

            update_list[current_json_path].update(update_info)

        print("Images downloaded")

        return update_list

    def download_images(self, which_task=None):
        imagePath_imageURL_dict = self.get_path_url_dict(which_task)

        if len(imagePath_imageURL_dict) == 0:
            print("Nothing to download")
            return

        update_list = self.get_update_list(imagePath_imageURL_dict)

        for json_path, images in update_list.items():
            with open(json_path) as json_file:
                json_dataset = json.load(json_file)

                new_images = []

                for i in json_dataset['images']:
                    temp = i.copy()
                    temp['height'] = images[temp['url']][0]
                    temp['width'] = images[temp['url']][1]
                    new_images.append(temp)

                new_dataset = {
                    "label_type": json_dataset['label_type'],
                    "images": new_images,
                    "label_category": json_dataset['label_category']
                }

            os.remove(json_path)
            with open(json_path, 'w') as output:
                json.dump(new_dataset, output, indent=4)
                print("Updated to: ", json_path)

    def get_path_url_dict(self, which_task):
        result = dict()
        # k = ./results/小齐/
        # v = ./results/小齐/无锡电梯超员_24899_2021_01_04/xxx.json
        for k, v in self.json_path.items():
            # if which is not none
            # check each json, if it is not target one
            # jump to the next one
            if which_task is not None:
                if v.split('/')[-2] != which_task:
                    continue

            with open(v) as json_file:
                j = json.load(json_file)
                for i in j['images']:
                    filename = i['filename']
                    image_url = i['url']

                    # k = ./results/小齐/无锡电梯超员_24899_2021_01_04/20210104114539.jpg
                    # v = url
                    result[os.path.join(k, filename)] = image_url

        return result

    def save_state(self):
        state = {
            "username": self.username,
            "pwd": self.pwd,
            "result_path": self.result_path,
            "user_result_path": self.user_result_path,
            "nickname": self.nickname,
            "task_json": self.task_json,
            "valid_dataset": self.valid_dataset,
            "downloaded_dataset": self.downloaded_dataset,
            "accept_status": self.accept_status,
            "json_path": self.json_path
        }

        with open('utils_object', 'wb') as output:
            pickle.dump(state, output)


if __name__ == "__main__":
    Min = ['+86 15137393991', '123456']
    Qing = ['+86 15536902280', 'cike567']

    result_path = './results'
    username = Min[0]
    pwd = Min[1]

    utils = Utils(username, pwd, result_path)
    # utils.set_nickname('小齐')
    # utils.set_user_result_path()
    utils.download_dataset(option=1, which_task="无锡电梯超员_24899_2021_01_04")
    utils.download_images(which_task="无锡电梯超员_24899_2021_01_04")
