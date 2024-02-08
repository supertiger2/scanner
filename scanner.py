import time
import datetime
import pymongo
import nkapi

def gettime():
    return datetime.datetime.utcfromtimestamp(time.time())

def getseason():
    mongoclient["sutil"]["sutil"].update_one({"_id": 0}, {"$set": {"seasonid": "no_season", "seasonname": "0", "expire": 0}})
    season = ""
    season_end = -1
    latestend = -1
    while True:
        r = nkapi.get("https://data.ninjakiwi.com/battles2/homs")
        j = r.json()
        res = None
        for i in j["body"]:
            thing = {"_id": i["id"], "name": i["name"], "start": i["start"], "end": i["end"]}
            if mongoclient["sutil"]["slist"].find_one(thing) == None:
                mongoclient["sutil"]["slist"].insert_one(thing)
            else:
                mongoclient["sutil"]["slist"].update_one({"_id": thing["_id"]}, {"$set": thing})
            if (i['start'] <= time.time()*1000) and (i['end'] > latestend):
                latestend = i['end']
                seasonN = [int(i) for i in i["name"].split() if i.isdigit()][0]
                mongoclient["sutil"]["sutil"].update_one({"_id": 0}, {"$set": {"seasonid": i['id'], "seasonname": i["name"], "seasonN": seasonN, "expire": i['end']//1000}})
                print(f"Found new latest season {season} (ending at {season_end})", flush=True)
            if (i['start'] <= time.time()*1000) and (i['end'] > time.time()*1000):
                season = i['id']
                season_end = i['end']//1000
                print(f"Found currenttly active season {season} (ending at {season_end})", flush=True)
                mongoclient["b2"]["players"].create_index(["plid", ("date", -1)], background=True)
                mongoclient["b2"]["lb"].create_index([("date", -1)], background=True)
                mongoclient["b2"]["matches"].create_index(["winner"], background=True)
                mongoclient["b2"]["matches"].create_index(["loser"], background=True)
                mongoclient["b2"]["umatches"].create_index(["winner"], background=True)
                mongoclient["b2"]["umatches"].create_index(["loser"], background=True)
                res = (season, season_end, i['leaderboard'])
        if res != None:
            return res
        timestr = str(datetime.datetime.now())
        print(f"[{timestr}] No active season found", flush=True)
        time.sleep(300)

def getlb(lburl):
    lb = []
    r = nkapi.get(lburl).json()
    while r['next'] != None:
        lb += r['body']
        r = nkapi.get(r['next']).json()
    lb += r['body']
    return lb

def getmatches(profile, proftime):
    matchurl = profile["body"]["matches"]
    r = nkapi.get(matchurl).json()
    minidelta = datetime.timedelta(microseconds=2000)
    for i in reversed(r["body"]):
        mtable = "umatches"
        if i["gametype"] == "Ranked":
            mtable = "matches"
        winner = "draw"
        loser = "draw"
        if mongoclient["b2"][mtable].find_one({"_id":i["id"]}) == None:
            if i["playerLeft"]["result"] == "win":
                winner = i["playerLeft"]["profileURL"]
                loser = i["playerRight"]["profileURL"]
            else:
                winner = i["playerRight"]["profileURL"]
                loser = i["playerLeft"]["profileURL"]
            minidelta = minidelta+datetime.timedelta(microseconds=2000)
            mongoclient["b2"][mtable].insert_one({"_id": i["id"], "date": proftime+minidelta, "season": season, "winner": winner, "loser": loser, "body": i})

def getplayer_hom(lbentry, place):
    r = nkapi.get(lbentry["profile"]).json()
    plid = lbentry["profile"]
    score = lbentry["score"]
    playerentry = r["body"]
    # we should update entry if place/score changes
    playerentry["__place"] = place
    playerentry["__score"] = score
    del playerentry["accolades"]
    #del playerentry["badges_all"]
    lasttime = mongoclient["b2"]['players'].find_one({"plid":plid, "season": season}, sort=[("date", -1)])
    if (lasttime == None):
        proftime = gettime()
        mongoclient["b2"]['players'].insert_one({"plid": plid, "date": proftime-datetime.timedelta(seconds=10) , "season": season, "priv": False, "zomg": False, "score": 3500, "place": 0, "body": playerentry})
        getmatches(r, proftime)
        mongoclient["b2"]['players'].insert_one({"plid": plid, "date": proftime, "season": season, "priv": False, "zomg": False, "score": score, "place": place, "body": playerentry})
    elif not lasttime["body"] == playerentry:
        proftime = gettime()
        getmatches(r, proftime)
        mongoclient["b2"]['players'].insert_one({"plid": plid, "date": proftime, "season": season, "priv": False, "zomg": False, "score": score, "place": place, "body": playerentry})
    return playerentry["displayName"]

if __name__ == "__main__":
    time.sleep(3)
    global mongoclient
    mongoclient = pymongo.MongoClient("mongodb://root:example@database:27017/")
    if mongoclient["sutil"]["sutil"].find_one({"_id":0}) == None:
        mongoclient["sutil"]["sutil"].insert_one({"_id": 0, "seasonid": "no_season", "seasonname": "0", "expire": 0})
    global season
    timestr = str(datetime.datetime.now())
    print(f"[{timestr}] Getting started", flush=True)
    season = ""
    season_end = -1
    while True:
        if (season == "") or (season_end < time.time()):
            s = getseason()
            season = s[0]
            season_end = s[1]
            lburl = s[2]
        stime = time.time()
        lb = getlb(lburl)
        #print(lb, flush=True)
        namelist = []
        for place, i in enumerate(lb):
            pname = getplayer_hom(i, place+1)
            namelist.append(pname)
            #timestr = str(datetime.datetime.now())
            #print(f"[{timestr}] updated {place}", flush=True)
        mongoclient["b2"]['lb'].insert_one({"date": gettime(), "season": season, "lbsize": len(lb), "lb": lb, "namelist": namelist})
        interval = 60*6
        timestr = str(datetime.datetime.now())
        print(f"[{timestr}] Updated {len(lb)} players, it took {round(time.time()-stime)}s ({round(interval-(time.time()-stime))}s to wait)", flush=True)
        if interval-(time.time()-stime) > 0:
            time.sleep(interval-(time.time()-stime))

