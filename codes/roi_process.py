import os
import re

anno_path = '/home/chenyang/sed/data/Annotations/'
#roi_dbs = ['raw_bbox', 'pose_roi']
roi_dbs = ['refine', 'pose_roi']
final_path = '/home/chenyang/sed/data/Annotations/roi/'

def merge_roidb(roi_dbs):
    for roi_db in roi_dbs:
        roi_path = os.path.join(anno_path, roi_db)
        roi_files = os.listdir(roi_path)
        for roi_file in roi_files:
            f_roi = open(os.path.join(roi_path, roi_file))
            final_roi = os.path.join(final_path, roi_file)
            if os.path.exists(final_roi):
                print roi_file
            with open(final_roi, 'a') as f:
                f.write(f_roi.read())

files = ['/home/chenyang/sed/data/ImageSets/train.txt', '/home/chenyang/sed/data/ImageSets/test.txt']
src = ['/home/chenyang/sed/data/Annotations/refine/', '/home/chenyang/sed/data/Annotations/pose_roi/'] 
#src = ['/home/chenyang/sed/data/Annotations/refine_jia/', '/home/chenyang/sed/data/Annotations/pose_roi/']
#src = ['/home/chenyang/sed/data/Annotations/refine/']
dst = '/home/chenyang/sed/data/Annotations/roi/'
def extract_roidb(files, src, dst):
    all_imgs = []
    for img_set in files:
        with open(img_set) as f:
            imgs = [x.strip() for x in f.readlines()]
        for img in imgs:
            if img in all_imgs:
                continue
            all_imgs.append(img)
            found = 0
            roi = os.path.join(dst, img + '.roi')
            if os.path.exists(roi):
                print img
            for roidb in src:
                src_roi = os.path.join(roidb, img + '.roi')
                if not os.path.exists(src_roi):
                    continue
                found = found + 1

                src_file = open(src_roi)
                if os.path.exists(roi):
                    print img
                with open(roi, 'a') as f:
                    f.write(src_file.read() + '\n')

            if found == 0:
                print 'Not find roi of image {} from src'.format(img)
                with open(roi, 'w') as f:
                    f.write('')

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
    #print 'Intersect:', Intersect
    Union = (box1[2]-box1[0])*(box1[3]-box1[1]) + (box2[2]-box2[0])*(box2[3]-box2[1]) - Intersect
    #print 'Union:', Union
    #print 'IoU:', Intersect / Union
    assert Union >= 0, str(box1) + '\n' + str(box2) + '\n' + str(Union) + '\n' +  str(Intersect)
    return Intersect / Union

main_cls = ['Embrace', 'Pointing', 'CellToEar']
overlap_threshod = 0.1
def check_overlap(pose_roi, rois):
    if pose_roi[0] in main_cls:
        return True
    main_rois = [x for x in rois if x[0] in main_cls]
    for roi in main_rois:
        #print pose_roi, roi, IoU(pose_roi[1:], roi[1:])
        if IoU(pose_roi[1:], roi[1:]) > overlap_threshod:
            return False
    return True

def filter_roidb(dst):
    roidbs = os.listdir(dst)
    for roidb in roidbs:
        roi_file = os.path.join(dst, roidb)
        with open(roi_file) as f:
            rois = [list(x) for x in re.findall('(\S+) (\d+) (\d+) (\d+) (\d+)', f.read())]
        change = False

        new_rois = [x for x in rois if check_overlap(x, rois)]
        if len(new_rois) != len(rois):
            change = True
            print 'Removed {} overlaped bounding box in {}'.format(str(len(rois) - len(new_rois)),roidb)
            rois = new_rois

        for ind, roi in enumerate(rois):
            if int(roi[1]) > 719:
                change = True
                roi[1] = '719'
            if int(roi[2]) > 575:
                change = True
                roi[2] = '575'
            if int(roi[3]) > 719:
                change = True
                roi[3] = '719'
            if int(roi[4]) > 757: 
                change = True
                roi[4] = '575'
        if change:
            print 'refine -> ', roidb
            with open(roi_file, 'w') as f:
                for roi in rois:
                    f.write(' '.join(roi) + '\n')

if __name__ == '__main__':
    #merge_roidb(roi_dbs)
    #extract_roidb(files, src, dst)
    filter_roidb(dst)
