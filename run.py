import xml.etree.ElementTree as ET
import os
import sys
import cv2
import pdb
import argparse
import json
from progress.bar import IncrementalBar

### All input directories must both have images/ and annotations/ subdirs ###

def str2bool(s):
    if isinstance(s, bool): return s
    if s == "True": return True
    return False


def parse_args():
    """
    Parse input arguments
    """
    parser = argparse.ArgumentParser(description='Split an image')
    parser.add_argument('--size', dest='crop_size',
                        help='size of square cropped sections',
                        default=700, type=int)
    parser.add_argument('--stride', dest='perc_stride',
                        help='fraction of overlap for cropped regions (default 0.1)',
                        default=0.1, type=float)
    parser.add_argument('--img_type', dest='filext',
                        help='file type of image (e.g. .tif, .png)',
                        default=".tif", type=str)
    parser.add_argument('--truncated', dest='include_trunc',
                        help='whether to include truncated objects',
                        default=True, type=str2bool)
    parser.add_argument('--input_dirs', dest='input_dirs',
                        help='directories to take input imgs and anns to split',
                        nargs="+")
    parser.add_argument('--output_dir', dest='output_dir',
                        help='directory to save cropped imgs and anns',
                        type=str)
    parser.add_argument('--for_training', dest='train_mode',
                        help='whether to prepare images for training or \
                        just predictions. Default is training.', default=True,
                        type=str2bool)

    args = parser.parse_args()
    return args


class BoundingBox:
    def __init__(self, cat_name, cat_id, trunc, diff, xmin, ymin, xmax, ymax):
        self.cat_name = cat_name
        self.cat_id = cat_id
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax


def bndbox_in_img(include_trunc, conditions):
    # To include truncated objects, include all fully and partially contained
    if include_trunc:
        if all(conditions):
            return True
        if conditions.count(False) == 1:
            return "trunc"
    # include only fully contained
    else:
        if all(conditions):
            return True
    return False    


# Parse XMLs to populate BoundingBox object members
def read_xml(xml_file: str):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    bndboxes = []
    categories = []
    cat_counter = 0
    for boxes in root.iter('object'):
        name = boxes.find("name").text
        cat_id = cat_counter
        if name not in categories:
            categories.append(name)
            cat_counter+=1

        for box in boxes.findall("bndbox"):
            xmin = int(box.find("xmin").text)
            ymin = int(box.find("ymin").text)
            xmax = int(box.find("xmax").text)
            ymax = int(box.find("ymax").text)
        
        bb = BoundingBox(name, cat_counter, xmin, ymin, xmax, ymax)
        bndboxes.append(bb)

    return bndboxes, categories


# performs splitting logic
def split_images_and_annotations(crop_size, perc_stride, stride, filext, include_trunc, input_dirs, 
                                 output_dir, dummy_obj, train_mode):
    # if preparing for training, 2 sub-input-directories are needed
    input_imgs_lst = []
    input_anns_lst = []
    if train_mode:
        for in_dir in input_dirs:
            input_imgs_lst.append(os.path.join(in_dir, "images/"))
            input_anns_lst.append(os.path.join(in_dir, "annotations/"))

    # iterate through every input img directory
    for dir_num, input_imgs in enumerate(input_imgs_lst):
        # iterate through every image in input_dirs
        for image in os.scandir(input_imgs):
            # only check images with correct extension
            if not image.name.endswith(filext):
                print('{} not being parsed - does not have {} extension'.format(image.name, filext))
                continue

            img = cv2.imread(image.path)                # load image
            img_height, img_width = img.shape[:2]       # input image original size

            # adjust crop size to eliminate remainder
            horz_crops = int(img_width  / (crop_size-stride))
            vert_crops = int(img_height / (crop_size-stride))
            width_rem  = (img_width  / (crop_size-stride)) % 1
            height_rem = (img_height / (crop_size-stride)) % 1

            if width_rem < height_rem:      # less remainder in width than in height
                # if width > 0.5, add row which shrinks size
                # if width <= 0.5, keep num of rows which grows size
                width_rem_hi_lo = (width_rem > 0.5)
                crop_minus_stride = int(img_width / (horz_crops + width_rem_hi_lo))
            else:                           # less remainder in height than in width
                # if length > 0.5, add col which shrinks size
                # if length <= 0.5, keep num of cols which grows size
                height_rem_hi_lo = (height_rem > 0.5)
                crop_minus_stride = int(img_height / (vert_crops + height_rem_hi_lo))

            crop_size = int( (crop_minus_stride*100) / (100-(perc_stride*100)) )
            stride = int(crop_size * perc_stride)

            # for output viz
            bar = IncrementalBar("Processing " + image.name, max=horz_crops*vert_crops)

            if train_mode:
                # get list of BoundingBox objects
                bndboxes, categories = read_xml(os.path.join(
                        input_anns_lst[dir_num], os.path.splitext(image.name)[0] + ".xml"))

                # create basic json structure and fill categories
                annot = {}
                annot['images'] = []
                annot['annotations'] = []
                annot['categories'] = [{'id':idx, 'name':cat} for idx, cat in enumerate(categories)]

            row_count = -1      # row count to be included in file name
            img_id = 0          # img id in annotation
            box_id = 0          # bndbox id in annotation
            # split image
            for y in range(0, img_height, crop_size-stride):
                row_count += 1
                col_count = -1
                for x in range(0, img_width, crop_size-stride):
                    col_count += 1
                    # crop image
                    crop_img = img[y:y+crop_size, x:x+crop_size]

                    # if photo is all black or remainder, skip
                    b_and_w = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                    if (cv2.countNonZero(b_and_w) == 0) or (crop_img.shape[0] != crop_img.shape[1]):
                        continue

                    # write img
                    entry_name = '{}_Split{:03d}{:03d}'.format( \
                            os.path.splitext(image.name)[0], \
                            row_count, col_count)

                    if train_mode:
                        output_image = os.path.join(output_dir, "images/", \
                                '{}{}'.format(entry_name, filext))
                    else:
                        output_image = os.path.join(output_dir, \
                                '{}{}'.format(entry_name, filext))
                    
                    # actual image write
                    cv2.imwrite(output_image, crop_img)

                    # if prediction mode, skip all the remaining steps --------------------
                    if not train_mode:
                        bar.next()
                        continue

                    # add image entry to annotation
                    # TODO maybe make the ints into str
                    annot['images'].append({
                        'id': img_id,
                        'file_name': entry_name + filext,
                        'height': crop_size,
                        'width': crop_size
                    })

                    malformed = False
                    # Bounding box fully contained in image or truncated
                    # Depending on arg
                    for box in bndboxes:
                        # need to be at least 10 pixels out from border
                        conditions = [x+5 < box.xmin < x+crop_size-5, \
                                      y+5 < box.ymin < y+crop_size-5, \
                                      x+5 < box.xmax < x+crop_size-5, \
                                      y+5 < box.ymax < y+crop_size-5]
                        # check conditions
                        true_or_trunc = bndbox_in_img(include_trunc, conditions)
                        
                        if true_or_trunc in [True,"trunc"]:
                            # set truncated objects to difficult
                            if true_or_trunc == "trunc":
                                box.truncated = 1

                            # add new object to json
                            bbox_x_min, x1 = max(1, box.xmin-x)
                            bbox_y_min, y1 = max(1, box.ymin-y)
                            bbox_x_max, x2 = min(crop_img_width, box.xmax-x)
                            bbox_y_max, y2 = min(crop_img_height, box.ymax-y)
                            bbox_width = x2 - x1
                            bbox_height = y2 - y1
                            bbox = [bbox_x_min, bbox_y_min, bbox_width, bbox_height]
                            area = bbox_width * bbox_height
                            seg = [[x1,y1 , x2,y1 , x2,y2 , x1,y2]]

                            annot['annotations'].append({
                                  'image_id': img_id,
                                  'id': box_id,
                                  'category_id': box.cat_id,
                                  'bbox': bbox,
                                  'area': area,
                                  'segmentation': seg,
                                  'iscrowd': 0
                            })
                            
                            # check for malformed boxes
                            if max(1, box.xmin-x) >= min(crop_img_width, box.xmax-x) or \
                                    max(1, box.ymin-y) >= min(crop_img_height, box.ymax-y):
                                malformed = True

                            box_id+=1       # increment bndbox id

                    if malformed:
                        print("\nMalformed box in " + entry_name)
                        exit()

                    img_id+=1       # increment image id
                    bar.next()      # advance progress bar

            bar.finish()

        # print annotation
        with open('coco_annotation.json', 'w') as outfile:
            json.dump(annot, outfile)


if __name__ == '__main__':

    args = parse_args()
    
    print("Called with args:")
    print(args)

    # set stride from percent to amount of pixels
    stride = int(args.crop_size * args.perc_stride)

    split_images_and_annotations(args.crop_size, args.perc_stride, stride, args.filext, 
                                 args.include_trunc, args.input_dirs, args.output_dir,
                                 args.dummy_obj, args.train_mode)
