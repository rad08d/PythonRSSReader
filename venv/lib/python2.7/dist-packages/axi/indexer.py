# -*- coding: utf-8 -*-
#
# axi/indexer.py - apt-xapian-index indexer
#
# Copyright (C) 2007--2010  Enrico Zini <enrico@debian.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import axi
import sys
import os
import imp
import socket, errno
import fcntl
import textwrap
import xapian
import shutil
import itertools
import time
import re
import urllib
import cPickle as pickle

APTLISTDIR="/var/lib/apt/lists"

class Addon:
    """
    Indexer plugin wrapper
    """
    def __init__(self, fname, progress=None, **kw):
        self.filename = os.path.basename(fname)
        self.name = os.path.splitext(self.filename)[0]
        oldpath = sys.path
        try:
            sys.path.append(os.path.dirname(fname))
            self.module = imp.load_source("axi.plugin_" + self.name, fname)
        finally:
            sys.path = oldpath
        try:
            self.obj = self.module.init(**kw)
        except TypeError:
            self.obj = self.module.init()
        if self.obj:
            try:
                try:
                    self.info = self.obj.info(**kw)
                except TypeError:
                    self.info = self.obj.info()
            except Exception, e:
                if progress:
                    progress.warning("Plugin %s initialisation failed: %s" % (fname, str(e)))
                self.obj = None

    def finished(self):
        if hasattr(self.obj, "finished"):
            self.obj.finished()

    def send_extra_info(self, **kw):
        func = getattr(self.obj, "send_extra_info", None)
        if func is not None:
            func(**kw)

class Plugins(list):
    def __init__(self, **kw):
        """
        Read the plugins, in sorted order.

        Pass all the keyword args to the plugin init
        """
        if "langs" not in kw:
            kw["langs"] = self.scan_available_languages()
        progress = kw.get("progress", None)

        self.disabled = []
        for fname in sorted(os.listdir(axi.PLUGINDIR)):
            # Skip non-pythons, hidden files and python sources starting with '_'
            if fname[0] in ['.', '_'] or not fname.endswith(".py"): continue
            fullname = os.path.join(axi.PLUGINDIR, fname)
            if not os.path.isfile(fullname): continue
            if progress: progress.verbose("Reading plugin %s." % fullname)
            addon = Addon(fullname, **kw)
            if addon.obj != None:
                self.append(addon)

    def scan_available_languages(self):
        # Languages we index
        langs = set()

        # Look for files like: ftp.uk.debian.org_debian_dists_sid_main_i18n_Translation-it
        # And extract the language code at the end
        tfile = re.compile(r"_i18n_Translation-([^-]+)$")
        for f in os.listdir(APTLISTDIR):
            mo = tfile.search(f)
            if not mo: continue
            langs.add(urllib.unquote(mo.group(1)))

        return langs


class Progress:
    """
    Normal progress report to stdout
    """
    def __init__(self):
        self.task = None
        self.halfway = False
        self.is_verbose = False
    def begin(self, task):
        self.task = task
        print "%s..." % self.task,
        sys.stdout.flush()
        self.halfway = True
    def progress(self, percent):
        print "\r%s... %d%%" % (self.task, percent),
        sys.stdout.flush()
        self.halfway = True
    def end(self):
        print "\r%s: done.  " % self.task
        self.halfway = False
    def verbose(self, *args):
        if not self.is_verbose: return
        if self.halfway:
            print
        print " ".join(args)
        self.halfway = False
    def notice(self, *args):
        if self.halfway:
            print
        print >>sys.stderr, " ".join(args)
        self.halfway = False
    def warning(self, *args):
        if self.halfway:
            print
        print >>sys.stderr, " ".join(args)
        self.halfway = False
    def error(self, *args):
        if self.halfway:
            print
        print >>sys.stderr, " ".join(args)
        self.halfway = False

class BatchProgress:
    """
    Machine readable progress report
    """
    def __init__(self):
        self.task = None
    def begin(self, task):
        self.task = task
        print "begin: %s\n" % self.task,
        sys.stdout.flush()
    def progress(self, percent):
        print "progress: %d/100\n" % percent,
        sys.stdout.flush()
    def end(self):
        print "done: %s\n" % self.task
        sys.stdout.flush()
    def verbose(self, *args):
        print "verbose: %s" % (" ".join(args))
        sys.stdout.flush()
    def notice(self, *args):
        print "notice: %s" % (" ".join(args))
        sys.stdout.flush()
    def warning(self, *args):
        print "warning: %s" % (" ".join(args))
        sys.stdout.flush()
    def error(self, *args):
        print "error: %s" % (" ".join(args))
        sys.stdout.flush()

class SilentProgress:
    """
    Quiet progress report
    """
    def begin(self, task):
        pass
    def progress(self, percent):
        pass
    def end(self):
        pass
    def verbose(self, *args):
        pass
    def notice(self, *args):
        pass
    def warning(self, *args):
        print >>sys.stderr, " ".join(args)
    def error(self, *args):
        print >>sys.stderr, " ".join(args)

class ClientProgress:
    """
    Client-side progress report, reporting progress from another running
    indexer
    """
    def __init__(self, progress):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(None)
        self.sock.connect(axi.XAPIANDBUPDATESOCK)
        self.progress = progress

    def loop(self):
        hasBegun = False
        while True:
            msg = self.sock.recv(4096)
            try:
                args = pickle.loads(msg)
            except EOFError:
                self.progress.error("The other update has stopped")
                return
            action = args[0]
            args = args[1:]
            if action == "begin":
                self.progress.begin(*args)
                hasBegun = True
            elif action == "progress":
                if not hasBegun:
                    self.progress.begin(args[0])
                    hasBegun = True
                self.progress.progress(*args[1:])
            elif action == "end":
                if not hasBegun:
                    self.progress.begin(args[0])
                    hasBegun = True
                self.progress.end(*args[1:])
            elif action == "verbose":
                self.progress.verbose(*args)
            elif action == "notice":
                self.progress.notice(*args)
            elif action == "error":
                self.progress.error(*args)
            elif action == "alldone":
                break
            else:
                self.progress.error("unknown action '%s' from other update-apt-xapian-index.  Arguments: '%s'" % (action, ", ".join(map(repr, args))))


class ServerSenderProgress:
    """
    Server endpoint for client-server progress report
    """
    def __init__(self, sock, task = None):
        self.sock = sock
        self.task = task
    def __del__(self):
        self._send(pickle.dumps(("alldone",)))
    def _send(self, text):
        try:
            self.sock.send(text)
        except:
            pass
    def begin(self, task):
        self.task = task
        self._send(pickle.dumps(("begin", self.task)))
    def progress(self, percent):
        self._send(pickle.dumps(("progress", self.task, percent)))
    def end(self):
        self._send(pickle.dumps(("end", self.task)))
    def verbose(self, *args):
        self._send(pickle.dumps(("verbose",) + args))
    def notice(self, *args):
        self._send(pickle.dumps(("notice",) + args))
    def warning(self, *args):
        self._send(pickle.dumps(("warning",) + args))
    def error(self, *args):
        self._send(pickle.dumps(("error",) + args))

class ServerProgress:
    """
    Send progress report to any progress object, as well as to client indexers
    """
    def __init__(self, mine):
        self.task = None
        self.proxied = [mine]
        self.sockfile = axi.XAPIANDBUPDATESOCK
        try:
            os.unlink(self.sockfile)
        except OSError:
            pass
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(axi.XAPIANDBUPDATESOCK)
        self.sock.setblocking(False)
        self.sock.listen(5)
        # Disallowing unwanted people to mess with the file is automatic, as
        # the socket has the ownership of the user we're using, and people
        # can't connect to it unless they can write to it
    def __del__(self):
        self.sock.close()
        os.unlink(self.sockfile)
    def _check(self):
        try:
            sock = self.sock.accept()[0]
            self.proxied.append(ServerSenderProgress(sock, self.task))
        except socket.error, e:
            if e.args[0] != errno.EAGAIN:
                raise
        pass
    def begin(self, task):
        self._check()
        self.task = task
        for x in self.proxied: x.begin(task)
    def progress(self, percent):
        self._check()
        for x in self.proxied: x.progress(percent)
    def end(self):
        self._check()
        for x in self.proxied: x.end()
    def verbose(self, *args):
        self._check()
        for x in self.proxied: x.verbose(*args)
    def notice(self, *args):
        self._check()
        for x in self.proxied: x.notice(*args)
    def warning(self, *args):
        self._check()
        for x in self.proxied: x.warning(*args)
    def error(self, *args):
        self._check()
        for x in self.proxied: x.error(*args)


class ExecutionTime(object):
    """
    Helper that can be used in with statements to have a simple
    measure of the timing of a particular block of code, e.g.
    with ExecutionTime("db flush"):
        db.flush()
    """
    import time
    def __init__(self, info=""):
        self.info = info
    def __enter__(self):
        self.now = time.time()
    def __exit__(self, type, value, stack):
        print "%s: %s" % (self.info, time.time() - self.now)

class Indexer(object):
    """
    The indexer
    """
    def __init__(self, progress, quietapt=False):
        self.progress = progress
        self.quietapt = quietapt
        self.verbose = getattr(progress, "is_verbose", False)
        # Timestamp of the most recent data source
        self.ds_timestamp = 0
        # Apt cache instantiated on demand
        self.apt_cache = None
        # Loaded plugins
        self.plugins = None
        # OS file handle for the lock file
        self.lockfd = None

        # Ensure the database and cache directories exist
        self.ensure_dir_exists(axi.XAPIANDBPATH)
        self.ensure_dir_exists(axi.XAPIANCACHEPATH)

    def ensure_dir_exists(self, pathname):
        """
        Create a directory if missing, but do not complain if it already exists
        """
        try:
            # Try to create it anyway
            os.mkdir(pathname)
        except OSError, e:
            if e.errno != errno.EEXIST:
                # If we got an error besides path already existing, fail
                raise
            elif not os.path.isdir(pathname):
                # If that path already exists, but is not a directory, also fail
                raise

    def _test_wrap_apt_cache(self, wrapper):
        """
        Wrap the apt-cache in some proxy object.

        This is used to give tests some control over the apt cache results
        """
        if self.apt_cache is not None:
            raise RuntimeError("the cache has already been instantiated")
        # Instantiate the cache
        self.aptcache()
        # Wrap it
        self.apt_cache = wrapper(self.apt_cache)

    def aptcache(self):
        if not self.apt_cache:
            #import warnings
            ## Yes, apt, thanks, I know, the api isn't stable, thank you so very much
            ##warnings.simplefilter('ignore', FutureWarning)
            #warnings.filterwarnings("ignore","apt API not stable yet")
            import apt
            import apt_pkg
            #warnings.resetwarnings()

            if self.quietapt:
                class AptSilentProgress(apt.progress.text.OpProgress) :
                    def __init__(self): 
                        pass
                    def done(self):
                        pass
                    def update(self,percent=None):
                        pass
                aptprogress = AptSilentProgress()
            else:
                aptprogress = None

            # memonly=True: force apt to not write a pkgcache.bin
            apt_pkg.init_config()
            self.apt_cache = apt.Cache(memonly=True, progress=aptprogress)
        return self.apt_cache

    def lock(self):
        """
        Lock the session to prevent further updates.

        @returns
          True if the session is locked
          False if another indexer is running
        """
        # Lock the session so that we prevent concurrent updates
        self.lockfd = os.open(axi.XAPIANDBLOCK, os.O_RDWR | os.O_CREAT)
        try:
            fcntl.lockf(self.lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Wrap the current progress with the server sender
            self.progress = ServerProgress(self.progress)
            return True
        except IOError, e:
            if e.errno == errno.EACCES or e.errno == errno.EAGAIN:
                return False
            else:
                raise

    def slave(self):
        """
        Attach to a running indexer and report its progress.

        Return when the other indexer has finished.
        """
        self.progress.notice("Another update is already running: showing its progress.")
        childProgress = ClientProgress(self.progress)
        childProgress.loop()

    def setupIndexing(self, force=False, system=True):
        """
        Setup indexing: read plugins, check timestamps...

        @param force: if True, reindex also if the index is up to date

        @return:
          True if there is something to index
          False if there is no need of indexing
        """
        # Read values database
        #values = readValueDB(VALUESCONF, progress)

        # Read the plugins, in sorted order
        self.plugins = Plugins(progress=self.progress, system=system)

        # Ensure that we have something to do
        if len(self.plugins) == 0:
            self.progress.notice("No indexing plugins found in %s" % axi.PLUGINDIR)
            return False

        # Get the most recent modification timestamp of the data sources
        self.ds_timestamp = max([x.info['timestamp'] for x in self.plugins])

        # Get the timestamp of the last database update
        try:
            if os.path.exists(axi.XAPIANDBSTAMP):
                cur_timestamp = os.path.getmtime(axi.XAPIANDBSTAMP)
            else:
                cur_timestamp = 0
        except OSError, e:
            cur_timestamp = 0
            self.progress.notice("Reading current timestamp failed: %s. Assuming the index has not been created yet." % e)

        if self.verbose:
            self.progress.verbose("Most recent dataset:    %s." % time.ctime(self.ds_timestamp))
            self.progress.verbose("Most recent update for: %s." % time.ctime(cur_timestamp))

        # See if we need an update
        if cur_timestamp != 0 and int(self.ds_timestamp+.5) <= int(cur_timestamp+0.5):
            if force:
                self.progress.notice("The index %s is up to date, but rebuilding anyway as requested." % axi.XAPIANDBPATH)
            else:
                self.progress.notice("The index %s is up to date" % axi.XAPIANDBPATH)
                return False

        # Build the value database
        self.progress.verbose("Aggregating value information.")
        # Read existing value database to keep ids stable in a system
        self.values, self.values_desc = axi.readValueDB(quiet=True)
        values_seq = max(self.values.values()) + 1
        for addon in self.plugins:
            for v in addon.info.get("values", []):
                if v['name'] in self.values: continue
                self.values[v['name']] = values_seq
                values_seq += 1
                self.values_desc[v['name']] = v['desc']

        # Tell the plugins to do the long initialisation bits
        self.progress.verbose("Initializing plugins.")
        for addon in self.plugins:
            addon.obj.init(dict(values=self.values), self.progress)

        return True

    def get_document_from_apt(self, pkg):
        """
        Get a xapian.Document for the given apt package record
        """
        document = xapian.Document()
        # The document data is the package name
        document.set_data(pkg.name)
        # add information about the version of the package in slot 0
        document.add_value(0, pkg.candidate.version)
        # Index the package name with a special prefix, to be able to find this
        # document by exact package name match
        document.add_term("XP"+pkg.name)
        # the query parser is very unhappy about "-" in the pkgname, this
        # breaks e.g. FLAG_WILDCARD based matching, so we add a mangled
        # name here
        document.add_term("XPM"+pkg.name.replace("-","_"))
        # Have all the various plugins index their things
        for addon in self.plugins:
            addon.obj.index(document, pkg)
        return document

    def get_document_from_deb822(self, pkg):
        """
        Get a xapian.Document for the given deb822 package record
        """
        document = xapian.Document()

        # The document data is the package name
        document.set_data(pkg["Package"])
        # add information about the version of the package in slot 0
        document.add_value(0, pkg["Version"])
        # Index the package name with a special prefix, to be able to find this
        # document by exact package name match
        document.add_term("XP"+pkg["Package"])
        # Have all the various plugins index their things
        for addon in self.plugins:
            addon.obj.indexDeb822(document, pkg)
        return document

    def gen_documents_apt(self):
        """
        Generate Xapian documents from an apt cache
        """
        cache = self.aptcache()
        count = len(cache)
        for idx, pkg in enumerate(cache):
            if not pkg.candidate:
                continue
            # multiarch: do not index foreign arch if there is a native
            # archive version available (unless the pkg is installed)
            if (not pkg.installed and
                ":" in pkg.name and pkg.name.split(":")[0] in cache):
                continue
            # Print progress
            if idx % 200 == 0: self.progress.progress(100*idx/count)
            yield self.get_document_from_apt(pkg)

    def gen_documents_deb822(self, fnames):
        try:
            from debian import deb822
        except ImportError:
            from debian_bundle import deb822
        seen = set()
        for fname in fnames:
            infd = open(fname)
            # Get file size to compute progress
            total = os.fstat(infd.fileno())[6]
            for idx, pkg in enumerate(deb822.Deb822.iter_paragraphs(infd)):
                name = pkg["Package"]
                if name in seen: continue
                seen.add(name)
                # Print approximate progress by checking the current read position
                # against the file size
                if total > 0 and idx % 200 == 0:
                    cur = infd.tell()
                    self.progress.progress(100*cur/total)
                yield self.get_document_from_deb822(pkg)

    def compareCacheToDb(self, cache, db):
        """
        Compare the apt cache to the database and return dicts
        of the form (pkgname, docid) for the following states:

        unchanged - no new version since the last update
        outdated - a new version since the last update
        obsolete - no longer in the apt cache
        """
        unchanged = {}
        outdated = {}
        obsolete = {}
        self.progress.begin("Reading Xapian index")
        count = db.get_doccount()
        for (idx, m) in enumerate(db.postlist("")):
            if idx % 5000 == 0: self.progress.progress(100*idx/count)
            doc = db.get_document(m.docid)
            pkg = doc.get_data()
            # this will return '' if there is no value 0, which is fine because it
            # will fail the comparison with the candidate version causing a reindex
            dbver = doc.get_value(0)
            # check if the package no longer exists
            if not cache.has_key(pkg) or not cache[pkg].candidate:
                obsolete[pkg] = m.docid
            # check if we have a new version, we do not have to delete
            # the record,
            elif cache[pkg].candidate.version != dbver:
                outdated[pkg] = m.docid
            # its a valid package and we know about it already
            else:
                unchanged[pkg] = m.docid
        self.progress.end()
        return unchanged, outdated, obsolete

    def is_cjk_enabled (self):
        return "XAPIAN_CJK_NGRAM" in os.environ

    def updateIndex(self, pathname):
        """
        Update the index
        """
        try:
            db = xapian.WritableDatabase(pathname, xapian.DB_CREATE_OR_OPEN)
        except xapian.DatabaseLockError, e:
            self.progress.warning("DB Update failed, database locked")
            return

        # Make sure the index CJK-compatible
        if self.is_cjk_enabled() and db.get_metadata("cjk_ngram") != "1":
            self.progress.notice("The index %s is not CJK-compatible, rebuilding it" % axi.XAPIANINDEX)
            return self.rebuild()

        cache = self.aptcache()
        count = len(cache)

        unchanged, outdated, obsolete = self.compareCacheToDb(cache, db)
        self.progress.verbose("Unchanged versions: %s, oudated version: %s, "
                         "obsolete versions: %s" % (len(unchanged),
                                                    len(outdated),
                                                    len(obsolete)))

        self.progress.begin("Updating Xapian index")
        for a in self.plugins: a.send_extra_info(db=db, aptcache=cache)
        for idx, pkg in enumerate(cache):
            if idx % 1000 == 0: self.progress.progress(100*idx/count)
            if not pkg.candidate:
                continue
            if pkg.name in unchanged:
                continue
            elif pkg.name in outdated:
                # update the existing
                db.replace_document(outdated[pkg.name], self.get_document_from_apt(pkg))
            else:
                # add the new ones
                db.add_document(self.get_document_from_apt(pkg))

        # and remove the obsoletes
        for docid in obsolete.values():
            db.delete_document(docid)

        # finished
        for a in self.plugins:
            a.finished()
        db.flush()
        self.progress.end()

    def incrementalUpdate(self):
        if not os.path.exists(axi.XAPIANINDEX):
            self.progress.notice("No Xapian index built yet: falling back to full rebuild")
            return self.rebuild()

        dbkind, dbpath = open(axi.XAPIANINDEX).readline().split()
        self.updateIndex(dbpath)

        # Update the index timestamp
        if not os.path.exists(axi.XAPIANDBSTAMP):
            open(axi.XAPIANDBSTAMP, "w").close()
        if self.ds_timestamp > 0:
            os.utime(axi.XAPIANDBSTAMP, (self.ds_timestamp, self.ds_timestamp))

    def buildIndex(self, pathname, documents, addoninfo={}):
        """
        Create a new Xapian index with the content provided by the plugins
        """
        self.progress.begin("Rebuilding Xapian index")

        # Create a new Xapian index
        db = xapian.WritableDatabase(pathname, xapian.DB_CREATE_OR_OVERWRITE)

        # Mark the new index as CJK-enabled if relevant
        if self.is_cjk_enabled():
            db.set_metadata("cjk_ngram", "1")

        # It seems to be faster without transactions, at the moment
        #db.begin_transaction(False)

        for a in self.plugins: a.send_extra_info(db=db)

        # Add all generated documents to the index
        for doc in documents:
            db.add_document(doc)

        #db.commit_transaction();
        for a in self.plugins: 
            a.finished()
        db.flush()
        self.progress.end()

    def rebuild(self, pkgfiles=None):
        # Create a new Xapian index with the content provided by the plugins
        # Xapian takes care of preventing concurrent updates and removing the old
        # database if it's left over by a previous crashed update

        # Generate a new index name
        for idx in itertools.count(1):
            tmpidxfname = "index.%d" % idx
            dbdir = os.path.join(axi.XAPIANCACHEPATH, tmpidxfname)
            if not os.path.exists(dbdir): break;

        if pkgfiles:
            generator = self.gen_documents_deb822(pkgfiles)
        else:
            for a in self.plugins: a.send_extra_info(aptcache=self.aptcache())
            generator = self.gen_documents_apt()
        self.buildIndex(dbdir, generator)

        # Update the 'index' symlink to point at the new index
        self.progress.verbose("Installing the new index.")

        #os.symlink(tmpidxfname, axi.XAPIANDBPATH + "/index.tmp")
        out = open(axi.XAPIANINDEX + ".tmp", "w")
        print >>out, "auto", os.path.abspath(dbdir)
        out.close()
        os.rename(axi.XAPIANINDEX + ".tmp", axi.XAPIANINDEX)

        # Remove all other index.* directories that are not the newly created one
        def cleanoldcaches(dir):
            for file in os.listdir(dir):
                if not file.startswith("index."): continue
                # Don't delete what we just created
                if file == tmpidxfname: continue
                fullpath = os.path.join(dir, file)
                # Only delete directories
                if not os.path.isdir(fullpath): continue
                self.progress.verbose("Removing old index %s." % fullpath)
                shutil.rmtree(fullpath)
        cleanoldcaches(axi.XAPIANDBPATH)
        cleanoldcaches(axi.XAPIANCACHEPATH)

        # Commit the changes and update the last update timestamp
        if not os.path.exists(axi.XAPIANDBSTAMP):
            open(axi.XAPIANDBSTAMP, "w").close()
        if self.ds_timestamp > 0:
            os.utime(axi.XAPIANDBSTAMP, (self.ds_timestamp, self.ds_timestamp))

        self.writeValues()
        self.writePrefixes()
        self.writeDoc()

    def writePrefixes(self, pathname=axi.XAPIANDBPREFIXES):
        """
        Write the prefix information on the given file
        """
        self.progress.verbose("Writing prefix information to %s." % pathname)
        out = open(pathname+".tmp", "w")

        print >>out, textwrap.dedent("""
        # This file contains the information about keyword prefixes used in the
        # APT Xapian index.
        #
        # Xapian allows to prefix some terms so they can be told apart from
        # normal keywords: this is used for example with Debtags tags, and
        # stemmed forms.
        #
        # This file lists terms with their index prefix, their queryparser
        # prefix, whether queryparser should treat it as boolean or
        # probabilistic and a short description.
        """).lstrip()

        # Aggregate and normalise prefix information from all the plugins
        prefixes = dict()
        for addon in self.plugins:
            for p in addon.info.get("prefixes", []):
                idx = p.get("idx", None)
                if idx is None: continue
                qp = p.get("qp", None)
                type = p.get("type", None)
                desc = p.get("desc", None)
                # TODO: warn of inconsistencies (plugins that disagree on qp or type)
                old = prefixes.setdefault(idx, dict())
                if qp: old.setdefault("qp", qp)
                if type: old.setdefault("type", type)
                if desc: old.setdefault("desc", desc)

        for name, info in sorted(prefixes.iteritems(), key=lambda x: x[0]):
            print >>out, "%s\t%s\t%s\t# %s" % (
                name,
                info.get("qp", "-"),
                info.get("type", "-"),
                info.get("desc", "(description is missing)"))

        out.close()
        # Atomic update of the documentation
        os.rename(pathname+".tmp", pathname)

    def writeValues(self, pathname=axi.XAPIANDBVALUES):
        """
        Write the value information on the given file
        """
        self.progress.verbose("Writing value information to %s." % pathname)
        out = open(pathname+".tmp", "w")

        print >>out, textwrap.dedent("""
        # This file contains the mapping between names of numeric values indexed in the
        # APT Xapian index and their index
        #
        # Xapian allows to index numeric values as well as keywords and to use them for
        # all sorts of useful querying tricks.  However, every numeric value needs to
        # have a unique index, and this configuration file is needed to record which
        # indices are allocated and to provide a mnemonic name for them.
        #
        # The format is exactly like /etc/services with name, number and optional
        # aliases, with the difference that the second column does not use the
        # "/protocol" part, which would be meaningless here.
        """).lstrip()

        for name, idx in sorted(self.values.iteritems(), key=lambda x: x[1]):
            desc = self.values_desc[name]
            print >>out, "%s\t%d\t# %s" % (name, idx, desc)

        out.close()
        # Atomic update of the documentation
        os.rename(pathname+".tmp", pathname)

    def writeDoc(self, pathname=axi.XAPIANDBDOC):
        """
        Write the documentation in the given file
        """
        self.progress.verbose("Writing documentation to %s." % pathname)
        # Collect the documentation
        docinfo = []
        for addon in self.plugins:
            try:
                doc = addon.obj.doc()
                if doc != None:
                    docinfo.append(dict(
                        name = doc['name'],
                        shortDesc = doc['shortDesc'],
                        fullDoc = doc['fullDoc']))
            except:
                # If a plugin has problem returning documentation, don't worry about it
                self.progress.notice("Skipping documentation for plugin", addon.filename)

        # Write the documentation in pathname
        out = open(pathname+".tmp", "w")
        print >>out, textwrap.dedent("""
        ===============
        Database layout
        ===============

        This Xapian database indexes Debian package information.  To query the
        database, open it as ``%s/index``.

        Data are indexed either as terms or as values.  Words found in package
        descriptions are indexed lowercase, and all other kinds of terms have an
        uppercase prefix as documented below.

        Numbers are indexed as Xapian numeric values.  A list of the meaning of the
        numeric values is found in ``%s``.

        The data sources used for indexing are:
        """).lstrip() % (axi.XAPIANDBPATH, axi.XAPIANDBVALUES)

        for d in docinfo:
            print >>out, " * %s: %s" % (d['name'], d['shortDesc'])

        print >>out, textwrap.dedent("""
        This Xapian index follows the conventions for term prefixes described in
        ``/usr/share/doc/xapian-omega/termprefixes.txt.gz``.

        Extra Debian data sources can define more extended prefixes (starting with
        ``X``): their meaning is documented below together with the rest of the data
        source documentation.

        At the very least, at least the package name (with the ``XP`` prefix) will
        be present in every document in the database.  This allows to quickly
        lookup a Xapian document by package name.

        The user data associated to a Xapian document is the package name.


        -------------------
        Active data sources
        -------------------

        """)
        for d in docinfo:
            print >>out, d['name']
            print >>out, '='*len(d['name'])
            print >>out, textwrap.dedent(d['fullDoc'])
            print >>out

        out.close()
        # Atomic update of the documentation
        os.rename(pathname+".tmp", pathname)

