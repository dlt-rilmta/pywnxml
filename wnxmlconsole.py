#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
import os
try:
    import readline
except ImportError:
    pass  # Readline module not loaded, seems you're not using Linux. Be sure to fix that.

from WNQuery import WNQuery, InvalidPOSException
from SemFeatures import SemFeaturesParserContentHandler

arg_param_len = {'.h': lambda t: len(t) != 1,
                 '.q': lambda t: len(t) != 1,
                 '.i': lambda t: len(t) != 3,
                 '.l': lambda t: not 1 < len(t) < 5,
                 '.rl': lambda t: not 2 < len(t) < 5,
                 '.ri': lambda t: len(t) != 4,
                 '.ti': lambda t: len(t) != 4,
                 '.tl': lambda t: len(t) != 4,
                 '.ci': lambda t: len(t) != 5,
                 '.cl': lambda t: len(t) != 5,
                 '.s': lambda t: len(t) != 2,
                 '.sc': lambda t: len(t) != 4,
                 '.cli': lambda t: not (len(t) == 4 or (len(t) == 5 and t[4] == 'hyponyms')),
                 '.slc': lambda t: not (len(t) == 5 or (len(t) == 6 and t[5] == 'top')),
                 '.md': lambda t: len(t) != 4,
                 '.sg': lambda t: len(t) != 4
                 }


def process_query(wn, sf, query, out):
    # BEGIN ARGPARSE
    t = query.split(' ')

    if t[0] not in arg_param_len:
        print('Unknown command\n', file=out)
        return
    elif arg_param_len[t[0]](t):
        print('Incorrect format for command', t[0], end='\n\n', file=out)
        return

    if t[0] == '.h':    # .h
        buf = ['Available commands:', '.h                                                this help',
               '.q                                                quit',
               '.i   <id> <pos>                                   look up synset id in given POS (n,v,a,b)',
               '.l   <literal>                                    look up all synsets containing literal in all POS',
               '.l   <literal> <pos>                              look up all synsets containing literal in given POS',
               '.l   <literal> <sensenum> <pos>                   look up synset containing literal with given sense'
               ' number in given POS',
               '.rl  <literal> <pos>                              list known relations of all senses of literal in POS',
               '.rl  <literal> <pos> <relation>                   look up relation (hypernym, hyponym) of all senses'
               ' of literal with id and POS, list target ids',
               '.ri  <id> <pos> <relation>                        look up relation of synset with id and POS,'
               ' list target ids',
               '.ti  <id> <pos> <relation>                        trace relations of synset with id and POS',
               '.tl  <literal> <pos> <relation>                   trace relations of all senses of literal in POS',
               '.ci  <id> <pos> <relation> <id1> [<id2>...]       check if any of id1,id2,... is reachable from id by'
               ' following relation',
               '.cl  <literal> <pos> <relation> <id1> [<id2>...]  check if any of id1,id2,... is reachable'
               ' from any sense of literal by following relation',
               '.cli <literal> <pos> <id> [hyponyms]              check if synset contains literal, or'
               ' if \'hyponyms\' is added, any of its hyponyms',
               '.slc <literal1> <literal2> <pos> <relation> [top] calculate Leacock-Chodorow similarity for all senses'
               ' of literals in pos using relation',
               '                                                  if \'top\' is added, an artificial root node is added'
               ' to relation paths, making WN interconnected.',
               '.md  <id> <pos> <relation>                        calculate the longest possible path to synset with id'
               ' and POS from the root level using relation',
               '.sg  <id> <pos> <relation>                        calculate the number of nodes in the graph starting'
               ' from synset id doing a recursive trace using relation']
        if sf:
            buf.append('.s  <feature>                                     look up semantic feature')
            buf.append('.sc <literal> <pos> <feature>                    check whether any sense of literal'
                       ' is compatible with semantic feature')
        print('\n'.join(buf), end='\n\n', file=out)

    # END ARGPARSE

    elif t[0] == '.q':
        sys.exit(0)
    elif len(t) == 0:
        pass
    elif t[0] == '.i':    # .i
        syns = wn.look_up_id(t[1], t[2])
        if syns is None:
            print('Synset not found', end='\n\n', file=out)
        else:
            syns.write_str(out)
            print(file=out)

    elif t[0] == '.l':   # .l
        if len(t) == 2:  # .l <literal>
            wn.look_up_literal_for_pos_os(t[1], out)  # For all POS

        elif len(t) == 3:  # .l <literal> <pos>
            wn.look_up_literal_for_pos_os(t[1], out, pos_list=(t[2],))  # For t[2] POS only

        elif len(t) == 4:  # .l <literal> <sensenum> <pos>
            syns = wn.look_up_sense(t[1], int(t[2]), t[3])
            if syns is None:
                print('Word sense not found', end='\n\n', file=out)
            else:
                syns.write_str(out)
                print(file=out)

    elif t[0] == '.rl':   # .rl
        senses = wn.look_up_literal(t[1], t[2])
        if not senses:
            print('Literal not found', file=out)

        elif len(t) == 3:  # .rl <literal> <pos>
            for j in senses:
                j.write_str(out)
                rs = set()
                for _, rel in j.ilrs:
                    if rel not in rs:
                        print(' ', rel)
                        rs.add(rel)
                print('', file=out)

        elif len(t) == 4:  # .rl <literal> <pos> <relation>
            for j in senses:
                wn.write_synset_id_to_os(j.wnid, t[2], out)
                for i in wn.look_up_relation(j.wnid, t[2], t[3]):
                    print('  ', end='', file=out)
                    wn.write_synset_id_to_os(i, t[2], out)
                print('', file=out)

    elif t[0] == '.ri':   # .ri
        ids = wn.look_up_relation(t[1], t[2], t[3])
        if len(ids) == 0:
            print('Synset not found or has no relations of the specified type', file=out)
        else:
            for i in ids:
                wn.write_synset_id_to_os(i, t[2], out)

    elif t[0] == '.ti':   # .ti
        wn.trace_realation_os(t[1], t[2], t[3], out)

    elif t[0] == '.tl':   # .tl
        senses = wn.look_up_literal(t[1], t[2])
        if len(senses) == 0:
            print('Literal not found', end='\n\n', file=out)
        else:
            for i in senses:
                wn.trace_realation_os(i.wnid, t[2], t[3], out)

    elif t[0] == '.ci':   # .ci
        foundtarg = wn.is_id_connected_with(t[1], t[2], t[3], set(t[4:]))
        if foundtarg is not None:
            print('Connection found:\nTarget id: ', foundtarg, file=out)
        else:
            print('No connection found', file=out)

    elif t[0] == '.cl':   # .cl
        foundid, foundtarg = wn.is_literal_connected_with(t[1], t[2], t[3], set(t[4:]))
        if foundid is not None and foundtarg is not None:
            print('Connection found:\nSense of literal: ', foundid, '\nTarget id: ', foundtarg,  sep='', file=out)
        else:
            print('No connection found', file=out)

    elif t[0] == '.s':    # .s
        if not sf:
            print('Sorry, semantic features not loaded.', file=out)
        else:
            ids = sorted(sf.look_up_feature(t[1]))
            if len(ids) > 0:
                print(len(ids), ' synset(s) found:\n', '\n'.join(ids), sep='', file=out)
            else:
                print('Semantic feature not found', file=out)

    elif t[0] == '.sc':   # .sc
        if not sf:
            print('Sorry, semantic features not loaded.', file=out)
        else:
            foundid, foundtargid = sf.is_literal_compatible_with_feature(t[1], t[2], t[3])
            if foundid is not None and foundtargid is not None:
                print('Compatibility found:\nSense of literal: ', end='', file=out)
                wn.write_synset_id_to_os(foundid, t[2], out)
                print('Synset ID pertaining to feature: ', end='', file=out)
                wn.write_synset_id_to_os(foundtargid, t[2], out)
            else:
                print('Compatibility not found', file=out)

    elif t[0] == '.cli':  # .cli <literal> <pos> <id> [hyponyms]
        if wn.is_literal_compatible_with_synset(t[1], t[2], t[3], len(t) > 4 and t[4] == 'hyponyms'):
            print('Compatible', file=out)
        else:
            print('Not compatible', file=out)

    elif t[0] == '.slc':  # .slc <literal1> <literal2> <pos> <relation>
        print('Results:', file=out)
        for key, (wnid1, wnid2) in sorted(wn.similarity_leacock_chodorow(t[1], t[2], t[3], t[4],
                                                                         len(t) > 5 and t[5] == 'top').items(),
                                          reverse=True):  # tSims
            print('  ', key, '\t', wnid1, '  ', wnid2, sep='', file=out)

    elif t[0] == '.md':   # .md
        print(wn.get_max_depth(t[1], t[2], t[3]), file=out)

    elif t[0] == '.sg':   # .sg
        print(wn.get_sub_graph_size(t[1], t[2], t[3]), file=out)


def main():
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print('Usage:\n ', sys.argv[0], '<WN_XML_file> [<semantic_features_XML_file>]', file=sys.stderr)
        sys.exit(1)

    # init WN
    print('Reading XML...', file=sys.stderr)
    # Logging to devnull for all OS
    # Source: http://stackoverflow.com/a/2929946
    wn = WNQuery(sys.argv[1], open(os.devnull, 'w'))
    wn.write_stats(sys.stderr)

    # init SemFeatures (if appl.)
    if len(sys.argv) == 3:
        print('Reading SemFeatures...', file=sys.stderr)
        sf = SemFeaturesParserContentHandler.read_xml(wn, sys.argv[2], sys.stderr)
    else:
        sf = None

    # query loop
    print('Type your query, or .h for help, .q to quit', file=sys.stderr)
    while True:
        sys.stderr.flush()
        line = input('>').strip()
        try:
            process_query(wn, sf, line, sys.stdout)
        except InvalidPOSException as e:
            print(e, file=sys.stderr)


if __name__ == '__main__':
    main()
