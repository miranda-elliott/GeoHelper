#
# geohelper.py
#
# Author: Miranda Elliott
#
# Date: 8/18/2014
#
# Extracts locations from foreign aid project documents and finds their matches in GeoNames and sentences throughout the document corpus mentioning these location matches.
# Designed to increase geocoding efficiency at AidData.
#

import ner
import unicodedata
from nltk import metrics
from collections import Counter
from scipy.stats import scoreatpercentile
import os
import urllib
import xml.etree.ElementTree as ET


''' HELPER LIST METHODS '''

def removeDuplicatesAdv(values):
    ''' returns given list of lists with removed duplicates ''' 
    output = []
    seen = set()
    valueID = [x[0] for x in values]
    i = 0
    for id in valueID:
        if id not in seen:
            output.append(values[i])
            seen.add(id)
        i += 1
    return output

def removeDuplicatesSimp(values):
    ''' returns given list with removed duplicates '''
    seen = set()
    seen_add = seen.add
    return [x for x in values if x not in seen and not seen_add(x)]

def getNames(loclist):
    ''' return location names from location information list '''
    return [x[0] for x in loclist]


''' EXTRACT LOCATIONS FROM DOCUMENTS ''' 

def strip(doc):
    ''' strips non-ASCII characters '''
    content = ""
    with open(doc, 'r') as f:        
        for line in f:
            content += "".join(x for x in line if 31 < ord(x) < 127)
    return content

# to use tagger must type into terminal in stanford-ner-2014-01-04 folder: 
# java -mx1000m -cp stanford-ner.jar edu.stanford.nlp.ie.NERServer -loadClassifier classifiers/english.muc.7class.distsim.crf.ser.gz -port 8080 -outputFormat inlineXML
def mineLocs(content):
    ''' returns list of words tagged with 'LOCATION' by stanford NER '''
    tagger = ner.SocketNER(host = 'localhost', port = 8080)  
    loclist = []
    sentence = ""
    for char in content: 
        if char == ".":
            sentence += "."
            tagsent = tagger.get_entities(sentence)
            if u'LOCATION' in tagsent:
                loclist.extend(tagsent[u'LOCATION'])
            sentence = ""
        else:
            sentence += char
    nerlocs = [unicodedata.normalize('NFD', x).encode('ascii', 'ignore').lower() for x in loclist]
    # or x.encode('ascii').lower()
    return removeDuplicatesSimp(nerlocs)


''' FIND LOCATION MATCHES IN GEONAMES ''' 

def appendInfo(XMLtag, tree, matches):
    ''' returns matches list with added field of information for given tag '''
    i = 0
    for elem in tree.iter(tag = XMLtag):
        matches[i].extend([elem.text])
        i+=1
    return matches

def extractFromXML(url):
    ''' returns information from geonames API XML doc at given URL '''
    matches = []
    tree = ET.parse(urllib.urlopen(url))
    for elem in tree.iter(tag='toponymName'):
        name = elem.text
        matches.append([name.encode('ascii', 'ignore').lower()])
    matches = appendInfo('lat', tree, matches)
    matches = appendInfo('lng', tree, matches)
    matches = appendInfo('countryCode', tree, matches)
    matches = appendInfo('fcode', tree, matches)
    matches = appendInfo('geonameId', tree, matches)
    return matches
        
def getLocData(name):
    ''' returns geonames matches for given location '''
    url = "http://api.geonames.org/search?name_equals=" + name + "&username=dnicholson"
    matches = extractFromXML(url)
    if len(matches) == 0:
        url = "http://api.geonames.org/search?q=" + name + "&fuzzy=0.8" + "&username=dnicholson"
        fuzzyMatches = extractFromXML(url)
        if (len(matches) == 0) and (len(fuzzyMatches) == 0):
            return None
        else:
            return removeDuplicatesAdv(matches + fuzzyMatches)
    else:
        return removeDuplicatesAdv(matches)

def getGeonamesMatches(loclist):
    ''' returns list of location matches found in geonames '''
    geonameLocs = []
    for loc in loclist:
        matches = getLocData(loc)
        if matches is not None:
            geonameLocs.extend(matches)
    return removeDuplicatesAdv(geonameLocs)

    
def sentsContaining(content, locs):
    ''' returns list of sentences containing location names '''
    sentlist = []
    content = content.lower()
    content = content.replace(':', '.')
    content = content.replace(';', '.')
    for sentence in content.split('.'):
        for loc in locs:
            if loc in sentence:
                sentlist.append(sentence)
    return sentlist


''' IDENTIFY AND ELIMINATE GEOGRAPHIC OUTLIERS '''

def findCountryOutliers(loclist):
    ''' returns identified country outliers '''
    outliers = []
    countryList = []
    for loc in loclist:
        i = 0
        n = len(loclist)
        while i < n:
            country = loclist[i][3]
            countryList.append(country)
            i += 1
    countryFreq = Counter(countryList).most_common()  
    j = 0
    if len(countryFreq) > 1:
        for entry in countryFreq:
            i = 0
            if j != 0:
                while i < len(loclist):
                    if entry[0] == loclist[i][3]:
                        outliers.append(loclist[i])
                    i += 1
            j += 1
    return outliers

def findCoordOutliers(loclist, coord):
    ''' returns identified coordinate outliers '''
    outliers = []
    coordDict = {}
    cIndex = 0
    if coord == 'lat':
        cIndex = 1
    if coord == 'lng':
        cIndex = 2
    for loc in loclist:
        i = 0
        n = len(loclist)
        while i < n:
            coordVal = float(loclist[i][cIndex])
            coordDict[coordVal] = loc
            i += 1      

    coordList = coordDict.keys()
    Q1 = scoreatpercentile(coordList, 25)
    Q3 = scoreatpercentile(coordList, 75)
    IQR = Q3 - Q1
    lower = Q1 - (1.5 * IQR)
    upper = Q3 + (1.5 * IQR)
    for num in coordList:
        if lower <= num <= upper:
            pass
        else:
            outliers.append(coordDict[num])   
    return outliers
    
def eliminateOutliers(loclist):
    ''' returns loclist with deleted country and coordinate outliers '''
    outliers = []
    outliers.extend(findCountryOutliers(loclist))
    outliers.extend(findCoordOutliers(loclist, 'lat'))
    outliers.extend(findCoordOutliers(loclist, 'lng'))
 
    for x in removeDuplicatesAdv(outliers):
        loclist.remove(x)
    return loclist


''' RUN MAIN PROGRAM '''

def run(doclist):
    content = ""
    for doc in doclist:
        content += strip(doc)
        
    locs1 = mineLocs(content)
    print('Locations from NER: ', locs1)
    locs2 = getGeonamesMatches(locs1)
    locs2_names = getNames(locs2)
    print('Locations from NER in GeoNames: ', locs2_names)
    locs3 = eliminateOutliers(locs2)
    locs3_names = getNames(locs3)
    print('Locations with outliers eliminated: ', locs3_names)
    sents = removeDuplicatesSimp(sentsContaining(content, locs3_names))
    
    print('\nFinal locations found:\n', locs3)
    print('Sentences containing final locations found:\n', sents)
    
    orig_count = len(content.split())
    print('Word count of original content: ', orig_count)
    sent_count = 0
    for x in sents:
        sent_count += len(x.split())
    print('Word count of output sentences: ', sent_count)
    

''' GET USER INPUT '''

if __name__ == "__main__":
    print('\nMove .txt formatted project documents to GeoHelper folder.')
    documents = []
    more = ''
    while more != 'n':
        doc = str(raw_input('\nEnter the document\'s full name: '))
        if os.path.isfile(doc) is False:
            print('\nMove document to GeoHelper folder. \nIf document already in folder, make sure spelling of document name matches.')
        elif doc.split('.')[1].lower() != 'txt':
            print('\nConvert your document to .txt format and try again. \nIf document already in .txt format, make sure its name ends in file extension .txt. If it doesn\'t, rename it to end in .txt.')
        else:
            documents.append(doc)
        more = str(raw_input('\nType Y if more documents to enter and N if all documents have been entered: ')).lower()
    run(documents)
