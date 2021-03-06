#!/usr/bin/env python

# --------------------------------------------------------
# Fast R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------

"""Train a Fast R-CNN network on a region of interest database."""

import _init_paths
from fast_rcnn.train import get_training_roidb, train_net
from fast_rcnn.test import im_detect, test_net
from fast_rcnn.nms_wrapper import nms
from fast_rcnn.config import cfg, cfg_from_file, cfg_from_list, get_output_dir
from utils.cython_bbox import bbox_overlaps
from datasets.factory import get_imdb
import datasets.imdb
import caffe
import argparse
import pprint
import numpy as np
import sys
import os
import cv2
import scipy

def parse_args():
    """
    Parse input arguments
    """
    parser = argparse.ArgumentParser(description='Train a Fast R-CNN network')
    parser.add_argument('--gpu', dest='gpu_id',
                        help='GPU device id to use [0]',
                        default=0, type=int)
    parser.add_argument('--solver', dest='solver',
                        help='solver prototxt',
                        default=None, type=str)
    parser.add_argument('--iters', dest='max_iters',
                        help='number of iterations to train',
                        default=40000, type=int)
    parser.add_argument('--weights', dest='pretrained_model',
                        help='initialize with pretrained model weights',
                        default=None, type=str)
    parser.add_argument('--cfg', dest='cfg_file',
                        help='optional config file',
                        default=None, type=str)
    parser.add_argument('--imdb', dest='imdb_name',
                        help='dataset to train on',
                        default='sed_train', type=str)
    parser.add_argument('--rand', dest='randomize',
                        help='randomize (do not use a fixed seed)',
                        action='store_true')
    parser.add_argument('--set', dest='set_cfgs',
                        help='set config keys', default=None,
                        nargs=argparse.REMAINDER)
    parser.add_argument('--testprototxt', dest='testprototxt',
                        help='test prototxt',
                        default=None, type=str)
    parser.add_argument('--test_imdb', dest='test_imdb',
                        help='image database for test',
                        default='sed_test', type=str)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args

def combined_roidb(imdb_names):
    def get_roidb(imdb_name):
        imdb = get_imdb(imdb_name)
        print 'Loaded dataset `{:s}` for training'.format(imdb.name)
        imdb.set_proposal_method(cfg.TRAIN.PROPOSAL_METHOD)
        print 'Set proposal method: {:s}'.format(cfg.TRAIN.PROPOSAL_METHOD)
        roidb = get_training_roidb(imdb)
        return roidb

    # print imdb_names.split('+')
    roidbs = [get_roidb(s) for s in imdb_names.split('+')]
    roidb = roidbs[0]
    print 'combined_roidb ------->', len(roidb)
    if len(roidbs) > 1:
        for r in roidbs[1:]:
            roidb.extend(r)
        imdb = datasets.imdb.imdb(imdb_names)
    else:
        imdb = get_imdb(imdb_names)
    return imdb, roidb

delta = 5
def IoU(box1, box2):
    box1 = [float(x) for x in box1]
    box2 = [float(x) for x in box2]
    if box1[0]-delta < box2[0] and box1[2]+delta > box2[2] and box1[1]-delta < box2[1] and box1[3]+delta > box2[3]:
        return 1
    if box2[0]-delta < box1[0] and box2[2]+delta > box1[2] and box2[1]-delta < box1[1] and box2[3]+delta > box1[3]:
        return 1
    if box1[0] >= box2[2] or box1[2] <= box2[0] or box1[1] >= box2[3] or box1[3] <= box2[1]:
        return 0
    Intersect = min(box1[2], box2[2]) - max(box1[0], box2[0])
    if Intersect <= 0:
        Intersect = 0.0
    Intersect = Intersect * (min(box1[3], box2[3]) - max(box1[1], box2[1]))
    if Intersect <= 0:
        Intersect = 0.0
    Union = (box1[2]-box1[0])*(box1[3]-box1[1]) + (box2[2]-box2[0])*(box2[3]-box2[1]) - Intersect
    assert Union >= 0, str(box1) + '\n' + str(box2) + '\n' + str(Union) + '\n' +  str(Intersect)
    return Intersect / Union

FG_THRESH = 0.5
CLASSES = ['__background__', 'Embrace', 'Pointing', 'CellToEar']#, 'Pose']
def hardNeg_learning(score, box, gt_boxes, roidb):
    '''
    judge if a box is a hard negative example, add it to roidb if true
    '''
    if score < 0.7:
        return False
    #print score
    #print box
    #print gt_boxes
    for gt_box in gt_boxes:
        assert gt_box[-1] != 0
        if IoU(box, gt_box[:4]) > FG_THRESH:
            return False
    
    ''' Debug 
    for gt_box in gt_boxes:
        assert gt_box[-1] != 0
        print IoU(box, gt_box[:4])
    
    print '-------------------------------' 
    print box
    print score
    print gt_boxes
    print '-------------------------------'
    '''
    
    overlaps = bbox_overlaps(
        np.ascontiguousarray([box], dtype=np.float),
        np.ascontiguousarray(gt_boxes[:, :4], dtype=np.float))
    overlap = np.zeros(len(CLASSES), dtype=np.float32)
    overlap[0] = 1.0
    for ind, cls in enumerate(CLASSES[1:]):
        ind = ind + 1
        cls_overlap = [y for x, y in enumerate(overlaps[0]) if gt_boxes[x,-1] == ind]
        if len(cls_overlap) > 0:
            overlap[ind] = np.max(cls_overlap)

    roidb['boxes'] = np.append(roidb['boxes'], [box], axis=0)
    roidb['gt_classes'] = np.append(roidb['gt_classes'], [0], axis=0)
    roidb['gt_overlaps'] = scipy.sparse.csr_matrix(np.append(scipy.sparse.csr_matrix(roidb['gt_overlaps']).toarray(), [overlap], axis=0))
    roidb['seg_areas'] = np.append(roidb['seg_areas'], [(box[2] - box[0] + 1) * (box[3] - box[1] + 1)], axis=0) 
    
    # print roidb
    return True 

def get_allboxes(scores, boxes):
    '''
        extract scores and boxes from detected data, except boxes of background
        scores: [N, K], i*4~(i+1)*4 is box for class i
        boxes:  [N, K * 4]
        K is the class number
        return:
            all_score: [N * (k - 1)]
            boxes:     [N * (k - 1), 4]
    '''
    num_box = len(boxes) * (len(CLASSES) - 1)
    all_score = np.zeros((num_box), dtype=np.float)
    all_box = np.zeros((num_box, 4), dtype=np.float)
    for cls_ind, cls in enumerate(CLASSES[1:]):
        cls_boxes = boxes[:, 4*(cls_ind + 1) : 4*(cls_ind + 2)]
        cls_scores = scores[:, cls_ind + 1]
        #print all_box.shape, cls_boxes.shape
        #print cls_ind * len(boxes),  (cls_ind+1) * len(boxes)
        all_box[cls_ind * len(boxes) : (cls_ind+1) * len(boxes), :] = cls_boxes[:, :]
        all_score[cls_ind * len(boxes) : (cls_ind+1) * len(boxes)] = cls_scores[:]

    return all_score, all_box


if __name__ == '__main__':
    args = parse_args()

    print('Called with args:')
    print(args)

    if args.cfg_file is not None:
        cfg_from_file(args.cfg_file)
    if args.set_cfgs is not None:
        cfg_from_list(args.set_cfgs)

    cfg.GPU_ID = args.gpu_id

    print('Using config:')
    pprint.pprint(cfg)

    if not args.randomize:
        # fix the random seeds (numpy and caffe) for reproducibility
        np.random.seed(cfg.RNG_SEED)
        caffe.set_random_seed(cfg.RNG_SEED)

    # set up caffe
    caffe.set_mode_gpu()
    caffe.set_device(args.gpu_id)

    imdb, roidb_ori = combined_roidb(args.imdb_name)
    print '{:d} roidb entries'.format(len(roidb_ori))

    output_dir = get_output_dir(imdb)
    print 'Output will be saved to `{:s}`'.format(output_dir)

    caffemodel = train_net(args.solver, roidb_ori, output_dir,
            pretrained_model=args.pretrained_model,
            max_iters=args.max_iters)

    #caffemodel = ['/home/chenyang/py-faster-rcnn/output/faster_rcnn_end2end/train/zf_faster_rcnn_iter_10000.caffemodel']
    #caffemodel = ['/home/chenyang/py-faster-rcnn/output/faster_rcnn_end2end/train/zf_HNL_4cls.caffemodel']
    #caffemodel = ['/home/chenyang/py-faster-rcnn/output/faster_rcnn_end2end/train/HNL_zf_iter_10000.caffemodel']
    # Do hard negative learning
   
    imgs = [os.path.join(imdb._data_path, 'Images', x + '.jpg') for x in imdb._image_index]

    log_file = '/home/chenyang/lib/log/result_5cls_1113_HNM.txt'
    iters = 1
    hard_negs = []
    threshold = 1
    while True:
        print iters, 'time training end.'
        print caffemodel 
        net = caffe.Net(args.testprototxt, str(caffemodel[-1]), caffe.TEST)
        net.name = os.path.splitext(os.path.basename(str(caffemodel[-1])))[0]
        print '\n\nLoaded network {:s}'.format(caffemodel[-1])
       
        total_hardNeg = 0
        total_proposal = 0
        roidb = roidb_ori
        for im_ind, im_file in enumerate(imgs):
            # print 'Get hard negatives from', im_file
            im = cv2.imread(im_file)
            all_score, all_boxes = im_detect(net, im)
            scores, boxes = get_allboxes(all_score, all_boxes)
            
            total_proposal = total_proposal + len(boxes)
            if im_ind % 100 == 0:
                print 'Get Hard Negatives: {}/{}'.format(im_ind, len(imgs))
            
            # print roidb[im_ind]['boxes'].shape, roidb[im_ind]['gt_classes'].shape
            gt_boxes = np.column_stack((roidb[im_ind]['boxes'], roidb[im_ind]['gt_classes']))
            gt_ind = np.where(gt_boxes[:, -1] != 0)
            gt_boxes = gt_boxes[gt_ind]

            for box_ind, box in enumerate(boxes):
                if hardNeg_learning(scores[box_ind], box, gt_boxes, roidb[im_ind]):
                    total_hardNeg = total_hardNeg + 1
        
        hard_negs.append(total_hardNeg)
        print 'Total proposal: ', total_proposal
        print 'Total Hard Negative', total_hardNeg
        with open(log_file, 'a') as f:
            f.write('---------------------------\n')
            f.write(str(iters) + ' time recursion\n')
            f.write('Total proposal: ' + str(total_proposal) + '\n')
            f.write('Total Hard Negtive: ' + str(total_hardNeg) + '\n')
            f.write('Test Result:\n')
            test_imdb = get_imdb(args.test_imdb)
            f.write(str(test_net(net, test_imdb)) + '\n')
            f.write('---------------------------\n')

        if total_hardNeg < threshold:
            print 'Done'
            break
        print 'Train recursively...'
       
        # print len(roidb)
        caffemodel = train_net(args.solver, roidb, output_dir,
                pretrained_model=str(caffemodel[-1]),
                max_iters=args.max_iters)
        iters = iters + 1

    print hard_negs

