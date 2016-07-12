#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib, urllib2, cookielib
from HTMLParser import HTMLParser
import requests
import shutil
import traceback
import re
import os
import Queue
from threading import Thread
from threading import current_thread
import sys
import socket
import time
import platform
if platform.system() == 'Windows':
    import msvcrt

def reporthook(a,b,c):
    # ',' at the end of the line is important!
    # print "% 3.1f%% of %d bytes\r" % (min(100, float(a * b) / c * 100), c),
    #you can also use sys.stdout.write
    sys.stdout.write("\r% 3.1f%% of %d bytes" % (min(100, float(a * b) / c * 100), c))
    sys.stdout.flush()

def download(name, sess, url, path):

    if not os.path.isfile(path):
        try:
            resp = sess.get(url)

            # Check return code
            if resp.status_code == 404:
                return True
            if not resp.status_code == 200:
                sys.stdout.write('*RET '+name+', code = '+str(resp.status_code)+' '+ url +'\n')
                return False

            # Check length
            total_length = int(resp.headers.get('content-length'))
            actual_length = len(resp.content)
            if not total_length == actual_length:
                sys.stdout.write('*SHORT '+name+', '+str(actual_length)+' of '+str(total_length)+' '+ url +'\n')
                return False

            # Write to file
            with open(path, 'wb') as file:
                resp.raw.decode_content = True
                file.write(resp.content)

        except:
            exc_info = sys.exc_info()
            traceback.print_exception(*exc_info)
            try:
                os.remove(path)
            except:
                pass
            return False

    return True

def worker(sess, msg):
    #threadName = current_thread().getName()

    post = msg[0]
    url = msg[1]
    sys.stdout.write('PROC '+str(post)+' '+ url +'\n')


    filename = re.match('.*/(.*)',url).group(1)
    #filename = re.match('.*/(.*\.(?:jpg|gif|jpeg|png))',url).group(1)
    directory = 'download/'+str(post)

    try:
        os.makedirs(directory)
    except:
        #exc_info = sys.exc_info()
        #traceback.print_exception(*exc_info)
        pass

    path = directory+'/'+filename
    return download(str(post), sess, url, path);

def proc(Q):

    # Q item: (cmd,msg)
    # cmd: 99   quit
    # cmd: 1    process
    # cmd: 0    process-first

    sess = requests.Session()

    while True:
        item = Q.get(True)
        Q.task_done()
        time.sleep(1)

        if item[0] is 99:
            sys.stdout.write('['+current_thread().getName()+'] quit\n')
            break

        if not worker(sess,item[1]):
            time.sleep(30)
            # sess = requests.Session()
            Q.put((0,item[1]))

def dispatcher(Q):

    sess = requests.Session()

    #already have 255922 - 252674
    # 638278 - 599893
    for i in range(582895,255922,-1):
        time.sleep(1)

        if platform.system() == 'Windows' and msvcrt.kbhit():
            keyPress=msvcrt.getch()
            if keyPress == 's':
                print 'Key Press: '+ keyPress
                break
        else:
            keyPress=None

        print '-------------------------------------',i
        link = 'http://bcy.net/coser/detail/1/'+str(i)

        content = None

        while True:
            try:
                resp = sess.get(link, timeout=5)
            except requests.exceptions.ConnectionError:
            #except requests.exceptions.Timeout:
                sess = requests.Session()
                time.sleep(30)
                continue

            # Check return code
            if resp.status_code == 404:
                break

            if not resp.status_code == 200:
                print '------------------------------------- RET =', resp.status_code
                sess = requests.Session()
                time.sleep(30)
                continue

            content = resp.text
            break;

        #with open("Output.html", "w") as f:
        #   f.write(content.encode("utf-8", "replace"))

        if content==None or content.find(u'[正片]') == -1:
            continue

        match = re.findall('<img class=\'detail_std detail_clickable\' src=\'(\S*?)(?:|/w650)\' />', content)
        #match = re.findall('.*?detail_clickable.*?(http://img.+?\.bcyimg.com/.*?\.(?:jpg|gif|jpeg|png)).*?', content)
        #print match
        #exit(1)

        if len(match) == 0:
            continue

        for m in match:
            if not 'photo' in m:
                #print 'put',m
                if len(m) > 100:
                    continue
                yield (str(i),m)

def main():

    THREAD_NUMBER = 5

    Q = Queue.PriorityQueue()
    keyPress=None

    workers = []
    for i in range(THREAD_NUMBER):
        worker = Thread(target=proc, args=(Q,))
        worker.setDaemon(True)
        worker.start()
        workers.append(worker)

    for msg in dispatcher(Q):
        while Q.qsize() > 2 * THREAD_NUMBER:
            time.sleep(1)
        Q.put((1,msg))

    for i in range(len(workers)):
        Q.put((99,None))

    print '[Main] Joining Queue'
    Q.join()
    print '[Main] Joining Threads'
    for worker in workers:
        worker.join()

if __name__ == '__main__':
    main()
