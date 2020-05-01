import xml.etree.ElementTree as ET
import os
import sys
import cv2
from pprint import pprint
from progress.bar import IncrementalBar

## Input and output directories must have images/ and annotations/ subdirs ###

class BoundingBox:
    def __init__(self, name, trunc, diff, xmin, ymin, xmax, ymax):
        self.name = name
        self.truncated = trunc
        self.difficult = diff
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    def __str__(self):
        return vars(self)

def split_images(args):
    input_dir = args[0]     # images and annotations that will be split
    output_dir = args[1]    # saved split images and annotations
    size = int(args[2])      # size of the square output pictures
    stride = int(args[3])    # amount of overlap
    filext = args[4]    # files to look for

    input_images = os.path.join(input_dir, "images/")
    input_annotations = os.path.join(input_dir, "annotations/")

    for image in os.scandir(input_images):
        if image.name.endswith(filext):
            img = cv2.imread(image.path)
            height, width = img.shape[:2]

            bar = IncrementalBar("Processing " + image.name, max= \
                    len(range(0, height, size-stride))* \
                    len(range(0, width, size-stride)))
           
            # Get list of BoundingBox objects for image
            bndboxes = read_xml(os.path.join( \
                    input_annotations, \
                    os.path.splitext(image.name)[0] + ".xml"))
            # bndboxes.sort(key=lambda i: (i[0], i[1]))

            # Create basic xml structure for writing
            crop_ann = ET.Element('annotation')
            filename = ET.SubElement(crop_ann, 'filename')

            count = 0
            # Split image and xml
            for y in range(0, height, size-stride):
                for x in range(0, width, size-stride):
                    crop_img = img[y:y+size, x:x+size]
                    
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
                                box.xmax < (x+size) and box.ymax < (y+size):
                            
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
                            xmax.text = str(box.xmax-(x+size))
                            ymax.text = str(box.ymax-(y+size))

                            # add obj and bndbox to root tree
                            crop_ann.append(obj)
                            crop_ann.append(bndbox)

                    # convert xml tree to string
                    root = ET.tostring(crop_ann, encoding='unicode')
                    xmlfile = open(output_annotation, 'w')
                    xmlfile.write(root)                     # write xml
                    cv2.imwrite(output_image, crop_img)     # write img
                    count+=1
                    bar.next()

            bar.finish()
            
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

"""
print('img: {}, {}, {}, {}' \
        .format(x, y, x+size, y+size))
print('box: {}, {}, {}, {}' \
        .format(box.xmin, box.ymin, box.xmax, box.ymax))
        """
