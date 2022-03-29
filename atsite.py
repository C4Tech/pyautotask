#!/usr/bin/python3.9
"""
Python package to interact with Autotask API
"""
import shutil
import time
import warnings
import json
import logging
import requests



"""For testing purposes:
logging.basicConfig(filename='pyunifi.log', level=logging.WARN,
                    format='%(asctime)s %(message)s')
"""  # pylint: disable=W0105
CONS_LOG = logging.getLogger(__name__)


class APIError(Exception):
    """API Error exceptions"""


class atSite:

    """Interact with a Autotask API.

	All this is stolen from pyUnifi. Any cleverness in this code is from them,
	any mistakes are my own.

	Will attempt to fix this example when I understand the code better
    >>> from unifi.controller import Controller
    >>> c = Controller('192.168.1.99', 'admin', 'p4ssw0rd')
    >>> for ap in c.get_aps():
    ...     print 'AP named %s with MAC %s' % (ap.get('name'), ap['mac'])
    ...
    AP named Study with MAC dc:9f:db:1a:59:07
    AP named Living Room with MAC dc:9f:db:1a:59:08
    AP named Garage with MAC dc:9f:db:1a:59:0b

    """

    def __init__(  # pylint: disable=r0913
            self,
            host,
            username,
            password,
			interactioncode
    ):
        """
        :param host: the site you are hosted on
        :param username: api user created within Autotask
        :param password: api password created within Autotask
        :param interactioncode: API Interactioncode you get from within Autotask
        """

        self.log = logging.getLogger(__name__ + ".atSite")

        self.host = host
        self.headers = {'ApiIntegrationCode' : interactioncode, 'UserName' : username, 'Secret' : password}
        self.username = username
        self.password = password
        self.interactioncode = interactioncode
        self.url = "https://" + host + "/ATServicesRest/V1.0/"
		# I don't think we need an auth url
		#self.auth_url = self.url + "api/login"

        self.log.debug("Controller for %s", self.url)
        #self._login()
        self.session = requests.Session()

	# This looks like an error detection fuction for returning data.
	# need to adjust to fix AT
    @staticmethod
    def _jsondec(data):
        obj = json.loads(data)
        if "errors" in obj:
            raise APIError(obj["errors"])
# TODO Have to deal with multipages
#'pageDetails': {'count': 500, 'requestCount': 500, 'prevPageUrl': None, 'nextPageUrl': 'https://webservices15.autotask.net/ATServicesRest/V1.0/Companies/query/next?paging=%7b%22pageSize%22%3a500%2c%22previousIds%22%3a%5b-1%5d%2c%22nextIds%22%3a%5b725%5d%7d&search=%7b%27filter%27%3a%5b%7b%27op%27%3a%27exist%27%2c%27field%27%3a%27IsActive%27%7d%5d%7d'}}
#        if "pageDetails" in obj:
#                raise APIError(obj["pageDetails"]["nextPageUrl"])
        if "items" in obj:
            result = obj["items"]
        else:
            result = obj

        return result

    # This section is more direct API calls

    def _read(self, url):
        # Try block to handle the unifi server being offline.
        response = self.session.get(url, headers=self.headers)
        return self._jsondec(response.text)

    def _api_read(self, url):
        return self._read(self.url + url)

    def _write(self, url, params=None):
        response = self.session.post(url, data=params, headers=self.headers)
        return self._jsondec(response.text)

    def _api_write(self, url, params=None):
        return self._write(self.url + url, params)
        
    def _update(self, url, params=None):
        response = self.session.patch(url, data=params, headers=self.headers)
        return self._jsondec(response.text)

    def _api_update(self, url, params=None):
        return self._update(self.url + url, params)


# Deprecated fuction
    def _api_active(self,url):
        return self._api_read(url + "/query?search={'filter':[{'op':'eq','field':'isActive','value': '1'}]}")

    def create_query(self, url, filter_fields, include_fields):
        if filter_fields is None:
            filter_fields = "{'op':'eq','field':'isActive','value': '1'}"
        if include_fields is None:
            return self._api_read(url + "/query?search={'filter':[" + filter_fields + "]}")
        # Need to make something that can deal with the IncludeFields
#        else:
#            return self._api_read(url + "/query?search={'IncludeFields': [" + include_fields + "], 'filter':" + filter_fields + "}")
    def create_filter(self, op, field, value, udf = None):
        if udf is None:
            filter_fields = "{'op': '" + op + "', 'field': '" + field + "', 'value': '" + value + "'}"
        else:
            filter_fields = "{'op': '" + op + "', 'field': '" + field + "', 'udf': true, 'value': '" + value + "'}"
        return filter_fields



    # end user fuctions
    def get_companies(self,filter_fields = None, include_fields = None):
        """Return a list of all active Companies"""
        return self.create_query("Companies", filter_fields, include_fields)
        
    def get_products(self):
        """Return a list of all active Products"""
        return self._api_active("Products")

    def get_cis(self, filter_fields = None, include_fields = None):
        """Return a list of all ConfigurationItems"""
        return self.create_query("ConfigurationItems", filter_fields, include_fields)
    def get_ci_types(self):
        """Return a list of all active ConfigureationItem Types"""
        return self._api_active("ConfigurationItemTypes")
    def get_ci_udf(self,filter_fields = None, include_fields = None):
        """Return a list of all active ConfigureationItems User Defined Fields"""
        return self._api_read("ConfigurationItems/entityInformation/userDefinedFields")


    def get_all_todos(self):
        """Return a list of all Appointments, past, present and future"""
        return self._api_read("Appointments" + "/query?search={'filter':[{'op':'exist','field':'startDateTime'}]}")
    def get_alerts(self):
        """Return a list of all Alerts for Companies"""
        return self._api_read("CompanyAlerts" + "/query?search={'filter':[{'op':'exist','field':'id'}]}")



    def add_ci(self, ci_cat, cid, ci_type, pid, name, ip, serial, udf):
        # TODO add notes for "returns"
        """Add a ci to a Company
        :param ci_cat: configurationItemCategoryID in Autotask
        :param cid: companyID in Autotask
        :param ci_type: configurationItemType in Autotask
        :param pid: productID in Autotask
        :param name: referenceTitle in Autotask
        :param ip: ip address of the CI in Autotask
        :param serial: serialNumber in Autotask
        :param udf: Defnition of User Defind Fields in Autotask
        :returns: Unknown as of yet         
        """
        params = {
            'configurationItemCategoryID': ci_cat,
            'companyID': cid, 
            'configurationItemType': ci_type,
            'isActive': True,
            'productID': pid,
            'referenceTitle': name,
            'serialNumber': serial,
# TODO when attempting to push User Definded Fields AT comes back with 'Object reference not set to an instance of an object. Need to figure out why this is happening and fix it.
#            'userDefinedFields': udf
            }

        #check if device already is in AT. Create a new CI if new. Update if it already in AT
        op = "eq"
        field = "serialNumber"
        value = serial
        filter_field = self.create_filter(op, field, value)
        response = self.get_cis(filter_field)

        # TODO The following will return an item with a item number if it works. We should check it or errors. example {'itemId': 1426}
        if not response:
            return self._api_write("ConfigurationItems", params)
        else:
            # TODO to be a little friendly on AT, we could compare everything and only push an update if things change.
            params_id = {'id': response[0]['id']}
            params.update(params_id)
            return self._api_update("ConfigurationItems", params)
        
        


