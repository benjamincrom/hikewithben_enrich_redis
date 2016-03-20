#!/usr/bin/python
"""
test_reservation_container.py - Unit tests for ReservationContainer class
"""
import datetime

from lib import reservation_container

reservation_obj = reservation_container.ReservationContainer()

def test_available_campsites_at_facility():
    assert reservation_obj.available_campsites_at_facility(
        72393,
        datetime.datetime.today(),
        datetime.datetime.today() + datetime.timedelta(days=40)
    )

def test_find_available_campsites_on_day():
    assert reservation_obj.find_available_campsites_on_day(
        datetime.datetime.today() + datetime.timedelta(days=20),
        73984
    )

def test_scrape_reservation_page():
    assert reservation_obj.scrape_reservation_page(
        ('http://www.recreation.gov/campsiteCalendar.do?page=calendar&'
         'contractCode=NRSO&parkId=72393'),
        datetime.datetime.today()
    )
