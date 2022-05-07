###########################################################################
## NGA Maritime Safety Broadcast
##
## Author: outsideKen
## Created: 11 December 2020
## Updated: 04 May 2022
##
################################################################################
################################################################################
## CHANGE LOG
## 2020-12-11 - Original script
## 2020-12-12 - Added Linestring geometries
## 2020-12-15 - Added Multigeometries
## 2020-12-16 - Cleaned up and streamline code
## 2020-12-21 - Added additiobal exception keywords
## 2021-01-13 - Added correction for bad raw data which caused MULTIPOLYGON
##              errors downstream in the model
## 2021-01-14 - Added partial extraction of M/V names from reports for tracking
##              and dashboard visualization purposes
## 2021-02-11 - Updated error corrections for malformed report
## 2022-05-04 - Handle malformed reports without throwing an error; Send 
##              malformed reports to model owner for alerting purposes
##              - also update to use the new brewlytics Define Python Script
##                functional
##
################################################################################
################################################################################

import pandas as pd
import re
import requests

from brewlytics import *
from datetime import datetime

################################################################################
## FUNCTIONS
################################################################################

def get_latlons(report):
    
    global lat_pat,lon_pat
    
    lats = [convert2dd(l) for l in re.findall(lat_pat,report)]
    lons = [convert2dd(l) for l in re.findall(lon_pat,report)]
    
    return lats,lons

def convert2dd(ll):
    
    ## Degrees-DecimalMinutes
    if ll.count('-') == 1:
        d,m = ll[:-1].split('-')
        dd = float(d) + float(m)/60.0
        
    ## Degrees-Minutes-Seconds
    else:
        d,m,s = ll[:-1].split('-')
        dd = float(d) + float(m)/60.0 + float(s)/3600.0
        
    if ('S' in ll) or ('W' in ll):
        dd *= -1
        
    return dd

def get_charts(report):
    
    global chart_pat1,chart_pat2
    
    if 'CHART' in report:
        charts = {c for c in re.findall(chart_pat1,report) if c not in ['','-']}
    elif 'DNC ' in report:
        charts = {c for c in re.findall(chart_pat2,report) if c not in ['','-']}
    else:
        charts = set() #'----'
        
    return charts

def get_country(report):
    
    global countries
    
    country = set()
    for c in countries:
        
        if c in report:
            
            country.add(c)
        
    return sorted(country)

def get_cancellation_date(report):
    
    global cancel_dtg_pat

    cancel_dtg = re.findall(cancel_dtg_pat,report,flags=re.IGNORECASE)
    if cancel_dtg:        
        cancelation_date = datetime.strptime(cancel_dtg[0],'%d%H%MZ %b %y')
    else:
        cancelation_date = None #'----'
        
    return cancelation_date

def extract_geometries(report):
    
    global lat_pat,lon_pat

    ## Set valid null geometries
    multipoint = 'MULTIPOINT EMPTY'
    multilinestring = 'MULTILINESTRING EMPTY'
    multipolygon = 'MULTIPOLYGON EMPTY'
        
    ## Format report to a single line by removing all whitespace characters
    ## and multiple consecutive spaces
    single_line = re.sub(r'\s+',' ',report)
    
    ## Segment single-line report by numbered paragraphs and 
    ## lettered-sub-paragraphs
    segmented_paragraphs = re.split(r' [1-9A-Z]{1}[.]{1} ',single_line)

    ## Extract Points as MULTIPOINTs
    if ('TRACKLINE' not in single_line) and ('BOUND B' not in single_line) and ('(NAIS)' not in single_line):    
        
        ## Use regex to extract patterns matching latitude and longitude
        lats,lons = get_latlons(single_line)
        
        ## Check for paired coordinate extraction
        if (lats) and len(lats) == len(lons):
            
            ## Add coordinates to a list of points
            points = ['(%f %f)' % tuple(z) for z in zip(lons,lats)]
            
            ## Create a valid MULTIPOINT geometry
            multipoint = 'MULTIPOINT(%s)' % (','.join(points))
     
    ## Extract Tracklines as MULTILINESTRINGS
    if 'TRACKLINE' in single_line:

        ## Check for multiple linestrings
        linestrings = list()
        
        ## Segment into numbered and lettered paragraphs and sub-paragraphs
        for paragraph in segmented_paragraphs:

            ## Use regex to extract patterns matching latitude and longitude
            lats,lons = get_latlons(paragraph)

            ## Test for valid linestring geometry
            if (lats) and (lons) and (len(lats) >= 2):
                
                points = ['%f %f' % tuple(z) for z in zip(lons,lats)]
                
                linestrings.append('(%s)' % ','.join(points))

        multilinestring = 'MULTILINESTRING(%s)' % ','.join(linestrings)

    ## Extract Areas Bound as MULTIPOLYGONS
    ## Check for keyword identified polygon data in report
    if re.findall(r'BOUND B[Y]?',single_line):
        
        ## Check for multiple polygons 
        polygons = list()

        ## Segment into numbered and lettered paragraphs and sub-paragraphs
        for paragraph in segmented_paragraphs:

            ## Use regex to extract patterns matching latitude and longitude
            lats,lons = get_latlons(paragraph)

            ## Test for valid polygon geometry
            if (lats) and (lons) and (len(lats) >= 3):

                ## Close the polygon
                lats += [lats[0]]
                lons += [lons[0]]
                                   
                points = ['%f %f' % tuple(z) for z in zip(lons,lats)]

                polygons.append('((%s))' % ','.join(points))

        multipolygon = 'MULTIPOLYGON(%s)' % ','.join(polygons)

    return multipoint,multilinestring,multipolygon

################################################################################
## MODEL DATA
################################################################################

now = datetime.utcnow()
now_str = now.strftime('%Y-%m-%d %H%MZ')

##------------------------------------------------------------------------------
## REGEX Patterns
##------------------------------------------------------------------------------

iso_format = '%Y-%m-%dT%H:%M:%S.%fZ'
dtg_pat = r'[\d]{6}Z [A-Z]{3} [\d]{2}'
cancel_dtg_pat = r'CANCEL THIS MSG ([\d]{6}Z [A-Z]{3} [\d]{2}).//'

chart_pat1 = r'(CHART [\d]*)'
chart_pat2 = r'(DNC [\d]{2})'

lat_pat = r'[\d]{1,2}-[\d\-.]{1,}[\d]{1}[NS]{1}'
lon_pat = r'[\d]{1,3}-[\d\-.]{1,}[\d]{1}[WE]{1}'

##------------------------------------------------------------------------------
## Countries,States and Regions
##------------------------------------------------------------------------------

countries = ['MEXICO','COLOMBIA','ECUADOR','EL SALVADOR','JAMAICA','GUYANA',
             'GRENADA','CANADA','FRANCE','ITALY','SPAIN','MOROCCO','TUNISIA',
             'FRENCH GUIANA','TOBAGO','TRINIDAD','SURINAME','VENEZUELA',
             'CALIFORNIA','ALASKA','TEXAS','FLORIDA','LOUISIANA','ECUADOR',
             'LABRADOR SEA','WESTERN SAHARA','ENGLAND','ANTARCTICA','BRAZIL',
             'SCOTLAND','ALGERIA','EGYPT','ISRAEL','CYPRUS','LEBANON','SYRIA',
             'TURKEY','LIYBA','NORWAY','MALTA','NETHERLANDS','GREENLAND',
             'DENMARK','SWEDEN','FINLAND','RUSSIA','BERMUDA','AZORES',
             'ISLE OF MAN','GABON','UKRAINE','ROMANIA','GREECE','NEW CALEDONIA',
             'NEW ZEALAND','AUSTRALIA','CHINA','VIETNAM','INDIA','GUAM',
             'INDONESIA','U.A.E.','PHILIPPINES','SOUTH KOREA','ADAMAN ISLANDS',
             'PERU','CHILE','PAKISTAN','IRAN','SRI LANKA','KUWAIT','QATAR',
             'BAHRAIN','ISLA DE PASCUA','JAPAN','FIJI','MOZAMBIQUE','TAHITI',
             'IRAQ','SAUDI ARABIA','FRENCH POLYNESIA','NIUE','SAMOA','SUDAN',
             'SOMALIA','KENYA','TANZANIA','SOUTH AFRICA','COMOROS (MAYOTTE)',
             'KIRIBATI','CRETE','MAURITANIA','MARSHALL ISLANDS','WALLIS AND FUTUNA',
             ]

##------------------------------------------------------------------------------
## NGA Maritime Safety Information URLs
##------------------------------------------------------------------------------

## Pacific
pacific_url = 'https://msi.nga.mil/api/publications/download?type=view&key=16694640/SFH00000/DailyMemXII.txt'
hydropac = 'https://msi.nga.mil/api/publications/download?type=view&key=16694640/SFH00000/DailyMemPAC.txt'

## Atlantic
atlantic_url = 'https://msi.nga.mil/api/publications/download?type=view&key=16694640/SFH00000/DailyMemIV.txt'
hydrolant_url = 'https://msi.nga.mil/api/publications/download?type=view&key=16694640/SFH00000/DailyMemLAN.txt'

## Arctic
hydroarc_url = 'https://msi.nga.mil/api/publications/download?type=view&key=16694640/SFH00000/DailyMemARC.txt'

urls = {'Pacific': pacific_url,
        'HYDROPAC': hydropac,
        
        'Atlantic': atlantic_url,
        'HYDROLANT': hydrolant_url,
       
        'HYDROARC': hydroarc_url}

##------------------------------------------------------------------------------
## Malformed Report Found Boolean - Send Notification containing malformed
## reports
##------------------------------------------------------------------------------

malformed_report_found = False

##------------------------------------------------------------------------------
## Colors
##------------------------------------------------------------------------------

packed_colors = {'#cb181d': ['SPACE DEBRIS','ROCKET']}

##------------------------------------------------------------------------------
## Corrections
##------------------------------------------------------------------------------

corrections = {'JOINING\n': 'JOINING ',
               '14-42N 110-42': '14-42N 110-42E',
               '20-18S 038-50.': '20-18S 038-50W.',
               'RACON AT VERAVAL ROADS 20-54-41N 070-21-11.': 'RACON AT VERAVAL ROADS 20-54-41N 070-21-11E.',
               'VALPARAISO (B) 32-48.4S 071-29.2.': 'VALPARAISO (B) 32-48.4S 071-29.2W.',
               'NAVTEX STATION GUAM (V) 13-28.6N 144-50.1.': 'NAVTEX STATION GUAM (V) 13-28.6N 144-50.1E.',
               'CAP DE LA HAGUE LIGHT 49-43.3N 001-57.3.': 'CAP DE LA HAGUE LIGHT 49-43.3N 001-57.3E.',
               'DUE TO ENGINE FAILURE IN 13-11N 110-56.': 'DUE TO ENGINE FAILURE IN 13-11N 110-56E.',
               'DART BUOY ADRIFT IN VICINITY 19-48S 172-00': 'DART BUOY ADRIFT IN VICINITY 19-48S 172-00W',
               '24-15.52E 052-00.53E': '24-15.52N 052-00.53E',
               'M/V ASEAN PROTECTOR AN.': 'M/V ASEAN PROTECTOR AND'}

################################################################################
## BODY
################################################################################

malformed_reports = set()
regions_found = set()
output = list()
for key,url in urls.items():

    ## Retrieve NGA Pacific/Atlantic Maritime Safety Broadcast
    r = requests.get(url)

    ##--------------------------------------------------------------------------
    ## Extract cleaned text report and segement into individual reports
    cleaned_text = re.sub(r'\r','',r.text)
    reports = [r for r in re.sub(r'. \n','.\n',cleaned_text).split('\n\n') 
               if r not in ['']]

    ##--------------------------------------------------------------------------
    ## Extract Broadcast DTG from the first report of the broadcast
    dtg = re.findall(dtg_pat,reports[0],flags=re.IGNORECASE)
    if dtg:
        if_date = datetime.strptime(dtg[0],'%d%H%MZ %b %y')

    ##--------------------------------------------------------------------------
    for report in reports[3:]:

        ## Scrub text for corrections to enable clean regex extraction
        for key,val in corrections.items():
            report = report.replace(key,val)
        
        ## Find M/V names in reports based on M/V tag
        vessels = list()
        if ('M/V' in report) and ('DERELICT' not in report) and ('PIRATES' not in report):
                      
            for tag in [' TOWING',' ALONG',' AND',' IN ',',']:
                mv = re.findall(r'M/V ([A-Z0-9\- ]*)' + tag,report)
                
                if mv:
                    vessels += ['M/V %s' % ship_name for ship_name in mv]
            
        if not vessels :
            vessels = ['----']
                
        parsed = report[:-3].split('.\n')

        nav_id = parsed[0]

        ## Extract Regions from report
        for exception in ['(NAIS)','COVID','PANDEMIC','IRIDIUM','WARNINGS IN FORCE']:
            if exception in report:
                
                region = exception
                
                print('Exception Found: %s' % exception)
                print()
                
                break
                
            elif (len(parsed) > 2) and ('WARNINGS IN FORCE' not in parsed[1]):
                
                region = re.sub(r'\n',' ',parsed[1])
                
                ## Set of regions found in the data
                regions_found.add(region)
                
            else:
                
                ## Set malformed_report = True to send notification email
                malformed_report_found = True
                
                malformed_reports.add(report)
                
        ## Extract geometries from safety reports
        points,tracklines,polygons = extract_geometries(report)
                
        output.append({'NAV Area': nav_id,
                       'Message DTG': dtg[0],
                       'In Force Date': if_date,
                       'Cancellation Date': get_cancellation_date(report),
                       'Region': region,
                       'Country': ','.join(get_country(report)),
                       'Chart': ','.join(get_charts(report)),
#                        'Narrative': '----',
                       'Raw Report': report.strip(),
                       'Vessels': '; '.join(vessels),
                       'Points': points,
                       'Tracklines': tracklines,
                       'Polygons': polygons
                       })
    
odf = pd.DataFrame(output)

if malformed_report_found:
    
    print('Malformed NGA Maritime Safety Reports Encountered!')
    print('Preparing Notification email...')
    print()
    
    subject = 'Malformed NGA Maritime Safety Reports Encountered'
    
    poc = 'This automated brewlytics Notification was generated on %s.' % now.strftime('%d %B %Y @ %H%MZ')
    
    stub = '<h2><b>%s</b></h2>' % subject
    stub += '<hr>'
    
    for rep in malformed_reports:
        
        for r in rep.split('\n'):
            stub += '''<p>%s</p>''' % r
        stub += '<hr>'
        
    stub += '<hr>'
    stub += '<p><center>%s</center></p>' % poc
    
    email = {'To{string}': inputs.string,
             'CC{string}': inputs.string,
             'Subject{string}': subject,
             'Body{string}': stub}

    notification = pd.DataFrame([email])
    
else:
    
    notification = pd.DataFrame([], columns = ['To{string}','CC{string}','Subject{string}','Body{string}'])

################################################################################
## OUTPUTS
################################################################################

##------------------------------------------------------------------------------
## OUTPUTS.RESOURCE
##------------------------------------------------------------------------------

filename = 'Notifications.csv'
notification.to_csv(filename, index = False)
outputs.resource = filename

##------------------------------------------------------------------------------
## OUTPUTS.TABLE
##------------------------------------------------------------------------------

outputs.table = odf
