import ner
import geonamescache
import unicodedata
from nltk import metrics
from collections import Counter
from scipy.stats import scoreatpercentile
import os

def makegeodict():
    geodict = {}
    values = geonamescache.GeonamesCache().get_cities().values()
    for value in values:
        city = value[u'name']
        city = unicodedata.normalize('NFD', city).encode('ascii', 'ignore')
        city = city.lower()
        if city == '':
            pass
        else:
            latlong = (float(value[u'latitude'].encode('ascii')), float(value[u'longitude'].encode('ascii')))
            geoid = value[u'geonameid'].encode('ascii')
            country = value[u'countrycode'].encode('ascii')
            if city in geodict:
                geodict[city].append((latlong, country, geoid))
            else:
                geodict[city] = [(latlong, country, geoid)]
    return geodict

def removedupes(seq):
    """ removes duplicate entries from list """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if x not in seen and not seen_add(x)]   

def fuzzysearch(geodict, givenloc):
    """ check if location is in geonames """
    fuzzymatch = []
    for loc in geodict:
        if metrics.edit_distance(loc, givenloc) <= 1:
            fuzzymatch.append(loc)
    return fuzzymatch   

def strip(doc):
    """ strips non-ASCII characters """
    content = ""
    with open(doc, 'r') as f:        
        for line in f:
            content += "".join(x for x in line if 31 < ord(x) < 127)
    return content
    
def locsent(content, locs):
    """ returns list of sentences containing location names """
    sentlist = []
    content = content.lower()
    content = content.replace(':', '.')
    content = content.replace(';', '.')
    for sentence in content.split('.'):
        for loc in locs:
            if loc in sentence:
                sentlist.append(sentence)
    return sentlist

# to use tagger must type into terminal in stanford-ner-2012-11-11 folder: 
# java -mx1000m -cp stanford-ner.jar edu.stanford.nlp.ie.NERServer -loadClassifier classifiers/english.muc.7class.distsim.crf.ser.gz -port 8080 -outputFormat inlineXML
def nerlocs(content):
    """ returns list of words tagged with 'LOCATION' by stanford NER """
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
    return removedupes(nerlocs)

def ingeonames(geodict, loclist):
    """ return list of locations found in geonames """
    geonamelocs = []
    for loc in loclist:
        name = fuzzysearch(geodict, loc)
        if name is not None:
            geonamelocs.extend(name)
    return removedupes(geonamelocs) 
    
def outliers(geodict, loclist):
    """ returns coordinate and country outliers """  
    # identifies country outliers
    outliers = []
    countrydict = {}
    for loc in loclist:
        i = 0
        n = len(geodict[loc])
        while i < n:
            country = geodict[loc][i][1]
            countrydict[country] = loc
            i += 1  
    countries = Counter(countrydict.keys()).most_common()
    i = 1
    if len(countries) > 1:
        while i < len(countries):
            outliers.append(countrydict[countries[i][0]])
            i += 1
    for x in removedupes(outliers):
        loclist.remove(x)
    
    # identifies coordinate outliers
    outliers = []
    latdict = {}
    londict = {}
    for loc in loclist:
        i = 0
        n = len(geodict[loc])
        while i < n:
            lat = geodict[loc][i][0][0]
            lon = geodict[loc][i][0][1]
            latdict[lat] = loc
            londict[lon] = loc
            i += 1      

    lat = latdict.keys()
    latQ1 = scoreatpercentile(lat, 25)
    latQ3 = scoreatpercentile(lat, 75)
    latIQR = latQ3 - latQ1
    latlower = latQ1 - (1.5 * latIQR)
    latupper = latQ3 + (1.5 * latIQR)
    for num in lat:
        if latlower <= num <= latupper:
            pass
        else:
            outliers.append(latdict[num])   
    
    lon = londict.keys()
    lonQ1 = scoreatpercentile(lon, 25)
    lonQ3 = scoreatpercentile(lon, 75)
    lonIQR = lonQ3 - lonQ1
    lonlower = lonQ1 - (1.5 * lonIQR)
    lonupper = lonQ3 + (1.5 * lonIQR)
    for num in lon:
        if lonlower <= num <= lonupper:
            pass
        else:
            outliers.append(londict[num])  
    
    for x in removedupes(outliers):
        loclist.remove(x)
    return loclist
    
def run(doclist):
    content = ""
    for doc in doclist:
        content += strip(doc)
        
    geodict = makegeodict()
    locs1 = nerlocs(content)
    print 'Locations from NER: ', locs1
    locs2 = ingeonames(geodict, locs1)
    print 'Locations from NER in GeoNames: ', locs2
    locs3 = outliers(geodict, locs2)
    print 'Locations with outliers eliminated: ', locs3
    sents = removedupes(locsent(content, locs3))
    
    print '\nFinal locations found:'
    print locs3
    print 'Sentences containing final locations found:'
    print sents
    
    orig_count = len(content.split())
    print 'Word count of original content: ', orig_count
    sent_count = 0
    for x in sents:
        sent_count += len(x.split())
    print 'Word count of output sentences: ', sent_count
    
    
if __name__ == "__main__":
    print '\nMove .txt formatted project documents to GeoHelper folder.'
    documents = []
    more = ''
    while more != 'n':
        doc = str(raw_input('\nEnter the document\'s full name: '))
        if os.path.isfile(doc) is False:
            print '\nMove document to GeoHelper folder. \nIf document already in folder, make sure spelling of document name matches.'
        elif doc.split('.')[1].lower() != 'txt':
            print '\nConvert your document to .txt format and try again. \nIf document already in .txt format, make sure its name ends in file extension .txt. If it doesn\'t, rename it to end in .txt.'
        else:
            documents.append(doc)
        more = str(raw_input('\nType Y if more documents to enter and N if all documents have been entered: ')).lower()
    print
    run(documents)