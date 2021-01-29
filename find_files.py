import json

input_dir = "../SplitData/grassOrth/COCO/"
ret = []

with open(input_dir + 'coco_annotation.json') as json_file:
    annot = json.load(json_file)

for el in annot['annotations']:
    img_id = el['image_id']
    cat_id = el['category_id']

    img_name = annot['images'][img_id]['file_name'].split('.')[0] + ".xml"
    cat = annot['categories'][cat_id]['name']
    
    ret.append(img_name + ":" + cat)

for i in ret:
    print(i)
