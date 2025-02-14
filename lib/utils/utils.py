"""
@Fire
https://github.com/fire717
"""
import os
import torch
import random
import numpy as np

from operator import itemgetter

from config import cfg

def setRandomSeed(seed=42):
    """Reproducer for pytorch experiment.

    Parameters
    ----------
    seed: int, optional (default = 2019)
        Radnom seed.

    Example
    -------
    setRandomSeed(seed=2019).
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.enabled = True


def printDash(num = 50):

    print(''.join(['-']*num))



############## task tool

# _center_weight = np.load('lib/data/center_weight.npy')
# _center_weight = np.reshape(_center_weight,(48,48))
# # _center_weight = _center_weight.repeat((1,7,1,1))
# def heatmap2locate(heatmap, size = cfg['img_size']//4):
#     """
#     input:
#             dist: [batchsize, 7, 64, 64]

#     return:
#             dist: [batchsize, 32]    x0,y0,x1,y1,...
#     """

#     heatmap = heatmap*_center_weight
#     # print(heatmap.shape)
#     # b
#     bs = heatmap.shape[0]
#     point_count = heatmap.shape[1]
#     h,w = heatmap.shape[2:]

#     heatmap = np.reshape(heatmap, (bs,point_count,-1))
#     max_id = np.argmax(heatmap, 2)#64, 16
#     # print(max_id[0])
#     y = max_id//size
#     y = y[:, : ,np.newaxis]
#     # print(x.shape)
#     x = max_id%size
#     x = x[:, : ,np.newaxis]
#     # print(y.shape)
#     # print(x[0])
#     # print(y[0])
    
#     res = np.concatenate((x,y), -1)
#     # print(res[0])
#     # print(res.shape)
    
#     res = np.reshape(res, (bs,-1))/size
#     # print(res.shape)
#     # print(res[0])
#     # b
#     return res


_center_weight = np.load('lib/data/center_weight_origin.npy').reshape(64,64)
# _center_weight = np.load("lib/data/my_weight_center.npy")

def maxPoint(heatmap, center=True):

    if len(heatmap.shape) == 3:
        batch_size,h,w = heatmap.shape
        c = 1

    elif len(heatmap.shape) == 4:
        # n,c,h,w
        batch_size,c,h,w = heatmap.shape
        # print(heatmap.shape)

    if center:
        #print(heatmap.shape)
        # print(heatmap[0][27:31,27:31])
        # print(_center_weight[27:31,27:31])
        heatmap = heatmap*_center_weight#加权取最靠近中间的
        # print(heatmap[0][27:31,27:31])


    heatmap = heatmap.reshape((batch_size,c, -1)) #64,c, 48x48
    # print(heatmap.shape)
    # print(heatmap[0,0,23*48+20:23*48+30])
    max_id = np.argmax(heatmap,2)#64,c, 1
    # print(max_id)
    # print(max_id, heatmap[0][0][max_id])
    # print(np.max(heatmap))
    y = max_id//w
    x = max_id%w
    # bv
    return x,y



def extract_keypoints(heatmap):
    """
    热力图解析为关键点
    """
    #print(heatmap.shape)#(1, 48, 48)
    #from light openpose

    heatmap = heatmap[0]



    heatmap[heatmap < 0.1] = 0
    #print(heatmap.shape)#500, 375
    heatmap_with_borders = np.pad(heatmap, [(2, 2), (2, 2)], mode='constant')
    # 1.上下左右分别扩张2像素，然后分别取上下左右中5个不同的heatmap
    #print(heatmap_with_borders.shape)#504, 379
    heatmap_center = heatmap_with_borders[1:heatmap_with_borders.shape[0]-1, 1:heatmap_with_borders.shape[1]-1]
    heatmap_left = heatmap_with_borders[1:heatmap_with_borders.shape[0]-1, 2:heatmap_with_borders.shape[1]]
    heatmap_right = heatmap_with_borders[1:heatmap_with_borders.shape[0]-1, 0:heatmap_with_borders.shape[1]-2]
    heatmap_up = heatmap_with_borders[2:heatmap_with_borders.shape[0], 1:heatmap_with_borders.shape[1]-1]
    heatmap_down = heatmap_with_borders[0:heatmap_with_borders.shape[0]-2, 1:heatmap_with_borders.shape[1]-1]
    #print(heatmap_center.shape, heatmap_left.shape,heatmap_right.shape,heatmap_up.shape,heatmap_down.shape,)
    #(502, 377) (502, 377) (502, 377) (502, 377) (502, 377
    heatmap_peaks = (heatmap_center > heatmap_left) &\
                    (heatmap_center > heatmap_right) &\
                    (heatmap_center > heatmap_up) &\
                    (heatmap_center > heatmap_down)
    # 2.通过center和周围比找峰值
    heatmap_peaks = heatmap_peaks[1:heatmap_center.shape[0]-1, 1:heatmap_center.shape[1]-1]
    # print(heatmap_peaks.shape)#500, 375
    #print(heatmap_peaks[22:26,22:26])

    keypoints = list(zip(np.nonzero(heatmap_peaks)[1], np.nonzero(heatmap_peaks)[0]))  # (w, h)
    # np.nonzero返回数组a中非零元素的索引值数组
    #keypoints = sorted(keypoints, key=itemgetter(0))
    keypoints = sorted(keypoints, key=lambda x:(x[0]-23.5)**2+(x[1]-23.5)**2)
    #print(keypoints)

    suppressed = np.zeros(len(keypoints), np.uint8)

    keypoints_with_score_and_id = []
    for i in range(len(keypoints)):
        if suppressed[i]:
            continue
        for j in range(i+1, len(keypoints)):
            if ((keypoints[i][0] - keypoints[j][0]) ** 2 +
                         (keypoints[i][1] - keypoints[j][1]) ** 2)**0.5 < 6:
            #如果两点距离小于6则忽略
                suppressed[j] = 1
        keypoint_with_score_and_id = [keypoints[i][0], keypoints[i][1], 
                                    heatmap[keypoints[i][1], keypoints[i][0]],
                                    _center_weight[keypoints[i][1], keypoints[i][0]],
                                    heatmap[keypoints[i][1], keypoints[i][0]]*_center_weight[keypoints[i][1], keypoints[i][0]]]
        # print(keypoint_with_score_and_id)
        #(43, 1, 0.46907818, 0) # [x,y,heatmap[x,y],total_keypoint_num]
        keypoints_with_score_and_id.append(keypoint_with_score_and_id)

        # bb

    
    #print(keypoints_with_score_and_id)
    keypoints_with_score_and_id = sorted(keypoints_with_score_and_id, 
                            key=lambda x:x[-1], reverse=True)
    x,y = keypoints_with_score_and_id[0][0],keypoints_with_score_and_id[0][1]
    return x,y