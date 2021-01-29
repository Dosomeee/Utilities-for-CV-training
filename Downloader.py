import pickle
from main import pretty_print
import os
import aiohttp
import asyncio
import aiofiles
import json
import cv2


async def download_image(url, image_path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(image_path, mode='wb')
                await f.write(await resp.read())
                await f.close()


# k = ./results/小齐/
# v = ./results/小齐/xxx.json
def get_json_path_list(input_path):
    result = dict()
    for directory in os.listdir(input_path):
        abs_path = os.path.join(input_path, directory)
        for i in os.listdir(abs_path):
            dataset_path = os.path.join(abs_path, i)
            for f in os.listdir(dataset_path):
                if f.split('.')[-1] == 'json':
                    result[dataset_path] = os.path.join(dataset_path, f)

    return result


# k = ./results/小齐/无锡电梯超员_24899_2021_01_04/20210104114539.jpg
# v = url
def get_path_url_dict(input_dict):
    result = dict()
    for k, v in input_dict.items():
        with open(v) as json_file:
            j = json.load(json_file)
            for i in j['images']:
                filename = i['filename']
                image_url = i['url']

                result[os.path.join(k, filename)] = image_url

    return result


def update_json(json_path, filename, shape):
    with open(json_path) as json_file:
        j = json.load(json_file)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    Min = ['+86 15137393991', '123456']
    Qing = ['+86 15536902280', 'cike567']

    result_path = './results'
    username = Min[0]
    pwd = Min[1]

    # k = ./results/小齐/
    # v = ./results/小齐/无锡电梯超员_24899_2021_01_04/xxx.json
    json_path_dict = get_json_path_list(result_path)
    imagePath_imageURL_dict = get_path_url_dict(json_path_dict)

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
            for i in json_path_dict.values():
                if os.path.dirname(i) == current_directory:
                    current_json_path = i

        loop.run_until_complete(download_image(v, k))
        shape = cv2.imread(k, 0).shape

        update_info = {
            'json_path': current_json_path,
            'image_url': v,
            'shape': shape
        }

        if current_directory not in update_list.keys():
            update_list[current_directory] = []

        update_list[current_directory].append(update_info)

    pretty_print(update_list)




