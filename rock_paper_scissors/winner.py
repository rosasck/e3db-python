
import e3db
import sys

# $ python3 winner.py round=1 tozny-client-credentials-filepath=./bruce_creds.json

if len(sys.argv) != 3 :
    sys.exit("Incorrect Arguments:\n python3 winner.py [round] [client-credentials]")


#Look up up bruces results from round and output who won 