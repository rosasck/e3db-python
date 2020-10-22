
import e3db
import sys

#$ python3 judge.py round=1 tozny-client-credentials-filepath=./clarence_creds.json

if len(sys.argv) != 3 :
    sys.exit("Incorrect Arguments:\n python3 play.py [round] [client-credentials]")




#Ask Levi how to format the json!




client = e3db.Client(
)


'''
if os.path.exists(credentials_path):
    print("found", credentials_path)
    client = e3db.Client(json.load(open(credentials_path)))
'''



#write a query to grab what alice and clarence have in the data storage 

alice_play= 'rock'
clarence_play='paper'





record_type = 'rps_winner'

'''
data = {
    'name': client_name,
    'round': sys.argv[1],
}
'''


if(alice_play == 'rock' and clarence_play == 'rock'):
    data = {
    'name': 'Tie',
    'round': sys.argv[1],
    }
elif(alice_play == 'rock' and clarence_play == 'paper'):
    data = {
    'name': 'Alicia',
    'round': sys.argv[1],
    }
elif(alice_play == 'rock' and clarence_play == 'scissors'):
    data = {
    'name': 'Alicia',
    'round': sys.argv[1],
    }
elif(alice_play == 'paper' and clarence_play == 'rock'):
    data = {
    'name': "Clarence",
    'round': sys.argv[1],
    }   
elif(alice_play == 'paper' and clarence_play == 'paper'):
    data = {
    'name': "Tie",
    'round': sys.argv[1],
    }
elif(alice_play == 'paper' and clarence_play == 'scissors'):
    data = {
    'name': "Clarence",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and clarence_play == 'rock'):
    data = {
    'name': "Clarence",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and clarence_play == 'paper'):
    data = {
    'name': "Alicia",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and clarence_play == 'scissors'):
    data = {
    'name': "Tie",
    'round': sys.argv[1],
    }
else:
    print("Invalid or Incomplete Data")


record = client.write(record_type, data)
print ('Wrote record ID {0}'.format(record.meta.record_id))