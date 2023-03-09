import os

import cv2
import json
import lmdb
import numpy as np
import six
import torch
from PIL import Image

from modelscope.metainfo import Models
from modelscope.msdatasets.task_datasets.builder import TASK_DATASETS
from modelscope.msdatasets.task_datasets.torch_base_dataset import \
    TorchTaskDataset
from modelscope.utils.constant import Tasks
from modelscope.utils.logger import get_logger

DATASET_STRUCTURE = {'image': 'image', 'label': 'label.txt', 'lmdb': 'lmdb'}


def Q2B(uchar):
    inside_code = ord(uchar)
    if inside_code == 0x3000:
        inside_code = 0x0020
    else:
        inside_code -= 0xfee0
    if inside_code < 0x0020 or inside_code > 0x7e:
        return uchar
    return chr(inside_code)


@TASK_DATASETS.register_module(
    Tasks.ocr_recognition, module_name=Models.ocr_recognition)
class OCRRecognitionDataset(TorchTaskDataset):

    def __init__(self, **kwargs):
        split_config = kwargs['split_config']
        cache_root = next(iter(split_config.values()))
        lmdb_path = os.path.join(cache_root, DATASET_STRUCTURE['lmdb'])
        self.env = lmdb.open(
            lmdb_path,
            max_readers=1,
            readonly=True,
            lock=False,
            readahead=False,
            meminit=False)
        if not self.env:
            print('cannot creat lmdb from %s' % (lmdb_path))
            sys.exit(0)
        self.nSamples = 0
        with self.env.begin(write=False) as txn:
            self.nSamples = int(txn.get('num-samples'.encode()))
        self.reco_preprocess = kwargs['preprocessor']

    def __len__(self):
        return self.nSamples

    def __getitem__(self, index):
        index += 1
        img_key = 'image-%09d' % index
        with self.env.begin(write=False) as txn:
            imgbuf = txn.get(img_key.encode())
            buf = six.BytesIO()
            buf.write(imgbuf)
            buf.seek(0)
            img = Image.open(buf).convert('L')
            if self.reco_preprocess is not None:
                img = self.reco_preprocess(img)

            label_key = 'label-%09d' % index
            label = txn.get(label_key.encode()).decode('utf-8')
            label = ''.join([Q2B(c) for c in label])

        return {'images': img, 'labels': label}
