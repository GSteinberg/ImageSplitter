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
	parser.add_argument('--stride', dest='pixel_stride',
						help='amount of overlap for cropped regions (default 10%%)',
						default=-1, type=int)
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
def new_object(box_name, box_diff, box_trunc, box_xmin, box_ymin, box_xmax, box_ymax):
	# create object xml tree
	obj = ET.SubElement(crop_ann, 'object')
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
def split_images_and_annotations(crop_size, stride, filext, include_trunc, input_imgs, output_imgs, dummy_obj, train_mode):
	# if preparing for training, 2 sub-input-directories are needed
	if train_mode:
		input_imgs = os.path.join(args.input_dir, "images/")
		input_anns = os.path.join(args.input_dir, "annotations/")

	# iterate through every image in input_dir
	for image in os.scandir(input_imgs):
		# only check images with correct extension
		if not image.name.endswith(args.filext):
			print('{} not being parsed - does not have {} extension'.format( \
				image.name, args.filext))
			continue

		img = cv2.imread(image.path)
		# input image original size
		img_height, img_width = img.shape[:2]

		# for output viz
		bar = IncrementalBar("Processing " + image.name, max= \
				len(range(0, img_height, crop_size-stride))* \
				len(range(0, img_width, crop_size-stride)))

		# if training, get list of BoundingBox objects for image
		if train_mode:
			bndboxes = read_xml(os.path.join( \
					input_annotations, \
					os.path.splitext(image.name)[0] + ".xml"))

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

				# if photo is all black, skip
				b_and_w = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
				if cv2.countNonZero(b_and_w) == 0:
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
					output_image = os.path.join(output_imgs, "images/", \
							'{}{}'.format(entry_name, filext))
				else:
					output_image = os.path.join(output_imgs, \
							'{}{}'.format(entry_name, filext))
				
				# actual write
				cv2.imwrite(output_image, crop_img)

				# if prediction mode, skip all the remaining steps --------------------
				if not train_mode:
					bar.next()
					continue

				# creating annotations
				output_annotation = os.path.join(output_imgs, "annotations/" \
						'{}.xml'.format(entry_name))
				# write to xml the image it corresponds to
				filename.text = entry_name + args.filext

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
					true_or_trunc = bndbox_in_img(args.include_trunc, conditions)
					
					if true_or_trunc in [True,"trunc"]:
						obj_present = True
						# set truncated objects to difficult
						if true_or_trunc == "trunc":
							box.truncated = 1

						# add new object to xml
						new_object(box.name, box.difficult, box.truncated, \
							max(1, box.xmin-x), \
							max(1, box.ymin-y), \
							min(crop_img_width, box.xmax-x), \
							min(crop_img_height, box.ymax-y))
						
						# check for malformed boxes
						if max(1, box.xmin-x) >= min(crop_img_width, box.xmax-x) or \
								max(1, box.ymin-y) >= min(crop_img_height, box.ymax-y):
							malformed = True

				# include dummy obj in background imgs
				if not obj_present and args.dummy_obj:
					# add new object to xml
					new_object("dummy", 0, 0, 1, 1, 3, 3)
				
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

	# adjust crop size to eliminate remainder
	

	# if no stride flag, set to default (10% of crop size)
	stride = None
	if args.pixel_stride < 0:
		stride = int(crop_size * 0.1)
	else:
		stride = args.pixel_stride


	split_images_and_annotations(crop_size, stride, args.filext, args.include_trunc, args.input_dir, args.output_dir,
								 args.dummy_obj, args.pred_mode)
