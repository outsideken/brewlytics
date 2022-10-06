################################################################################
################################################################################
## SpaceX Starlink Catalog
## Manage SpaceX Starlink Catalog; Update from N2YO.com API
## Author: K. Chadwick/N-ask
## Created: 04 April 2020
## Updated: 26 September 2022
## 
################################################################################
################################################################################
## CHANGE LOG
## 2020-04-11 - Original code to maintain and update the SpaceX Starlink
##              on-orbit satellite catalog
## 2020-06-01 - Added code to check for STARLINK GROUPs in the dataset; these 
##              result when the model is executed immediately after a Starlink
##              launch and individual TLEs have not yet been created/calculated
##              for individiual spacecraft; if found they are removed from the
##              dataset; added JSON output of catalog to Python Script 
##              functional to reduce overall functional count; added corrections
##              dictionary for fixing errors in data from source
## 2020-07-20 - Removed corrections dictionary - NORAD Catalog corrected at 
##              source
## 2020-10-06 - Added error trapping for Launch dates that return no data
## 2021-03-04 - Added COSPAR Id to output table
## 2022-03-09 - Updated the Python Script to use the new brewlytics Define 
##              Python Script functional
## 2022-09-26 - Fixed bugs in alternate workflow
################################################################################
################################################################################

from brewlytics import *

import json
import pandas as pd
import re

from datetime import datetime

################################################################################
################################################################################
## FUNCTIONS

def unpack_dictionary(packed_dictionary):
    
    unpacked = dict()
    for key,val in packed_dictionary.items():
        for v in val:
            unpacked[v] = key
        
    return unpacked 

def extract_cv_types(tdf):
    
    global cv_types
    
    cleaned = list()
    for column_name in tdf.columns:
        key = column_name.split('{')[0]
        
        cleaned.append(key)
        cv_types[key] = column_name

    return cleaned,cv_types

# def clean_column_names(tdf):
    
#     return [column_name.split('{')[0] for column_name in tdf.columns]

def remove_group_launches(tdf):
    
    return tdf[~tdf['Name'].str.contains('GROUP')]

def get_dataset(launch):
    
    global df, api_url, now_str, operator
    
    ## Read in data from source
    try:
        tdf = pd.read_html(api_url % launch)[2]
        
        ## Clean up data and column names from source
        if 'Action' in tdf.columns:
            tdf.drop(['Action'], axis = 1, inplace = True)

        tdf.columns = ['Name','NORAD ID',"Int'l Code",'Launch Date','Status']

        tdf['Operator'] = operator

        ## Add Data provenance information
        tdf['Source'] = 'N2YO.com'
        tdf['Source URL'] = api_url % launch
        tdf['Date Retrieved'] = now_str
        tdf['Classification'] = 'Unclassified'

        ## Filter out Grouped launch data
        filtered = remove_group_launches(tdf).copy()

    except:
        
        ## Create an empty dataframe
        filtered = pd.DataFrame([], columns = df.columns)
        
    return filtered
    
################################################################################
################################################################################
## MODEL DATA

md = json.loads(inputs.string)

##------------------------------------------------------------------------------
## Get the current date
##------------------------------------------------------------------------------

iso_format = '%Y-%m-%dT%H:%M:S.%fZ'
now = datetime.utcnow()
now_str = now.strftime(md['Date String Format'])

##------------------------------------------------------------------------------
## Retrieve Operator from model_data
##------------------------------------------------------------------------------

operator = md['Operator']

##------------------------------------------------------------------------------
## User provided Launch Dates
##------------------------------------------------------------------------------

launch_dates = [tuple(launch.split('-')) for launch in md['Launch Dates']]

##------------------------------------------------------------------------------
## Data source API with %-operators added
##------------------------------------------------------------------------------

# api_url = 'https://www.n2yo.com/database/?m=%s&d=%s&y=%s#results'
api_url = md['API URL']

##------------------------------------------------------------------------------
## NULL List: Null List to compare against Keywords List
##------------------------------------------------------------------------------

null_list = ['----','None',None]

##------------------------------------------------------------------------------
## Output_Table Column Order
##------------------------------------------------------------------------------

column_order = ['Name','COSPAR Id','NORAD ID',"Int'l Code",'Launch Date',
                'Status','Operator','Source','Source URL','Date Retrieved',
                'Classification']

##------------------------------------------------------------------------------
## brewlytics CV Types
##------------------------------------------------------------------------------

cv_types = {'COSPAR Id': 'COSPAR Id{string}'}

################################################################################
################################################################################
## BODY

##==============================================================================
## INPUTS.TABLES[0]: 
##==============================================================================
## Clean input_table column names of CV Types

df = inputs.tables[0].copy()
df.columns,cv_types = extract_cv_types(df)

##==============================================================================
## Filter out Grouped launch data
##==============================================================================

df = df[~df['Name'].str.contains('GROUP')].copy()

##==============================================================================
## Determine if there are new launch dates not currently in the persisted 
## dataset
##==============================================================================

mdy,ymd = ['%m-%d-%Y','%Y-%m-%d']
md_launch_dates = {datetime.strptime(launch,mdy).strftime(ymd) 
                   for launch in md['Launch Dates']}

## List comprehension to create a list of launch dates not in the aggregated 
## dataset
new_launch_dates = [ld for ld in md_launch_dates if ld not in df['Launch Date']]

##==============================================================================
## UPDATE DATASET: A BOOLEAN True or False to force a complete refresh 
## of the Starlink dataset from the source
##==============================================================================

if (md['Update Dataset']):

    print('Updating dataset ...')
    
    ## For loop to grab data and create CSV
    starlink = list()
    for launch in launch_dates:
    
        print('Retrieving %s launch data for %s' % (md['Operator'],launch))

        ## Read in data from API and append to list for contcatenation
        starlink.append(get_dataset(launch))

    constellation = pd.concat(starlink)

##==============================================================================
## Automatically update dataset when a launch date not in the persisted dataset
## is added by the user
##==============================================================================

elif (md['Auto Update Dataset When New Launch Dates Added']) and (new_launch_dates):
        
    print('New Launch Date(s) being added to dataset...')
    
    starlink = [df]
    for launch in new_launch_dates:
        
        print('Retrieving %s launch data for %s' % (md['Operator'],launch))
        
        ## Read in data from API and append to list for contcatenation
        yyyy,mm,dd = launch.split('-')
        starlink.append(get_dataset((mm,dd,yyyy)))
        
    constellation = pd.concat(starlink)

##==============================================================================
## Use the persisted dataset
##==============================================================================

else:
    
    print('Using persisted Starlink catalog')
    constellation = df.copy()
    
##------------------------------------------------------------------------------
## KEYWORD FILTER TERMS: Keyword filter of dataset
##------------------------------------------------------------------------------

tag = 'Keyword Filter Terms'
keywords = [keyword for keyword in md[tag] if keyword not in null_list]

constellation = constellation[constellation['Name'].str.contains('|'.join(keywords))]
    
##------------------------------------------------------------------------------
## Add COSPAR Id to dataset
##------------------------------------------------------------------------------

if 'COSPAR Id' not in constellation.columns:
    constellation['COSPAR Id'] = constellation["Int'l Code"].apply(lambda t: re.sub(r'[A-Z]*','',t))
    
################################################################################
################################################################################
## OUTPUTS

##------------------------------------------------------------------------------
## OUTPUTS.TABLE[0]: Concatenate dataframes into a single dataframe
##------------------------------------------------------------------------------
outputs.table = constellation[column_order].rename(columns = cv_types)

##------------------------------------------------------------------------------
## OUTPUTS.LIST[0]: List of NORAD Catalog Ids
##------------------------------------------------------------------------------
outputs.list = sorted([str(norad_id) for norad_id in constellation['NORAD ID']])

##------------------------------------------------------------------------------
## OUTPUTS.STRING[0]: JSON-formatted string of SpaceX Starlink Catalog
##------------------------------------------------------------------------------
catalog = {'SpaceX Starlink Catalog': constellation[column_order].to_dict(orient = 'records')}
outputs.string = json.dumps(catalog)

################################################################################
################################################################################
## SUMMARY

print('')
print('Dataset Shape: %d rows %d columns' % constellation[column_order].shape)
print('Column Names:\n\n- ' + '\n- '.join(constellation[column_order].columns))

## Save dataframe as a CSV
# filename = md['Filename Stub'] % now_str
# outputs.table.to_csv(filename, index = False)
