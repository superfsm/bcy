#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
import Queue
import re
import sys
import time
import traceback
from threading import Thread
from threading import current_thread

import requests
if platform.system() == 'Windows':
    import msvcrt


def reporthook(a, b, c):
    # ',' at the end of the line is important!
    # print "% 3.1f%% of %d bytes\r" % (min(100, float(a * b) / c * 100), c),
    # you can also use sys.stdout.write
    sys.stdout.write("% 3.1f%% of %d bytes" %
                     (min(100, float(a * b) / c * 100), c))
    sys.stdout.flush()


def url_get_retry(sess, tag, url):

    _TIMEOUT = 5
    _RETRY_AFTER = 30
    _MAX_RETRY = 3

    retry = 0
    while True:
        retry += 1
        if retry > _MAX_RETRY:
            sys.stdout.write('*MAX_RETRY %s %s\n' % (tag, url))
            return None

        try:
            resp = sess.get(url, timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError:
            sys.stdout.write('*TIMEOUT %s %s\n' % (tag, url))
            time.sleep(_RETRY_AFTER)
            continue
        except:
            exc_info = sys.exc_info()
            traceback.print_exception(*exc_info)
            time.sleep(RETRY_AFTER)
            continue

        # Check return code
        if resp.status_code == 404:
            sys.stdout.write('*RET %s, code = %d, %s\n' %
                             (tag, resp.status_code, url))
            return None

        if not resp.status_code == 200:
            sys.stdout.write('*RET %s, code = %d, %s\n' %
                             (tag, resp.status_code, url))
            time.sleep(_RETRY_AFTER)
            continue

        # Check length
        if resp.headers.get('content-length') is not None:
            total_length = int(resp.headers.get('content-length'))
            actual_length = len(resp.content)
            if not total_length == actual_length:
                sys.stdout.write('*SHORT %s (%d of %d) %s\n' %
                                 (tag, actual_length, total_length, url))
                time.sleep(_RETRY_AFTER)
                continue

        return resp

# return Boolean


def download_file(tag, sess, url, path):

    if not os.path.isfile(path):
        try:
            resp = url_get_retry(sess, tag, url)

            if resp is None:
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
    # threadName = current_thread().getName()

    post = msg[0]
    url = msg[1]
    # sys.stdout.write('PROC %s %s\n' % (post, url))

    filename = re.match('.*/(.*)', url).group(1)
    # filename = re.match('.*/(.*\.(?:jpg|gif|jpeg|png))',url).group(1)
    directory = 'download/' + post

    try:
        os.makedirs(directory)
    except:
        # exc_info = sys.exc_info()
        # traceback.print_exception(*exc_info)
        pass

    path = directory + '/' + filename
    download_file(post, sess, url, path)
    sys.stdout.write('DONE %s %s\n' % (post, url))
    return True


def _consumer(Q):

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
            sys.stdout.write('[%s] quit\n' % current_thread().getName())
            break

        worker(sess, item[1])


def producer(Q):

    sess = requests.Session()

    # already have 255922 - 252674
    # 638278 - 599893
    for i in range(493687,255922,-1):
        time.sleep(0.5)

        if platform.system() == 'Windows' and msvcrt.kbhit():
            keyPress = msvcrt.getch()
            if keyPress == 's':
                print 'Key Press: ' + keyPress
                break
        else:
            keyPress = None

        sys.stdout.write('-------------------------------------%d\n' % i)
        url = 'http://bcy.net/coser/detail/1/' + str(i)

        content = None

        resp = url_get_retry(sess, 'producer', url)

        if resp is None:
            continue

        content = resp.text

        # with open("Output.html", "w") as f:
        #   f.write(content.encode("utf-8", "replace"))

        if content is None or content.find(u'[正片]') == -1:
            continue

        match = re.findall(
            '<img class=\'detail_std detail_clickable\' src=\'(\S*?)(?:|/w650)\' />', content)
        # match = re.findall('.*?detail_clickable.*?(http://img.+?\.bcyimg.com/.*?\.(?:jpg|gif|jpeg|png)).*?', content)
        # print match
        # exit(1)

        if len(match) == 0:
            continue

        for m in match:
            if not 'photo' in m:
                # print 'put',m
                if len(m) > 100:
                    continue
                yield (str(i), m)


def main():

    _THREAD_NUMBER = 5

    Q = Queue.PriorityQueue()
    keyPress = None

    workers = []
    for i in range(_THREAD_NUMBER):
        worker = Thread(target=_consumer, args=(Q,), name=str(i + 1))
        worker.setDaemon(True)
        worker.start()
        workers.append(worker)

    for msg in producer(Q):
        while Q.qsize() > 2 * _THREAD_NUMBER:
            time.sleep(1)
        Q.put((1, msg))

    for i in range(len(workers)):
        Q.put((99, None))

    print '[Main] Joining Queue'
    Q.join()
    print '[Main] Joining Threads'
    for worker in workers:
        worker.join()

if __name__ == '__main__':
    main()
