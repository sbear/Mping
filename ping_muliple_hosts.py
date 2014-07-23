#!env python
# -*- coding: utf-8 -*-
import os, sys
import threading
import Queue
import re
import time

from ping import Ping

class Mping(object):
    '''
    并发ping
    从host列表中获取需要ping的机器列表，过滤掉暂时需要屏蔽的机器列表，
    根据需要过滤在指定检查周期内已经告警过的机器
    '''
    
    def __init__(self, hostlistfile, ignorelistfile, resultfile='Mping_resulst.list', repeatalarm=False,  timeout=1000, count=10, lastcount=10):
        self.hosts = []
        self.ignores = []
        self.job_queue = Queue.Queue()
        self.result_queue = Queue.Queue()
        self.count = count
        self.last_count = lastcount
        self.repeat_alarm = repeatalarm
        self.result_file = resultfile
        self.last_badip = []
        self.log_file = 'Mping.log'
        self.badip = []

        try:
            hostfh = open(hostlistfile, 'r')
            for line in hostfh:
                # 去掉多余的空格和换行符
                line = line.rstrip().lstrip()

                if line == '':
                    continue

                self.hosts.append(line)

            hostfh.close()

            if os.path.exists(ignorelistfile):
                ignorefh = open(ignorelistfile)
                for line in ignorefh:
                    line = line.rstrip().lstrip()
                    if line == '':
                        continue
                    self.ignores.append(line)
                
                ignorefh.close()

            if os.path.exists(self.result_file):
                last_resultfh = open(self.result_file)
                for line in last_resultfh:
                    line = line.rstrip().lstrip()
                    if line == '' or line.startswith('#'):
                        continue
                    self.last_badip.append(line)
                last_resultfh.close()

        except IOError as e:
            print e
            sys.exit()

    def _jobQueue(self):
        for ip in self.hosts:
            if self.repeat_alarm == False and ip in self.last_badip:
                continue

            if not ip in self.ignores:
                self.job_queue.put(ip)


    def mping(self, threadnum=100):
        '''
        并发线程数目
        '''

        self._jobQueue()
       
        # 准备线程池
        for i in range(threadnum):
            t = WorkerThread(self.job_queue, self.result_queue, self.count, self.last_count)
            #t.setDaemon(True)
            t.daemon = True
            t.start()
        
        # fix ctrl-c 
        ''' 
        ＃ 下面得代码并不能解决问题，
        ＃ 当队列为空时代码还是会阻塞在join上
        try:
            while True:
                if self.job_queue.empty() == False:
                    time.sleep(1)
                else:
                    break
        except KeyboardInterrupt: 
            sys.exit()
        '''

        self.job_queue.join()

        # set result
        self._set_result()

        # log result to file
        self._log_result()

    def _set_result(self):
        try:
            while True:
                ip = self.result_queue.get(block=None)
                self.badip.append(ip) 
        except Exception as e:
            print e
            pass

    def _log_result(self):
        if len(self.badip) > 0:
            now = time.strftime('%Y%m%d-%H%M', time.localtime())
            try:
                # log resulf file
                fh = open(self.result_file, 'w')
                fh.write('# %s:bad ip list\n' % now)

                print "badip list"
                for ip in self.badip:
                    print ip
                    fh.write('%s\n' % ip)
                fh.close()

                # log file
                logfh = open(self.log_file, 'a')
                logfh.write('time:%s|badip:%s\n' % (now, ','.join(self.badip)))
                logfh.close()
            except IOError as e:
                print e


class WorkerThread(threading.Thread):
    def __init__(self, job_queue, result_queue, count, lastcount):
        threading.Thread.__init__(self)
        self.job_queue = job_queue
        self.result_queue = result_queue
        self.count = count
        self.last_count = lastcount

    def run(self):
        while True:
            ip = self.job_queue.get()
            p = Ping(destination=ip)
            for i in range(self.count):
            #p.run(self.count)
                # 发送一个icmp包
                p.do()

                # 收到回包，ping ok
                if p.receive_count == 1:
                    break

            # count+last_count个包都丢了,当成ping不可达
            if p.receive_count == 0:
                self.result_queue.put(ip)

            print "ip %s done: %s" % (ip, p.receive_count)
            self.job_queue.task_done()

if __name__ == '__main__':
    m = Mping('allhosts.list', 'ignorehosts.list', repeatalarm=True)
    print "total %s hosts" % len(m.hosts)
    m.mping(100)
    
