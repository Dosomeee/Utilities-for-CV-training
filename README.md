# How to download dataset from database

## Intro

1. Every user has many tasks
2. Some tasks are finished, then they have a dataset with labeled images, others don't
3. One task has one dataset
4. We cannot download whatever dataset we want, we must log in first and download datasets belonged to this user

## Requirement

Install necessary python packages
```shell
pip3 install aiohttp, hashlib, json, aiofiles, python-opencv, pickle
```
Also username and password are needed
```python
"""
Parameters
----------
username : str
    a valid username to login
    
password : str
    user's password
    
which_task : str
    task name, which task to be downloaded, optional

Returns
-------
Save to folder: /results/username/task_name/datasets/

"""

Min = ['+86 15137393991', '123456']
Qing = ['+86 15536902280', 'cike567']

result_path = './results'
username = Min[0]
pwd = Min[1]
```

## How to use

1. Initialize one Utils object with a username, password and a result path
```python
from Utils import Utils

result_path = './results'
username = "username"
pwd = "password"

utils = Utils(username, pwd, result_path)
```
2. If this is your first time to download, you may just download every valid dataset under this user
```python
from Utils import Utils

result_path = './results'
username = "username"
pwd = "password"

utils = Utils(username, pwd, result_path)

utils.download_dataset()
utils.download_images()
```
3. Options and selectively download are supported
```python
from Utils import Utils

result_path = './results'
username = "username"
pwd = "password"

utils = Utils(username, pwd, result_path)

utils.download_dataset(option=1, which_task="无锡电梯超员_24899_2021_01_04")
utils.download_images(which_task="无锡电梯超员_24899_2021_01_04")
```

option=1
    
    download images with labels, images without labels would be printed out(their filename)

option=None

    download all images, with or without labels

which_task=None

    download all tasks

which_task is not valid:

    download nothing