#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from xml.sax.saxutils import escape
QUOTES = {'\'': '&apos;', '"': '&quot;'}


class Synonym:
    def __init__(self, literal, sense, lnote='', nucleus=''):
        self.literal = literal
        self.sense = sense
        self.lnote = lnote
        self.nucleus = nucleus

    def __str__(self):
        return f'Synonym(literal: {self.literal}, sense: {self.sense}, lnote: {self.lnote}, nucleus: {self.nucleus})'


class Synset:
    def __init__(self):
        self.wnid = ''
        self.wnid3 = ''  # PWN3.0 synset id
        self.pos = ''
        self.definition = ''
        self.bcs = ''
        self.stamp = ''
        self.domain = ''
        self.nl = ''
        self.tnl = ''

        self.usages = []  # List of strings
        self.snotes = []  # List of strings

        # Type for vector of 'pointer', which are pairs whose 1st component it the link target (id),
        # 2nd component is the link type
        # In Python: [ ('', '') ] WARNING: Tuples are inmutable in Python!
        self.ilrs = []          # (target-id, rel-type) relation pointers
        self.sumolinks = []     # (target-term, link-type) SUMO links
        self.elrs = []          # (target id, rel-type) pairs of external relation pointers
        self.elrs3 = []         # (target id, rel-type) pairs of external relation pointers, to PWN3.0
        self.ekszlinks = []     # (sense-id, link-type) pairs of EKSz links
        self.vframelinks = []   # (verb-frame-id, link-type) pairs of verb frame links

        self.synonyms: [Synonym] = []  # Vector of Synonym type

    @staticmethod
    def _str_list_of_pair(name, var):
        buf = ', '.join(sorted(f'({key}, {val})' for key, val in var))
        return f'{name}([{buf}])'

    def __str__(self):
        usages = ', '.join(sorted(self.usages))
        snotes = ', '.join(sorted(self.snotes))
        buf = [f'Synset(wnid: {self.wnid}, pos: {self.pos}, definition: {self.definition}, bcs: {self.bcs},'
               f' stamp: {self.stamp}, domain: {self.domain}, nl: {self.nl}, tnl: {self.tnl}, Usages([{usages}]),'
               f' Snotes([{snotes}])', self._str_list_of_pair('Ilrs', self.ilrs),
               self._str_list_of_pair('Sumolinks', self.sumolinks), self._str_list_of_pair('Elrs', self.elrs),
               self._str_list_of_pair('Ekszlinks', self.ekszlinks),
               self._str_list_of_pair('Vframelinks', self.vframelinks)]
        for s in self.synonyms:
            buf.append(str(s))
        ret = ', '.join(buf) + ')'
        return ret

    # clear/reset data members
    def clear(self):
        self.wnid = ''
        self.wnid3 = ''  # PWN3.0 synset id
        self.pos = ''
        self.definition = ''
        self.bcs = ''
        self.stamp = ''
        self.domain = ''
        self.nl = ''
        self.tnl = ''
        self.usages = []
        self.snotes = []
        self.ilrs = []
        self.sumolinks = []
        self.elrs = []
        self.elrs3 = []  # (target id, rel-type) pairs of external relation pointers, to PWN3.0
        self.ekszlinks = []
        self.vframelinks = []
        self.synonyms = []

    @staticmethod
    def write_xml_header(out):
        """Write XML declaration, DTD reference and root opening tag to out."""

        xml_decl = '<?xml version="1.0" encoding="UTF-8"?>'
        xml_doctypedecl = '<!DOCTYPE WNXML SYSTEM "wnxml.dtd">'
        print(xml_decl, xml_doctypedecl, '<WNXML>', sep='\n', file=out)

    @staticmethod
    def write_xml_footer(out):
        """Write XML root closing tag to out."""

        print('</WNXML>', file=out)
      
    def write_xml(self, out):
        """Write VisDic XML representation of synset to stream"""

        print('<SYNSET>', self._tagstr('ID', self.wnid), self._tagstr('ID3', self.wnid3, opt=True),
              self._tagstr('POS', self.pos), '<SYNONYM>', sep='', end='', file=out)

        for i in self.synonyms:
            print('<LITERAL>', escape(i.literal, entities=QUOTES), self._tagstr('SENSE', i.sense),
                  self._tagstr('LNOTE', i.lnote, opt=True), self._tagstr('NUCLEUS', i.nucleus, opt=True), '</LITERAL>',
                  sep='', end='', file=out)
        print('</SYNONYM>', end='', file=out)

        # uniq internal relations (remove inverted relations if needed?)
        self.ilrs = list(sorted(set(self.ilrs)))

        for key, val in self.ilrs:
            print('<ILR>', key, self._tagstr('TYPE', val), '</ILR>', sep='', end='', file=out)

        print(self._tagstr('DEF', self.definition, opt=True), self._tagstr('BCS', self.bcs, opt=True),
              sep='', end='', file=out)

        for i1 in self.usages:
            print(self._tagstr('USAGE', i1), end='', file=out)

        for i2 in self.snotes:
            print(self._tagstr('SNOTE', i2), end='', file=out)

        print(self._tagstr('STAMP', self.stamp, opt=True), self._tagstr('DOMAIN', self.domain, opt=True),
              sep='', end='', file=out)

        for key1, val1 in self.sumolinks:
            print('<SUMO>', key1, self._tagstr('TYPE', val1), '</SUMO>', sep='', end='', file=out)

        print(self._tagstr('NL', self.nl, opt=True), self._tagstr('TNL', self.tnl, opt=True), sep='', end='', file=out)

        for var, tag in ((self.elrs, 'ELR'), (self.elrs3, 'ELR3'), (self.ekszlinks, 'EKSZ'),
                         (self.vframelinks, 'VFRAME')):
            for key2, val2 in var:
                print('<', tag, '>', key2, self._tagstr('TYPE', val2), '</', tag, '>', sep='', end='', file=out)

        print('</SYNSET>', end='', file=out)

    def write_str(self, out):
        """
        Write string representation '<id> {<literal:sid>,...} (<definiton>)' to stream
        """
        print(self.wnid, '  {', ', '.join(f'{i.literal}:{i.sense}' for i in self.synonyms),
              '}  (', self.definition, ')', sep='', file=out)

    @staticmethod
    def _tagstr(tag, string, opt=False):
        if opt and string == '':
            return ''
        return f'<{tag}>{escape(string, entities=QUOTES)}</{tag}>'
