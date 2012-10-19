#!/usr/bin/env python
# Copyright 2012, Nathan Milford
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys
import time 
import pysvn
import shutil
import string
import socket
import commands
import logging
import smtplib

logger = logging.getLogger('cookbook-deploy')
hdlr = logging.FileHandler('/var/tmp/cookbook-deploy.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

knife        = '/usr/local/bin/knife'
svnlook      = '/usr/bin/svnlook'
svnUser      = ""
svnPass      = ""
svnRepo      = "https://myrepo/chef/cookbooks/"
target       = "/var/tmp/"
emailDom     = "example.com"
mailServer   = "smtp.example.com"
knifeConfig  = "/path/to/.chef/knife.rb"
mailFrom     = "chefuser@example.com" 
gServer      = "graphite.example.com"
gPort        = 2003

def getLogMsg(repo, rev):
  cmd = '%s log -r "%s" "%s"' % (svnlook, rev, repo)
  msg = os.popen(cmd, 'r').readline().rstrip('\n')
  return msg

def getCommitter(repo, ref):
  cmd = '%s author -r "%s" "%s"' % (svnlook, rev, repo)
  committer = os.popen(cmd, 'r').readline().rstrip('\n')
  logger.info('Author of commit %s is: "%s"' % (rev, committer))
  return committer

def getCookbook(repo, dst, cookbook):
  path = "%s/%s/" % (repo, cookbook)
  dest = "%s/%s/" % (dst, cookbook)
  os.makedirs(dest)
  logger.info('Creating target directory for svn checkout: "%s"' % dest)
  svn = pysvn.Client()
  svn.callback_ssl_server_trust_prompt = lambda t: (True, t['failures'], True)
  svn.callback_get_login = lambda x, y, z: (True, svnUser, svnPass, False)
  svn.checkout(path, dest)
  rev = svn.info(dest).revision.number
  logger.info('Revision of %s checked out: %s' % (cookbook, rev))
  return rev

def uploadCookbook(cookbook, path):
  cmd = '%s cookbook upload %s -o %s -c %s' % (knife, cookbook, path, knifeConfig)
  out = commands.getstatusoutput(cmd)
  exitCode = out[0]
  msg = out[1]
  ver = out[1].split(']')[0].split('[')[1]
  logger.info('%s cookbook version is %s' % (cookbook, ver))
  logger.info('knife exit status is %s' % exitCode)
  return exitCode, ver, msg

def whatCookbook(msg):
  cookbook = re.findall('#chefdeploy:([^ ]*)', logMsg)[0]
  logger.info('Cookbook to deploy: %s' % cookbook)
  return cookbook

def sendNotification(committer, cookbook, rev, mailSubj, mailText):
  mailTo   = "%s@%s" % (committer, emailDom)
  mailBody = string.join((
        "From: %s" % mailFrom,
        "To: %s" % mailTo,
        "Subject: %s" % mailSubj ,
        "",mailText), "\r\n")
  server = smtplib.SMTP(mailServer)
  server.sendmail(mailFrom, [mailTo], mailBody)
  server.quit()

def toGraphite(cookbook, rev):
  stat    = "events.chef.%s.%s" % (cookbook, rev)
  value   = 1
  ts      = int(time.time())
  payload = "\n%s %i %d\n" % (stat, value, ts)
  sock = socket.socket()
  sock.connect((gServer, gPort))
  sock.sendall(payload)
  sock.close()

def notifyComitter(exitCode, cookbook, ver, rev, comitter, cmdMsg):
  if exitCode == 0:
    subj = "Chef Deploy of %s %s on SVN commit %s was a success." % (cookbook, ver, rev)
    msg  = "Well done!\n\nCommand output is:\n\n%s" % cmdMsg
    toYammer("#Chef Deploy of %s %s on SVN commit %s by @%s." % (cookbook, ver, rev, comitter))
  else:
    subj = "Chef Deploy of %s on SVN commit %s failed." % (cookbook, rev)
    msg  = "Execution of knife cookbook upload exited with status %s, command output is:\n\n%s" % (exitCode, cmdMsg)

  sendNotification(committer, cookbook, rev, subj, msg)

def cleanup(dst, cookbook):
  target = "%s/%s/" % (dst, cookbook)
  logger.info('%s deleted' % target)
  if os.path.isdir(target):
    shutil.rmtree(target)

if __name__ == '__main__':
  if len(sys.argv) < 3:
    sys.stderr.write("Usage: %s repo rev\n" % (sys.argv[0]))
    sys.exit(-1)

  if os.environ.get('HOME') == None:
    sys.stderr.write("Knife needs HOME environment variable set please set it. Exiting.\n")
    logger.error('Knife needs HOME environment variable set please set it. Exiting.')
    sys.exit(-1)

  if os.environ.get('PATH') == None:
    sys.stderr.write("Knife needs PATH environment variable set please set it. Exiting.\n")
    logger.error('Knife needs PATH environment variable set please set it. Exiting.')
    sys.exit(-1)

  if not os.path.isfile(knife):
    sys.stderr.write("knife executable is missing. Exiting.\n")
    logger.error('knife executable is missing. Exiting.')
    sys.exit(-1)

  if not os.path.isfile(svnlook):
    sys.stderr.write("svnlook executable is missing. Exiting.\n")
    logger.error('svnlook executable is missing. Exiting.')
    sys.exit(-1)

  repo = sys.argv[1]
  rev  = sys.argv[2]
  logMsg = getLogMsg(repo, rev)

  if logMsg.find('#chefdeploy') > -1:
    logger.info('Log message for commit %s is: "%s"' % (rev, logMsg))
    committer = getCommitter(repo, rev)
    cookbook = whatCookbook(logMsg)
    cleanup(target, cookbook)
    getCookbook(svnRepo, target, cookbook)
    exitCode, ver, cmdMsg = uploadCookbook(cookbook, target)
    cleanup(target, cookbook)
    notifyComitter(exitCode, cookbook, ver, rev, committer, cmdMsg)
    toGraphite(cookbook, rev)
  else:
    sys.exit(0)
