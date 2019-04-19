from .auth import E3DBAuth
import os
if 'CRYPTO_SUITE' in os.environ and os.environ['CRYPTO_SUITE'] == 'NIST':
    from .nist_crypto import NistCrypto as Crypto
else:
    from .sodium_crypto import SodiumCrypto as Crypto
from .config import Config
from .types import ClientDetails, ClientInfo, IncomingSharingPolicy, OutgoingSharingPolicy, Meta, QueryResult, Query, Record, AuthorizerPolicy, File, Search, SearchResult, Params, Range
from .exceptions import APIError, LookupError, CryptoError, QueryError, ConflictError
import requests
import shutil
import hashlib

# wormhole
import wormhole
import random
import os
import subprocess
from datetime import datetime

class Client:
    """
    Client to perform E3DB operations with.

    The client is able to read, write, query, and many other methods to
    interact with data being stored and retrieved from E3DB.
    """
    DEFAULT_QUERY_COUNT = 100
    DEFAULT_API_URL = "https://api.e3db.com"

    def __init__(self, config):
        """
        Initialize the Client class.

        Parameters
        ----------
        config : dict
            JSON-style dictionary with config elements.

        Returns
        -------
        None
        """
        self.api_url = config['api_url']
        self.api_key_id = config['api_key_id']
        self.api_secret = config['api_secret']
        self.client_id = config['client_id']
        self.client_email = config['client_email']
        self.public_key = config['public_key']
        self.private_key = config['private_key']
        self.e3db_auth = E3DBAuth(self.api_key_id, self.api_secret, self.api_url)
        self.ak_cache = {}

    @classmethod
    def __response_check(self, response):
        """
        Raises errors based on response HTTP status code.

        Parameters
        ----------
        response : requests.models.Response
            Response object to get status code from.

        Returns
        -------
        None
        """

        # Map of HTTP error codes to exception messages
        errors = {
            400: APIError('Invalid request: HTTP 400'),
            401: APIError('Unauthenticated: HTTP 401'),
            403: APIError('Unauthorized: HTTP 403'),
            404: APIError('Requested item not found: HTTP 404'),
            409: ConflictError('Existing item cannot be modified: HTTP 409'),
            429: APIError('Too many requests made to endpoint. HTTP 429. Slow down.')
        }

        # Lookup type of error we should throw, and do so if needed.
        if response.status_code in errors:
            raise errors[response.status_code]

        # If we do not have a pre-formulated error to return, but get another HTTP
        # Error, we check if response is in the 4XX-5XX Range, and return a generic HTTP error
        if response.status_code >= 400 and response.status_code <= 600:
            raise APIError("HTTP Error: {0}".format(response.status_code))

    def __decrypt_record(self, record):
        """
        Private method for record decryption setup.

        Obtains the ak needed to decrypt the data, as well as calling
        `__decrypt_record_with_key` to decrypt each individual field.

        Parameters
        ----------
        record : e3db.Record
            Encrypted record

        Returns
        -------
        e3db.Record
            Decrypted record
        """

        meta = record.to_json()['meta']
        writer_id = meta['writer_id']
        user_id = meta['user_id']
        record_type = meta['type']
        ak = self.__get_access_key(writer_id, user_id, self.client_id, record_type)
        return self.__decrypt_record_with_key(record, ak)

    def __decrypt_record_with_key(self, record, ak):
        """
        Private method for decryption of record fields.

        Parameters
        ----------
        record : e3db.Record
            Encrypted record

        ak : str
            Access Key

        Returns
        -------
        e3db.Record
            Decrypted record
        """

        encrypted_record = record.to_json()

        for key, value in encrypted_record['data'].items():
            fields = value.split(".")

            if len(fields) != 4:
                raise CryptoError("Invalid Encrypted record fields: {0}".format(value))

            edk = Crypto.base64decode(fields[0])
            edkN = Crypto.base64decode(fields[1])
            ef = Crypto.base64decode(fields[2])
            efN = Crypto.base64decode(fields[3])

            dk = Crypto.decrypt_secret(ak, edk, edkN)
            pv = Crypto.decrypt_secret(dk, ef, efN)

            encrypted_record['data'][key] = pv.decode("utf-8")
        # return new Record object data with plaintext data
        return Record(Meta(encrypted_record['meta']), encrypted_record['data'])

    def __encrypt_record(self, plaintext_record):
        """
        Private method for encryption of record fields.

        Parameters
        ----------
        plaintext_record : e3db.Record
            Plaintext record

        Returns
        -------
        e3db.Record
            Encrypted record
        """

        record = plaintext_record.to_json()
        data = record['data']
        meta = record['meta']
        writer_id = meta['writer_id']
        user_id = meta['user_id']
        record_type = meta['type']

        # make copy of original record so we can modify it without altering
        # the original record
        new_meta = Meta(meta)
        record = Record(meta=new_meta, data=data).to_json()

        ak = self.__get_access_key(writer_id, user_id, self.client_id, record_type)

        # if the ak is missing, we need to create and push one to the server.
        if ak is None:
            ak = Crypto.random_key()
            self.__put_access_key(writer_id, user_id, self.client_id, record_type, ak)

        # Loop through the plaintext fields and encrypt them
        for key, value in record['data'].items():
            dk = Crypto.random_key()
            efN = Crypto.random_nonce()
            ef = Crypto.encrypt_secret(dk, value, efN)
            # remove nonce from ciphertext
            ef = ef[len(efN):]
            edkN = Crypto.random_nonce()
            edk = Crypto.encrypt_secret(ak, dk, edkN)
            # remove nonce from ciphertext
            edk = edk[len(edkN):]

            record['data'][key] = ".".join([Crypto.base64encode(c).decode("utf-8") for c in [edk, edkN, ef, efN]])

        # return new Record object data with encrypted data
        return Record(Meta(meta), record['data'])

    def __decrypt_eak(self, eak_json):
        """
        Private method for decryption of an encrypted access key.

        Parameters
        ----------
        eak_json : dict
            json-style body returned from the API

        Returns
        -------
        str
            ak
        """

        if Crypto.get_mode() == 'nist':
            k = eak_json['authorizer_public_key']['p384']
        else:
            k = eak_json['authorizer_public_key']['curve25519']
        authorizer_pubkey = Crypto.decode_public_key(k)
        fields = eak_json['eak'].split('.')
        if len(fields) != 2:
            raise CryptoError("Invalid access key format: {0}".format(eak_json['eak']))
        ciphertext = Crypto.base64decode(fields[0])
        nonce = Crypto.base64decode(fields[1])
        return Crypto.decrypt_eak(Crypto.decode_private_key(self.private_key), authorizer_pubkey, ciphertext, nonce)

    def __get_access_key(self, writer_id, user_id, reader_id, record_type):
        """
        Private method to obtain an access key.

        Parameters
        ----------
        writer_id : str
            uuid of the writer

        user_id : str
            uuid of the user

        reader_id : str
            uuid of the reader

        record_type: str
            type of the record to be stored

        Returns
        -------
        str
            ak
        """

        ak_cache_key = (str(writer_id), str(user_id), record_type)
        if ak_cache_key in self.ak_cache:
            return self.ak_cache[ak_cache_key]

        url = self.__get_url("v1", "storage", "access_keys", str(writer_id), str(user_id), str(reader_id), record_type)
        response = requests.get(url=url, auth=self.e3db_auth)
        # return None if eak not found, otherwise return eak
        if response.status_code == 404:
            return None
        else:
            self.__response_check(response)
            json = response.json()
            ak = self.__decrypt_eak(json)
            self.ak_cache[ak_cache_key] = ak
            return ak

    def __put_access_key(self, writer_id, user_id, reader_id, record_type, ak):
        """
        Private method to put an access key on the server.

        Parameters
        ----------
        writer_id : str
            uuid of the writer

        user_id : str
            uuid of the user

        reader_id : str
            uuid of the reader

        record_type: str
            type of the record to be stored

        ak: str
            access key

        Returns
        -------
        None
        """

        ak_cache_key = (str(writer_id), str(user_id), record_type)
        self.ak_cache[ak_cache_key] = ak

        reader_key = self.__client_key(reader_id)
        nonce = Crypto.random_nonce()
        eak = Crypto.encrypt_ak(Crypto.decode_private_key(self.private_key), reader_key, ak, nonce)
        # Need to strip the nonce off the front of the eak
        eak = eak[len(nonce):]
        encoded_eak = "{0}.{1}".format(Crypto.base64encode(eak).decode("utf-8"), Crypto.base64encode(nonce).decode("utf-8"))
        url = self.__get_url("v1", "storage", "access_keys", str(writer_id), str(user_id), str(reader_id), record_type)
        json = {
            'eak': encoded_eak
        }
        response = requests.put(url=url, json=json, auth=self.e3db_auth)
        self.__response_check(response)

    def __delete_access_key(self, writer_id, user_id, reader_id, record_type):
        """
        Private method to delete an access key on the server.

        Parameters
        ----------
        writer_id : str
            uuid of the writer

        user_id : str
            uuid of the user

        reader_id : str
            uuid of the reader

        record_type: str
            type of the record to be stored

        Returns
        -------
        None
        """

        url = self.__get_url("v1", "storage", "access_keys", str(writer_id), str(user_id), str(reader_id), record_type)
        response = requests.delete(url=url, auth=self.e3db_auth)
        self.__response_check(response)

    def __get_url(self, *args):
        """
        Private method to build an api url path.

        Parameters
        ----------
        *args : list
            list of url path strings

        Returns
        -------
        str
            Full api url with path
        """

        # list of paths that we make a nice url from
        return self.api_url + '/' + '/'.join(args)

    def __put_policy(self, user_id, writer_id, reader_id, record_type, policy):
        """
        Private method to delete an access key on the server.

        Parameters
        ----------
        user_id : str
            uuid of the user

        writer_id : str
            uuid of the writer

        reader_id : str
            uuid of the reader

        record_type: str
            type of the record to be stored

        policy: dict
            policy object to be stored

        Returns
        -------
        None
        """

        policy = dict(policy)
        url = self.__get_url("v1", "storage", "policy", str(user_id), str(writer_id), str(reader_id), record_type)

        response = requests.put(url=url, json=policy, auth=self.e3db_auth)
        self.__response_check(response)

    def outgoing_sharing(self):
        """
        Public Method to obtain outgoing sharing policies.

        This shows records, and clients that you have shared record types with.

        Parameters
        ----------
        None

        Returns
        -------
        list
            List of e3db.OutgoingSharingPolicy documents
        """

        url = self.__get_url("v1", "storage", "policy", "outgoing")
        response = requests.get(url=url, auth=self.e3db_auth)
        self.__response_check(response)
        # create list of policy objects, and return them
        policies = []
        # check if there are no policies
        if response.json():
            for policy in response.json():
                policies.append(OutgoingSharingPolicy(policy))
        return policies

    def incoming_sharing(self):
        """
        Public Method to obtain incoming sharing policies.

        This shows records, and clients that have shared record types with you.

        Parameters
        ----------
        None

        Returns
        -------
        list
            List of e3db.IncomingSharingPolicy documents
        """

        url = self.__get_url("v1", "storage", "policy", "incoming")
        response = requests.get(url=url, auth=self.e3db_auth)
        self.__response_check(response)
        # create list of policy objects, and return them
        policies = []
        # check if there are no policies
        if response.json():
            for policy in response.json():
                policies.append(IncomingSharingPolicy(policy))
        return policies

    @classmethod
    def register(self, registration_token, client_name, public_key, private_key=None, backup=False, api_url=DEFAULT_API_URL):
        """
        Public Method to register a client with the server.

        The server will return api key credentials, and a client id for the
        newly created client.

        Parameters
        ----------
        registration_token : str
            Token obtained from InnoVault console used for dynamic registration

        client_name : str
            Name of client to be registered with the InnoVault console

        public_key : str
            base64urlencoded public_key object obtained from
            e3db.Client.generate_keypair()

        private_key : str
            base64urlencoded public_key object obtained from
            e3db.Client.generate_keypair(). Optional. Included in client
            backup record for later key recovery in the InnoVault console,
            if desired.

        backup : bool
            Whether to backup client credentials to the InnoVault console.
            Optional.

        api_url : str
            API url useful for testing against different e3db instances.
            Optional.

        Returns
        -------
        e3db.ClientDetails
            Contains API credentials, a unique client_id generated by the
            server, client name, and client public key.
        """

        url = "{0}/{1}/{2}/{3}/{4}/{5}".format(api_url, 'v1', 'account', 'e3db', 'clients', 'register')
        if Crypto.get_mode() == 'nist':
            payload = {
                'token': registration_token,
                'client': {
                    'name': client_name,
                    'public_key': {
                        'p384': public_key
                    }
                }
            }
        else:
            payload = {
                'token': registration_token,
                'client': {
                    'name': client_name,
                    'public_key': {
                        'curve25519': public_key
                    }
                }
            }
        response = requests.post(url=url, json=payload)
        self.__response_check(response)
        client_info = response.json()
        backup_client_id = response.headers['x-backup-client']

        if backup:
            if private_key is None:
                raise RuntimeError("Cannot back up client credentials without a private key!")

            config = Config(
                client_info['client_id'],
                client_info['api_key_id'],
                client_info['api_secret'],
                public_key,
                private_key,
                api_url=api_url
            )

            client = Client(config())
            client.backup(backup_client_id, registration_token)

        # make ClientDetails object
        return ClientDetails(client_info)

    @classmethod
    def generate_keypair(self):
        """
        Public Method to generate a public and private keypair.

        Used for dynamic registration where the SDK generates its own keys
        and gives the server the public key to generate a client.

        Parameters
        ----------
        None

        Returns
        -------
        tuple
            (public_key, private_key) tuple. Keys are Base64URLencoded strings
            of bytes.
        """

        public_key, private_key = Crypto.generate_keypair()
        return (
            Crypto.encode_public_key(public_key).decode("utf-8"),
            Crypto.encode_private_key(private_key).decode("utf-8"))

    def client_info(self, client_id):
        """
        Public Method to retrieve client info from the server based on client id.

        Parameters
        ----------
        client_id : str
            UUID of the client to lookup info for

        Returns
        -------
        e3db.ClientInfo
            Contains client_id and client public key.
        """

        url = self.__get_url("v1", "storage", "clients", str(client_id))
        response = requests.get(url=url, auth=self.e3db_auth)
        if response.status_code == 404:
            raise LookupError('Client ID not found: {0}'.format(client_id))

        self.__response_check(response)
        json = response.json()

        client_id = json['client_id']
        public_key = json['public_key']
        validated = json['validated']
        return ClientInfo(client_id, public_key, validated)

    def __client_key(self, client_id):
        """
        Private method to retrieve decoded public key from the server based
        on client id.

        Parameters
        ----------
        client_id : str
            UUID of the client to lookup info for

        Returns
        -------
        nacl.public.PublicKey
            Public key from client_id specified
        """

        if client_id == self.client_id:
            return Crypto.decode_public_key(self.public_key)
        else:
            client_info = self.client_info(client_id).to_json()
            if Crypto.get_mode() == 'nist':
                return Crypto.decode_public_key(client_info['public_key']['p384'])
            else:
                return Crypto.decode_public_key(client_info['public_key']['curve25519'])

    def __read_raw(self, record_id):
        """
        Private method to retrieve encrypted record from the server.

        Parameters
        ----------
        record_id : str
            UUID of the record to retrieve

        Returns
        -------
        e3db.Record
            Encrypted E3DB record
        """

        url = self.__get_url("v1", "storage", "records", str(record_id))
        response = requests.get(url=url, auth=self.e3db_auth)
        self.__response_check(response)
        json = response.json()
        # craft meta object
        # craft record object
        meta_json = json['meta']
        data_json = json['data']
        meta = Meta(meta_json)
        record = Record(meta, data_json)
        return record

    def read(self, record_id):
        """
        Public Method to retrieve encrypted record from the server, and decrypt it
        locally.

        Parameters
        ----------
        record_id : str
            UUID of the record to retrieve

        Returns
        -------
        e3db.Record
            Decrypted E3DB record
        """

        return self.__decrypt_record(self.__read_raw(record_id))

    def write(self, record_type, data, plain=None):
        """
        Public Method to take a plaintext record, encrypt it locally, and send it
        to the server.

        Parameters
        ----------
        record_type: str
            type of the record to be stored

        data : dict
            JSON-style document containing data to encrypt

        plain : dict
            JSON-style document containing plaintext meta data.
            Optional.

        Returns
        -------
        e3db.Record
            Decrypted E3DB record
        """

        url = self.__get_url("v1", "storage", "records")
        meta_data = {
            'writer_id': str(self.client_id),
            'user_id': str(self.client_id),
            'type': record_type,
            'plain': plain
        }
        meta = Meta(meta_data)
        record = Record(meta, data)
        encrypted_record = self.__encrypt_record(record)
        response = requests.post(url=url, json=encrypted_record.to_json(), auth=self.e3db_auth)
        self.__response_check(response)
        response_json = response.json()
        response_meta = Meta(response_json['meta'])
        decrypted = self.__decrypt_record(Record(response_meta, response_json['data']))
        return decrypted

    def update(self, record):
        """
        Public Method to take an updated plaintext record, encrypt it locally, and
        send it to the server.

        Maintains the same record id, while the record version, and data
        changes.

        Parameters
        ----------
        record: e3db.Record
            plaintext record to encrypt and send updated version to server

        Returns
        -------
        e3db.Record
            Decrypted E3DB record, with updated record version
        """
        record_serialized = record.to_json()
        record_id = record_serialized['meta']['record_id']
        version = record_serialized['meta']['version']
        url = self.__get_url("v1", "storage", "records", "safe", str(record_id), version)
        encrypted_record = self.__encrypt_record(record)
        # We don't want to post datetime objects to the server, so we remove
        # them as they are unnecessary
        encrypted_record_json = encrypted_record.to_json()
        del encrypted_record_json['meta']['created']
        del encrypted_record_json['meta']['last_modified']
        response = requests.put(url=url, json=encrypted_record_json, auth=self.e3db_auth)
        self.__response_check(response)
        json = response.json()
        new_meta = Meta(json['meta'])
        new_data = json['data']
        new_record = Record(meta=new_meta, data=new_data)
        return self.__decrypt_record(new_record)

    def delete(self, record_id, version):
        """
        Public Method to delete a record.

        Requires both the record id, and current version to ensure a safe
        delete operation.

        Parameters
        ----------
        record_id: str
            UUID of the record

        version: str
            UUID version from the record

        Returns
        -------
        None
        """
        url = self.__get_url("v1", "storage", "records", "safe", str(record_id), version)
        response = requests.delete(url=url, auth=self.e3db_auth)
        self.__response_check(response)

    def backup(self, client_id, registration_token):
        """
        Public Method to write backup credentials to InnoVault console
        for recovery, if desired during registration.

        Parameters
        ----------
        client_id: str
            UUID of client

        registration_token: str
            Token obtained from InnoVault console used for dynamic registration

        Returns
        -------
        None
        """
        # credentials must be json encoded in order to decode
        # properly in the innovault console.
        credentials = {
            'version': '1',
            'client_id': "\"{0}\"".format(self.client_id),
            'api_key_id': "\"{0}\"".format(self.api_key_id),
            'api_secret': "\"{0}\"".format(self.api_secret),
            'client_email': "\"{0}\"".format(self.client_email),
            'public_key': "\"{0}\"".format(self.public_key),
            'private_key': "\"{0}\"".format(self.private_key),
            'api_url': "\"{0}\"".format(self.api_url)
        }

        self.write('tozny.key_backup', credentials, {'client': self.client_id})
        # share this record type with the backup client
        self.share('tozny.key_backup', client_id)

        url = self.__get_url('v1', 'account', 'backup', registration_token, str(self.client_id))
        response = requests.post(url=url, auth=self.e3db_auth)
        self.__response_check(response)

    def query(self, data=True, writer=[], record=[], record_type=[], plain=None, page_size=DEFAULT_QUERY_COUNT, last_index=0):
        """
        Public method to Query E3DB records according to selection criteria.


        The default behavior is to return all records written by the current
        authenticated client.

        Query results can be restricted based on types of records, record ids,
        writers, plaintext meta filters. Results can be 'paged' to limit large
        amounts of records being returned.

        Parameters
        ----------
        data: bool
            Whether to include the record's data when returned in the query.
            Optional.

        writer: list
            List of writer ids to filter on.
            Optional.

        record: list
            List of record ids to filter on.
            Optional.

        record_type: list
            List of record types to filter on.
            Optional.

        plain: dict
            JSON-style Plaintext meta data query object to use for matching
            against record plaintext meta data fields.
            Optional.

        page_size : int
            How many records to return per query. Can be used in conjunction
            with last_index to read records in 'batches'.

        last_index : int
            Retrieve records from this index onwards. Starts at 0 to return all.
            Useful for retrieving records in 'batches'. Exposed to user through
            the QueryResult.after_index method.

        Returns
        -------
        e3db.QueryResult
            Iterable object that returns decrypted e3db.Record objects.
        """
        all_writers = False
        if writer == "all":
            all_writers = True
            writer = []

        # convert all possible UUID types back to strings
        writer = [str(i) for i in writer]
        record = [str(i) for i in record]

        q = Query(after_index=last_index, include_data=data, writer_ids=writer,
                record_ids=record, content_types=record_type, plain=plain,
                user_ids=[], count=page_size,
                include_all_writers=all_writers)

        response = self.__query(q)

        # take this apart
        last_index = response['last_index']
        results = response['results']
        records = self.__parse_results(results, data)
        qr = QueryResult(q, records)
        qr.after_index = last_index
        return qr

    def __query(self, query):
        """
        Private Method to send query to server and return response.

        Parameters
        ----------
        query: e3db.Query
            Query to run against the server.

        Returns
        -------
        dict
            server response as dict (JSON)
        """
        url = self.__get_url('v1', 'storage', 'search')
        response = requests.post(url=url, json=query.to_json(), auth=self.e3db_auth)
        try:
            json = response.json()
            if 'error' in json:
                # we had an error, return this to user
                raise QueryError(json['error'])
            self.__response_check(response)
            return json
        except ValueError:
            # This Value error only occurs if there is no json body, we want it suppressed
            pass
        # In the case of a value error see if the response is non 200 and map to the correct exception
        self.__response_check(response)
        # It is unlikely that this return will get called, it would require the service to return a 200 level response
        # code with no body, which the query endpoint should not do, however mapping that to a query exception make
        # sense if that situation does arise
        return QueryError("An unexpected response occurred, and no results were returned")

    def search(self, query):
        """
        Public Method to perform improved search request for E3db records according to the query provided.

        Requires a Search object to perform the Query. Construction and Execution is as follows:

        search_this = Search().Match(records=[some_params,...]).Exclude(writers=[omit_this,...])
        search_result = client.search(search_this)

        For more information see the documentation of the Search Object or Tests.

        Parameters
        ----------
        query : Search
            Object that contains the information to search for.

        Returns
        -------
        SearchResult
            Result of a valid response from E3DB.
        """
        response = self.__search(query)
        results = response['results']
        next_token = response['last_index']
        search_id = response['search_id']
        total_results = response['total_results']

        if results is None:
            return SearchResult(query, [], next_token, total_results, search_id)

        records = self.__parse_results(results, query.include_data)
        qr = SearchResult(query, records, next_token, total_results, search_id)
        return qr

    def __search(self, query):
        """
        Private Method to send search request to E3DB and return a json response.

        Parameters
        ----------
        query: Search
            Search object represents the query made to the E3DB.

        Returns
        -------
        dict
            response from the server as json (dict).
        """
        url = self.__get_url('v2', 'search')
        response = requests.post(url=url, json=query.to_json(), auth=self.e3db_auth)
        self.__response_check(response)
        json = response.json() # server does not return error message, just status codes
        return json

    def __parse_results(self, results, include_data):
        """
        Private Method to parse the response of a search v1 or v2 request.

        A Query/Search Response comes in as json and is abstracted into the
        Meta and Record class. If data is included in the response (result_data != None),
        then the data is decrypted with the provided access_key.

        Parameters
        ----------
        results: dict[string]object (json)
            json response from PDS

        include_data: bool
            Flag to indicate if data is included in the response, taken from the Query.

        Returns
        ----------
        [Records]
            List of Record Objects
        """
        records = []
        for result in results:
            result_meta = result['meta']
            meta = Meta(result_meta)
            result_data = result['record_data']
            record = Record(meta=meta, data=result_data)
            if include_data:
                # need to decrypt all the results before returning.
                access_key = result['access_key']
                if access_key:
                    ak = self.__decrypt_eak(access_key)
                    record = self.__decrypt_record_with_key(record, ak)
                else:
                    record = self.__decrypt_record(record)
            records.append(record)
        return records

    def share(self, record_type, reader_id):
        """
        Public Method to share a record type with another client.

        Records are shared based on record type between clients. Once a record
        type is shared between clients, all future records of that type are
        automatically shared, and able to be read by both parties.

        Parameters
        ----------
        record_type: str
            type of the record to be stored

        reader_id : str
            The reader's client id (UUID) to share this record type with.

        Returns
        -------
        None
        """
        if reader_id == self.client_id:
            return

        ak = self.__get_access_key(self.client_id, self.client_id, self.client_id, record_type)
        if ak is None:
            ak = Crypto.random_key()
            self.__put_access_key(self.client_id, self.client_id, self.client_id, record_type, ak) # Give yourself the ak
        self.__put_access_key(self.client_id, self.client_id, reader_id, record_type, ak)

        allow_read = {
            'allow': [
                {'read': {}}
            ]
        }

        self.__put_policy(str(self.client_id), str(self.client_id), str(reader_id), record_type, allow_read)

    def revoke(self, record_type, reader_id):
        """
        Public Method to revoke access to a record type that was previously
        shared with another client.

        Deletes the keys used by the other client to be able to decrypt the
        shared data.

        Parameters
        ----------
        record_type: str
            type of the record to be stored

        reader_id : str
            The reader's client id (UUID) to share this record type with.

        Returns
        -------
        None
        """
        if reader_id == self.client_id:
            return

        deny_read = {
            'deny': [
                {
                    'read': {}
                }
            ]
        }

        self.__put_policy(str(self.client_id), str(self.client_id), str(reader_id), record_type, deny_read)
        self.__delete_access_key(self.client_id, self.client_id, reader_id, record_type)

    def add_authorizer(self, record_type, authorizer_id):
        """
        Public Method to share a record type with an authorizer.

        Parameters
        ----------
        record_type: str
            type of the record to be stored

        authorizer_id : str
            The authorizer's client id (UUID) to share this record type with.

        Returns
        -------
        None
        """

        # Use get_authorizers to see if this client is already authorized
        authorizer_policies = self.get_authorizers()
        for policy in authorizer_policies:
            if policy.authorizer_id == authorizer_id and policy.record_type == record_type:
                # The authorizer has already been authorized, we can safely return now
                return None

        ak = self.__get_access_key(str(self.client_id), str(self.client_id), str(self.client_id), record_type)
        if ak is None:
            ak = Crypto.random_key()
            self.__put_access_key(str(self.client_id), str(self.client_id), str(self.client_id), record_type, ak)

        # write the EAK for the new authorizer client
        self.__put_access_key(str(self.client_id), str(self.client_id), str(authorizer_id), record_type, ak)

        allow_authorizer = {
            'allow': [
                {'authorizer': {}}
            ]
        }

        self.__put_policy(str(self.client_id), str(self.client_id), str(authorizer_id), record_type, allow_authorizer)

    def remove_authorizer(self, record_type, authorizer_id):
        """
        Public Method to revoke access of a record type shared with an authorizer.

        Parameters
        ----------
        record_type: str
            type of the record to be stored

        authorizer_id : str
            The authorizer's client id (UUID) to share this record type with.

        Returns
        -------
        None
        """

        deny_authorizer = {
            'deny': [
                {'authorizer': {}}
            ]
        }

        self.__put_policy(str(self.client_id), str(self.client_id), str(authorizer_id), record_type, deny_authorizer)
        self.__delete_access_key(str(self.client_id), str(self.client_id), str(authorizer_id), record_type)

    def share_on_behalf_of(self, writer_id, reader_id, record_type):
        """
        Public Method for an authorizer to share data it has been authorized to share
        with another client

        Parameters
        ----------
        writer_id: str
            data producer id

        reader_id : str
            The reader's client id (UUID) to share this record type with.

        record_type: str
            type of the record to be stored

        Returns
        -------
        None
        """

        ak = self.__get_access_key(str(writer_id), str(writer_id), str(self.client_id), record_type)
        # This should only happen if the authorizer tries to share on behalf of, and has had
        # their authorizer rights revoked, the eak will be missing from the E3DB system at that point
        if ak is None:
            raise APIError('Requested item not found: HTTP 404')

        self.__put_access_key(str(writer_id), str(writer_id), str(reader_id), record_type, ak)

        allow_read = {
            'allow': [
                {'read': {}}
            ]
        }

        self.__put_policy(str(writer_id), str(writer_id), str(reader_id), record_type, allow_read)

    def revoke_on_behalf_of(self, writer_id, reader_id, record_type):
        """
        Public Method for an authorizer to revoke previously shared data between
        two clients that it has been previously authorized for.

        Parameters
        ----------
        writer_id: str
            data producer id

        reader_id : str
            The reader's client id (UUID) to share this record type with.

        record_type: str
            type of the record to be stored

        Returns
        -------
        None
        """

        deny_read = {
            'deny': [
                {
                    'read': {}
                }
            ]
        }

        self.__put_policy(str(writer_id), str(writer_id), str(reader_id), record_type, deny_read)
        self.__delete_access_key(str(writer_id), str(writer_id), str(reader_id), record_type)

    def get_authorized_by(self):
        """
        Public Method to get a list of all clients (and associated record types) that
        this client may act as an authorizer

        Parameters
        ----------
        None

        Returns
        -------
        list
            List of e3db.AuthorizerPolicy documents
        """

        url = self.__get_url("v1", "storage", "policy", "granted")
        response = requests.get(url=url, auth=self.e3db_auth)
        self.__response_check(response)
        # create list of policy objects, and return them
        policies = []
        # check if there are no policies
        if response.json():
            for policy in response.json():
                policies.append(AuthorizerPolicy(policy))
        return policies

    def get_authorizers(self):
        """
        Public Method to get a list of all clients (and associated record types) that
        this client has authorized to share on its behalf.

        Parameters
        ----------
        None

        Returns
        -------
        list
            List of e3db.AuthorizerPolicy documents
        """

        url = self.__get_url("v1", "storage", "policy", "proxies")
        response = requests.get(url=url, auth=self.e3db_auth)
        self.__response_check(response)
        # create list of policy objects, and return them
        policies = []
        # check if there are no policies
        if response.json():
            for policy in response.json():
                policies.append(AuthorizerPolicy(policy))
        return policies

    def write_file(self, record_type, plaintext_filename, plain={}):
        """
        Encrypt a plaintext file, and write it to the Server.

        Does not Encrypt or Delete the plaintext file after operation is
        complete. The SDK user must manage their plaintext files.

        Parameters
        ----------
        record_type : str
            Type of the record

        plaintext_filename: str
            Filename string, including path, to read, encrypt, and send to server

        plain: dict
            Plaintext metadata information to attach to the File

        Returns
        -------
        e3db.File
            File metadata information
        """
        # Get EAK for this record_type, for my client id
        ak = self.__get_access_key(str(self.client_id), str(self.client_id), str(self.client_id), record_type)
        if ak is None:
            ak = Crypto.random_key()
            self.__put_access_key(str(self.client_id), str(self.client_id), str(self.client_id), record_type, ak)

        encrypted_filename, file_checksum, file_size = Crypto.encrypt_file(plaintext_filename, ak)
        file_compression = 'raw'

        upload_file = File(file_checksum.decode("utf-8"), file_compression, file_size, self.client_id, self.client_id, record_type, plain=plain)

        url = self.__get_url("v1", "storage", "files")
        response = requests.post(url=url, json=upload_file.to_json(), auth=self.e3db_auth)
        self.__response_check(response)
        if response.status_code != 202:
            raise APIError("File return status code: {0}, body: {1}".format(response.status_code, response.body))

        # pending file write created
        response_json = response.json()
        upload_file.file_url = response_json["file_url"]
        upload_file.record_id = response_json["id"]
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-MD5': upload_file.checksum
        }

        # Read our encrypted file, upload it to E3DB Large Files data storage
        with open(encrypted_filename, 'rb') as data:
            # Don't need e3db_auth, since the file url is a signed url just for this session
            response = requests.put(url=upload_file.file_url, headers=headers, data=data)

        self.__response_check(response)
        if response.status_code != 200:
            raise APIError("File upload status code: {0}, body: {1}".format(response.status_code, response.body))

        # File is uploaded now to storage endpoint, need to confirm with E3DB server
        # to "COMMIT" the file
        url = self.__get_url("v1", "storage", "files", str(upload_file.record_id))
        response = requests.patch(url=url, auth=self.e3db_auth)
        response_json = response.json()
        # Delete temporary encrypted file, now it is on the server
        os.remove(encrypted_filename)

        # Construct File Object to be returned to the user
        return File(
            response_json['meta']['file_meta']['checksum'],
            response_json['meta']['file_meta']['compression'],
            response_json['meta']['file_meta']['size'],
            response_json['meta']['writer_id'],
            response_json['meta']['user_id'],
            response_json['meta']['type'],
            file_url=response_json['meta']['file_meta']['file_url'],
            file_name=response_json['meta']['file_meta']['file_name'],
            record_id=response_json['meta']['record_id'],
            created=response_json['meta']['created'],
            last_modified=response_json['meta']['last_modified'],
            version=response_json['meta']['version'],
            plain=response_json['meta']['plain']
        )

    def read_file(self, record_id, destination_filename):
        """
        Retrieve an Encrypted file from the server based on record_id.
        Decrypt the file, and store the plaintext file in destination_filename.

        Parameters
        ----------
        record_id : str
            ID of the record to retrieve

        destination_filename: str
            Filename string, including path, to store the plaintext file at.

        Returns
        -------
        e3db.File
            File metadata information
        """

        # Check if destination file can be written to
        try:
            destination_file_handle = open(destination_filename, 'w+')
        except IOError:
            destination_file_handle.close()
        destination_file_handle.close()

        url = self.__get_url("v1", "storage", "files", str(record_id))
        response = requests.get(url=url, auth=self.e3db_auth)
        self.__response_check(response)
        if response.status_code != 200:
            raise APIError("File fetch status code: {0}, body: {1}".format(response.status_code, response.body))

        # decode the response
        response_json = response.json()

        get_file_info = File(
            response_json['meta']['file_meta']['checksum'],
            response_json['meta']['file_meta']['compression'],
            response_json['meta']['file_meta']['size'],
            response_json['meta']['writer_id'],
            response_json['meta']['user_id'],
            response_json['meta']['type'],
            file_url=response_json['meta']['file_meta']['file_url'],
            file_name=response_json['meta']['file_meta']['file_name'],
            record_id=response_json['meta']['record_id'],
            created=response_json['meta']['created'],
            last_modified=response_json['meta']['last_modified'],
            version=response_json['meta']['version'],
            plain=response_json['meta']['plain']
        )

        # Get AK to decrypt the record
        ak = self.__get_access_key(get_file_info.writer_id, get_file_info.user_id, self.client_id, get_file_info.record_type)

        if ak is None:
            raise APIError("Can't read records of type {0}".format(get_file_info.record_type))

        # Download the file from the storage server, store encrypted on filesystem
        # until we decrypt it in the next steps
        # Uses efficient copy from storage server to filesystem courtesy of:
        # https://stackoverflow.com/a/39217788
        encrypted_filename = "enc-{0}.bin".format(destination_filename)
        with requests.get(url=get_file_info.file_url, stream=True) as r:
            with open(encrypted_filename, 'wb+') as f:
                shutil.copyfileobj(r.raw, f)

        # Now we have the file locally, but it is still encrypted. We will now
        # decrypt the file with our AK retrieved earlier
        Crypto.decrypt_file(encrypted_filename, destination_filename, ak)
        # Delete temporary encrypted file
        os.remove(encrypted_filename)
        return File(
            response_json['meta']['file_meta']['checksum'],
            response_json['meta']['file_meta']['compression'],
            response_json['meta']['file_meta']['size'],
            response_json['meta']['writer_id'],
            response_json['meta']['user_id'],
            response_json['meta']['type'],
            file_url=response_json['meta']['file_meta']['file_url'],
            file_name=response_json['meta']['file_meta']['file_name'],
            record_id=response_json['meta']['record_id'],
            created=response_json['meta']['created'],
            last_modified=response_json['meta']['last_modified'],
            version=response_json['meta']['version'],
            plain=response_json['meta']['plain']
        )

    def write_p2p(self, plaintext_filename, receiver_id):

        # client.send_p2p(record_type, 'plaintext_filename', receiver_id)
            # internally does heavy lifting
            # creates access key
            # encrypts files using access key, stores encrypted file locally
            # shares access key with receiver_id
            # writes special record type "toz.p2p.{0}".format(client.client_id), uses AK same as file
            # wormhole code written in record_type
            # shares special record type with receiver_id
            # starts wormhole sender server
            # loops until connection is made with proper wormhole code
            # sends encrypted file over wormhole
            # closes connection
            # TODO have timeout for sending files?

        # 50 char limit
        record_type = "toz.p2p.{0}".format(Crypto.encode_private_key(Crypto.random_key())[:16].decode('utf-8'))
        print("Record type: {0}".format(record_type))

        # Get EAK for this record_type, for my client id
        ak = self.__get_access_key(str(self.client_id), str(self.client_id), str(self.client_id), record_type)
        if ak is None:
            ak = Crypto.random_key()
            self.__put_access_key(str(self.client_id), str(self.client_id), str(self.client_id), record_type, ak)

        print("encrypting file: {0}".format(plaintext_filename))
        encrypted_filename, file_checksum, file_size = Crypto.encrypt_file(plaintext_filename, ak)
        print("file encrypted: {0}".format(encrypted_filename))

        # The invitation code uses the same format either way: channel-ID, a hyphen, and an arbitrary string.
        # using crypto methods to just get some random bytes
        rand = Crypto.encode_private_key(Crypto.random_key())[:16]
        wormhole_code = "{0}-{1}-{2}".format(random.randint(0,1000), self.api_url, rand.decode('UTF-8'))
        print("wormhole-code: {0}".format(wormhole_code))
        data = {
            'wormhole-code': wormhole_code,
            'filename': plaintext_filename,
            'encrypted-filename': encrypted_filename
        }
        wormhole_record = self.write(record_type, data)
        print("Wrote record id: {0} with wormhole code information.".format(wormhole_record.meta.record_id))
        self.share(record_type, receiver_id)
        print("Sharing record type {0} with client {1}".format(record_type, receiver_id))
        # wormhole send --code 11234-dev.e3db.com-test README.md
        # start wormhole server
        # uses default wormhole developer relay server

        # Due to lack of time the wormhole cli was used instead of using the python API

        #w = wormhole.create(appid, relay_url, reactor, delegate=MyDelegate())
        #w.allocate_code()
        #w.set_code(wormhole_code)
        #w.dilate()
        #w.send_message(msg)
        #w.close()

        print("Attempting to send file {0}...".format(encrypted_filename))
        # TODO note that shelling out leaves code execution issues, THIS IS JUST A DEMO DO NOT ACTUALLY DO THIS
        # for example someone could say wormhole-code = "test; rm -rf *;" and popen would run the rm command, not Good!
        proc = subprocess.Popen(["wormhole", "send", "--code", wormhole_code, encrypted_filename], stdout=subprocess.PIPE)

        # wait for the process to return
        com = proc.communicate()[0]
        # read cert in from file
        if proc.returncode == 0:
          # made cert hopefully *crosses fingers*
          print("INFO: seems to have run with exit code 0")
        else:
          print("INFO: certbot -- an error occurred during cert creation. "
                "Non-zero Status code ({})".format(proc.returncode))
        # print(stdout from subprocess)
        print(com)

        # docker run -it --rm --entrypoint=sh -v "$HOME/.tozny/p2p-sender:/root/.tozny/" tozny/e3db-python
        # python sender.py

        # cleanup
        # TODO
        # delete record type
        # delete records
        # unshare?
        os.remove(encrypted_filename)


    def read_p2p(self, sender_client_id=None):
        # client.recv_p2p(sender_client_id)
            # sender_client_id optional, could just browser for all shared files
            # checks for new shared records of type "toz.p2p.*" or "toz.p2p.{0}".format(sender_client_id)
            # fetches records, decrypts, holds onto access key used on record
            # gets magicwormhole code
            # initiates download from magicwormhole source
            # stores encrypted file locally
            # decrypts encrypted file with stored access key
            # writes plaintext file to disk

        # docker run -it --rm --entrypoint=sh -v "$HOME/.tozny/p2p-sender:/root/.tozny/" tozny/e3db-python
        # python sender.py

        # record_type = "toz.p2p.{0}/{1}".format(self.client_id, receiver_id)
        # need to go from incoming_sharing to record_id of record with that type

        # TODO use search v2
        found = {}

        for policy in self.incoming_sharing():
            if sender_client_id:
                if policy.writer_id == sender_client_id and "toz.p2p." in policy.record_type:
                    found[str(policy.writer_id)] = policy.record_type
            else:
                # no sender client id, so we get generic matches
                if "toz.p2p." in policy.record_type:
                    found[str(policy.writer_id)] = policy.record_type

        # TODO this is fragile
        record = None
        # hacky, like super hacky. this is just to find a recent written record to try to discover
        # what the latest wormhole is. #HAX
        for writer_id, record_type in found.items():
            query_result = self.query(writer=[writer_id], record_type=[record_type])
            for r in query_result:
                delta = datetime.now() - r.meta.created
                seconds_ago = delta.seconds
                if seconds_ago < 120:
                    # if record was written in last 120 seconds, this is probably the wormhole we are looking for
                    record = r #grab first record, FRAGILE
                    break

        print("Record: {0}, Record_type: {1}".format(record.meta.record_id, record.meta.record_type))
        wormhole_code = record.data['wormhole-code']
        plaintext_filename = record.data['filename']
        encrypted_filename = record.data['encrypted-filename']

        print("receiving {0}, filename: {1}, wh-code: {2}".format(encrypted_filename, plaintext_filename, wormhole_code))
        # after we read record, the aK will be in cache, then we can fetch from there
        ak = self.__get_access_key(record.meta.writer_id, record.meta.writer_id, self.client_id, record.meta.record_type)

        #### MAGIC WORMHOLE #######
        print("Attempting to RECV file {0}...".format(plaintext_filename))
        # TODO note that shelling out leaves code execution issues, THIS IS JUST A DEMO DO NOT ACTUALLY DO THIS
        # for example someone could say wormhole-code = "test; rm -rf *;" and popen would run the rm command, not Good!
        proc = subprocess.Popen(["wormhole", "receive", wormhole_code, "--hide-progress", "--accept-file"], stdout=subprocess.PIPE)
        # wormhole receive 11234-dev.e3db.com-test --hide-progress --accept-file

        # wait for the process to return
        com = proc.communicate()[0]
        # read cert in from file
        if proc.returncode == 0:
          # made cert hopefully *crosses fingers*
          print("INFO: seems to have run with exit code 0")
        else:
          print("INFO: certbot -- an error occurred during cert creation. "
                "Non-zero Status code ({})".format(proc.returncode))
        # print(stdout from subprocess)
        print(com)
        # TODO parse filename from this

        ### DECRYPTTTTTT #####
        Crypto.decrypt_file(encrypted_filename, plaintext_filename, ak)
        os.remove(encrypted_filename)

        return plaintext_filename
