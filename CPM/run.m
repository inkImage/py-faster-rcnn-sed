function run()

testindex = '/home/chenyang/cydata/sed_subset/annodata/test.txt';
trainindex = '/home/chenyang/cydata/sed_subset/annodata/train.txt';
imagepath = '/home/chenyang/cydata/sed_subset/annodata/images/';
outputpath = '/home/chenyang/lib/CPM/';
annopath = '/home/chenyang/lib/CPM/results_model5/'
control(trainindex, imagepath, outputpath, 'train', annopath);
control(testindex, imagepath, outputpath, 'test', annopath);

function control(indexfile, imagepath, outputpath, setname, annopath)

[images, rect, cls] = load_index(indexfile);
%predict_pose(images, rect, cls)
%interest_layers_list = {{'conv5_2_CPM'}; {'Mconv7_stage2'}; {'Mconv7_stage3'};{'Mconv7_stage4'};{'Mconv7_stage5'};{'Mconv7_stage6'};};

interest_layers_list = {{'conv5_2_CPM'}};%; {'conv3_4'}};
for i = 1 : length(interest_layers_list)
    interest_layers = interest_layers_list{i}
    CPM_feature(images, rect, imagepath, outputpath, setname, interest_layers);
end

interest_layers_list = {{'conv5_2_CPM'}};%; {'conv3_4'}};
for i = 1 : length(interest_layers_list)
    interest_layers = interest_layers_list{i}
    CPM_partfeature(images, rect, cls, imagepath, outputpath, setname, interest_layers, annopath);
end


function [images, rect, cls] = load_index(indexfile)
index = fopen(indexfile, 'r');
images = {};
rect = {};
cls = {};
while true
    newline = fgetl(index);
    if ~ischar(newline); break; end
    
    t = strsplit(newline, ' ');
    images = [images; [t{1}]];
    cls = [cls; [t{2}]];
    
    t1 = str2num(t{3});
    t2 = str2num(t{4});
    t3 = str2num(t{5});
    t4 = str2num(t{6});
    rect = [rect; [t1, t2, t3-t1, t4-t2]];
end

fclose(index);


function predict_pose(images, rect, cls)
close all;
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/src');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/util');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/util/ojwoodford-export_fig-5735e6d/');
param = config();

fprintf('Description of selected model: %s \n', param.model(param.modelID).description);

model = param.model(param.modelID)
net = caffe.Net(model.deployFile, model.caffemodel, 'test')

results = {};
visible = {};
for i = 1:length(images)
    [result, v] = run_CPM(images{i}, rect{i}, param, net);
    results = [results; [result]];
    visible = [visible; [v]];
    fprintf('%d / %d\n', i, length(images))
end

articulation = {'head', 'neck', 'Rsho', 'Relb', 'Rwri', ...
                'Lsho', 'Lelb', 'Lwri', ...
                'Rhip', 'Rkne', 'Rank', ...
                'Lhip', 'Lkne', 'Lank', 'bkg'};    

outputroot = ['/home/chenyang/lib/CPM/results_model', num2str(param.modelID), '/'];

for  i = 1:length(results)
    x1 = num2str(rect{i}(1));
    y1 = num2str(rect{i}(2));
    x2 = num2str(rect{i}(1) + rect{i}(3));
    y2 = num2str(rect{i}(2) + rect{i}(4));
    imgfile = fopen([outputroot, images{i}, '_', cls{i}, '_', x1, '_', y1, '_', x2, '_', y2, '.txt'], 'w');
    for j = 1:length(results{i})
        fprintf(imgfile, '%d %d %s %f\n', results{i}(j,1), results{i}(j, 2), articulation{j}, visible{i}(j));
    end
    fclose(imgfile);
end


function CPM_feature(images, rect, imagepath, outputpath, setname, interest_layers)

addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/src');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/util');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/util/ojwoodford-export_fig-5735e6d/');
param = config();

fprintf('Description of selected model: %s \n', param.model(param.modelID).description);

model = param.model(param.modelID);
net = caffe.Net(model.deployFile, model.caffemodel, 'test');

features = [];
for i = 1:length(images)
    cnnfeature = extract_feature([imagepath, images{i}, '.jpg'], param, rect{i}, net, interest_layers);
    
    %TO DO
    % Write feature to file
    feature = [];
    size(cnnfeature)
    size(cnnfeature{1})
    for j = 1:length(cnnfeature)
        t = reshape(cnnfeature{j}, 1, []);
        feature = [feature, t];
    end
    
    features = [features; feature];
    %filename = [outputpath, images{i}, '.mat'];
    %save(filename, 'feature');
    info = [num2str(i), ' / ', num2str(length(images))];
    disp(info)
end

size(features)
filename = [outputpath, setname];
for i = 1:length(interest_layers)
    filename = [filename, '_', interest_layers{i}];
end
filename = [filename, '.mat']
%save(filename, 'features');
save(filename, 'features', '-v7.3');


function CPM_partfeature(images, rect, cls, imagepath, outputpath, setname, interest_layers, annopath)

addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/src');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/util');
addpath('/home/chenyang/workspace/convolutional-pose-machines-release/testing/util/ojwoodford-export_fig-5735e6d/');
param = config();

fprintf('Description of selected model: %s \n', param.model(param.modelID).description);

model = param.model(param.modelID);
net = caffe.Net(model.deployFile, model.caffemodel, 'test');

features = [];
for i = 1:length(images)
    % Load detected pose feature
    poses = load_anno(images{i}, rect{i}, cls{i}, annopath);
    
    % Extract articulations' local feature
    cnnfeature = extract_partfeature([imagepath, images{i}, '.jpg'], param, rect{i}, net, interest_layers, poses);
    
    features = [features; cnnfeature];
    info = [num2str(i), ' / ', num2str(length(images))];
    disp(info)
end

size(features)
filename = [outputpath, setname];
for i = 1:length(interest_layers)
    filename = [filename, '_', interest_layers{i}];
end
filename = [filename, '.mat']
%save(filename, 'features');
save(filename, 'features', '-v7.3');


function poses = load_anno(imgname, rect, cls, annopath)
    filename = [annopath, imgname, '_', cls, '_', num2str(rect(1)), '_', num2str(rect(2)), ...
        '_', num2str(rect(1)+rect(3)), '_', num2str(rect(2)+rect(4)), '.txt'];
    imgfile = fopen(filename);
    poses = [];
    for i = 1:14
        t = sscanf(fgetl(imgfile), '%d %d %s %f')';
        if t(length(t)) > 0.1
            poses = [poses; [t(1),t(2)]];
        else
            poses = [poses; [0, 0]];
        end
    end
    
    fclose(imgfile);
