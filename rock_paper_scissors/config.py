import e3db

#This file is no longer being used 
'''
token= '2ce1cf9eb7f99ea84c1b02347b9635f7663e2ea620966d5cf24722cb76a5e6bb'
client_name= 'Alice'

public_key, private_key = e3db.Client.generate_keypair()

client_info = e3db.Client.register(token, client_name, public_key)

config = e3db.Config(
    client_info.client_id,
    client_info.api_key_id,
    client_info.api_secret,
    public_key,
    private_key
)

   config = {
                'version': str(self.version),
                'client_id': str(self.client_id),
                'api_key_id': str(self.api_key_id),
                'api_secret': str(self.api_secret),
                'client_email': str(self.client_email),
                'public_key': str(self.public_key),
                'private_key': str(self.private_key),
                'api_url': str(self.api_url),
            }

{
    "version": "1",
    "client_id": "f2b4b6a0-4fca-4d33-bdee-0b0b5866b5b4",
    "api_key_id": "980cbedb56ea39469f76c8c7e11c9a00f7e5d59df102b72fb7bfd3958aa523f1",
    "api_secret": "022e3a686f3f90bd596a236d9beab96573acd2ec8f62918851278424e4356c15",
    "client_email": "",
    "public_key": "-CBYrysKiK-4mHAqw73e-lC5Avgrtxq_Zcpk33hl3Xs",
    "private_key": "loB2Baiv8ZlDYC161Rlts-_7xSAs9cDNMjXxAXMWLlA",
    "api_url": "https://api.e3db.com"
}
config = e3db.Config(
    os.environ["client_id"],
    os.environ["api_key_id"],
    os.environ["api_secret"],
    os.environ["public_key"],
    os.environ["private_key"]
)



#config.write()

client = e3db.Client(config())

print("Client ID: ", client.client_id)
print("client public", client.public_key)
print("client public", client.private_key)


'''
