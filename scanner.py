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
    latestbeg = -1
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
            #if (i['start'] <= time.time()*1000) and
            if (i['start'] > latestbeg):
                latest = i
                latestbeg = i['end']
                seasonN = [int(i) for i in i["name"].split() if i.isdigit()][0]
                mongoclient["sutil"]["sutil"].update_one({"_id": 0}, {"$set": {"seasonid": i['id'], "seasonname": i["name"], "seasonN": seasonN, "expire": i['end']//1000}})
                print(f"Found new latest season {season} (ending at {season_end})", flush=True)
        if True or res != None:
            #if (i['start'] <= time.time()*1000) and (i['end'] > time.time()*1000):
            season = latest['id']
            season_end = latest['end']//1000
            print(f"Found currenttly active season {season} (ending at {season_end})", flush=True)
            mongoclient["b2"]["players"].create_index(["plid", ("date", -1)], background=True)
            mongoclient["b2"]["players"].create_index(["season", "plid", ("date", -1)], background=True)
            mongoclient["b2"]["lb"].create_index(["season", ("date", -1)], background=True)
            mongoclient["b2"]["lb"].create_index([("date", -1)], background=True)
            mongoclient["b2"]["matches"].create_index(["season", "winner", ("date", -1)], background=True)
            mongoclient["b2"]["matches"].create_index(["season", "loser", ("date", -1)], background=True)
            mongoclient["b2"]["matches"].create_index(["season", "winner"], background=True)
            mongoclient["b2"]["matches"].create_index(["season", "loser"], background=True)
            res = (season, season_end, latest['leaderboard'])
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

def getmatches(profile, plid, lblist, scantime):
    matchurl = profile["body"]["matches"]
    r = nkapi.get(matchurl).json()
    if (mongoclient['b2']['latestm'].find_one({"_id": plid})==None) and (len(r["body"]) > 0):
        mongoclient['b2']['latestm'].insert_one({"_id": plid, "match": None})
    for i in reversed(r["body"]):
        mtable = "umatches"
        if i["gametype"] == "Ranked":
            mtable = "matches"
        if i["gametype"] == "Ranked" and ((not mongoclient["b2"]["zmatches"].find_one({"_id":i["id"]}) == None) or (not (i["playerRight"]["profileURL"] in lblist and i["playerLeft"]["profileURL"] in lblist))):
            mtable = "zmatches"
        winner = "draw"
        loser = "draw"
        if i["playerLeft"]["result"] == "win":
            winner = i["playerLeft"]["profileURL"]
            loser = i["playerRight"]["profileURL"]
        if i["playerRight"]["result"] == "win":
            winner = i["playerRight"]["profileURL"]
            loser = i["playerLeft"]["profileURL"]
        if mongoclient["b2"][mtable].find_one({"_id":i["id"]}) == None:
            mongoclient["b2"][mtable].insert_one({"_id": i["id"], "date": scantime, "season": season, "winner": winner, "loser": loser, "body": i})
        if mtable == "matches":
            mongoclient['b2']['latestm'].update_one({"_id": plid}, {"$set": {"_id": plid, "match": {"_id": i["id"], "date": scantime, "season": season, "winner": winner, "loser": loser, "body": i}}})


def getplayer_hom(lbentry, place, lblist, scantime):
    r = nkapi.get(lbentry["profile"]).json()
    plid = lbentry["profile"]
    score = lbentry["score"]
    playerentry = r["body"]
    # we should update entry if place/score changes
    playerentry["__place"] = place
    playerentry["__score"] = score
    del playerentry["accolades"]
    #del playerentry["badges_all"]
    getmatches(r, plid, lblist, scantime)
    lasttime = mongoclient["b2"]['players'].find_one({"plid":plid, "season": season}, sort=[("date", -1)])
    if (lasttime == None):
        mongoclient["b2"]['players'].insert_one({"plid": plid, "date": scantime-datetime.timedelta(seconds=10) , "season": season, "priv": False, "zomg": False, "score": 3500, "place": 0, "body": playerentry})
        mongoclient["b2"]['players'].insert_one({"plid": plid, "date": scantime, "season": season, "priv": False, "zomg": False, "score": score, "place": place, "body": playerentry})
    elif not lasttime["body"] == playerentry:
        mongoclient["b2"]['players'].insert_one({"plid": plid, "date": scantime, "season": season, "priv": False, "zomg": False, "score": score, "place": place, "body": playerentry})
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
        scantime = gettime()
        lb = getlb(lburl)
        lblist = []
        for i in lb:
            tmp = i["profile"]
            lblist.append(tmp)
        #print(lblist, flush=True)
        #print(lb, flush=True)
        namelist = []
        for place, i in enumerate(lb):
            pname = getplayer_hom(i, place+1, lblist, scantime)
            namelist.append(pname)
            #print(place, flush=True)
            #timestr = str(datetime.datetime.now())
            #print(f"[{timestr}] updated {place}", flush=True)
        mongoclient["b2"]['lb'].insert_one({"date": scantime, "season": season, "lbsize": len(lb), "lb": lb, "namelist": namelist})
        interval = 60*5
        timestr = str(datetime.datetime.now())
        print(f"[{timestr}] Updated {len(lb)} players, it took {round(time.time()-stime)}s ({round(interval-(time.time()-stime))}s to wait)", flush=True)
        if interval-(time.time()-stime) > 0:
            time.sleep(interval-(time.time()-stime))

