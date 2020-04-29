import xml.etree.ElementTree as Et
import os
import sys
import cv2
from progress.bar import IncrementalBar

## Input and output directories must have images/ and annotations/ subdirs ###

def split_images(args):
    input_dir = args[0]     # images and annotations that will be split
    output_dir = args[1]    # saved split images and annotations
    size = args[2]      # size of the square output pictures
    stride = args[3]    # amount of overlap
    fileext = args[4]   # files to look for

    input_images = os.path.join()

    for image in os.scandir(inputdir):


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
