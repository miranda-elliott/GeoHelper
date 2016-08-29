# GeoHelper

Extracts locations from foreign aid project documents and finds their matches in GeoNames and sentences throughout the document corpus mentioning these location matches.

Designed to increase geocoding efficiency at AidData.


## Dependencies

You must have the following libraries installed in Python to use GeoHelper:

* [Stanford Named Entity Recognizer](https://pypi.python.org/pypi/ner/)
* [Natural Language Toolkit](http://www.nltk.org/)
* [SciPy](https://www.scipy.org/)

## Usage example

Within this repository, run the following command on the project document you'd like to geocode. The document must be in txt format. I've included a few example documents titled ISDS1.txt, ISDS2.txt, PID1.txt, and PID2.txt, so I'll use ISDS1.txt in this example. 

```sh
python geohelper.py ISDS1.txt
```