import json
import sys, getopt
from os.path import exists
import socket
from datetime import datetime
import logging

argumentList = sys.argv[1:]
 
# Options
options = "hc:"

ConfigFilePath = ""

long_options = ["Help", "ConfigFilePath"]

try:
    # Parsing argument
    arguments, values = getopt.getopt(argumentList, options, long_options)

    for currentArgument, currentValue in arguments:
        if currentArgument in ("-h", "--Help"):
            print ("Displaying Help")
             
        elif currentArgument in ("-c", "--ConfigFilePath"):
            ConfigFilePath = currentValue
             
except getopt.error as err:
    # output error, and return with an error code
    print(str(err))

if not exists(ConfigFilePath):
    print("json config file specified at " + ConfigFilePath + " does not exist, aborting process")
    exit()

objConfigFile = open (ConfigFilePath, "r")

try:
    jsonData = json.loads(objConfigFile.read())
except:
    print("Config file of " + ConfigFilePath + " is not a valid json file, aborting process")
    exit()


if not exists(jsonData['required']['localBackupDirectory']):
    print("local backup path of " + jsonData['required']['localBackupDirectory'] + "does not exist, aborting process")
    exit()


strServerName = socket.gethostname()

intDaysToKeepUDMBackups = 0
intDaysToKeepLogFiles = 0

strUDMUsername = "root"
strUDMIPHostname = "192.168.1.1"
strUDMRemoteBackupDirectory = "/data/unifi/data/backup/autobackup"

blnSendSMTPErrorReport = False
blnSMTPAuthRequired = False
blnBackupSuccessful = False
blnWriteToLog = False
intSMTPPort = 587

if "logsDirectory" in jsonData['optional'] and exists(jsonData['optional']['logsDirectory']):
    blnWriteToLog = True
    strTimeStamp = datetime.now().strftime("%Y-%m-%d-%H_%M_%S")
    strDetailLogFilePath = str(jsonData['optional']['logsDirectory']) + "\\udmpro-backup-detail-" + strTimeStamp + ".log"
    logging.basicConfig(filename=strDetailLogFilePath, format='%(asctime)s %(message)s', filemode='w')
    detailLogger=logging.getLogger()
    detailLogger.setLevel(logging.INFO)

def LogWrite(detailLogger, strLogString, blnDisplayInConsole=True):
    if blnDisplayInConsole:
        print(strLogString)
    detailLogger.info(strLogString)

#configure days to keep local backup retention
if "daysToKeepUDMBackups" in jsonData['optional']:
    try:
        tempDaysToKeepUDMBackups = int(jsonData['optional']['daysToKeepUDMBackups'])
        if tempDaysToKeepUDMBackups >= 0 and tempDaysToKeepUDMBackups <= 65534:
            intDaysToKeepUDMBackups = tempDaysToKeepUDMBackups
            LogWrite(detailLogger, "Info: Using " + jsonData['optional']['daysToKeepUDMBackups'] + " value specified in config file for backup retention")
        else:
            LogWrite(detailLogger, "Warning: " + jsonData['optional']['daysToKeepUDMBackups'] + " value specified in config file is not valid, defaulting to unlimited backup retention")
    except:
        LogWrite(detailLogger, "Warning: " + jsonData['optional']['daysToKeepUDMBackups'] + " value specified in config file is not valid, defaulting to unlimited backup retention")

#configure days to keep log files
if "daysToKeepLogFiles" in jsonData['optional']:
    try:
        tempDaysToKeepLogFiles = int(jsonData['optional']['daysToKeepLogFiles'])
        if tempDaysToKeepLogFiles >= 0 and tempDaysToKeepLogFiles <= 65534:
            intDaysToKeepLogFiles = tempDaysToKeepLogFiles
            LogWrite(detailLogger, "Info: Using " + jsonData['optional']['daysToKeepLogFiles'] + " value specified in config file for log retention")
        else:
            LogWrite(detailLogger, "Warning: " + jsonData['optional']['daysToKeepLogFiles'] + " value specified in config file is not valid, defaulting to unlimited log retention")
    except:
        LogWrite(detailLogger, "Warning: " + jsonData['optional']['daysToKeepLogFiles'] + " value specified in config file is not valid, defaulting to unlimited log retention")
    
#configure smtp port
if "smtpport" in jsonData['optional']:
    try:
        tempSMTPPort = int(jsonData['optional']['smtpport'])
        if tempSMTPPort >= 0 and tempSMTPPort <= 65534:
            intSMTPPort = tempSMTPPort
            LogWrite(detailLogger, "Info: Using " + jsonData['optional']['smtpport'] + " value specified in config file for log for smtp port")
        else:
            LogWrite(detailLogger, "Warning: " + jsonData['optional']['smtpport'] + " value specified in config file is not valid, defaulting to " + str(intSMTPPort))
    except:
        LogWrite(detailLogger, "Warning: " + jsonData['optional']['smtpport'] + " value specified in config file is not valid, defaulting to " + str(intSMTPPort))
    



if "sendEmailError" in jsonData['optional']:
    try:
        tempSMTPSendError = str(jsonData['optional']['sendEmailError'])
        tempSMTPServer = str(jsonData['optional']['smtpServer'])
        tempEmailRecipient = str(jsonData['optional']['emailReportRecipient'])
        tempSMTPAuthRequied = str(jsonData['optional']['smtpauthrequired'])
        tempSMTPUsername = str(jsonData['optional']['smtpUsername'])
        tempSMTPPassword = str(jsonData['optional']['smtpPassword'])
        if tempSMTPSendError.lower() == "true":
            if len(tempSMTPServer) > 0 and len(tempEmailRecipient) > 0:
                blnSendSMTPErrorReport = True
                LogWrite(detailLogger, "Info: Sending email error report via " + jsonData['optional']['smtpServer'] + " to " + jsonData['optional']['emailReportRecipient'] + " as specified in config file")
            if  tempSMTPAuthRequied.lower() == "true" and (len(tempSMTPUsername) > 0 and len(tempSMTPPassword) > 0):
                blnSMTPAuthRequired = True
                LogWrite(detailLogger, "Info: Using " + jsonData['optional']['smtpUsername'] + " as smtp username and  smtp password in config file file for smtp authentication as specified in config file")
            else:
                LogWrite(detailLogger, "Warning: SMTP auth required but no smtp username or password file were specified, aborting smtp send")
    except:
        LogWrite(detailLogger, "Warning: Invalid email configuration data, not sending email report")

if "udmUsername" in jsonData['optional']:
    try:
        strUDMUsername = str(jsonData['optional']['udmUsername'])
        LogWrite(detailLogger, "Info: username of " + jsonData['optional']['udmUsername'] + " configured in config file, overriding default")
    except:
        LogWrite(detailLogger, "Warning: username of " + jsonData['optional']['udmUsername'] + " configured in config file is invalid, using default")

if "udmIPHostname" in jsonData['optional']:
    try:
        strUDMIPHostname = str(jsonData['optional']['udmIPHostname'])
        LogWrite(detailLogger, "Info: IP address/hostname of " + jsonData['optional']['udmIPHostname'] + " of UDMP Pro configured in config file, overriding default")
    except:
        LogWrite(detailLogger, "Warning: IP address/hostname of " + jsonData['optional']['udmIPHostname'] + " configured in config file is invalid, using default")

if "udmRemoteBackupDirectory" in jsonData['optional']:
    try:
        strUDMRemoteBackupDirectory = str(jsonData['optional']['udmRemoteBackupDirectory'])
        LogWrite(detailLogger, "Info: Remote backup directory of " + jsonData['optional']['udmRemoteBackupDirectory'] + " for UDMP Pro configured in config file, overriding default")
    except:
        LogWrite(detailLogger, "Warning: Remote backup directory of " + jsonData['optional']['udmRemoteBackupDirectory'] + " configured in config file is invalid, using default")

LogWrite(detailLogger, "Info: Beginning process to backup UDM Pro via scp at " + strUDMIPHostname + " with " + strUDMUsername + ", copying " + strUDMRemoteBackupDirectory + " to " + jsonData['required']['localBackupDirectory'])