import subprocess
import platform

# On windows, we'll redefine Popen so that no new window is created
# when running gpg. Otherwise, after running PyInstaller, a lot of
# windows pop up and disappear again
if platform.system() == "Windows":
    import win32process
    
    oldPopen = subprocess.Popen
    def newPopen(*args, **kwargs):
        #print("newPopen")
        #print(args)
        #print(kwargs)
        kwargs["creationflags"] = win32process.CREATE_NO_WINDOW
        return oldPopen(*args, **kwargs)

    #print("Redefining Popen")
    subprocess.Popen = newPopen

