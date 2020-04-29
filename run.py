import xml.etree.ElementTree as Et
import os
import sys
import cv2
from progress.bar import IncrementalBar

## Input and output directories must have images/ and annotations/ subdirs ###

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

            count = 0
            for y in range(0, height, size-stride):
                for x in range(0, width, size-stride):
                    crop_img = img[y:y+size, x:x+size]

                    output_image = os.path.join(output_dir, "images/" \
                            '{}_Split{:03d}{}'.format( \
                            os.path.splitext(image.name)[0], count, filext))

                    cv2.imwrite(output_image, crop_img)
                    count+=1
                    bar.next()

            bar.finish()

def read_xml(xml_file: str):
    tree = Et.parse(xml_file)
    root = tree.getroot()
    filename = root.find('filename').text

    bndboxes = []
    for boxes in root.iter('object'):
        for box in boxes.findall("bndbox"):
            ymin = int(box.find("ymin").text)
            xmin = int(box.find("xmin").text)
            ymax = int(box.find("ymax").text)
            xmax = int(box.find("xmax").text)

        bndboxes.append([xmin, ymin, xmax, ymax])

    return bndboxes

def main():
    if len(sys.argv) < 5:
        print("Invalid number of arguments")
        exit(1)
    split_images(sys.argv[1:])

main()
