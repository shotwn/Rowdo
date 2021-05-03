import sys
import os

import win32serviceutil  # ServiceFramework and commandline helper
import win32service  # Events
import servicemanager  # Simple setup and logging

import rowdo.watcher
import rowdo.database
import rowdo.logging


class RowdoServiceFramework(win32serviceutil.ServiceFramework):

    _svc_name_ = 'Rowdo'
    _svc_display_name_ = 'Rowdo Service'

    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.watcher.stop()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        """Start the service; does not return until stopped"""
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        try:
            db = rowdo.database.Database()
            self.watcher = rowdo.watcher.Watcher(db)
        except Exception as err:
            self.log(os.path.dirname(__file__))
            self.log(err)
            raise err

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        # Run the service
        try:
            self.watcher.loop()
        except Exception as err:
            self.log(os.getcwd())
            self.log(err)
            raise err

    def log(self, msg):
        rowdo.logging.logger.warning(msg)
        servicemanager.LogInfoMsg(str(msg))


def init():
    if len(sys.argv) == 1:
        exe_file_dir = sys.argv[0]
        os.chdir(os.path.dirname(exe_file_dir))
        rowdo.logging.start_log_file()
        rowdo.logging.logger.info(sys.argv)

        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(RowdoServiceFramework)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(RowdoServiceFramework)


if __name__ == '__main__':
    init()
