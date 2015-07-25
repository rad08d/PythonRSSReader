#!/usr/bin/python3

import os

from file_io import load_file
from lists import to_list
from text import to_bool

class InvalidConfig():
    def __init__(self, item):
        self.item = item
    def __str__(self):
        return "Invalid configuration: %s" %(self.item)

class Config(object):
    '''Yet another INI-style config file parser.

    Assumes a "key = value" style file, with # anywhere on line to
    indicate a comment.

    Lines can be continued with either backslash (\) or a trailing
    comma, if the subsequent line is space-indented.

    All keys from the file are loaded as data members of this class so
    can be easily referenced as "config.key".

    If a key name includes one or more periods (.) it is converted into
    a dict.  So, "foo.bar.baz = doh.blah, 42.1" in the config file would be
    referenced in code as "foo['bar']['baz'] = 'doh.blah, 42.1'.

    The 'include' keyword is supported as a way to import the contents
    of another file, which is then parsed and handled as above, with all
    elements brought into the current namespace.
    '''
    def __init__(self, filename=None, lines=None):
        if filename is not None:
            self._filename = os.path.expanduser(filename)
            if os.path.exists(self._filename):
                self.load(load_file(self._filename))
        if lines is not None:
            self.load(lines=lines)

    @property
    def filename(self):
        """The name of the file the config was loaded from.

        Returns None if config was provided directly during
        initialization.
        """
        try:
            return self._filename
        except:
            return None

    def clear(self):
        """Deletes all config data from object"""
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            del self.__dict__[key]

    def copy(self, obj):
        """Copies contents of another config object"""
        if obj is None or len(obj.__dict__.keys()) < 1:
            return

        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue
            old_value = self.__dict__.get(key, None)
            if old_value is not None and type(old_value) != type(value):
                if type(old_value) is list and type(value) is str:
                    value = to_list(value)
                else:
                    raise InvalidConfig("key %s (type %s) given for a type %s" %(
                            key, type(value), type(old_value)))
            self.__dict__[key] = value

    def set(self, option, value):
        """Sets an option, handling dots as a path of dicts"""
        def _recurse_set(parent_dict, fields, value):
            field = fields[0]
            if len(fields) == 1:
                if type(parent_dict.get(field,None)) is list:
                    parent_dict[field] = to_list(value)
                elif type(parent_dict.get(field,None)) is bool:
                    parent_dict[field] = to_bool(value)
                else:
                    parent_dict[field] = value
                return
            if field not in parent_dict:
                parent_dict[field] = {}
            elif type(parent_dict[field]) is not dict:
                buf = parent_dict[field]
                parent_dict[field] = {'': buf}
            _recurse_set(parent_dict[field], fields[1:], value)

        _recurse_set(self.__dict__, option.split('.'), value)

    def get(self, option, default=None):
        """Retrieves an option, with dots navigating dict tree"""
        def _recurse_get(parent_dict, fields):
            field = fields[0]
            if field not in parent_dict:
                parent_dict[field] = ''
            if type(parent_dict[field]) is not dict:
                return parent_dict[field]
            return _recurse_get(parent_dict[field], fields[1:])

        return _recurse_get(self.__dict__, option.split('.'))

    def load(self, lines=None):
        """Parses given lines into the config"""
        if not lines:
            return
        if type(lines) is not list:
            lines = lines.split("\n")

        assert(type(lines) is list)
        possible_continuation = False
        last_option = None
        for line in lines:
            if len(line.strip()) == 0:
                last_option = None
                possible_continuation = False
                continue
            # We can continue only if this line starts with space and
            # the prior line ended in a continuation character (\ or ,)
            if possible_continuation and not line[0].isspace():
                possible_continuation = False
                last_option = None
            line = line.split('#')[0].strip()

            # Check for possible continuation to the next line
            if line.endswith('\\'):
                possible_continuation = True
                line = line[:-1].strip()
            elif line.endswith(','):
                possible_continuation = True

            # Add the option to ourself
            if '=' in line:
                option, value = line.split('=', 1)
                option = option.strip()
                if option:
                    last_option = option
                    self.set(option, value.strip())

            # Line continues from previous, just append to prior value
            elif possible_continuation and last_option:
                old_value = self.get(last_option)
                if type(old_value) is list:
                    old_value.extend(to_list(line))
                else:
                    old_value += " " + line
                self.set(last_option, old_value)

            # Import another config file
            elif line[:8] == 'include ':
                filename = line[8:].strip()
                lines = load_file(filename)
                self.load(lines)
                possible_continuation = False
                last_option = None

    def __str__(self):
        def _value_to_str(key, value):
            assert(type(value) is not dict)
            if value is None:
                return "%s=\n" %(key)
            elif type(value) is list:
                return "%s=%s\n" %(key, ', '.join(str(x) for x in value))
            else:
                return "%s=%s\n" %(key, str(value))
        def _items_to_str(parent, items):
            text = ''
            for key, value in items:
                if parent is not None:
                    param = "%s.%s" %(parent, key)
                else:
                    param = key
                if type(value) is dict:
                    text += _items_to_str(param,value.items())
                else:
                    text += _value_to_str(param,value)
            return text

        return _items_to_str(None, self.__iter__())

    def __len__(self):
        return len(list(self.__iter__()))

    def __getitem__(self, key):
        return self.__dict__.get(key, None)

    def __iter__(self):
        keys = self.__dict__.items()
        keys.sort()
        for key,value in keys:
            if key.startswith('_') or key=='':
                continue
            yield (key,value)

    def __contains__(self, item):
        if item.startswith('_'):
            return False
        return item in self.__dict__.keys()

if __name__ == "__main__":
    #config = Config("~/.config/user-dirs.dirs")
    #config = Config("~/.taskhelmrc")
    config = Config("~/.taskrc")
    print(config)
    print()
    print(config.shell['prompt'])
    print(config.color)

    config.clear()
    assert( str(config) == '')
