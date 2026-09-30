import os,signal,subprocess,sys
child=subprocess.Popen(sys.argv[1:],start_new_session=True)
def forward(sig,frame):
    try: os.killpg(child.pid,sig)
    except ProcessLookupError: pass
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP,signal.SIGQUIT):
    signal.signal(sig,forward)
while True:
    try: pid,status=os.waitpid(-1,0)
    except InterruptedError: continue
    except ChildProcessError: sys.exit(1)
    if pid==child.pid:
        sys.exit(os.waitstatus_to_exitcode(status))
