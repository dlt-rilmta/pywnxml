#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re


class Synonym:
    def __init__(self, lit, s, o='', n=''):
        self.literal = lit
        self.sense = s
        self.lnote = o
        self.nucleus = n

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

        self.synonyms = []  # Vector of Synonym type

    def empty(self):
        """
        check if empty
        """
        return self.wnid == ''

    @staticmethod
    def str_list_of_pair(name, var):
        buf = ', '.join(sorted(f'({key}, {val})' for key, val in var))
        return f'{name}([{buf}])'

    def __str__(self):
        usages = ', '.join(sorted(self.usages))
        snotes = ', '.join(sorted(self.snotes))
        buf = [f'Synset(wnid: {self.wnid}, pos: {self.pos}, definition: {self.definition}, bcs: {self.bcs},'
               f' stamp: {self.stamp}, domain: {self.domain}, nl: {self.nl}, tnl: {self.tnl}, Usages([{usages}]),'
               f' Snotes([{snotes}])', self.str_list_of_pair('Ilrs', self.ilrs),
               self.str_list_of_pair('Sumolinks', self.sumolinks), self.str_list_of_pair('Elrs', self.elrs),
               self.str_list_of_pair('Ekszlinks', self.ekszlinks),
               self.str_list_of_pair('Vframelinks', self.vframelinks)]
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
        self.elrs3 = []         # (target id, rel-type) pairs of external relation pointers, to PWN3.0
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

        if self.wnid3 != '':
            wnid3 = self._tagstr('ID3', self.wnid3)
        else:
            wnid3 = ''
        print('<SYNSET>', self._tagstr('ID', self.wnid), wnid3, self._tagstr('POS', self.pos), '<SYNONYM>',
              sep='', end='', file=out)

        for i in self.synonyms:
            if i.lnote != '':
                lnote_out = self._tagstr('LNOTE', i.lnote)
            else:
                lnote_out = ''

            if i.nucleus != '':
                nucleus_out = self._tagstr('NUCLEUS', i.nucleus)
            else:
                nucleus_out = ''

            print('<LITERAL>', self._escape_pcdata_chars(i.literal), self._tagstr('SENSE', i.sense), lnote_out,
                  nucleus_out, '</LITERAL>', sep='', end='', file=out)

        print('</SYNONYM>', end='', file=out)

        # uniq internal relations (remove inverted relations if needed?)
        self.ilrs = list(sorted(set(self.ilrs)))

        self._tag_helper(self.ilrs, 'ILR', out)

        self._tag_helper2(self.definition, 'DEF', self.bcs, 'BCS', out)

        self._tag_helper3(self.usages, 'USAGE', out)

        self._tag_helper3(self.snotes, 'SNOTE', out)

        self._tag_helper2(self.stamp, 'STAMP', self.domain, 'DOMAIN', out)

        self._tag_helper(self.sumolinks, 'SUMO', out)

        self._tag_helper2(self.nl, 'NL', self.tnl, 'TNL', out)

        self._tag_helper(self.elrs, 'ELR', out)

        self._tag_helper(self.elrs3, 'ELR3', out)

        self._tag_helper(self.ekszlinks, 'EKSZ', out)

        self._tag_helper(self.vframelinks, 'VFRAME', out)

        print('</SYNSET>', end='', file=out)

    def _tag_helper(self, var, tag, out):
        for key, val in var:
            print('<', tag, '>', key, self._tagstr('TYPE', val), '</', tag, '>', sep='', end='', file=out)

    def _tag_helper2(self, var, tag, var2, tag2, out):
        if var != '':
            var_out = self._tagstr(tag, var)
        else:
            var_out = ''

        if var2 != '':
            var2_out = self._tagstr(tag2, var2)
        else:
            var2_out = ''

        print(var_out, var2_out, sep='', end='', file=out)

    def _tag_helper3(self, var, tag, out):
        for i in var:
            print(self._tagstr(tag, i), end='', file=out)

    def write_str(self, out):
        """
        Write string representation (see below) to stream
        """
        print(self.to_string(), end='', file=out)

    def to_string(self):
        """
        Return string representation: '<id> {<literal:sid>,...} (<definiton>)'
        """
        synonyms = ', '.join(f'{i.literal}:{i.sense}' for i in self.synonyms)
        return f'{self.wnid}  {{{synonyms}}}  ({self.definition})'

    def _tagstr(self, tag, string):
        return f'<{tag}>{self._escape_pcdata_chars(string)}</{tag}>'

    @staticmethod
    def _escape_pcdata_chars(string):
        return re.sub('&(?![a-zA-Z0-9_#-]+;)', '&amp;', string).replace('<', '&lt;').replace('>', '&gt;').\
            replace('\'', '&apos;').replace('"', '&quot;')
