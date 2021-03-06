import os
import re
import shutil
import random

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

files = ['/home/chenyang/sed/data/ImageSets/refine_train.txt', '/home/chenyang/sed/data/ImageSets/refine_test.txt']
person_files = ['/home/chenyang/sed/data/ImageSets/pose_train.txt', '/home/chenyang/sed/data/ImageSets/pose_test.txt']
src = ['/home/chenyang/sed/data/Annotations/refine/', '/home/chenyang/sed/data/Annotations/pose_roi/'] 
#src = ['/home/chenyang/sed/data/Annotations/refine_jia/', '/home/chenyang/sed/data/Annotations/pose_roi/']
#src = ['/home/chenyang/sed/data/Annotations/refine/']
dst = '/home/chenyang/sed/data/Annotations/roi/'
ctr = '/home/chenyang/sed/raw/txt/'
all_imgs = []
def extract_roidb(files, src, dst, ctr = None):
    print 'extract_roidb', files, src, dst, ctr
    count = 0
    pair_count = 0
    for img_set in files:
        with open(img_set) as f:
            imgs = [x.strip() for x in f.readlines()]
        for img in imgs:
            if img in all_imgs:
                continue
            #all_imgs.append(img)

            if ctr != None:
                data = img.split('_')
                ctr_file = os.path.join(ctr, '_'.join(data[:-1]) + '.txt')
                frame = int(data[-1])
                with open(ctr_file) as f:
                    frame_sets = re.findall('(\S+) (\d+) (\d+)', f.read())
                frame_sets = [[int(x[1]), int(x[2])] for x in frame_sets]
                paired = False
                for frame_set in frame_sets:
                    if frame_set[0] <= frame and frame_set[1] >= frame:
                        #print frame, frame_set
                        pair_count = pair_count + 1
                        paired = True
                        break
                if paired:
                    continue

            all_imgs.append(img)

            found = 0
            roi = os.path.join(dst, img + '.roi')
            #if os.path.exists(roi):
            #    print img
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
            count = count + 1

    print 'Extracted {} roidbs'.format(count)
    print 'Filtered {} roidbs'.format(pair_count)

delta = 5
def IoU(box1, box2):
    box1 = [float(x) for x in box1]
    box2 = [float(x) for x in box2]
    #if box1[0]-delta < box2[0] and box1[2]+delta > box2[2] and box1[1]-delta < box2[1] and box1[3]+delta > box2[3]:
    #    return 1
    #if box2[0]-delta < box1[0] and box2[2]+delta > box1[2] and box2[1]-delta < box1[1] and box2[3]+delta > box1[3]:
    #    return 1
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

        new_rois = []
        for i in rois:
            if i not in new_rois:
                new_rois.append(i)
        if len(new_rois) != len(rois):
            change = True
            print 'Removed {} duplicated bounding box in {}'.format(str(len(rois) - len(new_rois)),roidb)
            rois = new_rois

        for ind, roi in enumerate(rois):
            if int(roi[1]) > 719:
                change = True
                roi[1] = '719'
            if int(roi[1]) < 1:
                change = True
                roi[1] = '1'
            if int(roi[2]) > 575:
                change = True
                roi[2] = '575'
            if int(roi[2]) < 1:
                change = True
                roi[2] = '1'
            if int(roi[3]) > 719:
                change = True
                roi[3] = '719'
            if int(roi[3]) < 1:
                change = True
                roi[3] = '1'
            if int(roi[4]) > 757: 
                change = True
                roi[4] = '575'
            if int(roi[4]) < 1:
                change = True
                roi[4] = '1'
        if change:
            print 'refine -> ', roidb
            with open(roi_file, 'w') as f:
                for roi in rois:
                    f.write(' '.join(roi) + '\n')

imageset_path = '/home/chenyang/lib/ImageSets/'
def generate_imageset(imageset_path):
    train = open(os.path.join(imageset_path, 'train.txt'), 'w')
    train_count = 0
    test = open(os.path.join(imageset_path, 'test.txt'), 'w')
    test_count = 0
    for img in all_imgs:
        data = img.split('_')
        date = int(data[1][-4:])
        if date < 1201:
            train.write(img + '\n')
            train_count = train_count + 1
        else:
            test.write(img + '\n')
            test_count = test_count + 1

    print 'Total training images:', train_count
    print 'Total testing images:', test_count


CLASSES = ['Embrace', 'Pointing', 'CellToEar', 'Pose']

def export_roidb():#imgsets, imgsrc, annosrc, dstpath, num_cls):
    imgsets = ['train', 'test']
    imgsrc = '/home/chenyang/sed/data/Images/'
    annosrc = '/home/chenyang/sed/data/Annotations/roi/'
    dstpath = '/home/chenyang/sed/annodata/'
    num_cls = {'train': {'Embrace': 100, 'Pointing': 100, 'CellToEar': 100, 'Pose': 300},
                'test': {'Embrace': 50, 'Pointing': 50, 'CellToEar': 50, 'Pose': 150}}
    for imset in imgsets:
        src = os.path.join('/home/chenyang/sed/data/ImageSets', imset + '.txt')
        with open(src) as f:
            imgset = [x.strip() for x in f.readlines()]
       
        #print dstpath, imset
        annodst = os.path.join(dstpath, imset + '.txt')
        if os.path.exists(annodst):
            os.remove(annodst)
       
        annoset = dict()
        for cls in CLASSES:
            annoset[cls] = []

        for img in imgset:
            annofile = os.path.join(annosrc, img + '.roi')
            if not os.path.exists(annofile):
                print 'cannot find annotation source', annofile
                continue
            with open(annofile) as f:
                annos = [x.strip().split(' ') for x in f.readlines() if x.strip()]
            
            for anno in annos:
                #print img, anno
                annoset[anno[0]].append([img] + anno)
            #with open(annodst, 'a') as f:
            #    for anno in annos:
            #        f.write(img + ' ')
            #        f.write(anno)
            #        f.write('\n')

        for cls in CLASSES:
            print cls, len(annoset[cls])
            cls_anno = random.sample(annoset[cls], num_cls[imset][cls])
            
            for anno in cls_anno:
                with open(annodst, 'a') as f:
                    f.write(' '.join(anno))
                    f.write('\n')
            
                img = anno[0]        
                dstfile = os.path.join(dstpath, 'images', img + '.jpg')
                if os.path.exists(dstfile):
                    continue
            
                imgfile = os.path.join(imgsrc, img + '.jpg')
                if not os.path.exists(imgfile):
                    print 'cannot find image source', imgfile
                    continue

                shutil.copy(imgfile, dstfile)


if __name__ == '__main__':
    #merge_roidb(roi_dbs)
    #extract_roidb(files, src, dst)
    #filter_roidb(dst)
    #extract_roidb(person_files, src, dst, ctr)
    #filter_roidb(dst)
    filter_roidb('/home/chenyang/sed/data/Annotations/roi/')
    filter_roidb('/home/chenyang/sed/data/Annotations/pose_roi/')
    filter_roidb('/home/chenyang/sed/data/Annotations/refine')
    #generate_imageset(imageset_path)
    #export_roidb()
