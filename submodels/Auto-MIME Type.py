################################################################################
################################################################################
## brewlytics Sub-Model
## Auto-MIME Type with Error Notification
## Author:  outsideKen
## Created: 27 June 2020
## Updated: 28 April 2022
##
################################################################################
################################################################################
## CHANGE LOG
## 2020-06-27 - Original Code - a single Python Script provides two disctinct
##              functionalities in this brew sub-model
##              - MIME Mode: Checks input filename extension and outputs the 
##                           correct MIME type; If the correct MIME type is not
##                           found, the MIME type is set to 'text/plain'
##              - Email Mode: Generates HTML-formatted Notification Email
## 2020-06-29 - Added KML/KMZ MIME types to the CSV and documentation
## 2020-10-01 - Corrected Notification Email details ordering
## 2020-10-05 - Added brew instance to Notification Email
## 2022-02-22 - Updated model to utilize the new Python Script (Beta) Functional
##              and GitHub hosting of Python Script; added "Error Only" email
##              Notification
## 2022-04-04 - Completed Send Notification Email transition to use new brew
##              Define Python Script functional
##              - Implemented JSON Model Data
##              - Modified the mode to use the Hormel Email utility
## 2022-04-09 - Simplified model by moving the persistence and email 
##              notification to a separate sub-model that will be embedded in
##              the Auto-MIME sub-model
## 2022-04-28 - Cleaned up Python Script and removed code no longer required
################################################################################

import json
import pandas as pd

from brewlytics import *
from datetime import datetime

################################################################################
## FUNCTIONS

## Remove brewlytics CV Type substrings from column names
def remove_cv_type_substrings(df):
    return [column_names.split('{')[0] for column_names in df.columns]

##------------------------------------------------------------------------------
## get_MIME_type: Checks filename for a '.' and splits on the '.' to extract the
## file extension. The file extension is checked in the MIME Types dictionary
## - if the file extension is in the MIME Types dictionary the mime_type is set
##   and mime_error is set to False
## - if the file extension is NOT in the MIME Types dictionary the mime_type is
##   set and mime_error is set to True
## - if no file extension is found in the user-defined filename, a '.txt' will 
##   be appended to the filename, the mime_type will be set to 'text/plain' and
##   the mime_error is set to True  
##------------------------------------------------------------------------------
def get_MIME_type(filename):
    
    # Extract file extension from filename input
    if '.' in filename:
        file_extension = filename.split('.')[-1].lower()
        
        ## Check for file_extension in mime.keys
        if file_extension in mime.keys():
            mime_type = mime[file_extension]['MIME Type']
            mime_error = False
        else:
            
            ## Default MIME type if file extension not recognized
            mime_type = 'text/plain'
            mime_error = True
            
    else:
        ## Default MIME type if file extension not recognized
        filename += '.txt'
        mime_type = 'text/plain'
        mime_error = True
        
    return filename,mime_type,mime_error

################################################################################
## MODEL DATA
################################################################################

iso8601 = '%Y-%m-%dT%H:%M:%S.%fZ'
now = datetime.utcnow()
now_str = now.strftime('%d %B %Y at %H%MZ')

##------------------------------------------------------------------------------
## Create brewlytics Instance from the 'Get Brew Host' functional
##------------------------------------------------------------------------------

instances = {'https://demo.brewlytics.com': {'Instance': 'Demo',
                                             'Root URL': 'https://demo.brewlytics.com/app/#/build/'},
             'https://zeus.brewlytics.com': {'Instance': 'Zeus',
                                             'Root URL': 'https://zeus.brewlytics.com/app/#/build/'}}

##------------------------------------------------------------------------------
## Model User-Defined Notification Email Template - NOTE: A recent change in
## brew truncates strings in the models and required the movement of the email
## template into the Python Script to retain functionality
##------------------------------------------------------------------------------

##------------------------------------------------------------------------------
## MIME Error Notification Email Values to Insert
##------------------------------------------------------------------------------

## - Subject
## - Date & Time (Z)
## - brew Instance (Host)
## - Model Name
## - Filename
## - UUID
## - Date

email_template = '''
<h1>%s</h1>
<hr>
<p>The following brew persistence action occurred at %s:</p>
<ul>
<li><b>brew Instance</b>: %s</li>
<li><b>Model Name</b>: %s</li>
<li><b>Filename</b>: %s</li>
<li><b>UUID</b>: %s</li>
</ul>
<p></p>
<hr>
<p><center>This brewlytics email was generated on %s.</center></p>
'''

################################################################################
## BODY
################################################################################

##--------------------------------------------------------------------------
## INPUTS.RESOURCES[0]: MIME Types CSV
##--------------------------------------------------------------------------

tdf = pd.read_csv(inputs.resources[0])

## Remove brewlytics CV Type substrings from column names
tdf.columns = remove_cv_type_substrings(tdf)

print()
print('Number of File Extensions: %d' % len((tdf['File Extension'].unique())))
print('Number of Unique MIME Types: %d' % len((tdf['MIME Type'].unique())))
print()

##--------------------------------------------------------------------------
## Convert the tdf dataframe to a dictionary with 'File Extension' as the 
## key
##--------------------------------------------------------------------------

mime = tdf.set_index('File Extension').to_dict(orient = 'index')

##--------------------------------------------------------------------------
## INPUTS.STRING: Filename with File Type Extension
##--------------------------------------------------------------------------

filename,file_uuid,host,parent_uuid,parent_model_name,email_address = inputs.string.split('|')

## Get brewlytics instance & create A HREF HTML string for notification email
instance = instances[host]['Instance']

model_url = instances[host]['Root URL'] + parent_uuid
parent_model_html = '<a href="%s" target="blank">%s</a>' % (model_url,parent_model_name)

## Auto-Generate MIME type based on filename
## - Validates the file extension type against the list of accepted MIME types
## - Sets MIME ERROR as True is there is a MIME type error
## - Appends a '.txt' file extension to the filename if one is missing

corrected_filename,mime_type,mime_error = get_MIME_type(filename)

##--------------------------------------------------------------------------
## MIME Error Notification
##--------------------------------------------------------------------------

if mime_error:
    
    subject = 'Filename Missing Extension or Contains MIME Type Not Identified'
    
    ## Values to insert into the email body
    values = (subject,now_str,instance,parent_model_html,filename,uuid,now.strftime('%d %B %Y'))
    email_body = email_template % values
    
    email = {'To': email_address,
             'CC': 'outsideken@gmail.com',
             'Subject': subject,
             'Body': email_body}
    
    email_df = pd.DataFrame([email])

else:

    email_df = pd.DataFrame([], columns = ['To','CC','Subject','Body'])
    
################################################################################
## OUTPUT
################################################################################

outputs.table = email_df.copy()

outputs.list = [corrected_filename,mime_type]
