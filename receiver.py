# client.recv_p2p(sender_client_id)
    # sender_client_id optional, could just browser for all shared files
    # checks for new shared records of type "toz.p2p.*" or "toz.p2p.{0}".format(sender_client_id)
    # fetches records, decrypts, holds onto access key used on record
    # gets magicwormhole code
    # initiates download from magicwormhole source
    # stores encrypted file locally
    # decrypts encrypted file with stored access key
    # writes plaintext file to disk

import e3db

conf = e3db.Config.load()

# Now create a client using that configuration.
client = e3db.Client(conf)

plaintext_file = client.read_p2p()

print("Decrypted filename: {0}".format(plaintext_file))
