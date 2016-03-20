#!/usr/bin/python
'''
redis_daemon.py - Run this script to put the redis database in the correct
                  state.  It will initialize the database with weather-enriched
                  recarea data and then fetch the latest reservation data.
'''
import datetime
import json
import logging
import multiprocessing
import os

import redis

from lib.reservation_container import ReservationContainer

DB_FILE_STR = 'files/recareas-{file_id}-of-{total_files}.json'
DEFAULT_PROCESS_POOL_SIZE = 72
TOTAL_DB_FILES = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_instance = redis.from_url(os.environ['REDIS_URL'])

def enrich_recarea_entry(parameter_tuple):
    '''
    Fetch reservation data for the given recarea and update the recarea's
    redis entry.
    '''
    try:
        reservation_obj = ReservationContainer()
        (recarea, start_date, finish_date) = parameter_tuple
        recarea_id = int(recarea['RecAreaID'])

        for facility in recarea.get('facilities'):
            if 'LegacyFacilityID' in facility and facility['LegacyFacilityID']:
                facility_legacy_id = int(facility['LegacyFacilityID'])
                date_str = '%s/%s/%s' % (start_date.month,
                                         start_date.day,
                                         start_date.year)

                facility['reservation_url'] = (
                    reservation_obj.RECREATION_GOV_URL
                    % (date_str, facility_legacy_id)
                )

                facility['reservation'] = (
                    reservation_obj.available_campsites_at_facility(
                        facility_legacy_id,
                        start_date,
                        finish_date
                    )
                )

                if facility.get('reservation'):
                    with open(str(facility_legacy_id), 'w') as filehandle:
                        filehandle.write(
                            '{}: {}\n{}\n'.format(
                                recarea.get('RecAreaName'),
                                facility.get('FacilityName'),
                                facility.get('reservation'),
                            )
                        )

        redis_instance.set(str(recarea_id), json.dumps(recarea))
    except Exception, e:
        logger.error('Recarea %s: %s', int(recarea['RecAreaID']), e)

def enrich_redis_recareas_dict():
    '''
    Map all recareas to the process pool.  The pool will fetch reservation
    data for each recarea.
    '''
    start_date = datetime.date.today()
    finish_date = datetime.date(start_date.year, 12, 31)

    parameter_tuple_list = []
    for recarea_id_str in redis_instance.keys():
        recarea = json.loads(redis_instance.get(recarea_id_str))
        if 'facilities' in recarea:
            parameter_tuple_list.append((recarea, start_date, finish_date))

    process_pool = multiprocessing.Pool(DEFAULT_PROCESS_POOL_SIZE)
    results = process_pool.map_async(enrich_recarea_entry, parameter_tuple_list)
    results.get()

if __name__ == '__main__':
    enrich_redis_recareas_dict()
