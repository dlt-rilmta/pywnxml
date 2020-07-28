#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
from xml.sax.handler import ErrorHandler, ContentHandler
from xml.sax.xmlreader import Locator
from xml.sax import make_parser
from collections import defaultdict

DEBUG = False


class SemFeaturesParserException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class SemFeaturesParserErrorHandler(ErrorHandler):
    def warning(self, msg):
        print('SAX parser warning:', msg, file=sys.stderr)

    def error(self, msg):
        raise SemFeaturesParserException(f'SAX parser error: {msg}')

    def fatal(self, msg):
        raise SemFeaturesParserException(f'SAX parser fatal error: {msg}')


class SemFeaturesParserContentHandler(ContentHandler):
    def __init__(self, wn):
        """
        Constructor.
            :param wn: an existing WNQuery object, that will be used for querying.
            @exception SemFeaturesException on file parsing errors
        """

        ContentHandler.__init__(self)
        self._locator = Locator()  # Dummy setDocumentLocator does the same!
        self.setDocumentLocator(self._locator)
        self.m_lcnt = 0                     # input line number
        self.m_ppath = []                   # contains the XML path to the current node (names of the ancestors)
        self.m_currfeat = ''                # feature currently being processed
        self.m_wn = wn                      # WordNet (WNQuery)
        self.m_featmap = defaultdict(list)  # semantic features to synset ids

    def startElement(self, name, attrs):
        if DEBUG:
            print('(', self._locator.getLineNumber(), ', ', self._locator.getColumnNumber(), '): /',
                  '/'.join(self.m_ppath), '/START: ', name, sep='')
            self.m_ppath.append(name)

        if name == 'semfeature' and 'name' in attrs:
            # save current attribute
            self.m_currfeat = attrs['name']
        elif name == 'synset' and 'id' in attrs:
            # save current attribute + synset pair
            self.m_featmap[self.m_currfeat].append(attrs['id'])

    def characters(self, chrs):
        if DEBUG:
            print('(', self._locator.getLineNumber(), ', ', self._locator.getColumnNumber(), '): /',
                  '/'.join(self.m_ppath), '#PCDATA: ', chrs, sep='')

    def endElement(self, name):
        if DEBUG:
            print('(', self._locator.getLineNumber(), ', ', self._locator.getColumnNumber(), '): /',
                  '/'.join(self.m_ppath), '/END: ', name, sep='')

        self.m_ppath.pop()

    def look_up_feature(self, feature):
        """
        Get synset ids mapped to a semantic feature.
        :param feature: name of semantic feature to look up
        :return: res result: synset ids pertaining to feature, or empty if feature was not found
        """
        return {wnid for wnid in self.m_featmap[feature] if feature in self.m_featmap}

    def is_literal_compatible_with_feature(self, literal, pos, feature):
        """
        Check whether a literal with given POS is compatible with the given semantic feature.
        Check if any sense of literal in WN is a (distant) hyponym of any of the synset ids corresponding
         to the semantic feature.
        :param literal: the literal to check
        :param pos: part-of-speech of literal (allowed values: n, v, a, b)
        :param feature: feature semantic feature to check
        :return: res_sense_ssid if compatibility was found, the id of the synset containing the sense of the literal
                            that was compatible with the feature
             res_feature_ssid if compatibility was found, the synset id of the interpretation of the feature
                            that was found to be compatible with the literal
             true if compatibility was found, false otherwise (no sense of literal was compatible with any of ids
                            pertaining to feature, or literal or feature was not found)
        """
        feat_ids = self.look_up_feature(feature)
        if len(feat_ids) > 0:
            return self.m_wn.is_literal_connected_with(literal, pos, 'hypernym', feat_ids)
        return None, None

    @classmethod
    def read_xml(cls, wn, semfeaturesfilename, os):
        """
        Read mapping (semantic features to synset ids) from XML file.
        :param wn: An Initialised WNQuery instance
        :param semfeaturesfilename: name of XML file
        :param os: output stream number of feature name-synset id pairs read successfully
        :return: Initialised instance
        """
        content_handler = cls(wn)
        # open file
        try:
            with open(semfeaturesfilename, encoding='UTF-8') as fh:
                # Magic lies here
                # Source: http://stackoverflow.com/a/12263340
                # Make parser
                xml_reader = make_parser()
                # set self as ContentHandler
                xml_reader.setContentHandler(content_handler)
                # Set ErrorHandler
                xml_reader.setErrorHandler(SemFeaturesParserErrorHandler())
                # Do the actual parsing
                xml_reader.parse(fh)
        except (OSError, IOError) as e:
            raise SemFeaturesParserException(f'Could not open file: {semfeaturesfilename} because: {e}')

        # Close defaultdict for safety
        content_handler.m_featmap.default_factory = None
        # Return the gathered result
        m_featmap_len = 0
        for it in content_handler.m_featmap.values():
            m_featmap_len += len(it)
        print(m_featmap_len, 'pairs read', file=os)
        return cls
