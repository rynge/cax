"""File system operations through cax

This allows you to move or remove files while still notifying the run database,
but also checks for strays.
"""

import logging
import os
import shutil
import subprocess

from cax import config
from cax.task import Task


class SetPermission(Task):
    """Set the correct permissions at the PDC in Stockholm"""

    def __init__(self):
        self.chmod_file = '/cfs/klemming/projects/xenon/misc/basic_file'
        self.chmod_folder = '/cfs/klemming/projects/xenon/misc/basic'

        Task.__init__(self)
        self.destination_config = config.get_config(config.get_hostname())
        self.set_rec = "-R"

    def each_run(self):
        """Set ownership and permissons for files/folders"""
        for data_doc in self.run_doc['data']:
            # Is not local, skip
            if 'host' not in data_doc or \
                            data_doc['host'] != config.get_hostname() or \
                            data_doc['host'] != 'tegner-login-1':
                continue

            self.log.info("Set owner and group via chmod %s",
                          config.get_hostname())
            subprocess.Popen(["chown", self.set_rec, "bobau:xenon-users",
                              data_doc['location']],
                             stdout=subprocess.PIPE)

            self.log.info("Set permissions via setfacl %s",
                          config.get_hostname())

            if data_doc['type'] == 'raw':
                subprocess.Popen(["setfacl", self.set_rec, "-M",
                                  self.chmod_folder,
                                  data_doc['location']],
                                 stdout=subprocess.PIPE)
            else:
                subprocess.Popen(["setfacl", self.set_rec, "-M",
                                  self.chmod_file,
                                  data_doc['location']],
                                 stdout=subprocess.PIPE)


class RenameSingle(Task):
    """Rename a file

    This renames a file or folder then updates the run database to reflect it.
    This is an unsafe operation since it does not perform a new checksum.
    """

    def __init__(self, input, output):
        # Save filesnames to use
        self.input = os.path.abspath(input)
        self.output = os.path.abspath(output)

        # Perform base class initialization
        Task.__init__(self)

    def each_run(self):
        # For each data location, see if this filename in it
        for data_doc in self.run_doc['data']:
            # Is not local, skip
            if 'host' not in data_doc or \
                            data_doc['host'] != config.get_hostname():
                continue

            if data_doc['location'] != self.input:
                continue

            self.log.info("Moving %s to %s" % (self.input,
                                               self.output))
            # Perform renaming
            os.renames(self.input,
                       self.output)

            # Notify run database
            if config.DATABASE_LOG is True:
                self.collection.update({'_id' : self.run_doc['_id'],
                                        'data': {'$elemMatch': data_doc}},
                                       {'$set': {
                                           'data.$.location': self.output}})
            break


class RemoveSingle(Task):
    """Remove a single file or directory

    This notifies the run database.
    """

    def __init__(self, location):
        # Save filesnames to use
        self.location = os.path.abspath(location)

        # Perform base class initialization
        Task.__init__(self)

    def each_run(self):
        # For each data location, see if this filename in it
        for data_doc in self.run_doc['data']:
            # Is not local, skip
            if 'host' not in data_doc or \
                            data_doc['host'] != config.get_hostname():
                continue

            if data_doc['location'] != self.location:
                continue

            # Notify run database
            if config.DATABASE_LOG is True:
                self.collection.update({'_id': self.run_doc['_id']},
                                       {'$pull': {'data': data_doc}})

            # Perform operation
            self.log.info("Removing %s" % (self.location))
            if os.path.isdir(data_doc['location']):
                shutil.rmtree(data_doc['location'])
            else:
                os.remove(self.location)

            break

class RemoveTSMEntry(Task):
    """Remove a single file or directory

    This notifies the run database.
    """

    def __init__(self, location):
        # Save filesnames to use
        self.location = location
        print("delete from database: ", self.location)
        # Perform base class initialization
        Task.__init__(self)

    def each_run(self):
        # For each data location, see if this filename in it
        #print(self.run_doc)
        cnt = 0        
        for data_doc in self.run_doc['data']:
            # Is not local, skip
            if data_doc['host'] == "tsm-server":
                print("found: ", data_doc)
                cnt+=1
        
        for data_doc in self.run_doc['data']:
            
            if 'host' not in data_doc or data_doc['host'] != "tsm-server":
                continue

            if data_doc['location'] != self.location:
                continue
            
            # Notify run database
            if config.DATABASE_LOG is True:
              print("Delete this: ", data_doc)
              res = self.collection.update({'_id': self.run_doc['_id']},
                                           {'$pull': {'data': data_doc}}
                                           )
              for key, value in res.items():
                print( " * " + str(key) + ": " + str(value) )
            else:
              print("This should be deleted:")
              print(data_doc)
            break
        
        print("There are {a} entries in the runDB with \"tsm-server\" for the same run number or name".format(a=str(cnt)))   

class FindStrays(Task):
    """Remove a single file or directory

    This notifies the run database.
    """

    locations = []

    def each_location(self, data_doc):
        if data_doc['host'] == config.get_hostname():
            self.locations.append(data_doc['location'])

    def check(self, directory):
        if directory is None:
            return

        for root, dirs, files in os.walk(directory, topdown=False):
            if root in self.locations:
                continue
            for name in files:
                if os.path.join(root, name) not in self.locations:
                    print(os.path.join(root, name))
            for dir in dirs:
                if os.path.join(root, dir) not in self.locations:
                    if root != config.get_processing_base_dir():
                        print(os.path.join(root, name))

    def shutdown(self):
        self.check(config.get_raw_base_dir())
        self.check(config.get_processing_base_dir())


class StatusSingle(Task):
    """Status of a single file or directory

    This notifies the run database.
    """

    def __init__(self, node__, status__):
        # Save filesnames to use
        self.node = node__
        self.status = status__

        # Perform base class initialization
        Task.__init__(self)

    def each_run(self):
        # print(self.run_doc['data'])

        # For each data location, see if this filename in it
        for data_doc in self.run_doc['data']:
            #Show entries only for requested host
            if self.node == data_doc['host'] and self.status == data_doc[
                'status']:
                status_db = data_doc["status"]
                location_db = data_doc['location']
                logging.info("Ask for status %s at node %s: %s", self.node,
                             status_db, location_db)
