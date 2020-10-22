import e3db

#This file is no longer being used 

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
'''
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
'''
#config.write()

client = e3db.Client(config())

print("Client ID: ", client.client_id)
print("client public", client.public_key)
print("client public", client.private_key)




