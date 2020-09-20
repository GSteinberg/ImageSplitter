# **ImageSplitter**
### **Split your orthomosaics to:**
1. **Use them for training data in Faster R-CNN**
2. **Do predictions on them with Faster R-CNN**
---
### Prerequisites
*anaconda*

Run the following command to download all necessary packages

`conda create --name <env> --file conda_requirements.txt`

You may also need to run the following command if any conda packages cannot be found

`conda config --append channels conda-forge`

*pip*

Run the following command to download all necessary packages

`pip install -r pip_requirements.txt`

I used python 3.6 but this will likely work for future python versions

### Preparing your data
*Preparing data for training*

The script is set to the training data mode by default. Do not include the ***--predictions*** flag and it will execute the training data mode.

You must have orthomosaics and their cooresponding annotations organized like below:
```
Orthomosaics
├── annotations 
│   ├── 1_RGB.xml  
│   ├── 2_RGB.xml  
│   ├── 3_RGB.xml  
│   └── 4_RGB.xml  
└── images 
    ├── 1_RGB.tif 
    ├── 2_RGB.tif 
    ├── 3_RGB.tif 
    └── 4_RGB.tif  
```
***Notes***
- *Orthomosaics* in this case is what you would put in the ***--input_dir*** parameter
- The directory that you set as your ***--output_dir*** must also have directories named *annotations* and *images* in it or else the script will fail
- The images and xmls do not have be named in this format (i.e. 1_RGB, 2_RGB) but the corresponding annotations and images must have the same file stem.

*Preparing data for predictions*

This is more simple since there are no annotations to work with. Just set the ***--predictions*** flag and the script will execute in prediction mode.

Your directories do not need to be in a special format, just include in ***--input_dir***, an input directory with orthomasics and in ***--output_dir***, an empty output directory to be filled with split photos.

### To run
Run the following command to see the available parameters and what they mean:
`python run.py --help`

### Next
Go to the following Faster R-CNN repository to perform predictions or perform training and testing on your newly split data:
https://github.com/GSteinberg/faster-rcnn.pytorch
