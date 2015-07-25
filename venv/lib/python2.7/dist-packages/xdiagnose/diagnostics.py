#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2010-2012 Bryce Harrington <bryce@canonical.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import absolute_import, print_function, unicode_literals

class Diagnostic:
    def __init__(self):
        self.name = None

    def run(self):
        pass

    def results(self):
        return "Results"

    def backup_xorg_conf(self):
        # xorg_conf_backup="/etc/X11/xorg.conf-backup-${timestamp}"
        # cp /etc/X11/xorg.conf ${xorg_conf_backup}
        print("Your config could not be backed up.")
        return False

    def default_config(self):
        if not self.backup_xorg_conf():
            return False

        # rm /etc/X11/xorg.conf
        #print "Failure restoring configuration to default."
        #print "Your config has not been changed."
        print("Your configuration has been restored to default and")
        print("your old configuration backed up.  Please restart.")
        return True

    def run_xorgconf(self):
        if not self.backup_xorg_conf():
            return False

        # Xorg :99 -configure
        print("Could not generate a new configuration")
        return False

    def view_xorg_log(self):
        # zenity --text-info --filename=$xorg_log --width=640 --height=480
        pass

    def view_gdm_log(self):
        # zenity --text-info --filename=${gdm_log_1} --width=640 --height=480
        pass

    def verify_xorgconf(self):
        # Run Alberto's xorg.conf checker (once it's available in main)
        print("Sorry, this option is not implemented yet")
        return False

    def edit_config(self):
        if not self.backup_xorg_conf():
            return False

        # xorg_conf_tmp=$(mktemp -t xorg.conf.XXXXXXXX)
        # zenity --text-info --editable --filename=/etc/X11/xorg.conf --width=640 --height=480 > "${xorg_conf_tmp}" && mv "${xorg_conf_tmp}" /etc/X11/xorg.conf
        # chmod 644 /etc/X11/xorg.conf

    def save_config_logs(self):
        pass
        #xorg_backup_name=failsafeX-backup-${timestamp}
        #xorg_backup_dir=$(mktemp -d -t ${xorg_backup_name}.XXX)
        #xorg_backup_file=/var/log/${xorg_backup_name}.tar

        # cp $xorg_conf $xorg_backup_dir
        #cp /etc/X11/xorg.conf $xorg_backup_dir
        #cp ${xorg_log} $xorg_backup_dir
        #cp ${xorg_log}.old $xorg_backup_dir
        #cp ${gdm_log} $xorg_backup_dir
        #cp ${gdm_log_1} $xorg_backup_dir
        #cp ${gdm_log_2} $xorg_backup_dir
        #lspci -vvnn > ${xorg_backup_dir}/lspci-vvnn.txt
        #xrandr --verbose > ${xorg_backup_dir}/xrandr-verbose.txt
        #tar -cf ${xorg_backup_file} ${xorg_backup_dir}
        #rm -rf ${xorg_backup_dir}

        #zenity --info --text "$(eval_gettext 'Relevant configuration and log files have been saved to:\n')"\$xorg_backup_file"\n$(gettext 'Bug reports can be submitted at http://www.launchpad.net/ubuntu/.\n')"


    def system_checkup(self):
        # * Look if user's video card pci id is not listed as supported by kernel or driver
        # * Look if -vesa or -fbdev has been loaded
        # * Look if glxgears shows software rendering
        # * Look if user has proprietary driver loaded
        # * Look for error messages in Xorg.0.log, dmesg, etc.
        #   LOG_ERRORS=$(grep -e "^(EE)" $xorg_log)
        # * Look if EDID information indicates something is incorrect
        # * Check if user has anything in xorg.conf and using a free driver
        pass

    def measure_performance(self):
        # Do some basic 2D and 3D operations to get some performance measurements
        pass

    def menu(self, level):
        if level == "0":
            print("Choice:")
            print("1. Run in low-graphics mode for just one session")
            print("2. Reconfigure graphics")
            print("3. Troubleshoot the error")
            print("4. Exit to console login")

        elif level == "1":
            pass

        elif level == "2":
            print("Reconfiguration:")
            print("How would you like to reconfigure your display?")
            print("2a. Use default (generic) configuration")
            print("2b. Create new configuration for this hardware")
            print("2c. Use your backed-up configuration")

        elif level == "3":
            print("Troubleshooting:")
            print("What information would you like to review?")
            print("3a. Review the xserver log file")
            print("3b. Review the startup errors")
            print("3c. Edit configuration file")
            print("3d. Archive configuration and logs")

        else:
            print("xdiagnose walks you through troubleshooting a few common X errors.")
            print()
            print(" * Screen blanks when lid is closed, and never comes back")
            print(" * 3D performance is horrible")
            print(" * Maximum resolution is lower than what screen can actually perform")

    def lid_close_blank(self):
        # Examine kernel logs to see if there was any evidence of it
        # Turn on storing of kernel logs from boot to boot
        # Tell user to reproduce the lid close blanking and then come back here
        # Once we know the cause, generate a quirk or whatnot for the issue
        pass

if __name__ == "__main__":

    diagnostic = Diagnostic()
    diagnostic.menu(0)
