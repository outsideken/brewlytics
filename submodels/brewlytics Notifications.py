################################################################################
################################################################################
## brewlytics Utility
## Generic Error Notification
## Author:  outsideKen
## Created: 19 February 2022
## Updated: 19 February 2022
##
################################################################################
## CHANGE LOG
## 2022-02-19 - Original Code and Github hosting of Python script
##
################################################################################
################################################################################

from brewlytics import *

import json

from datetime import datetime

################################################################################
## FUNCTIONS
################################################################################

################################################################################
## MODEL DATA
################################################################################

utcnow = datetime.utcnow()
utcnow_str = utcnow.strftime('%d %B %Y at %H%MZ')

## brewlytics Python Script
md = json.loads(inputs.string)
email_body = inputs.list[1]

## Jupyter Notebook
# md = json.loads(inputs_string[0])
# email_body = inputs_string[1]
    
message = md['Message']
instance = md['brew Instance']

model_name = md['Model Name']
model_uuid = md['Model Id']

root_urls = {'Demo': 'https://demo.brewlytics.com/app/#/build/'}

url = root_urls[instance] + model_uuid

################################################################################
## BODY
################################################################################

result = email_body % (message,instance,url,model_name,model_uuid,utcnow_str,utcnow.strftime('%d %B %Y'))

################################################################################
## OUTPUTS
################################################################################

outputs.string = result
