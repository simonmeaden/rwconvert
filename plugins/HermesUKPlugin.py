'''
Created on 5 Oct 2017

@author: Simon Meaden
'''
#import abc
#import string
from PyQt5.Qt import (
    QDialog,
    QLabel,
    QLineEdit,
    #QFrame,
    QGridLayout
    )
from convert_iplugin import ConvertInterface, AddressType, GAddress
from stringutil import StringUtil
import requests
from db.database import Database
from addressparser.addressparser import parser
import convert_iplugin

# constant values
PATHS = 'Paths'
FILES = 'Files'
FORMS = 'Forms'
NAMES = 'Names'

class StreetDialog(QDialog):

    def __init__(self, street, streetdata, notes, parent=None):
        super(StreetDialog, self).__init__(parent)
        self.setWindowTitle('My Form')
        self.street = street
        self.streetdata = streetdata
        self.notes = notes
        self.replacement = ''
        self.initGui()
        self.lat = 0.0
        self.lon = 0.0

    def initGui(self):
        l = QGridLayout()
        self.setLayout(l)

        self.setWindowTitle('Incorrect street name format')

        l.addWidget(QLabel('Original Street name'), 0, 0)
        l.addWidget(QLabel(self.street), 0, 1)
        l.addWidget(QLabel('Replacement Street name'), 1, 0)

        self.edit = QLineEdit(self.street)
        l.addWidget(self.edit)
        self.edit.textChanged.connect(self.repStreet)

    def repStreet(self, text):
        self.replacement = text


class HermesUKPlugin(ConvertInterface):
    '''
    classdocs
    '''

    search_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    details_url = 'https://maps.googleapis.com/maps/api/place/details/json'
    geocode_url = 'http://maps.googleapis.com/maps/api/geocode/json?'
    county_search_url = 'https://maps.googleapis.com/maps/api/geocode/json' #?address=Winnetka&key=YOUR_API_KEY
    config = {}


    def __init__(self, config, comms):
        '''
        Constructor
        '''
        super().__init__(config, comms)
        self.pluginname = 'Hermes (UK) manifest CSV Converter'
        self.plugindescription = ('Converts Hermes (UK) CSV manifest files into '
                                  ' a format that Road Warrior online Upload facility understands,'
                                  ' basically an Excel xlsx file.')
        self.filetypes = 'Manifest CSV Files (manifest*.csv)'

#         db = Database(self.config[PATHS]['db_path'], self.config[FILES]['db_name'])

    def parse_file(self,  fo):
        parser = parser(self.config[PATHS]['db_path'], self.config[FILES]['db_name'])
        lines = fo.readlines()
        data = []
        for line in lines:
            blocks = line.split(',')

            route = street = sender = info = user_info = phone = postcode = ''
            if len(blocks) > 0: postcode = blocks[0]
            # 1 & 2 are internal codes defining parcel type - not used here
            if len(blocks) > 3: name = StringUtil.titlecase(blocks[3])
            if len(blocks) > 4: street = blocks[4].strip()
            if len(blocks) > 5: phone = blocks[5].strip()
            if len(sender) > 6: sender = self.expandSender(blocks[6]) # the company/person sending the package - added to note
            if len(blocks) > 7: info = blocks[7]
            if len(blocks) > 8: route = blocks[8][3:6]
            if len(user_info) > 9: user_info = blocks[9]

            postcodevalid, postcode = RWAddressParser.validatePostcode(postcode)
            if not postcodevalid:
                # TODO some form of error checking and reporting
                continue
                #error = 'Error : Route={route}, Name={name}, Postcode={postcode} - Invalid postcode'.format(route=route, name=name, postcode = postcode)
               # self.comms.emit(error)
                #continue
            
            address = parser.parse(street, postcode, name)
            if address:
                notes = sender
                notes += ' : ' + info

                rowlist = []
                rowlist.append(address.address())     # should be number + street
                rowlist.append(address.city) # town/city
                rowlist.append(address.region2)       # County/State
                rowlist.append(postcode)     # post code
                rowlist.append(address.country)            # Country
                rowlist.append("1.0")              # Priority
                rowlist.append(phone)    # Phone number
                rowlist.append(StringUtil.chomp(notes))
                rowlist.append(address.lat)
                rowlist.append(address.lon)
                data.append(rowlist)
        self.m_rwdata[route] = data

    def expandSender(self, sender):
        if sender == 'AMAZ':
            return 'Amazon'
        elif sender == 'NEXT':
            return 'Next'
        else:
            return sender


    def getAddress(self, query):
        search_payload = {'key':'AIzaSyCAZVZOLgF4htpnLsAGkCZi7ygAsI7aFts', 'query':query}
        search_req = requests.get(self.search_url, params=search_payload)
        search_json = search_req.json()

        form_add = search_json['results'][0]['formatted_address']
        place_id = search_json['results'][0]['place_id']
        self.lat = search_json['results'][0]['geometry']['location']['lat']
        self.lon = search_json['results'][0]['geometry']['location']['lng']

        details_payload = {"key":'AIzaSyCAZVZOLgF4htpnLsAGkCZi7ygAsI7aFts', "placeid":place_id}
        details_resp = requests.get(self.details_url, params=details_payload)
        details_json = details_resp.json()

        self.region = details_json['result']['address_components'][3]['long_name']

        return form_add

    def getCounty(self, town):
        search_payload = {'key':'AIzaSyCAZVZOLgF4htpnLsAGkCZi7ygAsI7aFts', 'address':town}
        search_req = requests.get(self.search_url, params=search_payload)
        search_json = search_req.json()

        #         county = search_json[''][0]['formatted_address']
        county = ''

    #     details_payload = {'key':key, 'placeid':place_id}
    #     details_resp = requests.get(details_url, params=details_payload)
    #     details_json = details_resp.json()

    #     url = details_json['result']['url']
        return county


    def convert(self, filenames):
        '''
        actual conversion is done here
        '''
        self.rwdata = {} # empty rwdata
        for filename in filenames:
            fo = open(filename,  'r')
            self.parse_file(fo)
            fo.close()

