
import e3db
import sys
import json
import os 
#python3 play.py round=1 name=alicia move=rock tozny-client-credentials-filepath=./alicia_creds.json




# Argument Counter Check, Making sure user is passing in 
if len(sys.argv) != 5 :
    sys.exit("Incorrect Arguments:\n python3 play.py [round] [name] [move] [client-credentials]")

#check if move is rock, paper, or scissors



if (sys.argv[3] == 'rock') or (sys.argv[3] == 'paper') or (sys.argv[3] == 'scissors') :
    print("Verifying credentials")
else:
    sys.exit("You must submit a move from the following list: rock, paper, scissors")


move = str(sys.argv[3])

file = open(sys.argv[4], "r")

client_json = json.loads(file.read())

client_name=client_json["name"]

if client_name == sys.argv[2] and ( client_name == 'Alicia' or client_name == 'alicia' or client_name == 'Bruce' or client_name == 'bruce') :
    print("Verified Permissions")
else :
    print(sys.argv[2])
    sys.exit("Permisions not valid")

token= client_json["token"]

credentials_path= sys.argv[4]
if os.path.exists(credentials_path):
    client = e3db.Client(json.load(open(credentials_path)))


file.close


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
print ('Round "{0}" '.format(record2.data['round']), 'Move "{0}"'.format(record2.data['move']), 'for {0} Submitted!'.format(record2.data['name']))
