#coding: utf-8

'''
Checks the status of the washing machines at Berg Studentby, Trondheim, and logs the result for later analysis.

Data is written to a new file every day, in the format 
{machine name}: {busy_interval_start}-{busy_interval_end}, {busy_interval2_start}-{busy_interval2_end}

The internal data structure, the dict stats, is constructed like this:
stats[machine_id] = [(starttime, endtime), (starttime2, endtime2)]

or, in the event that a wash isnt completed yet, the last entry for a machine is the tuple (starttime, None).

A pure counter is written, in the format 
    {timestamp} {num_machines } / {num_occupied} / {num_broken_down}
    
A pickled dump of the data is also written, to ease appending data during the day.

Dependencies: 
    - BeautifulSoup v4.
    - An account to log into the system, user and pw stored in LOGIN_DATA

Tarjei Husøy, 2012

Licensed under a new-style BSD license, see LICENSE.txt.
'''

from bs4 import BeautifulSoup
from contextlib import closing
from machine import *
import logging
import os
import pickle
import re
import sys
import time
try:
    #python 3
    from urllib import request as url_src
except ImportError:
    #python 2
    import urllib2 as url_src

__author__ = 'Tarjei Husøy (admin@husoymedia.no)'
__version__ = 0.3
__copyright__ = 'Copyright (c) 2012 Tarjei Husøy'
__licencse__ = 'New-style BSD'
__status__ = 'Development'

URL = 'http://129.241.126.11/LaundryState?lg=2&ly=9106'
LOGIN_DATA = 'login_data.txt'
DATA_DIR = 'data/'

def init():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    logging.basicConfig(filename='log.log', format='%(asctime)s %(levelname)-10s %(message)s', level=logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    
def run():
    user, pw = get_user_and_pw()
    page = get_page(URL, user, pw)
    soup = BeautifulSoup(page)
    stats = get_old_data()
    logging.debug('Input data: ' + str(stats))
    analyze(soup, stats)
    save(stats)
    
def get_user_and_pw():
    with open(LOGIN_DATA) as file_obj:
        lines = file_obj.readlines()
        user = lines[0].strip()
        pw = lines[1].strip()
        logging.info('''Using account '%s'.''', user)
        return user, pw
    
def get_page(url, user, pw):
    password_manager = url_src.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, user, pw)
    authhandler = url_src.HTTPDigestAuthHandler(password_manager)
    opener = url_src.build_opener(authhandler)
    url_src.install_opener(opener)
    with closing(url_src.urlopen(url)) as response:
        return response.read()
        
def get_old_data():
    filename = get_todays_filename() + '.pickle'
    try:
        with open(DATA_DIR + filename, 'rb') as file_obj:
            logging.info('Fould earlier data from today, reading...')
            return pickle.load(file_obj)
    except:
        # First run of the day
        logging.info('No earlier data from today found.')
        delete_old_files(filename)
        return {}

def delete_old_files(todays_filename):
    pickles = re.compile("^(\d{1,2}-){2}(\d{2})\.pickle")
    for file in os.listdir(DATA_DIR):
        if pickles.match(file) and not file == todays_filename:
            logging.debug('Deleting old file: ' + str(file))
            os.remove(DATA_DIR + file)

def analyze(soup, stats):
    for machine in find_statuses(soup):
        times_occupied = stats.get(machine, [])
        machine_running = bool(times_occupied and times_occupied[-1][1] is None)
        if isinstance(machine, OccupiedMachine):
            if machine_running:
                # Still running
                logging.info('%s is still running.', machine)
            else:
                # New run found
                start = get_time_formatted()
                stat_entry = (start, None)
                logging.info('%s has been started.', machine)
                times_occupied.append(stat_entry)
        elif isinstance(machine, AvailableMachine):
            if machine_running:
                # Last time we checked it was running
                logging.info('%s has finished, and is available.', machine)
                last_entry = times_occupied[-1]
                del times_occupied[-1]
                new_entry = (last_entry[0], get_time_formatted())
                times_occupied.append(new_entry)
            else:
                # No change
                logging.info('%s is available', machine)
        elif isinstance(machine, BrokenDownMachine):
            if times_occupied and times_occupied[-1] == 'Ute av drift':
                # No change
                logging.info('%s is still broken down.', machine)
            else:
                # New machine has broken down
                times_occupied.append('Ute av drift')
                logging.info('%s has broken down.', machine)
        elif isinstance(machine, UnknownMachine):
            logging.warning('%s has an unknown status: %s', machine, machine.status)
        elif isinstance(machine, ClosedMachine):
            if machine_running:
                last_entry = times_occupied[-1]
                del times_occupied[-1]
                new_entry = (last_entry[0], get_time_formatted())
                times_occupied.append(new_entry)
                logging.info('%s is finishing final run before closing.', machine)
            else:
                logging.info('%s is closed.', machine)
                
        stats[machine] = times_occupied
            
def save(stats):
    filename = get_todays_filename()
    
    #Save the stats
    with open(DATA_DIR + filename + '.txt', 'w+') as file_obj:
        machines = sorted(stats.keys(), key=lambda m: m.machine_id)
        for machine in machines:
            file_obj.write('%s: ' % machine)
            file_obj.write(', '.join(str(entry) for entry in stats[machine]))
            file_obj.write('\n')
            
    # Save the pickled stats
    with open(DATA_DIR + filename + '.pickle', 'wb+') as file_obj:
        pickle.dump(stats, file_obj)
        
    # Save the counts
    with open(DATA_DIR + 'counter.txt', 'a') as file_obj:
        current_time = get_time_formatted('%d.%m.%y %H:%M')
        output_format = '{time} {num_total} / {num_available} / {num_broken_down}\n'
        file_obj.write(output_format.format(num_total=Machine.num_machines,
                  num_available=AvailableMachine.num_available,
                  num_broken_down=BrokenDownMachine.num_broken_down,
                  time=current_time))
    logging.debug('Output data: ' + str(stats))
    
def get_todays_filename():
    date = get_time_formatted('%d-%m-%y')
    return date

def find_statuses(soup):
    for table in soup.find_all('table', class_='tb'):
        for td in table.find_all('td', class_='p'):
            name = td.find('b').get_text()
            machine_id = get_machine_id(name)
            if sys.version_info[0] >= 3:
                status_text = ' '.join(list(td.children)[2:-1:2])
            else:
                status_text = list(td.children)[1].get_text()
            machine = get_machine(machine_id, status_text)
            yield machine
            
def get_time_formatted(time_format='%H:%M', timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    localtime = time.localtime(timestamp)
    return time.strftime(time_format, localtime)

def get_machine(machine_id, status):
    machine = None
    if status.startswith('Resttid: ') or status == 'Opptatt':
        machine = OccupiedMachine(machine_id)
    elif status.startswith('Ute av drift'):
        machine = BrokenDownMachine(machine_id)
    elif status.startswith('Ledig '):
        machine = AvailableMachine(machine_id)
    elif status.startswith('Steng'):
        machine = ClosedMachine(machine_id)
    else:
        machine = UnknownMachine(machine_id, status)
    return machine

if __name__ == '__main__':
    init()
    try:
        logging.info('Starting data mining.')
        run()
        logging.info('Completed successfully.\n')
    except:
        logging.exception('Something failed.')
