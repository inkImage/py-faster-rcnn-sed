from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA
from sklearn.svm import SVC
import numpy as np
import h5py
import re
import sys
import os
import pickle
from scipy.io import loadmat

CPMfeature = './CPMfeature/'
annopath = '/home/chenyang/lib/CPM/results_model5/'
trainanno = '/home/chenyang/cydata/sed_subset/annodata/train_annos'
testanno = '/home/chenyang/cydata/sed_subset/annodata/test_annos'
trainset = '/home/chenyang/cydata/sed_subset/annodata/train.txt'
testset = '/home/chenyang/cydata/sed_subset/annodata/test.txt'
clsname = dict()
clsname['Pose'] = 0
clsname['Embrace'] = 1
clsname['Pointing'] = 2
clsname['CellToEar'] = 3

interest_part = ['head', 'neck', 'Rsho', 'Relb', 'Rwri', 'Lsho', 'Lelb', 'Lwri']
part_edge = [[0,1],[1,2],[1,5],[2,3],[3,4],[5,6],[6,7],[8,9],[9,10],[11,12],[12,13]]
threshold = 0.10

def load_anno(setpath, annopath):
    with open(setpath) as f:
        imgset = [x.strip().split(' ') for x in f.readlines()]

    features = []
    labels = []
    visibles = []

    #filelist = os.listdir(annopath)
    for annofile in imgset:
        annofile = '_'.join(annofile) + '.txt'
        filepath = os.path.join(annopath, annofile)
        with open(filepath) as f:
            data = [x.strip().split(' ') for x in f.readlines()]


        if len(data) != 14:
            print annofile
            print data
            print 'File Format Error!'
            sys.exit()

        imgname = os.path.splitext(annofile)[0]
        imginfo = imgname.split('_')
        x1 = int(imginfo[-4])
        y1 = int(imginfo[-3])
        x2 = int(imginfo[-2])
        y2 = int(imginfo[-1])

        feature = []
        label = clsname[imginfo[-5]]
        #visible = []

        for ind, anno in enumerate(data):
            if len(anno) != 4:
                print annofile
                print anno
                print 'File Format Error!'
                sys.exit()

            part_name = anno[2]
            #if part_name not in interest_part:
            #    continue

            visible = float(anno[3])
            visibles.append(visible)

            x = int(anno[0])
            y = int(anno[1])

            if visible > threshold:
                x = (x - x1) * 1.0 / (x2 - x1)
                y = (y - y1) * 1.0 / (y2 - y1)
            else:
                x = -1
                y = -1
            
            feature.append(x)
            feature.append(y)

        for i in xrange(len(part_edge)):
            if (visibles[part_edge[i][0]] > threshold) and (visibles[part_edge[i][1]] > threshold):
                x1 = feature[part_edge[i][0] * 2]
                y1 = feature[part_edge[i][0] * 2 + 1]
                x2 = feature[part_edge[i][1] * 2]
                y2 = feature[part_edge[i][1] * 2 + 1]
                feature.append(x2 - x1)
                feature.append(y2 - y1)
            else:
                feature.append(-1)
                feature.append(-1)

        features.append(feature)
        labels.append(label)

    return features, labels

def evaluate(pre_y, Ty):
    count = 0
    confusion = [[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]]
    for ind, y in enumerate(pre_y):
        if y == Ty[ind]:
            count += 1
        confusion[Ty[ind]][y] += 1

    print 'Accuracy:', count * 1.0 / len(Ty)
    print 'Pose', confusion[0]
    print 'Embrace', confusion[1]
    print 'Pointing', confusion[2]
    print 'CellToEar', confusion[3]

def cal_mean(part, caltype):
    meanpart = np.zeros((len(part), 60), dtype=float)
    if caltype == 0:
        for i in xrange(len(part)):
            for j in xrange(60):
                meanpart[i,j] = np.mean(part[i][j::60])
        return meanpart
    elif caltype == 1:
        for i in xrange(len(part)):
            for j in xrange(60):
                meanpart[i,j] = np.mean(part[i][60*j:60*j+60])
        return meanpart
    else:
        return part

def cal_max(part, caltype):
    maxpart = np.zeros((len(part), 60), dtype=float)
    if caltype == 0:
        for i in xrange(len(part)):
            for j in xrange(60):
                maxpart[i,j] = np.max(part[i][j::60])
        return maxpart
    elif caltype == 1:
        for i in xrange(len(part)):
            for j in xrange(60):
                maxpart[i,j] = np.max(part[i][46*46*j:46*46*(j+1)])
        return maxpart 
    else:
        return part

if __name__ == '__main__':
    X, Y = load_anno(trainset, annopath)

    print np.array(X).shape
    cpm = loadmat('CPM_feature/train_conv5_2_CPM.mat')['features']
    #cpm = cal_mean(cpm, 1)
    cpm = cal_max(cpm, 1)
    #cpmfile = h5py.File('CPM_feature/train_conv5_1_CPM.mat')
    #cpm = np.array(cpmfile['features'].value).swapaxes(0,1)
    #print cpm.shape
    #partfile = h5py.File('part_feature/train_conv5_2_CPM.mat')
    #partfile = h5py.File('part_feature/random_train_conv5_2_CPM.mat')
    #part = np.array(partfile['features'].value).swapaxes(0,1)
    #part = cal_mean(part, 0)
    #part = cal_max(part, 0)
    #cnn = pickle.load(open('/Users/chenyang/Desktop/CMU/train_features.pkl', 'rb'))
    #pca = PCA(n_components=600)
    #pca.fit(cpm)
    #pca_feature = pca.transform(cpm)

    #print pca_feature
    #print len(X), pca_feature.shape
    #print part
    #X = part
    #X = pca_feature
    X = cpm
    #X = np.hstack((X, part))
    #X = np.hstack((X, pca_feature))
    #X = np.hstack((X, cnn))
    print len(X), len(X[0])

    clf = RandomForestClassifier(n_estimators=30)
    #clf = LogisticRegression(solver='sag', max_iter=100, random_state=42, multi_class='multinomial')
    #clf = SVC(100000)
    clf.fit(X, Y)

    Tx, Ty = load_anno(testset, annopath)

    print np.array(Tx).shape
    cpmtest = loadmat('./CPM_feature/test_conv5_2_CPM.mat')['features']
    #cpmtest = cal_mean(cpmtest, 1)
    cpmtest = cal_max(cpmtest, 1)
    #cpmtestfile = h5py.File('CPM_feature/test_conv5_1_CPM.mat')
    #cpmtest = np.array(cpmtestfile['features'].value).swapaxes(0,1)
    #print cpmtest.shape
    #parttestfile = h5py.File('part_feature/test_conv5_2_CPM.mat')
    #parttestfile = h5py.File('part_feature/random_test_conv5_2_CPM.mat')
    #parttest = np.array(parttestfile['features'].value).swapaxes(0,1)
    #parttest = cal_mean(parttest, 0)
    #parttest = cal_max(parttest, 0)
    #cnn = pickle.load(open('/Users/chenyang/Desktop/CMU/test_features.pkl', 'rb'))
    #pca_feature_test = pca.transform(cpmtest)

    #Tx = parttest
    #Tx = pca_feature_test
    Tx = cpmtest
    #Tx = np.hstack((Tx, parttest))
    #print Tx.shape
    #Tx = np.hstack((Tx, pca_feature_test))
    #Tx = np.hstack((Tx, cnn))
    print len(Tx), len(Tx[0])

    pre_y = clf.predict(Tx)
    evaluate(pre_y, Ty)

