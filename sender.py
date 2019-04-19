import e3db

conf = e3db.Config.load()

# Now create a client using that configuration.
client = e3db.Client(conf)

# wget https://i.giphy.com/media/1APaqOO5JHnWKLc7Bi/giphy-downsized.gif
plaintext_filename = 'secretimage.gif'

receiver_id = '0e88523d-1f61-4b51-bca6-85009ad9ebd3'
client.write_p2p(plaintext_filename, receiver_id)
