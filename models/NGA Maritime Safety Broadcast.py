################################################################################
################################################################################
## NGA Maritime Safety Broadcast
##
## Author: outsideKen
## Created: 11 December 2020
## Updated: 07 May 2022
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
## 2022-05-07 - Added additional code to handle incomplete DTGs by imputing
##              current year if missing from the In Force DTG; added additional
##              handling if the In Force DTG regex pattern does not return
##              an expected string
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

## Reports are not consistently separated with a separating sub-string; using 
## the report DTG patten to separate joined reports
def check_for_multiple_reports(rpt):
    
    global message_dtg_regex
    
    dtgs = re.findall(message_dtg_regex,rpt)
    messages = [m.strip() for m in re.split(message_dtg_regex,rpt)
                if m != '']

    return ['%s%s' % tuple(z) for z in zip(dtgs,messages)]

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

def get_nav_id(rpt):
    
    global navarea_regex,hydro_regex
    
    if 'NAVAREA' in rpt:
        nav_id = re.findall(navarea_regex,rpt)[0]
    elif 'HYDRO' in rpt:
        nav_id = re.findall(hydro_regex,rpt)[0]
    else:
        nav_id = '---'
    
    return nav_id

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

def extract_dtg(rpt):
    
    global dtg_patterns
    
    dtg = re.findall(dtg_patterns,rpt,flags=re.IGNORECASE)
    if dtg:
        
        if (len(dtg[0]) == 11):
            
            dtg = '%s %s' % (dtg[0],now.strftime('%y'))
            
        elif (len(dtg[0]) == 14):
            
            dtg = dtg[0]
            
    ## If a valid/handled DTG format is not found return
    ## return an Error Notification
    else:
        
        dtg = pd.NaT
    
    return dtg

def get_cancellation_date(report):
    
    global cancel_dtg_pat

    cancel_dtg = re.findall(cancel_dtg_pat,report,flags=re.IGNORECASE)
    
    if not cancel_dtg:        
        cancel_dtg = [None]
        
    return cancel_dtg[0]

def find_vessels(rpt):
    
    ## Find M/V names in reports based on M/V tag
    vessels = list()
    if ('M/V' in rpt) and ('DERELICT' not in rpt) and ('PIRATES' not in rpt):
                      
        for tag in [' TOWING',' ALONG',' AND',' IN ',',']:
            mv = re.findall(r'M/V ([A-Z0-9\- ]*)' + tag,rpt)
                
            if mv:
                vessels += ['M/V %s' % ship_name for ship_name in mv]
            
    if not vessels :
        vessels = ['----']
        
    return vessels

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

iso8601 = '%Y-%m-%dT%H:%M:%S.%fZ'
now = datetime.utcnow()
now_str = now.strftime('%Y-%m-%d %H%MZ')

##------------------------------------------------------------------------------
## REGEX Patterns
##------------------------------------------------------------------------------

## Nav Id REGEX patterns
navarea_regex = r'(NAVAREA[A-Z0-9\/\(\) ]*).'
hydro_regex = r'(HYDRO[A-Z0-9\/\(\) ]*).'

## In Force DTG REGEX patterns with and without the year
dtg_patterns = r'[\d]{6}Z [A-Z]{3} [\d]{2}|[\d]{6}Z [A-Z]{3}'

## Message DTG REGEX pattern
message_dtg_regex = r'[\d]{6}Z [A-Z]{3} [\d]{2}\n'

## Message Cancel DTG REGEX pattern
cancel_dtg_pat = r'CANCEL THIS MSG ([\d]{6}Z [A-Z]{3} [\d]{2}).'

## Chart REGEX patterns
chart_pat1 = r'(CHART [\d]*)'
chart_pat2 = r'(DNC [\d]{2})'

## Latitude and Longitude REGEX patterns
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
             'KIRIBATI','CRETE','MAURITANIA','MARSHALL ISLANDS',
             'WALLIS AND FUTUNA',
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
               'M/V ASEAN PROTECTOR AN.': 'M/V ASEAN PROTECTOR AND',
               '. \nCANCEL THIS MSG': '. CANCEL THIS MSG',
               'RMKS/\nHYDROPAC 543/21(61).': 'RMKS/\n\nHYDROPAC 543/21(61).'}

################################################################################
## BODY
################################################################################

malformed_reports = set()
regions_found = set()
output = list()
for url_key,url in urls.items():

    print()
    print('Retrieving %s...' % url_key)
    print()
    
    ## Retrieve NGA Pacific/Atlantic Maritime Safety Broadcast
    r = requests.get(url)

    ##--------------------------------------------------------------------------
    ## Extract cleaned text report and segement into individual reports
    cleaned_text = re.sub(r'\r','',r.text)
    reports = [r for r in re.sub(r'. \n','.\n',cleaned_text).split('\n\n') 
               if r not in ['']]

    ##--------------------------------------------------------------------------
    for report in reports[3:]:

        ## Scrub text for corrections to enable clean regex extraction
        for key,val in corrections.items():
            report = report.replace(key,val)
        
        ## Find M/V names in reports based on M/V tag
        vessels = find_vessels(report)

        ## Extract Non-Regional (Exception Reports) and Regions from reports
        for exception in ['(NAIS)','COVID','PANDEMIC','IRIDIUM','WARNINGS IN FORCE']:

            parsed = report[:-3].split('.\n')
            
            if exception in report:
                
                region = exception
                
                print('- Exception Found: %s' % exception)
                
                break
                
            elif (len(parsed) > 2) and ('WARNINGS IN FORCE' not in report):

                region = re.sub(r'\n',' ',parsed[1])

                ## Set of regions found in the data
                regions_found.add(region)

            else:

                ## Set malformed_report = True to send notification email
                malformed_report_found = True

                malformed_reports.add(report)
                
        ## Extract geometries from safety reports
        points,tracklines,polygons = extract_geometries(report)
                
        output.append({'NAV Region': url_key,
                       'NAV Area': get_nav_id(report),
                       'Message DTG': extract_dtg(report),
                       'Cancellation DTG': get_cancellation_date(report),
                       'Region': region,
                       'Country': ','.join(get_country(report)),
                       'Chart': ','.join(get_charts(report)),
                       'Raw Report': report.strip(),
                       'Vessels': '; '.join(vessels),
                       'Points': points,
                       'Tracklines': tracklines,
                       'Polygons': polygons
                       })
    
odf = pd.DataFrame(output)

if malformed_report_found:
    
    print('Malformed/Unhandled NGA Maritime Safety Reports Encountered!')
    print('Preparing Notification email...')
    print()
    
    subject = 'Malformed/Unhandled NGA Maritime Safety Reports Encountered'
    
    poc = 'This automated brewlytics Notification was generated on %s.' % now.strftime('%d %B %Y @ %H%MZ')
    
    stub = '<h2><b>%s</b></h2>' % subject
    stub += '<hr>'
    
    for mal_rep in malformed_reports:
        
        for mr in mal_rep.split('\n'):
            stub += '''<p>%s</p>''' % mr
        stub += '<hr>'
        
    stub += '<hr>'
    stub += '<p><center>%s</center></p>' % poc
    
    email = {'To{string}': 'toedfish@yahoo.com',
             'CC{string}': 'toedfish@yahoo.com',
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
