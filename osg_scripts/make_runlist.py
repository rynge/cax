import pymongo
import os
import sys


def make_runlist():
    uri = 'mongodb://eb:%s@xenon1t-daq.lngs.infn.it:27017,copslx50.fysik.su.se:27017,zenigata.uchicago.edu:27017/run'
    uri = uri % os.environ.get('MONGO_PASSWORD')
    c = pymongo.MongoClient(uri,
                            replicaSet='runs',
                            readPreference='secondaryPreferred')
    db = c['run']
    collection = db['runs_new']
    
    query = {"detector" : "tpc",
             "tags.name" : "_sciencerun0",
             #"$or" : [{"tags.name" : "_sciencerun0"},{"tags.name" : "_sciencerun0_candidate"}],
             "source.type" : "AmBe"}
             #"source.type" : {"$ne" : "LED"}}

    cursor = collection.find(query, {"number" : True,
                                     "data" : True,
                                     "trigger.events_built" : True,
                                     "_id" : False})
    
    cursor = list(cursor)
    
    print("Total runs: %d" % len(cursor))
    bad = []
    stashlist = []
    processed_list = []
    processing = []
    stage_list = []
    not_rucio = []
    error = []

    for run in cursor:
        on_stash = False
        on_midway = False
        on_rucio = False

        processed = False

        if 'data' not in run or 'trigger' not in run or 'events_built' not in run['trigger']:
            bad.append(run['number'])
            continue

        if run["trigger"]["events_built"] < 1:
            bad.append(run['number'])
            continue

        for d in run['data']:
            if d['type'] == 'processed' and 'pax_version' in d:
                if d['pax_version'] == 'v6.4.2' and d['status'] == 'transferred':
                    processed  = True
                    #continue

                elif d['pax_version'] == 'v6.4.2' and d['status'] == 'transferring' and d['host'] == 'login':
                    processing.append(run['number'])
                    #continue
                
                elif d['pax_version'] == 'v6.4.2' and d['status'] == 'error' and d['host'] == 'login':
                    error.append(run['number'])

            if d['host'] == 'rucio-catalogue' and d['type']=='raw' and d['status'] == 'transferred':
                if 'UC_OSG_USERDISK' in d['rse']:
                    on_stash = True
                on_rucio = True

            elif d['host'] == 'login' and d['type']=='raw' and d['status'] == 'transferred':
                if os.path.exists(d['location']):
                    on_stash = True

            elif d['host'] == 'midway-login1' and d['type']=='raw' and d['status'] == 'transferred':
                on_midway = True

        if processed:
            processed_list.append(run["number"])
            continue
        if run["number"] in processing:
            continue
        if on_stash or on_midway:
            stashlist.append(run["number"])

        else:
            if on_rucio:
                stage_list.append(run["number"])
            else:
                not_rucio.append(run["number"])


    #return stashlist
    print("BAD: %d" % len(bad))

    print("NOT IN RUCIO OR CHICAGO: %d" % len(not_rucio))
#    print(not_rucio)

    print("TO STAGE: %d" % len(stage_list))
    print(stage_list)

    print("ON STASH OR MIDWAY: %d" % len(stashlist))
#    print(stashlist)

    print("PROCESSING: %d" % len(processing))
    print(processing)

    print("PROCESSED: %d" % len(processed_list))
    #print(processed_list)

    print("ERROR: %d" % len(error))
    print(error)

    stashlist = [r for r in stashlist if r not in error and r not in processing]
    return stashlist

if __name__ == '__main__':
    make_runlist()
    