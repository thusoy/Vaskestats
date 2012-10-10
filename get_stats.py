#coding: utf-8

'''
Checks the status of the washing machines at Berg Studentby, Trondheim, and logs the result for later analysis.

Data is written to a new file every day, in the format 
{machine name}: {busy_interval_start}-{busy_interval_end}, {busy_interval2_start}-{busy_interval2_end}

A pure counter is written, in the format 
    {timestamp} {num_machines } / {num_occupied} / {num_broken_down}
    
A pickled dump of the data is also written, to ease appending data during the day.

Dependencies: 
    - BeautifulSoup v4.
    - An account to log into the system, user and pw stored in LOGIN_DATA

Tarjei Husøy, 2012
'''

from bs4 import BeautifulSoup
from contextlib import closing
import cPickle as pickle
import os
import time
import urllib2
import logging

URL = 'http://129.241.126.11/LaundryState?lg=2&ly=9106'
LOGIN_DATA = 'C:/login_data.txt'
DATA_DIR = 'data/'
AVG_WASH_DURATION = 46
num_taken = 0
num_broken_down = 0
num_total = 0

def run():
    user, pw = get_user_and_pw()
    page = get_page(URL, user, pw)
    soup = BeautifulSoup(page)
    stats = get_old_data()
    analyze(soup, stats)
    save(stats)
    
def get_page(url, user, pw):
    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, user, pw)
    authhandler = urllib2.HTTPDigestAuthHandler(password_manager)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    with closing(urllib2.urlopen(url)) as response:
        return response.read()
        
def get_user_and_pw():
    with open(LOGIN_DATA) as file_obj:
        lines = file_obj.readlines()
        user = lines[0].strip()
        pw = lines[1].strip()
        logging.info('''Using account '%s'.''', user)
        return user, pw

def analyze(soup, stats):
    global num_total
    for table in soup.find_all('table', class_='tb'):
        for td in table.find_all('td', class_='p'):
            num_total += 1
            name = td.find('b').get_text()
            machine_id = get_machine_id(name)
            status = td.find('br').get_text()
            clean = clean_status(status)
            times_occupied = stats.get(machine_id, [])
            if clean: 
                times_occupied.append(clean)
            stats[machine_id] = times_occupied
    return stats
            
def clean_status(status):
    global num_taken
    global num_broken_down
    stat_entry = None
    if status.startswith('Resttid: '):
        start_of_time_index = status.find(': ') + 2
        min_remaining = int(status[start_of_time_index:status.find(' min')])
        min_since_start = AVG_WASH_DURATION - min_remaining
        starttime = time.time() - min_since_start * 60
        endtime = time.time() + min_remaining * 60
        start = get_time_formatted('%H:%M', starttime)
        end = get_time_formatted('%H:%M', endtime)
        stat_entry = '%s-%s' % (start, end)
        num_taken += 1
    elif status == 'Opptatt':
        start = get_time_formatted('%H:%M')
        end_time = time.time() + AVG_WASH_DURATION * 60
        end = get_time_formatted('%H:%M', end_time)
        stat_entry = '%s-%s' % (start, end)
        num_taken += 1
    elif status.startswith('Ute av drift'):
        stat_entry = status
        num_broken_down += 1
    elif status.startswith('Ledig '):
        pass
    else:
        logging.warning('Ukjent status: %s', status)
    return stat_entry

def save(stats):
    filename = get_todays_filename()
    with open(DATA_DIR + filename + '.txt', 'w+') as file_obj:
        machines = stats.keys()
        machines.sort()
        for machine in machines:
            file_obj.write(machine + ': ')
            file_obj.write(', '.join(stats[machine]))
            file_obj.write('\n')
    with open(DATA_DIR + filename + '.pickle', 'w+') as file_obj:
        pickle.dump(stats, file_obj)
    with open(DATA_DIR + 'counter.txt', 'a+') as file_obj:
        current_time = get_time_formatted('%d.%m.%y %H:%M')
        file_obj.write('%s %d / %d / %d\n' % (current_time, num_total, num_taken, num_broken_down))
    
def get_time_formatted(time_format, timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    localtime = time.localtime(timestamp)
    return time.strftime(time_format, localtime)

def get_todays_filename():
    date = get_time_formatted('%d-%m-%y')
    return date

def get_old_data():
    filename = get_todays_filename() + '.pickle'
    try:
        with open(DATA_DIR + filename) as file_obj:
            return pickle.load(file_obj)
    except:
        # First run of the day
        #TODO Old dumps will be aggregating, delete all except the last one.
        
        return {}
    
def get_machine_id(machine_name):
    machine_num = int(machine_name.split()[1])
    machine_id = 'Machine #%2d' % machine_num
    return machine_id
    
def init():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    logging.basicConfig(filename='log.log', format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
    logging.info('Starting data mining.')
        
if __name__ == '__main__':
    init()
    try:
        run()
        logging.info('Completed successfully.')
    except:
        logging.exception('Something failed.')
