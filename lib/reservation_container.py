#!/usr/bin/python
'''
reservation_container.py - Look up reservation data for a given facility
'''
import collections
import datetime
import logging
import re
import time

from pyvirtualdisplay import Display
from selenium import webdriver

SECONDS_SLEEP = 5
DRIVER_START_NUM_RETRIES = 20
WEBDRIVER_START_ERROR_STR = (
    'Could not start webdriver: facility {facility_id}, try {try_num}'
)
WEBDRIVER_START_FAILURE_STR = (
    'Failed to start webdriver for {facility_id} after {try_num} tries.'
)

display = Display(visible=0, size=(1600, 900))
display.start()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReservationContainer(object):
    '''
    Contains data and methods required to look up a facility's reservation data
    '''
    RECREATION_GOV_URL = ('http://www.recreation.gov/campsiteCalendar.do?page='
                          'matrix&calarvdate=%s&contractCode=NRSO&parkId=%s')

    RECREATION_GOV_ROOT = 'http://www.recreation.gov%s'
    APOLOGY_STRING = 'Our apologies. We are experiencing some difficulties.'
    NEXT_PAGE_REGEX = r'<a id="resultNext" href="(\S+)">'

    RESERVATION_REGEX = (r'<div title=".*?class="loopName">(.*?)</div></td>\n'
                         '<td class="status (.).*?<td class="status (.).*?'
                         '<td class="status (.).*?<td class="status (.).*?'
                         '<td class="status (.).*?<td class="status (.).*?'
                         '<td class="status (.).*?<td class="status (.).*?'
                         '<td class="status (.).*?<td class="status (.).*?'
                         '<td class="status (.).*?<td class="status (.).*?'
                         '<td class="status (.).*?<td class="status (.).*?'
                         '<tr class="separator">')

    @staticmethod
    def initialize_webdriver(legacy_facility_id):
        '''
        Create a firefox selenium webdriver.  Retry a set number of times and
        raise Exception if driver cannot be created after that set number of
        retries.
        '''
        for i in range(0, DRIVER_START_NUM_RETRIES):
            try:
                driver = webdriver.Firefox()
            except Exception:
                logger.debug(
                    WEBDRIVER_START_ERROR_STR.format(
                        facility_id=legacy_facility_id,
                        try_num=i
                    )
                )
                time.sleep(SECONDS_SLEEP)
                continue

            return driver

        raise Exception(
            WEBDRIVER_START_FAILURE_STR.format(
                facility_id=legacy_facility_id,
                try_num=DRIVER_START_NUM_RETRIES
            )
        )

    def available_campsites_at_facility(self, legacy_facility_id, start_date,
                                        finish_date):
        ''' Return list of available campsites by dates for a recarea. '''
        driver = self.initialize_webdriver(legacy_facility_id)
        date_page_list = [start_date]
        while finish_date - date_page_list[-1] > datetime.timedelta(days=14):
            date_page_list.append(
                date_page_list[-1] + datetime.timedelta(days=14)
            )

        campsite_date_dict = {}
        for date in date_page_list:
            campsites_by_date = self.find_available_campsites_on_day(
                date,
                legacy_facility_id,
                driver
            )
            campsite_date_dict.update(campsites_by_date)

        keys_for_removal = []
        for date in campsite_date_dict:
            if date < start_date or date >= finish_date:
                keys_for_removal.append(date)

        for key in keys_for_removal:
            campsite_date_dict.pop(key)

        campsite_str_date_dict = {}
        for date in campsite_date_dict:
            date_str = date.isoformat()
            campsite_str_date_dict[date_str] = campsite_date_dict[date]

        driver.quit()
        return campsite_str_date_dict

    def find_available_campsites_on_day(self, date, park_id, driver):
        ''' Find all available campsites for given park on given day. '''
        date_string = '{0}/{1}/{2}'.format(date.month, date.day, date.year)
        next_page_url = self.RECREATION_GOV_URL % (date_string, park_id)
        campsites_by_date = {}
        while next_page_url:
            next_page_url = next_page_url.replace('&amp;', '&')
            result_tuple = self.scrape_reservation_page(next_page_url,
                                                        date,
                                                        driver)

            (next_page_url, campsites_on_page) = result_tuple

            for this_date in campsites_on_page:
                if this_date in campsites_by_date:
                    existing_campsite_counter = collections.Counter(
                        campsites_by_date[this_date]
                    )
                    new_campsite_counter = collections.Counter(
                        campsites_on_page[this_date]
                    )
                    campsites_by_date[this_date] = dict(
                        existing_campsite_counter + new_campsite_counter
                    )
                else:
                    campsites_by_date[this_date] = campsites_on_page[this_date]

        driver.delete_all_cookies()
        return campsites_by_date


    def scrape_reservation_page(self, page_url, date, driver):
        ''' Scrape a single reservation url to get all available campsites. '''
        next_page_url = None
        campsites_by_date = {}
        driver.get(page_url)
        if driver.page_source.find(self.APOLOGY_STRING) == -1:
            reservation_match_list = re.findall(self.RESERVATION_REGEX,
                                                driver.page_source,
                                                re.DOTALL)

            for reservation_match in reservation_match_list:
                campsite_name = reservation_match[0]
                day_status_list = reservation_match[1:]
                for i, reservation_status in enumerate(day_status_list):
                    this_date = date + datetime.timedelta(days=i)
                    if ((reservation_status == 'a') or
                            (reservation_status == 'w')):
                        if this_date not in campsites_by_date:
                            campsites_by_date[this_date] = {}

                        if campsite_name not in campsites_by_date[this_date]:
                            campsites_by_date[this_date][campsite_name] = 1
                        else:
                            campsites_by_date[this_date][campsite_name] += 1

            next_page_match = re.search(self.NEXT_PAGE_REGEX,
                                        driver.page_source)

            if next_page_match and next_page_match.group(1):
                next_page_url = (self.RECREATION_GOV_ROOT
                                 % next_page_match.group(1))

        return (next_page_url, campsites_by_date)
