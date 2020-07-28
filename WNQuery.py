#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
import math
from collections import defaultdict

from WNXMLParser import WNXMLParserContentHandler

DEBUG = False
DEBUG2 = False


class WNQueryException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class InvalidPOSException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class WNQuery:
    """Class for querying WordNet, read from VisDic XML file. Character encoding of all results is UTF-8"""

    def __init__(self, wnxmlfilename, log=sys.stderr):
        """
        Constructor. Create the object: read XML file, create internal indices, invert invertable relations etc.
        :param wnxmlfilename: file name of VisDic XML file holding the WordNet you want to query
        :param log: file handle for writing warnings (e.g. invalid POS etc.) to while loading.
         The default value creates a logger to stderr.
        The following warnings may be produced:
        Warning W01: synset with id already exists
        Warning W02: invalid PoS for synset (NOTE: these synsets are omitted)
        Warning W03: synset is missing (the target synset, when checking when inverting relations)
        Warning W04: self-referencing relation in synset
        @exception WNQueryException thrown if input parsing error occurs
        """
        self.log = log

        # synset ids to synsets
        self.m_ndat = {}  # nouns
        self.m_vdat = {}
        self.m_adat = {}
        self.m_bdat = {}

        # literals to synset ids
        self.m_nidx = defaultdict(list)  # nouns
        self.m_vidx = defaultdict(list)
        self.m_aidx = defaultdict(list)
        self.m_bidx = defaultdict(list)
        self._invRelTable = {'hypernym': 'hyponym', 'holo_member': 'mero_member', 'holo_part': 'mero_part',
                             'holo_portion': 'mero_portion', 'region_domain': 'region_member',
                             'usage_domain': 'usage_member', 'category_domain': 'category_member',
                             'near_antonym': 'near_antonym', 'middle': 'middle', 'verb_group': 'verb_group',
                             'similar_to': 'similar_to', 'also_see': 'also_see', 'be_in_state': 'be_in_state',
                             'eng_derivative': 'eng_derivative', 'is_consequent_state_of': 'has_consequent_state',
                             'is_preparatory_phase_of': 'has_preparatory_phase', 'is_telos_of': 'has_telos',
                             'subevent': 'has_subevent', 'causes': 'caused_by'}

        self._open_and_parse_synsets(wnxmlfilename)
        self.invert_relations()

        # Close defaultdict for safety
        self.m_nidx.default_factory = None
        self.m_vidx.default_factory = None
        self.m_aidx.default_factory = None
        self.m_bidx.default_factory = None

        if DEBUG:
            for curr_dict in (self.m_ndat, self.m_vdat, self.m_adat, self.m_bdat):
                for key, val in curr_dict.items():
                    print(key, ': ', val, sep='', file=sys.stdout)

        if DEBUG2:
            for curr_dict in (self.m_nidx, self.m_vidx, self.m_aidx, self.m_bidx):
                for key, val in curr_dict.items():
                    print(key, ': ', val, sep='', file=sys.stdout)

        self.LeaCho_D = {}
        self.LeaCho_noconnect = - 1.0

        self._pos_to_data = {'n': (self.m_ndat, self.m_nidx), 'v': (self.m_vdat, self.m_vidx),
                             'a': (self.m_adat, self.m_aidx), 'b': (self.m_bdat, self.m_bidx)}

    def write_stats(self, os):
        """
        Write statistics about number of synsets, word senses for each POS.
        :param os: the output stream to write to
        :return:
        """

        print('PoS\t\t#synsets\t#word senses\t#words', file=os)
        print('Nouns', len(self.dat('n')), sum(len(it) for it in self.idx('n').values()), len(self.idx('n')),
              sep='\t\t', file=os)
        print('Verbs', len(self.dat('v')), sum(len(it) for it in self.idx('v').values()), len(self.idx('v')),
              sep='\t\t', file=os)
        print('Adjectives\t', len(self.dat('a')), '\t\t', sum(len(it) for it in self.idx('a').values()), '\t\t',
              len(self.idx('a')), file=os)
        print('Adverbs', len(self.dat('b')), sum(len(it) for it in self.idx('b').values()), len(self.idx('b')),
              sep='\t\t', file=os)

    def _open_and_parse_synsets(self, wnxmlfilename):
        try:
            with open(wnxmlfilename, encoding='UTF-8') as fh:
                for syns, lcnt in WNXMLParserContentHandler().parse(fh):
                    if syns.wnid == '':
                        return

                    try:
                        # check if id already exists, print warning if yes
                        if syns.wnid in self.dat(syns.pos):
                            print('Warning W01: synset with this id (', syns.wnid, ') already exists (input line ',
                                  lcnt, ')', sep='', file=self.log)
                            return

                        # store synset
                        self.dat(syns.pos)[syns.wnid] = syns
                        # index literals
                        for i in syns.synonyms:
                            self.idx(syns.pos)[i.literal].append(syns.wnid)

                    except InvalidPOSException as e:
                        print('Warning W02:', e, 'for synset in input line ', lcnt, file=self.log)
        except (OSError, IOError) as e:
            raise WNQueryException(f'Could not open file: {wnxmlfilename} because: {e}')

    def invert_relations(self):
        """
        Create the inverse pairs of all reflexive relations in all POS.
        Ie. if rel points from s1 to s2, mark inv(rel) from s2 to s1.
        see body of _invRelTable().

        :return:
        """
        for name, dat in (('nouns', self.m_ndat), ('verbs', self.m_vdat), ('adjectives', self.m_adat),
                          ('adverbs', self.m_bdat)):
            print('Inverting relations for ', name, '...', sep='', file=self.log)
            # for all synsets
            for key, val in sorted(dat.items()):
                # for all relations of synset
                for synset_id, rel in sorted(val.ilrs):
                    # check if invertable
                    if rel in self._invRelTable:
                        invr = self._invRelTable[rel]
                        # check if target exists
                        if synset_id not in dat:
                            print('Warning W03: synset ', synset_id, ' is missing (\'', rel, '\' target from synset ',
                                  key, ')', sep='', file=self.log)
                        else:
                            tt = dat[synset_id]
                            # check wether target is not the same as source
                            if tt.wnid == val.wnid:
                                print('Warning W04: self-referencing relation \'', invr, '\' for synset ', val.wnid,
                                      sep='', file=self.log)
                            else:
                                # add inverse to target synset
                                tt.ilrs.append((key, invr))
                                print('Added inverted relation (target=', key, ',type=', invr, ') to synset ', tt.wnid,
                                      sep='', file=self.log)

    # The following functions give access to the internal representation of
    # all the content read from the XML file.
    # Use at your own risk.

    def dat(self, pos):
        """
        Get the appropriate synset-id-to-synset-map for the given POS.
        :param pos: part-of-speech: n|v|a|b
        # @exception WNQueryException if invalid POS
        """
        data = self._pos_to_data.get(pos)
        if data is not None:
            return data[0]
        else:
            raise InvalidPOSException(f'Invalid POS \'{pos}\'')

    def idx(self, pos):
        """
        Get the appropriate literal-to-synset-ids-multimap for the given POS.
        :param pos: part-of-speech: n|v|a|b
        # @exception WNQueryException if invalid POS
        """
        data = self._pos_to_data.get(pos)
        if data is not None:
            return data[1]
        else:
            raise InvalidPOSException(f'Invalid POS \'{pos}\'')

    def look_up_id(self, wnid, pos):
        """
        Get synset with given id.
        :param wnid: synset id to look up
        :param pos: POS of synset
        :return: the synset if it was found, None otherwise
        # @exception InvalidPOSException for invalid POS
        """
        return self.dat(pos).get(wnid)

    def look_up_literal(self, literal, pos):
        """
        Get synsets containing given literal in given POS.
        :param literal: literal to look up (all senses)
        :param pos: POS of literal
        :return: Synsets if liteal was found, None otherwise
        """

        res = []
        for i in self.idx(pos).get(literal, ()):
            syns = self.look_up_id(i, pos)
            if syns is not None:
                res.append(syns)
        return res

    def look_up_literal_s(self, literal, pos):
        """Get ids of synsets containing given literal in given POS."""
        return self.idx(pos).get(literal)

    def look_up_sense(self, literal, sensenum, pos):
        """
        Get synset containing word sense (literal with given sense number) in given POS.
        :param literal: literal to look up
        :param sensenum:sense number of literal
        :param pos: POS of literal
        :return: the synset containing the word sense if it was found, None otherwise
        @exception InvalidPOSException for invalid POS
        """
        for i in self.look_up_literal(literal, pos):
            for j in i.synonyms:
                if j.literal == literal and int(j.sense) == sensenum:
                    return i
        return None

    def look_up_relation(self, wnid, pos, relation):
        """
        Get IDs of synsets reachable from synset by relation
        :param wnid: synset id to look relation from
        :param pos: POS of starting synset
        :param relation: name of relation to look up
        :return: target_ids ids of synsets found go here (empty if starting synset was not found,
         or if no relation was found from it)
        @exception InvalidPOSException for invalid POS
        """
        target_ids = []
        # look up current synset
        if wnid in self.dat(pos):  # found
            # get relation targets
            for synset_id, rel in self.dat(pos)[wnid].ilrs:
                if rel == relation:
                    target_ids.append(synset_id)
        return target_ids

    def get_reach(self, wnid, pos, rel, add_top, dist=1):
        res = []
        # look up current synset
        if wnid in self.dat(pos):  # found
            # add current synset
            res.append((wnid, dist))
            # recurse on children
            dist += 1
            haschildren = False
            for synset_id, relation in self.dat(pos)[wnid].ilrs:  # for all relations of synset
                if relation == rel:  # if it is the right type
                    haschildren = True
                    res += self.get_reach(synset_id, pos, rel, add_top, dist)  # recurse on child

            # if it has no 'children' of this type (is terminal leaf or root level), add artificial 'root' if requested
            if not haschildren and add_top:
                res.append(('#TOP#', dist))
        return res

    def trace_relation(self, wnid, pos, rel, lev=None, unique=False):
        """
        Do a recursive (preorder) trace from the given synset along the given relation.
        :param wnid: id of synset to start from
        :param pos: POS of search
        :param rel: name of relation to trace
        :param lev: starting number of levels
        :param unique: the returning elements should be uniqe (i.e. set) or not (i.e. list) w/ optional levels
        :return: holds the ids of synsets found on the trace. It always holds at least the starting synset
         (so if starting synset has no relations of the searched type, result will only hold that synset).
        """

        # init according to the parameters
        if unique:
            res = set()
            res_append = res.add
        else:
            res = []
            res_append = res.append
        # get children
        ids = self.look_up_relation(wnid, pos, rel)
        # save current synset
        if lev is None:
            to_append = wnid
        else:
            to_append = (wnid, lev)
        res_append(to_append)
        # recurse on children
        lev += 1
        for synset_id in ids:  # for all searched relations of synset
            res += self.trace_relation(synset_id, pos, rel, lev, unique)  # recurse on target
        return res

    def trace_relation_os_r(self, wnid, pos, rel, lev=0):
        """Like trace_relation, but output goes to output stream with pretty formatting."""

        buf = []
        ids = self.look_up_relation(wnid, pos, rel)
        if len(ids) > 0:
            # print current synset
            indent = '  ' * lev
            current = {i.literal: i.sense for i in self.dat(pos)[wnid].synonyms}
            buf.append(f'{indent}{self.dat(pos)[wnid].wnid}  {current}  ({self.dat(pos)[wnid].definition})')
            # Continue lookup recursively
            lev += 1
            for synset_id in ids:
                buf += self.trace_relation_os_r(synset_id, pos, rel, lev)  # recurse on target
        return buf

    def trace_realation_os(self, wnid, pos, relation, out):
        oss = self.trace_relation_os_r(wnid, pos, relation)
        if not oss:
            print('Synset not found', end='\n\n', file=out)
        else:
            print('\n'.join(oss), end='\n\n', file=out)

    def write_synset_id_to_os(self, wnid, pos, out):
        syns = self.look_up_id(wnid, pos)
        if syns:
            syns.write_str(out)

    def look_up_literal_for_pos_os(self, lit, out, pos_list=('n', 'v', 'a', 'b')):
        res = [item for i in pos_list for item in self.look_up_literal(lit, i)]
        if len(res) == 0:
            print('Literal not found', end='\n\n', file=out)
        else:
            for i in res:
                i.write_str(out)
            print(file=out)

    def get_max_depth(self, wnid, pos, relation):
        """
        Calculate the longest possible path to synset from the root level using relation
        :param wnid: id of synset to start from
        :param pos: POS of search
        :param relation: name of relation to use
        :return: 1 if id is a top-level synset, 2 if it's a direct child of a top level synset,
         ..., 1+n for n-level descendants
        If there are several routes from synset to the top level, the longest possible route is used
        @exception InvalidPOSException for invalid POS
        """

        return max(depth for _, depth in self.trace_relation(wnid, pos, relation, lev=1))

    def get_sub_graph_size(self, wnid, pos, relation):
        """
        Calculate the number of nodes in the graph starting from synset id doing a recursive trace using relation
        :param wnid: id of synset to start from
        :param pos: POS of search
        :param relation: relation name of relation to use
        :return: 1 if id is a leaf node (no children using relation); n for n-1 total descendants
            Each descendant is counted only once, even if it can be reached via several different paths
        @exception InvalidPOSException for invalid POS
        """

        return len(self.trace_relation(wnid, pos, relation, unique=True))

    def is_id_connected_with(self, wnid, pos, rel, targ_ids):
        """Check if synset is connected with any of the given synsets on paths defined
         by relation starting from synset."""

        # check if current synset is any of the searched ids
        if wnid in targ_ids:  # found it
            return wnid
        # look up / get children of current synset
        children = self.look_up_relation(wnid, pos, rel)
        if children:
            # recurse on children
            for i in children:
                found_target_id = self.is_id_connected_with(i, pos, rel, targ_ids)  # recurse on target
                if found_target_id is not None:
                    return found_target_id
        return None

    def is_literal_connected_with(self, literal, pos, relation, targ_ids):
        """Check if any sense of literal in POS is connected with any of the specified synsets on paths defined
         by relation starting from that sense."""

        for i in self.look_up_literal(literal, pos):
            found_target_id = self.is_id_connected_with(i.wnid, pos, relation, targ_ids)
            if found_target_id is not None:
                return i.wnid, found_target_id
        return None, None

    def is_literal_compatible_with_synset(self, literal, pos, wnid, hyponyms):
        """Check if literal is in synset, or, if hyponyms is true, is in one of synset's hyponyms (recursive)"""

        # check if synset contains literal
        syns = self.look_up_id(wnid, pos)
        if syns:
            for i in syns.synonyms:
                if i.literal == literal:
                    return True
            # if allowed, recurse on hyponyms
            if hyponyms:
                for synset_id, rel in syns.ilrs:
                    if rel == 'hyponym' and self.is_literal_compatible_with_synset(literal, pos, synset_id, True):
                        return True
        return False

    def are_synonyms(self, literal1, literal2, pos):
        """
        Determine if two literals are synonyms in a PoS, also return id of a synset that contains both.
        :param literal1: first word to be checked
        :param literal2: second word to be checked
        :param pos: PoS of the words (n,v,a,b)
        :return: if there is a synset in 'pos' that contains both literal1 and literal2, its id is returned here
            Note, there may be more synsets containing these two words.
        @exception InvalidPOSException for invalid POS
        """

        # get senses of input literal1, for each sense, check if it contains literal2
        for i in self.look_up_literal(literal1, pos):
            if self.is_literal_compatible_with_synset(literal2, pos, i.wnid, False):
                return i.wnid
        # no common synset
        return None

    def similarity_leacock_chodorow(self, literal1, literal2, pos, relation, add_artificial_top):
        """
        Calculate Leacock-Chodorow similarity between two words using WN.
        :param literal1: the two input words
        :param literal2: the two input words
        :param pos: PoS of the words (n,v,a,b)
        :param relation: the name of the relation to use for finding connecting paths
        :param add_artificial_top: if true, add an artificial top (root) node to ends of relation paths
         so that the whole WN graph will be interconnected. If false, there can literals with zero connections
          (empty results map, see below).
        :return: the results: for every pair of synset ids of all the senses of the input words, the similarity score,
         or empty if either of the 2 words was not found in WN. For a score, first element of the pair of strings
         is the id of a sense of literal1, second element is the id of a sense of literal 2.
         The map is cleared by the function first.
         @exception InvalidPOSException for invalid POS
         Description of method:
         We first look up all the senses of the 2 input words in the given PoS.
         Then, for every possible pair (s1,s2) we calculate the formula:
         sim(s1,s2) = - log ( length_of_shortest_path( s1, s2, relation) / 2 * D)
         where D is a constant (should be at least as much as the longest path in WN using relation,
         see .cpp file for values) length_of_shortest_path is the number of nodes found in the path connecting
         s1 and s2 with relation, so
         if s1 = s2, length_of_shortest_path = 1,
         if s1 is hypernym of s2 (or vice versa), length_of_shortest_path = 2,
         if s1 and s2 are sister nodes (have a common hypernym), length_of_shortest_path = 3, etc.
         Note, when add_artificial_top is true, the formula returns a sim. score of 1.12494 (for path length 3)
         for invalid relation types (since since the path always contains the starting node,
          plus the artificial root node).
        """

        # get senses of input words
        results = {}
        # for each synset pair, calc similarity & put into results
        for i in self.look_up_literal(literal1, pos):
            for j in self.look_up_literal(literal2, pos):
                results[self.sim_lea_cho(i.wnid, j.wnid, pos, relation, add_artificial_top)] = (i.wnid, j.wnid)
        return results

    def sim_lea_cho(self, wnid1, wnid2, pos, relation, add_artificial_top):
        d = self.get_lea_cho_d(pos, relation)
        # get nodes reachable from wnid1, wnid2 by relation + their distances (starting with wnid1/2 with dist. 1)
        # find common node (O(n*m))
        ci_r1 = None
        ci_r2 = None
        path_length = 2*d
        for key1, val1 in self.get_reach(wnid1, pos, relation, add_artificial_top):
            for key2, val2 in self.get_reach(wnid2, pos, relation, add_artificial_top):
                if key1 == key2:
                    if val1 + val2 < path_length:
                        ci_r1 = (key1, val1)
                        ci_r2 = (key2, val2)
                        path_length = val1 + val2

        path_length -= 1  # because the common node was counted twice

        # return similarity score
        if ci_r1 and ci_r2:  # based on length of shortest connecting path
            return -1.0 * math.log10(float(path_length) / (2.0 * d))
        else:  # when no connecting path exists between synsets
            return self.LeaCho_noconnect

    def get_lea_cho_d(self, pos, relation):
        if (pos, relation) not in self.LeaCho_D:
            self.LeaCho_D[(pos, relation)] = max(self.get_max_depth(wnid, pos, relation) for wnid in self.m_ndat)

        return self.LeaCho_D[(pos, relation)]
