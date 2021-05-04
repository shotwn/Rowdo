import sys
import os

import win32serviceutil  # ServiceFramework and commandline helper
import win32service  # Events
import servicemanager  # Simple setup and logging

import rowdo

RUN_SERVICE_FLAG = '--run-as-service'
SERVICE_MANAGER_FLAG = '--service'


class RowdoServiceFramework(win32serviceutil.ServiceFramework):

    _svc_name_ = 'Rowdo'
    _svc_display_name_ = 'Rowdo Service'
    _exe_args_ = RUN_SERVICE_FLAG

    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        rowdo.stop()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        """Start the service; does not return until stopped"""
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            rowdo.start(sys.argv[0])  # Changes CWD
        except Exception as err:
            self.log(err)
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            raise err

    def log(self, msg):
        rowdo.logging.logger.warning(msg)
        servicemanager.LogInfoMsg(str(msg))


def init():
    # Starting the service
    if len(sys.argv) == 2 and sys.argv[1] == RUN_SERVICE_FLAG:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(RowdoServiceFramework)
        servicemanager.StartServiceCtrlDispatcher()
    # Service manager commands
    elif len(sys.argv) >= 2 and sys.argv[1] == SERVICE_MANAGER_FLAG:
        sys.argv.pop(1)
        win32serviceutil.HandleCommandLine(RowdoServiceFramework)
    # Routine start
    else:
        rowdo.start()


def debug_log(s):
    print(s)
    os.chdir(os.path.dirname(sys.argv[0]))
    with open('service.debug.log', 'w+') as f:
        f.write(s)


if __name__ == '__main__':
    init()
