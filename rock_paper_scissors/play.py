
import e3db
import sys
import json


#python3 play.py round=1 name=alicia move=rock tozny-client-credentials-filepath=./alicia_creds.json

if len(sys.argv) != 5 :
    sys.exit("Incorrect Arguments:\n python3 play.py [round] [name] [move] [client-credentials]")

#check if move is rock, paper, or scissors

move = str(sys.argv[3])
print(sys.argv[3])

if (sys.argv[3] != "rock") or (sys.argv[3] != 'paper') or (sys.argv[3] != 'scissors') :
    sys.exit("You must submit a move from the following list: rock, paper, scissors")



print(sys.argv[4])
file = open(sys.argv[4], "r")

client_json = json.loads(file.read())

client_name=client_json["name"]
token= client_json["token"]


public_key, private_key = e3db.Client.generate_keypair()

client_info = e3db.Client.register(token, client_name, public_key)

client = e3db.Client(
    client_info.client_id,
    client_info.api_key_id,
    client_info.api_secret,
    public_key,
    private_key
)

#config.write()  Ask Levi why this is only ran the first time with each user, and if that is correct 

#client = e3db.Client(config())



file.close



#look in other config.py file
#client = e3db.Client(
  # config
#)



record_type = 'rps_move'
data = {
    'name': client_name,
    'round': sys.argv[1],
    'move': move,
}


#CODE TAKEN FORM READ.ME
record = client.write(record_type, data)
print ('Wrote record ID {0}'.format(record.meta.record_id))

# Read that record back from the server and print the name
record2 = client.read(record.meta.record_id)
print ('Read name: {0}'.format(record2.data['first_name']))
