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
            obj = ET.SubElement(crop_ann, 'object')
            bndbox = ET.SubElement(obj, 'bndbox')

            count = 0
            # Split image and xml
            for y in range(0, height, size-stride):
                for x in range(0, width, size-stride):
                    crop_img = img[y:y+size, x:x+size]
                    
                    output_image = os.path.join(output_dir, "images/" \
                            '{}_Split{:03d}{}'.format( \
                            os.path.splitext(image.name)[0], count, filext))
                    output_annotation = os.path.join(output_dir, "annotations/" \
                            '{}_Split{:03d}.xml'.format( \
                            os.path.splitext(image.name)[0], count))

                    # bndbox is fully contained in image
                    for box in bndboxes:
                        if box.xmin > x and box.ymin > y and \
                                box.xmax < (x+size) and box.ymax < (y+size):
                            obj.set('name', box.name)
                            obj.set('truncated', box.truncated)
                            obj.set('difficult', box.difficult)
                            bndbox.set('xmin', box.xmin-x)
                            bndbox.set('ymin', box.ymin-y)
                            bndbox.set('xmax', box.xmax-(x+size))
                            bndbox.set('ymax', box.ymax-(y+size))

                            crop_ann.append(obj)
                            crop_ann.append(bndbox)
                            print("here")

                    xmlfile = open(output_annotation, 'w')
                    xmlfile.write( ET.tostring(crop_ann) )  # write xml
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
