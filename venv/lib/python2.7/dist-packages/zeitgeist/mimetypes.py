# -.- coding: utf-8 -.-

# Zeitgeist
#
# Copyright © 2010 Markus Korn <thekorn@gmx.de>
# Copyright © 2010 Canonical Ltd.
#             By Mikkel Kamstrup Erlandsen <mikkel.kamstrup@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re

from datamodel import Interpretation, Manifestation

__all__ = [
    "get_interpretation_for_mimetype",
    "get_manifestation_for_uri",
]

class RegExpr(object):
    """ Helper class which holds a compiled regular expression
    and its pattern."""
    
    def __init__(self, pattern):
        self.pattern = pattern
        self.regex = re.compile(self.pattern)
        
    def __str__(self):
        return self.pattern
        
    def __getattr__(self, name):
        return getattr(self.regex, name)
        
        
def make_regex_tuple(*items):
    return tuple((RegExpr(k), v) for k, v in items)

def get_interpretation_for_mimetype(mimetype):
    """ get interpretation for a given mimetype, returns :const:`None`
    if none of the predefined interpretations matches
    """
    interpretation = MIMES.get(mimetype, None)
    if interpretation is not None:
        return interpretation
    for pattern, interpretation in MIMES_REGEX:
        if pattern.match(mimetype):
            return interpretation
    return None
    
def get_manifestation_for_uri(uri):
    """ Lookup Manifestation for a given uri based on the scheme part,
    returns :const:`None` if no suitable manifestation is found
    """
    for scheme, manifestation in SCHEMES:
        if uri.startswith(scheme):
            return manifestation
    return None
    
    
MIMES = {
    # x-applix-*
    "application/x-applix-word": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "application/x-applix-spreadsheet": Interpretation.SPREADSHEET,
    "application/x-applix-presents": Interpretation.PRESENTATION,
    # x-kword, x-kspread, x-kpresenter, x-killustrator
    "application/x-kword": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "application/x-kspread": Interpretation.SPREADSHEET,
    "application/x-kpresenter": Interpretation.PRESENTATION,
    "application/x-killustrator": Interpretation.VECTOR_IMAGE,
    # MS
    "application/ms-powerpoint": Interpretation.PRESENTATION,
    "application/vnd.ms-powerpoint": Interpretation.PRESENTATION,
    "application/msword": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "application/msexcel": Interpretation.SPREADSHEET,
    "application/ms-excel": Interpretation.SPREADSHEET,
    "application/vnd.ms-excel": Interpretation.SPREADSHEET,
    # pdf, postscript et al
    "application/pdf": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "application/postscript": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "application/ps": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "application/rtf": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "image/vnd.djvu": Interpretation.PAGINATED_TEXT_DOCUMENT,

    # GNOME office
    "application/x-abiword": Interpretation.PAGINATED_TEXT_DOCUMENT,
    "application/x-gnucash": Interpretation.SPREADSHEET,
    "application/x-gnumeric": Interpretation.SPREADSHEET,

    # TeX stuff
    "text/x-tex": Interpretation.SOURCE_CODE,
    "text/x-latex": Interpretation.SOURCE_CODE,

    # Plain text
    "text/plain": Interpretation.TEXT_DOCUMENT,
    "text/csv": Interpretation.TEXT_DOCUMENT,
  
    # HTML files on disk are always HTML_DOCUMENTS while online we should
    # assume them to be WEBSITEs. By default we anticipate local files...
    "text/html": Interpretation.HTML_DOCUMENT,

    # Image types
    "application/vnd.corel-draw": Interpretation.VECTOR_IMAGE,
    "image/jpeg": Interpretation.RASTER_IMAGE,
    "image/pjpeg": Interpretation.RASTER_IMAGE,
    "image/png": Interpretation.RASTER_IMAGE,
    "image/tiff": Interpretation.RASTER_IMAGE,
    "image/gif": Interpretation.RASTER_IMAGE,
    "image/x-xcf": Interpretation.RASTER_IMAGE,
    "image/svg+xml": Interpretation.VECTOR_IMAGE,
    "image/vnd.microsoft.icon": Interpretation.ICON,
    
    # Audio
    "application/ogg": Interpretation.AUDIO,
    "audio/x-scpls": Interpretation.MEDIA_LIST,

    # Development files
    "application/ecmascript": Interpretation.SOURCE_CODE,
    "application/javascript": Interpretation.SOURCE_CODE,
    "application/json": Interpretation.SOURCE_CODE,
    "application/soap+xml": Interpretation.SOURCE_CODE,
    "application/xml-dtd": Interpretation.SOURCE_CODE,
    "application/x-csh": Interpretation.SOURCE_CODE,
    "application/x-designer": Interpretation.SOURCE_CODE,
    "application/x-dia-diagram": Interpretation.SOURCE_CODE,
    "application/x-fluid": Interpretation.SOURCE_CODE,
    "application/x-glade": Interpretation.SOURCE_CODE,
    "application/xhtml+xml": Interpretation.SOURCE_CODE,
    "application/x-java-archive": Interpretation.SOURCE_CODE,
    "application/x-javascript": Interpretation.SOURCE_CODE,
    "application/x-m4": Interpretation.SOURCE_CODE,
    "application/xml": Interpretation.SOURCE_CODE,
    "application/x-perl": Interpretation.SOURCE_CODE,
    "application/x-php": Interpretation.SOURCE_CODE,
    "application/x-ruby": Interpretation.SOURCE_CODE,
    "application/x-shellscript": Interpretation.SOURCE_CODE,
    "application/x-sql": Interpretation.SOURCE_CODE,
    "text/css": Interpretation.SOURCE_CODE,
    "text/javascript": Interpretation.SOURCE_CODE,
    "text/xml": Interpretation.SOURCE_CODE,
    "text/x-c": Interpretation.SOURCE_CODE,
    "text/x-c++": Interpretation.SOURCE_CODE,
    "text/x-chdr": Interpretation.SOURCE_CODE,
    "text/x-copying": Interpretation.SOURCE_CODE,
    "text/x-credits": Interpretation.SOURCE_CODE,
    "text/x-csharp": Interpretation.SOURCE_CODE,
    "text/x-c++src": Interpretation.SOURCE_CODE,
    "text/x-csrc": Interpretation.SOURCE_CODE,
    "text/x-dsrc": Interpretation.SOURCE_CODE,
    "text/x-eiffel": Interpretation.SOURCE_CODE,
    "text/x-gettext-translation": Interpretation.SOURCE_CODE,
    "text/x-gettext-translation-template": Interpretation.SOURCE_CODE,
    "text/x-haskell": Interpretation.SOURCE_CODE,
    "text/x-idl": Interpretation.SOURCE_CODE,
    "text/x-java": Interpretation.SOURCE_CODE,
    "text/x-lisp": Interpretation.SOURCE_CODE,
    "text/x-lua": Interpretation.SOURCE_CODE,
    "text/x-makefile": Interpretation.SOURCE_CODE,
    "text/x-objcsrc": Interpretation.SOURCE_CODE,
    "text/x-ocaml": Interpretation.SOURCE_CODE,
    "text/x-pascal": Interpretation.SOURCE_CODE,
    "text/x-patch": Interpretation.SOURCE_CODE,
    "text/x-python": Interpretation.SOURCE_CODE,
    "text/x-sql": Interpretation.SOURCE_CODE,
    "text/x-tcl": Interpretation.SOURCE_CODE,
    "text/x-troff": Interpretation.SOURCE_CODE,
    "text/x-vala": Interpretation.SOURCE_CODE,
    "text/x-vhdl": Interpretation.SOURCE_CODE,
    "text/x-m4": Interpretation.SOURCE_CODE,
    "text/x-jquery-tmpl": Interpretation.SOURCE_CODE,
    
    # Email
    "message/alternative": Interpretation.EMAIL,
    "message/partial": Interpretation.EMAIL,
    "message/related": Interpretation.EMAIL,
    
    # People
    "text/vcard": Interpretation.CONTACT,
    
    # Archives
    "application/zip": Interpretation.ARCHIVE,
    "application/x-gzip": Interpretation.ARCHIVE,
    "application/x-bzip": Interpretation.ARCHIVE,
    "application/x-lzma": Interpretation.ARCHIVE,
    "application/x-archive": Interpretation.ARCHIVE,
    "application/x-7z-compressed": Interpretation.ARCHIVE,
    "application/x-bzip-compressed-tar": Interpretation.ARCHIVE,
    "application/x-lzma-compressed-tar": Interpretation.ARCHIVE,
    "application/x-compressed-tar": Interpretation.ARCHIVE,
    "application/x-stuffit": Interpretation.ARCHIVE,
    
    # Software and packages
    "application/x-deb": Interpretation.SOFTWARE,
    "application/x-rpm": Interpretation.SOFTWARE,
    "application/x-ms-dos-executable": Interpretation.SOFTWARE,
    "application/x-executable": Interpretation.SOFTWARE,
    "application/x-desktop": Interpretation.SOFTWARE,
    "application/x-shockwave-flash": Interpretation.EXECUTABLE,
    
    # File systems
    "application/x-cd-image": Interpretation.FILESYSTEM_IMAGE,
    "inode/directory": Interpretation.FOLDER,
    
}

MIMES_REGEX = make_regex_tuple(
    # Star Office and OO.org
    ("application/vnd.oasis.opendocument.text.*", Interpretation.PAGINATED_TEXT_DOCUMENT),
    ("application/vnd.oasis.opendocument.presentation.*", Interpretation.PRESENTATION),
    ("application/vnd.oasis.opendocument.spreadsheet.*", Interpretation.SPREADSHEET),
    ("application/vnd.oasis.opendocument.graphics.*", Interpretation.VECTOR_IMAGE),
    ("application/vnd\\..*", Interpretation.DOCUMENT),
    # x-applix-*
    ("application/x-applix-.*", Interpretation.DOCUMENT),
    # MS
    ("application/vnd.ms-excel.*", Interpretation.SPREADSHEET),
    ("application/vnd.ms-powerpoint.*", Interpretation.PRESENTATION),
    ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.*", Interpretation.SPREADSHEET),
    ("application/vnd.openxmlformats-officedocument.presentationml.presentation.*", Interpretation.PRESENTATION),
    ("application/vnd.openxmlformats-officedocument.wordprocessingml.document.*", Interpretation.PAGINATED_TEXT_DOCUMENT),
    # TeX stuff
    (".*/x-dvi", Interpretation.PAGINATED_TEXT_DOCUMENT),
    # Image types
    ("image/.*", Interpretation.IMAGE),
    # Audio
    ("audio/.*", Interpretation.AUDIO),
    # Video
    ("video/.*", Interpretation.VIDEO),
)

SCHEMES = tuple((
    ("file://", Manifestation.FILE_DATA_OBJECT),
    ("http://", Manifestation.WEB_DATA_OBJECT),
    ("https://", Manifestation.WEB_DATA_OBJECT),
    ("ssh://", Manifestation.REMOTE_DATA_OBJECT),
    ("sftp://", Manifestation.REMOTE_DATA_OBJECT),
    ("ftp://", Manifestation.REMOTE_DATA_OBJECT),
    ("dav://", Manifestation.REMOTE_DATA_OBJECT),
    ("davs://", Manifestation.REMOTE_DATA_OBJECT),
    ("smb://", Manifestation.REMOTE_DATA_OBJECT),
))

# vim:noexpandtab:ts=4:sw=4
