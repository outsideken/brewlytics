################################################################################
################################################################################
## brewlytics Utility
## Generic Error Notification
## Author:  outsideKen
## Created: 19 February 2022
## Updated: 07 May 2022
##
################################################################################
## CHANGE LOG
## 2022-02-19 - Original Code and Github hosting of Python script
## 2022-05-07 - Update script to better implement md JSON functionality
##
################################################################################
################################################################################

import json

from brewlytics import *
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

email_body = md['Email Template']
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
