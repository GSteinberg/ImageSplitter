import xml.etree.ElementTree as ET
import os
import sys
import cv2
import pdb
import argparse
from progress.bar import IncrementalBar

### Input and output directories must both have images/ and annotations/ subdirs ###

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
    parser.add_argument('--input_dir', dest='input_dir',
                        help='directory to take input imgs and anns to split',
                        type=str)
    parser.add_argument('--output_dir', dest='output_dir',
                        help='directory to save cropped imgs and anns',
                        type=str)
    parser.add_argument('--dummy', dest='dummy_obj',
                        help='whether to put dummy object in background imgs to \
                        include them in training', default=True, type=str2bool)
    parser.add_argument('--for_training', dest='train_mode',
                        help='whether to prepare images for training or \
                        just predictions. Default is training.', default=True,
                        type=str2bool)

    args = parser.parse_args()
    return args


class BoundingBox:
    def __init__(self, name, trunc, diff, xmin, ymin, xmax, ymax):
        self.name = name
        self.truncated = trunc
        self.difficult = diff
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    # for printing
    def __str__(self):
        return vars(self)


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
    for boxes in root.iter('object'):
        name = boxes.find("name").text
        truncated = int(boxes.find("truncated").text)
        difficult = int(boxes.find("difficult").text)
        for box in boxes.findall("bndbox"):
            xmin = int(box.find("xmin").text)
            ymin = int(box.find("ymin").text)
            xmax = int(box.find("xmax").text)
            ymax = int(box.find("ymax").text)
        
        bb = BoundingBox(name, truncated, difficult, xmin, ymin, xmax, ymax)
        bndboxes.append(bb)

    return bndboxes


# add new object to current xml tree
def new_object(umbrella_elemt, box_name, box_diff, box_trunc, box_xmin, box_ymin, box_xmax, box_ymax):
    # create object xml tree
    obj = ET.SubElement(umbrella_elemt, 'object')
    name = ET.SubElement(obj, 'name')
    truncated = ET.SubElement(obj, 'truncated')
    difficult = ET.SubElement(obj, 'difficult')
    # create bndbox xml tree
    bndbox = ET.SubElement(obj, 'bndbox')
    xmin = ET.SubElement(bndbox, 'xmin')
    ymin = ET.SubElement(bndbox, 'ymin')
    xmax = ET.SubElement(bndbox, 'xmax')
    ymax = ET.SubElement(bndbox, 'ymax')

    # fill obj tree
    name.text = box_name
    truncated.text = str(box_trunc)
    difficult.text = str(box_diff)
    # fill bndbox tree
    xmin.text = str(box_xmin)
    ymin.text = str(box_ymin)
    xmax.text = str(box_xmax)
    ymax.text = str(box_ymax)


# performs splitting logic
def split_images_and_annotations(crop_size, perc_stride, stride, filext, include_trunc, input_dir, 
                                 output_dir, dummy_obj, train_mode):
    # if preparing for training, 2 sub-input-directories are needed
    if train_mode:
        input_imgs = os.path.join(input_dir, "images/")
        input_anns = os.path.join(input_dir, "annotations/")

    # iterate through every image in input_dir
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

        # if training, get list of BoundingBox objects for image
        if train_mode:
            bndboxes = read_xml(os.path.join(input_anns, os.path.splitext(image.name)[0] + ".xml"))

        # count to be included in file name
        row_count = -1
        # split image
        for y in range(0, img_height, crop_size-stride):
            row_count += 1
            col_count = -1
            for x in range(0, img_width, crop_size-stride):
                obj_present = False
                col_count+=1
                # crop image
                crop_img = img[y:y+crop_size, x:x+crop_size]

                # if photo is all black or remainder, skip
                b_and_w = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                if (cv2.countNonZero(b_and_w) == 0) or (crop_img.shape[0] != crop_img.shape[1]):
                    continue

                if train_mode:
                    # Create basic xml structure for writing
                    crop_ann = ET.Element('annotation')
                    filename = ET.SubElement(crop_ann, 'filename')
                    size = ET.SubElement(crop_ann, 'size')
                    width = ET.SubElement(size, 'width')
                    height = ET.SubElement(size, 'height')
                    depth = ET.SubElement(size, 'depth')
                    
                    # size of cropped img
                    crop_img_height, crop_img_width = crop_img.shape[:2]
                    # write size data to xml
                    height.text = str(crop_img_height)
                    width.text = str(crop_img_width)
                    depth.text = "3"

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

                # creating annotations
                output_annotation = os.path.join(output_dir, "annotations/" \
                        '{}.xml'.format(entry_name))
                # write to xml the image it corresponds to
                filename.text = entry_name + filext

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
                        obj_present = True
                        # set truncated objects to difficult
                        if true_or_trunc == "trunc":
                            box.truncated = 1

                        # add new object to xml
                        new_object(crop_ann, box.name, box.difficult, box.truncated, \
                            max(1, box.xmin-x), \
                            max(1, box.ymin-y), \
                            min(crop_img_width, box.xmax-x), \
                            min(crop_img_height, box.ymax-y))
                        
                        # check for malformed boxes
                        if max(1, box.xmin-x) >= min(crop_img_width, box.xmax-x) or \
                                max(1, box.ymin-y) >= min(crop_img_height, box.ymax-y):
                            malformed = True

                # include dummy obj in background imgs
                if not obj_present and dummy_obj:
                    # add new object to xml
                    new_object(crop_ann, "dummy", 0, 0, 1, 1, 3, 3)
                
                # convert xml tree to string
                root = ET.tostring(crop_ann, encoding='unicode')
                crop_ann.clear()
                
                xmlfile = open(output_annotation, 'w')
                xmlfile.write(root)                     # write xml

                if malformed:
                    print("\nMalformed box in " + entry_name)
                    exit()

                # advance progress bar
                bar.next()

        bar.finish()


if __name__ == '__main__':

    args = parse_args()
    
    print("Called with args:")
    print(args)

    # set stride from percent to amount of pixels
    stride = int(args.crop_size * args.perc_stride)

    split_images_and_annotations(args.crop_size, args.perc_stride, stride, args.filext, 
                                 args.include_trunc, args.input_dir, args.output_dir,
                                 args.dummy_obj, args.train_mode)
