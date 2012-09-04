#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Zynga Inc.
#

import shutil, os, tempfile, re, jasy, pip

from jasy.core.Logging import *
from jasy.env.Task import task, runTask
from jasy.env.State import session
from jasy.core.Error import JasyError
from jasy.core.Repository import isRepository, updateRepository
from jasy.core.Project import getProjectFromPath
from jasy.core.Util import getKey, getFirstSubFolder, massFilePatcher
from jasy.env.Config import Config
from distutils.version import StrictVersion

validProjectName = re.compile(r"^[a-z][a-z0-9]*$")

@task
def about():
    """Print outs the Jasy about page"""

    header("About")
    jasy.info()

    info("Command: %s", jasy.env.Task.getCommand())
    info("Version: %s", jasy.__version__)


@task
def help():
    """Shows this help screen"""

    header("Showing Help")
    jasy.info()
    
    print(colorize(colorize("Usage", "underline"), "bold"))
    print("  $ jasy [<options...>] <task1> [<args...>] [<task2> [<args...>]]")

    print()
    print(colorize(colorize("Global Options", "underline"), "bold"))
    jasy.env.Task.getOptions().printOptions()

    print()
    print(colorize(colorize("Available Tasks", "underline"), "bold"))
    jasy.env.Task.printTasks()

    print()


@task
def doctor():
    """Troubleshooting the Jasy environment"""

    header("Troubleshooting Environment")

    print('\n')

    dists = [dist for dist in pip.get_installed_distributions()]
    keys = [dist.key for dist in pip.get_installed_distributions()]
    
    versions = {}
    for dist in dists:
        versions[dist.key] = dist.version

    def checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction):
        print('\t%s:' % name)
        if name.lower() in keys:
            print('\t   - Found installation')
            if StrictVersion(minVersion) > StrictVersion("0.0"):
                if StrictVersion(versions[name.lower()]) >= StrictVersion(minVersion):
                    print('\t   - Version is OK (needed: %s installed: %s)' % (minVersion, versions[name.lower()]))
                else:
                    print(colorize(colorize('\t   - Version is NOT OK (needed: %s installed: %s)' % (minVersion, versions[name.lower()]) , "red"), "bold"))
                    print('\t     -> %s' % updateInstruction)
        else:
            print(colorize(colorize('\t   - Did NOT find installation', "red"), "bold"))
            print('\t     -> %s' % installInstruction)
        print('\n')


    # Needed packages
    print("Needed installations: \n")

    name = "Pygments"
    minVersion = "1.5"
    installInstruction = "Install the newest version of Pygments using '$ pip install Pygments'"
    updateInstruction = "Upgrade to the newest version of Pygments using '$ pip install --upgrade pygments'"
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)

    name = "polib"
    minVersion = "1.0"
    installInstruction = "Install the newest version of polib using '$ pip install polib'"
    updateInstruction = "Upgrade to the newest version of polib using '$ pip install --upgrade polib'"
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)

    name = "requests"
    minVersion = "0.13"
    installInstruction = "Install the newest version of requests using '$ pip install requests'"
    updateInstruction = "Upgrade to the newest version of requests using '$ pip install --upgrade requests'"
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)

    name = "CherryPy"
    minVersion = "3.2"
    installInstruction = "Install the newest version of CherryPy using '$ pip install CherryPy'"
    updateInstruction = "Upgrade to the newest version of CherryPy using '$ pip install --upgrade CherryPy'"
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)

    name = "PyYAML"
    minVersion = "3.0"
    installInstruction = "Install the newest version of PyYAML using '$ pip install PyYAML'"
    updateInstruction = "Upgrade to the newest version of PyYAML using '$ pip install --upgrade PyYAML'"
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)
    

    # Optional packages
    print("Optional installations: \n")

    name = "misaka"
    minVersion = "0.0"
    installInstruction = "Install the newest version of misaka using '$ pip install misaka'"
    updateInstruction = ""
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)

    name = "watchdog"
    minVersion = "0.0"
    installInstruction = "Install the jasy special version of watchdog using '$ pip install -e git+https://github.com/wpbasti/watchdog#egg=watchdog'"
    updateInstruction = ""
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)

    name = "pil"
    minVersion = "0.0"
    installInstruction = "Install the jasy special version of pil using '$ pip install -e git+https://github.com/zynga/pil-py3k#egg=pip-py3k'"
    updateInstruction = ""
    checkSingleInstallation(keys, versions, name, minVersion, installInstruction, updateInstruction)


@task
def create(name="myproject", origin=None, version=None, skeleton=None, destination=None, **argv):
    """Creates a new project"""

    header("Creating project %s" % name)

    if not validProjectName.match(name):
        raise JasyError("Invalid project name: %s" % name)


    #
    # Initial Checks
    #

    # Figuring out destination folder
    if destination is None:
        destination = name

    destinationPath = os.path.abspath(os.path.expanduser(destination))
    if os.path.exists(destinationPath):
        raise JasyError("Cannot create project %s in %s. File or folder exists!" % (name, destinationPath))

    # Origin can be either:
    # 1) None, which means a skeleton from the current main project
    # 2) An repository URL
    # 3) A project name known inside the current session
    # 4) Relative or absolute folder path

    if origin is None:
        originProject = session.getMain()

        if originProject is None:
            raise JasyError("Auto discovery failed! No Jasy projects registered!")

        originPath = originProject.getPath()
        originName = originProject.getName()
        originVersion = None

    elif isRepository(origin):
        info("Using remote skeleton")

        tempDirectory = tempfile.TemporaryDirectory()
        originPath = os.path.join(tempDirectory.name, "clone")
        originUrl = origin
        originVersion = version

        indent()
        originRevision = updateRepository(originUrl, originVersion, originPath)
        outdent()

        if originRevision is None:
            raise JasyError("Could not clone origin repository!")

        debug("Cloned revision: %s" % originRevision)

        originProject = getProjectFromPath(originPath)
        originName = originProject.getName()

    else:
        originProject = session.getProjectByName(origin)
        originVersion = None

        if originProject is not None:
            originPath = originProject.getPath()
            originName = origin

        elif os.path.isdir(origin):
            originPath = origin
            originProject = getProjectFromPath(originPath)
            originName = originProject.getName()

        else:
            raise JasyError("Invalid value for origin: %s" % origin)

    # Figure out the skeleton root folder
    skeletonDir = os.path.join(originPath, originProject.getConfigValue("skeletonDir", "skeleton"))
    if not os.path.isdir(skeletonDir):
        raise JasyError('The project %s offers no skeletons!' % originName)

    # For convenience: Use first skeleton in skeleton folder if no other selection was applied
    if skeleton is None:
        skeleton = getFirstSubFolder(skeletonDir)

    # Finally we have the skeleton path (the root folder to copy for our app)
    skeletonPath = os.path.join(skeletonDir, skeleton)
    if not os.path.isdir(skeletonPath):
        raise JasyError('Skeleton %s does not exist in project "%s"' % (skeleton, originName))


    #
    # Actual Work
    #

    # Prechecks done
    info('Creating %s from %s %s...', colorize(name, "bold"), colorize(skeleton + " @", "bold"), colorize(originName, "magenta"))
    debug('Skeleton: %s', colorize(skeletonPath, "grey"))
    debug('Destination: %s', colorize(destinationPath, "grey"))

    # Copying files to destination
    info("Copying files...")
    shutil.copytree(skeletonPath, destinationPath)
    debug("Files were copied successfully.")

    # Close origin project
    if originProject:
        originProject.close()

    # Change to directory before continuing
    os.chdir(destinationPath)

    # Create configuration file from question configs and custom scripts
    info("Starting configuration...")
    config = Config()

    config.set("name", name)
    config.set("jasy.version", jasy.__version__)
    config.set("origin.name", originName)
    config.set("origin.version", originVersion)
    config.set("origin.skeleton", os.path.basename(skeletonPath))

    config.injectValues(**argv)
    config.readQuestions("jasycreate", optional=True)
    config.executeScript("jasycreate.py", optional=True)

    config.write("jasyscript.yaml")

    # Do actual replacement of placeholders
    massFilePatcher(destinationPath, config)
    debug("Files were patched successfully.")

    # Done
    info('Your application %s was created successfully!', colorize(name, "bold"))

