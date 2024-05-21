import pymongo
import datetime
from json import dumps

global mongoclient
mongoclient = pymongo.MongoClient("mongodb://root:example@database:27017/")

season = "lrq7y3q3"

matchlist = list(mongoclient["b2"]["matches"].find({"season": season}, sort=[("date", 1)]))

newlist = []

for i in matchlist:
    date = i['date']
    del i['date']
    i['date'] = date.astimezone(datetime.timezone.utc).timestamp()
    newlist.append(i)

outstr = dumps(newlist)

file = open(f"/code/matchexport_{season}", 'w')
file.write(outstr)
file.close()

