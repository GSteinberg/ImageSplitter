import tensorflow as tf
from PIL import Image
from utils import visualization_utils as vis_utils
import json
import os
import random

input_dir = "../../../SplitData/grassOrth/COCO/"
all_img_names = []

with open(input_dir + 'coco_annotation.json') as json_file:
    annotations = json.load(json_file)

for img_name in os.scandir(input_dir):
    if img_name.name.endswith("tif"):
        all_img_names.append(img_name.name)

for idx, img_name in enumerate(all_img_names):
    # here get all the annotations that correspond to one image idx
    annots = [an for an in annotations["annotations"] if an['image_id'] == idx]

    img_path = os.path.join(input_dir, img_name)
    img = Image.open(img_path)
    for annot in annots:
        tlx, tly, w, h = annot['bbox']
        cat = annot['category_id']
        caption = annotations['categories'][cat]['name']
        vis_utils.draw_bounding_box_on_image(img, tly, tlx, tly+h, tlx+w,
                display_str_list = [caption],
                use_normalized_coordinates=False)

    img.save(os.path.join(input_dir, "Viz/", img_name))
