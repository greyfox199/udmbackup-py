import json
import sys, getopt
from os.path import exists
import socket
from datetime import datetime
import logging
import paramiko
from paramiko import SSHClient
from scp import SCPClient
import os, time, shutil
import smtplib, ssl
from email.mime.text import MIMEText

argumentList = sys.argv[1:]
 
# Options
options = "hc:"
ConfigFilePath = ""
long_options = ["Help", "ConfigFilePath"]

#get command line arguments
try:
    # Parsing argument
    arguments, values = getopt.getopt(argumentList, options, long_options)

    for currentArgument, currentValue in arguments:
        if currentArgument in ("-h", "--Help"):
            print ("Usage: python udmprobackup.py -c /path/to/config.json")
             
        elif currentArgument in ("-c", "--ConfigFilePath"):
            ConfigFilePath = currentValue
             
except getopt.error as err:
    # output error, and return with an error code
    print(str(err))

#we require a json config file, so if it doesn't exist, abort
if not exists(ConfigFilePath):
    print("json config file specified at " + ConfigFilePath + " does not exist, aborting process")
    exit()

#open config file and check that it's a valid json file, if its not, abort
objConfigFile = open (ConfigFilePath, "r")
try:
    jsonData = json.loads(objConfigFile.read())
except:
    print("Config file of " + ConfigFilePath + " is not a valid json file, aborting process")
    exit()

#now that we know we have a valid json file, try to extract some parameters from the file
#the password for the udm file is required, so check for it and abort if its not present
if "udmPassword" in jsonData["required"]:
    try:
        strUDMPassword = str(jsonData['required']['udmPassword'])
    except:
        print("required field for password to udm does not exist, aborting proces")
        exit()

#the local backup directory is required, so check for it and abort if its not present
if not exists(jsonData['required']['localBackupDirectory']):
    print("local backup path of " + jsonData['required']['localBackupDirectory'] + "does not exist, aborting process")
    exit()

#we're done with the required fields, so set some variables for use later on
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
lstErrors = []

#if the logs directory is present in the config and the directory exists, enable logging and create a log file
if "logsDirectory" in jsonData['optional'] and exists(jsonData['optional']['logsDirectory']):
    blnWriteToLog = True
    strTimeStamp = datetime.now().strftime("%Y-%m-%d-%H_%M_%S")
    strDetailLogFilePath = str(jsonData['optional']['logsDirectory']) + "/udmpro-backup-detail-" + strTimeStamp + ".log"
    logging.basicConfig(filename=strDetailLogFilePath, format='%(asctime)s %(message)s', filemode='w')
    detailLogger=logging.getLogger()
    detailLogger.setLevel(logging.INFO)

#function to write to log file and optionally display message in console
def LogWrite(detailLogger, strLogString, blnDisplayInConsole=True):
    if blnDisplayInConsole:
        print(strLogString)
    detailLogger.info(strLogString)

#if daysToKeepUDMBackups is set and is a valid integer from 0 to 65534, attempt to use it for backup retention
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

#if daysToKeepLogFiles is set and is a valid integet from 0 to 65534, attempt to use it for log file retention
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
    
#if smtp port is set and is a valid integer between 0 and 65534, use it to set the smtp port for email error reporting
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
    
#there are several options for sending email, so if the sendEmailError option is set in the config file, try to get other smtp-related options
if "sendEmailError" in jsonData['optional']:
    try:
        tempSMTPSendError = str(jsonData['optional']['sendEmailError'])
        tempSMTPServer = str(jsonData['optional']['smtpServer'])
        tempEmailRecipient = str(jsonData['optional']['emailReportRecipient'])
        tempSMTPAuthRequied = str(jsonData['optional']['smtpauthrequired'])
        tempSMTPUsername = str(jsonData['optional']['smtpUsername'])
        tempSMTPPassword = str(jsonData['optional']['smtpPassword'])
        tempSMTPSSLRequired = str(jsonData['optional']['smtpsslrequired'])
        tempSMTPPort = str(jsonData['optional']['smtpport'])
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

#if the udmUsername is set, use it as a string, overriding the default value
if "udmUsername" in jsonData['optional']:
    try:
        strUDMUsername = str(jsonData['optional']['udmUsername'])
        LogWrite(detailLogger, "Info: username of " + jsonData['optional']['udmUsername'] + " configured in config file, overriding default")
    except:
        LogWrite(detailLogger, "Warning: username of " + jsonData['optional']['udmUsername'] + " configured in config file is invalid, using default")

#if udmIPHostname is set, use it as a string, overriding the default value
if "udmIPHostname" in jsonData['optional']:
    try:
        strUDMIPHostname = str(jsonData['optional']['udmIPHostname'])
        LogWrite(detailLogger, "Info: IP address/hostname of " + jsonData['optional']['udmIPHostname'] + " of UDMP Pro configured in config file, overriding default")
    except:
        LogWrite(detailLogger, "Warning: IP address/hostname of " + jsonData['optional']['udmIPHostname'] + " configured in config file is invalid, using default")

#if udmRemoteBackupDirectory is set, overriding the default value
if "udmRemoteBackupDirectory" in jsonData['optional']:
    try:
        strUDMRemoteBackupDirectory = str(jsonData['optional']['udmRemoteBackupDirectory'])
        LogWrite(detailLogger, "Info: Remote backup directory of " + jsonData['optional']['udmRemoteBackupDirectory'] + " for UDMP Pro configured in config file, overriding default")
    except:
        LogWrite(detailLogger, "Warning: Remote backup directory of " + jsonData['optional']['udmRemoteBackupDirectory'] + " configured in config file is invalid, using default")

LogWrite(detailLogger, "Info: Beginning process to backup UDM Pro via scp at " + strUDMIPHostname + " with " + strUDMUsername + ", copying " + strUDMRemoteBackupDirectory + " to " + jsonData['required']['localBackupDirectory'])

#start actual backup process.  note that the scp and paramiko python modules are required, which usually require the ubuntu pip package to be installed
#sudo apt-get install python3-pip
#sudo pip3 install scp
#sudo pip3 install paramiko
try:
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=strUDMIPHostname, username=strUDMUsername, password=strUDMPassword)
    scp = SCPClient(ssh.get_transport())
    scp.get(strUDMRemoteBackupDirectory, jsonData['required']['localBackupDirectory'], recursive=True)
    scp.close()
    blnBackupSuccessful = True
except:
    LogWrite(detailLogger, "Error: Failed to backup udm pro via scp at " + strUDMIPHostname + " with " + strUDMUsername + ", copying " + strUDMRemoteBackupDirectory + " to " + jsonData['required']['localBackupDirectory'])
    lstErrors.append("Failed to backup udm pro via scp at " + strUDMIPHostname + " with " + strUDMUsername + ", copying " + strUDMRemoteBackupDirectory + " to " + jsonData['required']['localBackupDirectory'])

#if the backup was successful and intDaysToKeepUDMBackups is a valid non 0 integer, manage backup retention
if blnBackupSuccessful == True and intDaysToKeepUDMBackups > 0:
    intXDaysAgo = time.time() - (intDaysToKeepUDMBackups * 86400)
    strPathToCheck = jsonData['required']['localBackupDirectory'] + "\autobackup"
    LogWrite(detailLogger, "Info: Purging backups older than " + intDaysToKeepUDMBackups + " days from " + strPathToCheck)
    try: 
        for i in os-listdir(strPathToCheck):
            strFileToRemove = os.path.join(strPathToCheck, i)

            if os.stat(strFileToRemove).st_mtime <= intXDaysAgo:
                if os.path.isfile(strFileToRemove):
                    print(strFileToRemove)
    except:
        LogWrite(detailLogger, "Error: Failed to purge backup files older than " + intDaysToKeepUDMBackups + " days from " + strPathToCheck)
        lstErrors.append("Failed to purge backup files older than " + intDaysToKeepUDMBackups + " days from " + strPathToCheck)

#if intDaysToKeepLogFiles is a valid non 0 integer, manage log file retention
if intDaysToKeepLogFiles > 0:
    intXDaysAgo = time.time() - (intDaysToKeepLogFiles * 86400)
    strPathToCheck = jsonData['optional']['logsDirectory']
    LogWrite(detailLogger, "Info: Purging logs older than " + intDaysToKeepLogFiles + " days from " + strPathToCheck)
    try:
        for i in os-listdir(strPathToCheck):
            strFileToRemove = os.path.join(strPathToCheck, i)

            if os.stat(strFileToRemove).st_mtime <= intXDaysAgo:
                if os.path.isfile(strFileToRemove):
                    print(strFileToRemove)
    except:
        LogWrite(detailLogger, "Error: Failed to purge log files older than " + intDaysToKeepLogFiles + " days from " + strPathToCheck)
        lstErrors.append("Failed to purge log files older than " + intDaysToKeepLogFiles + " days from " + strPathToCheck)

#we logged errors to the lstErrors list, so if it has any entries and tempSMTPSendError is set to true, attempt to send email error report
#we have a few checks if ssl is required or not
if tempSMTPSendError == "true" and len(lstErrors) > 0:
    if len(tempSMTPServer) > 0 and len(tempSMTPUsername) > 0 and len(tempEmailRecipient) > 0:
        blnSendSMTPErrorReport = True
        LogWrite(detailLogger, "Info: Encountered " + str(len(lstErrors)) + " errors, sending error report email")
        intErrorCounter = 0
        strEmailBody = ""
        for item in lstErrors:
            intErrorCounter = intErrorCounter +1
            strEmailBody = strEmailBody + str(intErrorCounter) + ") " + item + "`n"
        strEmaillBody = strEmailBody + "`n`nPlease see " + strDetailLogFilePath + "on " + strServerName + " for more details"

        LogWrite(detailLogger, "Info: Sending email error report via " + tempSMTPServer + " from " + tempSMTPUsername + " to " + tempEmailRecipient + " as specified in config file")
        if tempSMTPAuthRequied.lower() == "true":
            #send authenticated message
            if tempSMTPSSLRequired.lower() == "true":
                #send authenticated message with ssl

                msg = MIMEText(strEmailBody)

                msg['Subject'] = '<<UDM Pro Backup>> Errors during process'
                msg['From'] = tempSMTPUsername 
                msg['To'] = tempEmailRecipient
                

                context = ssl.create_default_context()
                with smtplib.SMTP(tempSMTPServer, intSMTPPort) as server:
                    server.ehlo()  # Can be omitted
                    server.starttls(context=context)
                    server.ehlo()  # Can be omitted
                    server.login(tempSMTPUsername, tempSMTPPassword)
                    server.sendmail(tempSMTPUsername, tempEmailRecipient, msg.as_string())


                LogWrite(detailLogger, "Info: Email error report successfully sent")
            else:
                #send authenticated message without ssl
                msg = MIMEText(strEmailBody)

                msg['Subject'] = '<<UDM Pro Backup>> Errors during process'
                msg['From'] = tempSMTPUsername
                msg['To'] = tempEmailRecipient

                server.login(tempSMTPUsername, tempSMTPPassword)
                server.sendmail(tempSMTPUsername, tempEmailRecipient, msg.as_string())
                server.quit()
                print('mail successfully sent')
                LogWrite(detailLogger, "Info: Email error report successfully sent")

#we're finally done with the process, so log one final entry marking completion
LogWrite(detailLogger, "Info: Process Complete")
            
