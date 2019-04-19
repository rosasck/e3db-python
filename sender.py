import e3db

conf = e3db.Config.load()

# Now create a client using that configuration.
client = e3db.Client(conf)

# clean up old records
qr = client.query()
for record in qr:
    if 'p2p' in record.meta.record_type:
        version = record.meta.version
        record_id = record.meta.record_id
        print("{0} {1} {2}".format(record.meta.record_id, record.meta.version, record.meta.record_type))

plaintext_filename = '5gb.file'

receiver_id = '0e88523d-1f61-4b51-bca6-85009ad9ebd3'
client.write_p2p(plaintext_filename, receiver_id)
