from utils import visualization_utils as vis_utils
import json
import os

input_dir = "../OrthoData/grassOrth/"
output_dir = "../SplitData/grassOrth/COCO/"
all_img_names = []

with open(output_dir + 'coco_annotation.json') as json_file:
    annotations = json.load(json_file)

for img_name in os.scandir(input_dir + "images/"):
    all_img_names.append(img_name)

for idx, img_name in enumerate(all_img_names):
    annots = annotations["annotations"][idx]

    img_path = os.path.join(input_dir, img_name)
    img = Image.open(img_path)
    for annot in annots:
        tlx, tly, w, h = annot['bbox']
        cat = annot['category_id']
        caption = categories[cat]
        score = str(random.random())[:4]
        vis_utils.draw_bounding_box_on_image(img, tly, tlx, tly+h, tlx+w,
                display_str_list = [caption, score],
                use_normalized_coordinates=False)

    img.save(os.path.join(output_dir, "/Viz/", img_name))