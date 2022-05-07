################################################################################
################################################################################
## US CERT National Cyber Awareness System Alerts
## RSS Feed
## Author: outsideKen
## Created: 07 July 2020
## Updated: 07 May 2022
##
################################################################################
## CHANGE LOG
## 2020-07-07 - Initial code implementation in Brew
## 2020-07-08 - Modified output_table to include summary details only due to
##              encoding issues with the CSV to Table functional
## 2020-07-09 - Added HTML-formatted table to model data for output to Mission
##              Presenter
## 2020-07-10 - Implemented Subscriptions for notifications
## 2020-09-26 - Ported to Demo without Subscriptions; added ExcelWriter 
##              formatting for Excel output
## 2022-05-07 - Updated script to use the new brewlytics Define Python Script
##              functional
##
################################################################################

import json
import pandas as pd
import re
import requests

from brewlytics import *
from datetime import datetime

################################################################################
## FUNCTIONS

## Remove brewlytics CV Type substrings from column names
def remove_cv_type_substrings(df):
    return [column_names.split('{')[0] for column_names in df.columns]

##------------------------------------------------------------------------------
## Replace HTML Escaped text with weeble-readable text
def weeble(text):
    
    global replacements
    
    for key,val in replacements.items():
        text = re.sub(key,val,text)
        
    return text

##------------------------------------------------------------------------------
## Extract Published and Revised dates from Description
def find_dates(desc,pattern):
    
    date = re.findall(pattern,desc,flags=re.IGNORECASE)
    
    if date:
        publish = [d for d in date if d != ''][0]
    else:
        publish = '----'
        
    return publish

##------------------------------------------------------------------------------
## Add formatting to the output_resource Excel spreadsheet
def create_web_resource(df,filename,sheetname):
    
    global widths
        
    ## Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')

    ## Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(writer, sheet_name = sheetname, index = False)

    ## Get the xlsxwriter workbook and worksheet objects.
    workbook  = writer.book
    worksheet = writer.sheets[sheetname]

    ## Set the column widths of the output_table
    for column,width in widths.items():
        worksheet.set_column(column, width)

    ## Set the autofilter.
    worksheet.autofilter('A1:L%d' % len(df))

    ## Close the Pandas Excel writer and output the Excel file.
    writer.save()

    return

##------------------------------------------------------------------------------
## Unpacks a packed dictionary - creates a new dictionary with swapped
## key and value pairs
def unpack_dictionary(packed):
    
    unpacked = dict()
    for key,val in packed.items():
        for v in val:
            unpacked[v] = key
        
    return unpacked

################################################################################
## MODEL DATA

iso8601 = '%Y-%m-%dT%H:%M:%S.%fZ'
now = datetime.utcnow()
now_str = now.strftime(iso8601)

##------------------------------------------------------------------------------
## Model Data with model configuration
md = json.loads(inputs.string)

##------------------------------------------------------------------------------
## Weeble replacements
replacements = {'&lt;': '<',
                '&gt;': '>',
                '&amp;amp;': '&',
                '&nbsp;': ' '}

##------------------------------------------------------------------------------
## Correct column order of output_table
column_order = md['Output Table Column Order']
# column_order = ['Alert Id','Publish Date','Revision Date',
#                 'Title','Description','Summary','Link',
#                 'Date/Time Retrieved','USCERT URL']

##------------------------------------------------------------------------------
## Regex patterns
id_pat = r'<title>([A-Z0-9\-]*):'
publish_pat = r'date: ([a-z0-9 ,]*)[ |<]{1}'
revision_pat = r'revised: ([a-z0-9 ,]*)<br'

##------------------------------------------------------------------------------
## US CERT Logo URL
cert_logo = 'https://upload.wikimedia.org/wikipedia/commons/7/74/US-CERT_logo.png'

##------------------------------------------------------------------------------
## Configurations/Subscriptions
to_addressees = md['Addressees']

##------------------------------------------------------------------------------
## Set column widths for output_table
packed_widths = {12: ['A:A'],
                 20: ['B:B','C:C'],
                 25: ['D:D'],
                 30: ['E:E','F:F','H:H'],
                 40: ['G:G','I:I'],
                 75: ['D:D']}

widths = unpack_dictionary(packed_widths)

##------------------------------------------------------------------------------
## Create an empty EMAIL DF dataframe
email_df = pd.DataFrame([], columns = ['To','CC','Subject','Body'])

################################################################################
## BODY

## Remove brewlytics CV Type substrings from column names
df = inputs.table.copy()
inputs.table.columns = remove_cv_type_substrings(df)
alert_ids = set(df['Alert Id'].tolist())

##------------------------------------------------------------------------------
## Retrieve US CERT Alerts from RSS feed
url = md['US CERT System Alert URL']
r = requests.get(url)

## If data returned, parse to extract new alerts
add_to_repository = list()
if (r.status_code >= 200) and (r.status_code < 300):
    
    ## Segment
    rss_alerts = r.text.split('<item>')

    print('Successful retrieval of data!')
    print('There are %d items in this RSS update.' % (len(rss_alerts) - 1))
    
    ##--------------------------------------------------------------------------
    ## Extract US CERT Alerts from RSS results
    new_alerts = list()
    for alert in rss_alerts[1:]:
        
        ##----------------------------------------------------------------------
        ## Extract alert id from title text
        id_pat = r'<title>([A-Z0-9\-]*):'

        alert_id = re.findall(id_pat,alert)
        if alert_id:
            alert_data = {'Alert Id': alert_id[0].strip()}
        else:
            alert_data = {'Alert Id': 'Unidentified'}

        ##----------------------------------------------------------------------
        ## Extract Publish and Revision Dates
        publish_pat = r'date: ([a-z0-9 ,]*)[ |<]{1}'
        revision_pat = r'revised: ([a-z0-9 ,]*)<br'
        
        alert_data['Publish Date'] = find_dates(weeble(alert),publish_pat)
        alert_data['Revision Date'] = find_dates(weeble(alert),revision_pat)
            
        ##----------------------------------------------------------------------
        ## Extract Title, Link, and Description
        for tag in ['title','link','description']:

            pattern = '<%s>([\s\S]*?)</%s>' % (tag,tag)
            scrapped = re.findall(pattern,alert,flags = re.IGNORECASE)

            if scrapped:
                alert_data[tag.title()] = scrapped[0].strip()
            else:
                alert_data[tag.title()] = None

        ##----------------------------------------------------------------------
        ## Extract Summary
        summary = '<h3>Summary</h3>' + alert.split('<h3>Summary</h3>')[-1]
        alert_data['Summary'] = weeble(summary)
        
        ##----------------------------------------------------------------------
        ## Add provenance
        alert_data['Date/Time Retrieved'] = now_str
        alert_data['USCERT URL'] = url

        ########################################################################
        ##----------------------------------------------------------------------
        ## Check if new alerts are already in the repository; if not, add and 
        ## send email
        if alert_data['Alert Id'] not in alert_ids:
            
            add_to_repository.append(alert_data)
            
            print('New Alert published!! Sending Notification Email')
            
            h1 = '<h1><a href="%s" target="blank">%s</a></h1>'
            stub = '<img src="%s">' % cert_logo
            stub += h1 % (alert_data['Link'],alert_data['Title'])
            stub += alert_data['Summary']
            
            email = {'To': ','.join(to_addressees),
                     'CC': '',
                     'Subject': alert_data['Title'],
                     'Body': stub}
            
            md['Send Email'] = email

            email_df = pdDataFrame([email])

## If new alerts returned, add to repository
if add_to_repository:
    
    print('Adding new alerts to history ...')
    
    new_alerts = pd.DataFrame(add_to_repository)[column_order]
    tdf = pd.concat([input_table,new_alerts])[column_order]
    
    tdf.sort_values(by = 'Alert Id', ascending = False, inplace = True)
    
    tdf.reset_index(inplace = True)
    tdf.drop(['index'], axis = 1, inplace = True)
    
else:
    tdf = inputs.table.copy()

    
## Save as a instance local file for output_resource
filename = 'USCERT_Alerts.xlsx'
sheetname = 'US CERT Alerts'
create_web_resource(tdf,filename,sheetname)

##------------------------------------------------------------------------------
## Create HTML-formatted table of all US-CERT Alerts for Mission Presenter 
## IFrame
headers = ['Alert Id','Publish Date','Revision Date','Title']

href = '<a href="%s" target="blank">%s</a>'

stub = '<img src="%s">' % cert_logo
stub += '''
<h1><font color="#003366">US-CERT National Cyber Awareness System Alerts</font></h1>
<hr>
<table style="width:100%">
  <colgroup>
    <col span="1" style="width: 10%;">
    <col span="1" style="width: 15%;">
    <col span="1" style="width: 15%;">
    <col span="1" style="width: 60%;">
  </colgroup>'''

stub += '''  <tr>%s</tr>''' % ''.join(['<th>%s</th>' % column_name 
                                       for column_name in headers])

for idx in tdf.index:
    row = tdf.loc[idx]
    values = ''.join(['<td>%s</td>' % row[column_name] 
                      for column_name in headers[:-1]])
                     
    values += '<td>%s</td>' % (href % (row['Link'],row['Title']))
    stub += '''<tr>%s</tr>''' % values
#     stub += '''<tr><td>%s</td></tr>''' % row['Description']
stub += '</table><hr>'

md['Summary Table'] = stub

################################################################################
## OUTPUTS

outputs.resource = filename

outputs.table = email_df

outputs.string = json.dumps(md['Summary Table'])

################################################################################
## SUMMARY
