import cv2
import numpy as np

'''
pts_src and pts_dst are numpy arrays of points
in source and destination images. We need at least 
4 corresponding points. 
'''
pts_src = np.float32([[
    800.1176470588235,
    385.07563025210084
], [
    848.8571428571429,
    428.7731092436975
], [
    963.1428571428571,
    412.8067226890756
], [
    906.0,
    370.78991596638656
]])
pts_dst = np.float32([[
          414.75280898876395,
          579.5168539325842
        ], [
          422.6179775280898,
          849.1797752808989
        ], [
          692.2808988764045,
          848.0561797752808
        ], [
          690.0337078651685,
          575.0224719101124
        ]])

h, status = cv2.findHomography(pts_src, pts_dst)

img_src = cv2.imread("./Test_Images/Image2.jpeg")
size = (2000, 2000)

im_dst = cv2.warpPerspective(img_src, h, size)

# # Locate points of the documents or object which you want to transform
# pts1 = np.float32([[0, 260], [640, 260], [0, 400], [640, 400]])
# pts2 = np.float32([[0, 0], [400, 0], [0, 640], [400, 640]])
#
# img = cv2.imread('./test.png')
#
# matrix = cv2.getPerspectiveTransform(pts1, pts2)
# result = cv2.warpPerspective(img, matrix, (500, 600))
#
cv2.imshow('origin', img_src)
cv2.imshow('result', im_dst)

cv2.waitKey(0)
cv2.destroyAllWindows()
