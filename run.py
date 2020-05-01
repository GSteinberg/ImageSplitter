import xml.etree.ElementTree as ET
import os
import sys
import cv2
from pprint import pprint
from progress.bar import IncrementalBar

### Input and output directories must both have images/ and annotations/ subdirs ###

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

def split_images(args):
    input_dir = args[0]     # where to take input imgs and anns to split
    output_dir = args[1]    # where to save output imgs and annotations
    crop_size = int(args[2])      # size of square output imgs (xcept leftover)
    stride = int(args[3])    # amount of overlap
    filext = args[4]    # type of files to look for

    input_images = os.path.join(input_dir, "images/")
    input_annotations = os.path.join(input_dir, "annotations/")

    for image in os.scandir(input_images):
        # every input image
        if image.name.endswith(filext):
            img = cv2.imread(image.path)
            # input image original size
            img_height, img_width = img.shape[:2]

            # for output viz
            bar = IncrementalBar("Processing " + image.name, max= \
                    len(range(0, img_height, crop_size-stride))* \
                    len(range(0, img_width, crop_size-stride)))
           
            # get list of BoundingBox objects for image
            bndboxes = read_xml(os.path.join( \
                    input_annotations, \
                    os.path.splitext(image.name)[0] + ".xml"))

            # count to be included in file name
            count = 0
            # split image and xml
            for y in range(0, img_height, crop_size-stride):
                for x in range(0, img_width, crop_size-stride):
                    # crop image
                    crop_img = img[y:y+crop_size, x:x+crop_size]

                    # Create basic xml structure for writing
                    crop_ann = ET.Element('annotation')
                    filename = ET.SubElement(crop_ann, 'filename')
                    size = ET.SubElement(crop_ann, 'size')
                    width = ET.SubElement(size, 'width')
                    height = ET.SubElement(size, 'height')
                    depth = ET.SubElement(size, 'depth')
                    
                    # write size data to xml
                    width.text = str(img_width)
                    height.text = str(img_height)
                    depth.text = "3"

                    # names for each split image and xml pair
                    entry_name = '{}_Split{:03d}'.format( \
                            os.path.splitext(image.name)[0], count)
                    output_image = os.path.join(output_dir, "images/", \
                            '{}{}'.format(entry_name, filext))
                    output_annotation = os.path.join(output_dir, "annotations/" \
                            '{}.xml'.format(entry_name))
                    filename.text = entry_name + filext

                    # bndbox is fully contained in image
                    for box in bndboxes:
                        if box.xmin > x and box.ymin > y and \
                                box.xmax < x+crop_size and \
                                box.ymax < y+crop_size:
                            
                            # create object xml tree
                            obj = ET.SubElement(crop_ann, 'object')
                            name = ET.SubElement(obj, 'name')
                            truncated = ET.SubElement(obj, 'truncated')
                            difficult = ET.SubElement(obj, 'difficult')
                            # fill obj tree
                            name.text = box.name
                            truncated.text = str(box.truncated)
                            difficult.text = str(box.difficult)

                            # create bndbox xml tree
                            bndbox = ET.SubElement(obj, 'bndbox')
                            xmin = ET.SubElement(bndbox, 'xmin')
                            ymin = ET.SubElement(bndbox, 'ymin')
                            xmax = ET.SubElement(bndbox, 'xmax')
                            ymax = ET.SubElement(bndbox, 'ymax')
                            # fill bndbox tree
                            xmin.text = str(box.xmin-x)
                            ymin.text = str(box.ymin-y)
                            xmax.text = str(box.xmax-x)
                            ymax.text = str(box.ymax-y)

                    # convert xml tree to string
                    root = ET.tostring(crop_ann, encoding='unicode')
                    crop_ann.clear()
                    
                    xmlfile = open(output_annotation, 'w')
                    xmlfile.write(root)                     # write xml
                    cv2.imwrite(output_image, crop_img)     # write img
                    count+=1
                    bar.next()

            bar.finish()
           
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

def main():
    if len(sys.argv) < 5:
        print("Invalid number of arguments")
        exit(1)
    split_images(sys.argv[1:])

main()

