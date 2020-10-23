#Impports needed for program 
import e3db
import sys
import json
import os 

#Example command line arguments given by Levi: 
#python3 play.py round=1 name=alicia move=rock tozny-client-credentials-filepath=./alicia_creds.json


# Argument Counter Check, Making sure user is passing in all needed arguments 
if len(sys.argv) != 5 :
    sys.exit("Incorrect Arguments:\n python3 play.py [round] [name] [move] [client-credentials]")

# Double Checking that the game moves are only able to be rock paper or scissors 
if ((sys.argv[3]).lower() == 'rock') or ((sys.argv[3]).lower() == 'paper') or ((sys.argv[3]).lower() == 'scissors') :
    print("Verifying credentials")
else:
    sys.exit("You must submit a move from the following list: rock, paper, scissors")

#Save the valid move to an argument for further use 
move = str(sys.argv[3]).lower()

file = open(sys.argv[4], "r") #This opens the file that is passed in with the credentials 

client_json = json.loads(file.read())

client_name=client_json["name"] #Grabs name of client credentials 

file.close

#Limits access based on email 
#TODO: Find a way to grant access to records through E3db
if (client_name).lower() == str(sys.argv[2]).lower() and ( (client_name).lower() == 'alicia' or (client_name).lower() == 'bruce') :
    print("Verified Permissions")
else :
    sys.exit("Permisions not valid")


#Load in credentials to write to E3DB 
credentials_path= sys.argv[4]
if os.path.exists(credentials_path):
    client = e3db.Client(json.load(open(credentials_path)))


#Create record to store in E3DB, holding the name of the user, the round they are playing for
# and the move they are playing
record_type = 'rps_move'
data = {
    'name': client_name,
    'round': sys.argv[1],
    'move': move,
}


#This allows the records being created to be shared with the judge for him
#to judge
clarence_client_id= "a06e2162-ce38-4cd2-a63e-6837bbbe4c1a"
client.revoke(record_type, clarence_client_id)
client.share(record_type, clarence_client_id)

#CODE TAKEN FORM READ.ME
#To write the record to the E3DB 
record = client.write(record_type, data)
print ('Wrote record ID {0}'.format(record.meta.record_id))

# Read that record back from the server and print the name
# Make sure that the record was written 
record2 = client.read(record.meta.record_id)
print ('Round "{0}" '.format(record2.data['round']), 'Move "{0}"'.format(record2.data['move']), 'for {0} Submitted!'.format(record2.data['name']))
