################################################################################
################################################################################
## Scikit-learn DecisionTreeClassifier
## Create Multi-Class Tagged Ellipse Train/Test Dataset
## Author: OutsideKen
## Created: 02 November 2020
## Updated: 31 March 2022
##
################################################################################
## CHANGE LOG
## 2020-11-02 - Port of original exemplar script from TutorialsPoint
##              https://www.tutorialspoint.com/machine_learning_with_python/machine_learning_with_python_classification_algorithms_decision_tree.htm
## 2020-11-05 - Add Summary Report of Model Result to output_string
## 2022-01-17 - Swapped out the dataset for a Synthetic Ellipse dataset
## 2022-03-05 - Updated for 6-Class Synthetic Ellipse dataset
## 2022-03-08 - Added Output_Resource[1] - Trained Multi-Class Ellipse Decison
##              Tree model as a pickle
## 2022-03-26 - Added code to convert the ScikitLearn Confusion Matrix to a 
##              formatted pandas DataFrame for the Confusion Matrix plot
## 2022-03-31 - Updated Python Script for use in brewlytics
##
################################################################################
################################################################################

from brewlytics import *

import json
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
import re
import uuid

from collections import Counter
from datetime import datetime

################################################################################
## FUNCTIONS
################################################################################

def remove_cv_types(tdf):
    return [column_name.split('{')[0] for column_name in tdf.columns]

def format_plot(ax, font_size, color):
    
    ax.tick_params(direction='out', length = 4, width = 1, colors = color,
                   labelsize = font_size, labelcolor = color)

    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    
    return

################################################################################
## MODEL DATA
################################################################################

now = datetime.utcnow()
now_str = now.strftime('%Y-%m-%d %H:%MZ')

md = json.loads(inputs.string)

##------------------------------------------------------------------------------
## Set User-defined Random Seed
##------------------------------------------------------------------------------

random.seed(md['Random Seed'])

##------------------------------------------------------------------------------
## Set User-defined Maximum Semi-Major Axis length in Nautical Miles
##------------------------------------------------------------------------------

max_sma = md['Max Semi-Major Axis']

##------------------------------------------------------------------------------
## Set User-defined Maximum Number of Rows in Ellipse Dataset
##------------------------------------------------------------------------------

max_rows = md['Max Rows']
# max_rows = 100000

##------------------------------------------------------------------------------
## Define pi for calculating Ellipse Area: area = pi * Semi_Major * Semi_Minor
##------------------------------------------------------------------------------

pi = math.pi

##------------------------------------------------------------------------------
## Set User-define Output Table Column Order 
## (with brew CV Types in Column Names)
##------------------------------------------------------------------------------

order = md['Output Table Column Order']

## Create Column Order list and brew CV Types dictionary; if brew CV Type no in
## column name, add to CV Types dictionary as a {string} CV Type
cv_types = dict()
column_order = list()
for column_name in order:
    
    if ('{' in column_name) and ('}' in column_name):
        key = column_name.split('{')[0]
        cv_types[key] = column_name
        
        column_order.append(key)
        
    else:
        
        cv_types[key] = '%s{string}' % column_name
        column_order.append(column_name)

##------------------------------------------------------------------------------
## INPUTS.TABLE[0]: Convert User-define Ellipse Classes CSV to an to dictionary
## with the ellipse class as the key and parameters dictionary as the value
##------------------------------------------------------------------------------

## Multi-Class Classification - Add 'Class' columm to dataframe
## 81.7128249198705 nm of current methology

df = inputs.table.copy()
df.columns = [column_name.split('{')[0] for column_name in df.columns]

df['Area'] = [tuple(z) for z in zip(df['Area (min)'],df['Area (max)'])]

ellipse_classes = df.set_index('Class').to_dict(orient = 'index')

################################################################################
## BODY
################################################################################

data = list()
for i in range(0,max_rows):
    
    sma = random.randint(0,max_sma) + random.random()
    smi = random.randint(0,max_sma) + random.random()
    ori = random.randint(0,360) + random.random()
    
    ## Good random ellipse data
    if (sma > 0.0) and (smi > 0.0) and (smi <= sma):
    
        data.append({'Id': uuid.uuid4(),
                     'Semi-Major': sma,
                     'Semi-Minor': smi,
                     'Orientation': ori})    
    
    elif (sma == 0.0) or (smi == 0.0):
    
        data.append({'Id': uuid.uuid4(),
                     'Semi-Major': 0.1,
                     'Semi-Minor': 0.1,
                     'Orientation': ori})
    
    elif (smi > sma):
        
        data.append({'Id': uuid.uuid4(),
                     'Semi-Major': smi,
                     'Semi-Minor': sma,
                     'Orientation': ori})
    
    else:
        
        print('Bad Semi-Major or Semi-Minor Axis!!')
        print(sma,smi)

## Convert list of dictionaries to pandas DataFrame
edf = pd.DataFrame(data)

##------------------------------------------------------------------------------
## Add 'Area' column to dataframe
##------------------------------------------------------------------------------

edf['Area'] = math.pi * edf['Semi-Major'] * edf['Semi-Minor']

##------------------------------------------------------------------------------
## Add 'Eccentricity' column to dataframe
##------------------------------------------------------------------------------

edf['Eccentricity'] = np.sqrt(1 - (edf['Semi-Minor']**2 / edf['Semi-Major']**2))

##------------------------------------------------------------------------------
## Add User-defined Class tags to randomly generated Ellipse Dataset
##------------------------------------------------------------------------------

df2concat = list()
for key,val in ellipse_classes.items():
    
    print('Processing "%s" Class Ellispes...' % key)
    
    amin,amax = val['Area']
    
    if key != 'Bad':
        tdf = edf[(edf['Area'] > amin) & (edf['Area'] <= amax)].copy()
    else:
        ## For 'Bad' Ellipses, only a minimum area is used because any ellipse
        ## with an area larger than this will be considered 'Bad'
        tdf = edf[(edf['Area'] > amin)].copy()
        
    tdf['Class'] = key
    df2concat.append(tdf)
    
new_df = pd.concat(df2concat)

################################################################################
## OUTPUTS
################################################################################

##------------------------------------------------------------------------------
## OUTPUTS.TABLE[0]: Randomly Generated Ellipse Dataset
##------------------------------------------------------------------------------

outputs.table = new_df[column_order].rename(columns = cv_types).copy()

################################################################################
## SUMMARY
################################################################################

print()
for ec in Counter(new_df['Class']).items():
    print('%s: %d' % ec)
