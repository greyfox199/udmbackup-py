# udmbackup
this utility is used to backup a udm device to a location off the device itself. 

Requirements:  
-Assumes root level access to the udm device  
-Assumes auto backups have been configured on the udm device itself  
-Assumes remote host path can run python scripts (has only been tested on linux/ubuntu)   
-Assumes the python3-pip OS package is installed   
-Assumes the scp python module has been installed   
-Assumes the paramiko python module has been installed   
-Assumes scheduling is done via cron

# install
To install this script, either utilize the git-clone feature or manaually download from this repo.  It should be placed in a suitable location of your choosing for scheduled tasks.  This script requires a json config file to be passed in as a parameter.  The config file should be placed in an appropriate location; it does not have to reside in the same location as the script but it can.  This file WILL have the udm password and smtp password (until I can find a better way around this), so ensure that only the user running it can read it:

chmod 600 udmbackup.json

Once the python script and json config file have been created and configured, the script can be run manually as follows:  

python udmprobackup.py -c "/path/to/udmbackup.json"

A basic scheduled task via cron can be created as the user that has read access to the udmbackup.json file.  To run this daily at 2am, use the following cron entry:

0 2 * * * python3 /path/to/udmprobackup.py

Once the job has been configured, the files should consist of the historical backup files (.unf) along with a metadata json file:

```
ls -la
total 284
drwxr-xr-x 2 user user  4096 Aug 15 04:20 .
drwxrwxr-x 3 user user  4096 Aug 15 00:28 ..
-rw-r--r-- 1 user user 37376 Aug 15 04:20 autobackup_7.1.61_20220808_0800_1659945600013.unf
-rw-r--r-- 1 user user 35952 Aug 15 04:20 autobackup_7.1.61_20220809_0800_1660032000014.unf
-rw-r--r-- 1 user user 36480 Aug 15 04:20 autobackup_7.1.61_20220810_0800_1660118400017.unf
-rw-r--r-- 1 user user 38128 Aug 15 04:20 autobackup_7.1.61_20220811_0800_1660204800025.unf
-rw-r--r-- 1 user user 38816 Aug 15 04:20 autobackup_7.1.61_20220812_0800_1660291200039.unf
-rw-r--r-- 1 user user 38704 Aug 15 04:20 autobackup_7.1.61_20220813_0800_1660377600018.unf
-rw-r--r-- 1 user user 38704 Aug 15 04:20 autobackup_7.1.61_20220814_0800_1660464000023.unf
-rw-r--r-- 1 user user  1163 Aug 15 04:20 autobackup_meta.json
```

# config file
The config file is a json-formatted config file.  There are 2 required fields and several optional fields to control things like logging, sending error reports via email, and local backup/log retention:

The simplest file will be this:
```json
{
    "required": {
        "udmPassword": "[insert password]",
        "localBackupDirectory": "/path/to/udmbackupdir"
    }
}
```
**udmPassword**: This is the password for the root-level account to the udm device.  
**localBackupDirectory**: This is the path where the backups will be retained.  A directory called "autobackup" will be created in this directory and hold all accumulated udm backup files.  Note that without a retention configured as an optional parameter, the number of backup files will continue to grow unrestricted.

The complete list of optional parameters is as follows:  

```json
{
    "required": {
        "udmPassword": "[insert udm root password]",
        "localBackupDirectory": "/path/to/udmbackupdir"
    },
    "optional": {
        "logsDirectory": "/path/to/udmlogsdir",
        "daysToKeepUDMBackups": "0",
        "daysToKeepLogFiles": "0",
        "sendEmailError": "true",
        "smtpServer": "mail.server.address",
        "emailReportRecipient": "errorreport@recipient.com",
        "smtpUsername": "errorreport@sender.com",
        "smtpauthrequired": "true",
        "smtpPassword": "[insert smtp password]",
        "smtpsslrequired": "true",
        "smtpport": "587",
        "udmUsername": "root",
        "udmIPHostname": "192.168.1.1",
        "udmRemoteBackupDirectory": "/data/unifi/data/backup/autobackup"
    }
}
```

**logsDirectory**: This is the path to an optional directory to log the output of the job.  Without the additional optional daysToKeepLogFiles directive set, the log files will continue to be added each time the job is run without restrictions.  
**daysToKeepUDMBackups**: This setting controls the number of days to keep the udm backups locally.  It is expecting an unsigned int from range 0 to 65535, with 0 indicating that no local backups will be purged.  If this value is left blank, not numerical or outside the range of an unsigned int16, it defaults to 0.  
**daysToKeepLogFiles**: This setting controls the number of days to keep logs locally, assuming the logsDirectory directive was set.  It is expecting an unsigned int from range 0 to 65535, with 0 indicating that no local log files will be purged.  If this value is left blank, not numerical or outside the range of an unsigned int16, it defaults to 0.  
**sendEmailError**: This setting controls whether an email report will be sent if any errors occur.  This accepts two values, "true" or "false".  If this is empty or not one of those 2 values, it defaults to "false".  
**smtpServer**: This is the smtp mail server to use to send error reports if any errors occur.  This value is ignored if sendEmailError is not set to true.  
**emailReportRecipient**: This is the recipent that will receive the error report if any errors occur.  This value is ignored if sendEmailError is not set to true.  
**smtpUsername**: This is the sender that will be used to send the error report if any errors occur.  It is also the value for the username that is used if smtp auth is required.  This value is ignored if sendEmailError is not set to true.  
**smtpauthrequired**: This setting controls whether smtp authentication is required to connect to the configured mail server.  This accepts two values, "true" or "false".  If this is empty or not one of those 2 values, it defaults to "false".  This setting is ignored if sendEmailError is not set to true.  
**smtpPassword**: This is the password used for smtp authentication.  This setting is ignored if sendEmailError is not set to true.  
**smtpsslrequired**:  This setting controls whether a secure channel is required to connect to the specified smtp server.  This accepts two values, "true" or "false".  If this is empty or not one of those 2 values, it defaults to "false".  This setting is ignored if sendEmailError is not set to true.  
**smtpport**:  This setting controls the port number used to connect to the specified smtp server.  It is expecting an unsigned int from range 0 to 65535.  If this value is left blank, not numerical or outside the range of an unsigned int16, it defaults to 587.  This setting is ignored if sendEmailError is not set to true.  
**udmUsername**:  This setting controls the username used to connect to the udm device.  If left blank, it defaults to "root".  
**udmIPHostname**:  This setting controls the IP/hostname used to connect to the udm device.  It will accept a valid IP address or dns hostname.  If left blank, it defaults to "192.168.1.1".  
**udmRemoteBackupDirectory**:  This setting controls the location on the remote udm device that holds the configured backups.  If left blank, it defaults to "/data/unifi/data/backup/autobackup".  