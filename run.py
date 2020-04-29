import xml.etree.ElementTree as Et
import os
from progress.bar import bar

## Input and output directories must have images/ and annotations/ subdirs ###

INPUT_DIR = 
OUTPUT_DIR = 
SIZE = 700      # size of the output pictures


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
