import json
from shapely.geometry import Polygon


def calculate_rect_area(coordinate, height, width):
    rect_length = coordinate[2] * width
    rect_width = coordinate[3] * height

    return rect_width * rect_length


if __name__ == "__main__":
    json_path = r'./results/小齐/无锡电梯超员_24899_2021_01_04/无锡电梯超员_24899_2021_01_04.json'
    with open(json_path) as json_file:
        dataset = json.load(json_file)

    image_list = dataset['images']
    for i in image_list:
        height = i['height']
        width = i['width']

        for label in i['label']:
            print(calculate_rect_area(label['coordinate'], height, width))

    coords = ((-1, 0), (-1, 1), (0, 0.5), (1, 1), (1, 0), (-1, 0))

    polygon = Polygon(coords)

    area = polygon.area

    '''
    "coordinate": [
                        0.5522875816993464,
                        0.17851959361393324,
                        0.04466230936819173,
                        0.06095791001451379
                    ],
    leftmost: x, y
    1. x, y
    2. x + l, y
    3. x, y + w
    4. x + l, y + w
    
    length
    width
    '''
