#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
import os
try:
    import readline
except ImportError:
    pass  # Readline module not loaded, seems you're not using Linux. Be sure to fix that.

import WNQuery
import SemFeatures


def process_query(wn, sf, query, out):
    t = query.split(" ")
    if t[0] == ".h":    # .h
        buf = ["Available commands:", ".h                                                this help",
               ".q                                                quit",
               ".i   <id> <pos>                                   look up synset id in given POS (n,v,a,b)",
               ".l   <literal>                                    look up all synsets containing literal in all POS",
               ".l   <literal> <pos>                              look up all synsets containing literal in given POS",
               ".l   <literal> <sensenum> <pos>                   look up synset containing literal with given sense"
               " number in given POS",
               ".rl  <literal> <pos>                              list known relations of all senses of literal in POS",
               ".rl  <literal> <pos> <relation>                   look up relation (hypernym, hyponym) of all senses"
               " of literal with id and POS, list target ids",
               ".ri  <id> <pos> <relation>                        look up relation of synset with id and POS,"
               " list target ids",
               ".ti  <id> <pos> <relation>                        trace relations of synset with id and POS",
               ".tl  <literal> <pos> <relation>                   trace relations of all senses of literal in POS",
               ".ci  <id> <pos> <relation> <id1> [<id2>...]       check if any of id1,id2,... is reachable from id by"
               " following relation",
               ".cl  <literal> <pos> <relation> <id1> [<id2>...]  check if any of id1,id2,... is reachable"
               " from any sense of literal by following relation",
               ".cli <literal> <pos> <id> [hyponyms]              check if synset contains literal, or"
               " if \"hyponyms\" is added, any of its hyponyms",
               ".slc <literal1> <literal2> <pos> <relation> [top] calculate Leacock-Chodorow similarity for all senses"
               " of literals in pos using relation",
               "                                                  if 'top' is added, an artificial root node is added"
               " to relation paths, making WN interconnected.",
               ".md  <id> <pos> <relation>                        calculate the longest possible path to synset with id"
               " and POS from the root level using relation",
               ".sg  <id> <pos> <relation>                        calculate the number of nodes in the graph starting"
               " from synset id doing a recursive trace using relation"]
        if sf:
            buf.append(".s  <feature>                                     look up semantic feature")
            buf.append(".sc <literal> <pos> <feature>                    check whether any sense of literal"
                       " is compatible with semantic feature")
        print("\n".join(buf), end="\n\n", file=out)
        return

    if t[0] == ".i":    # .i
        if len(t) != 3:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return
        syns = wn.look_up_id(t[1], t[2])
        if not syns:
            print("Synset not found\n", file=out)
        else:
            write_synset(syns, out)
            print("", file=out)
        return

    if t[0] == ".l":    # .l
        if len(t) < 2 or len(t) > 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        if len(t) == 2:  # .l <literal>
            # For n, v, a, b elements we run the look_up_literal function,
            # then we flatten the resulting list of returned lists
            res = [item for i in ("n", "v", "a", "b") for item in wn.look_up_literal(t[1], i)]

            if not res:
                print("Literal not found\n", file=out)
            else:
                for i in res:
                    write_synset(i, out)
                print("", file=out)

        if len(t) == 3:  # .l <literal> <pos>
            res = wn.look_up_literal(t[1], t[2])
            if not res:
                print("Literal not found\n", file=out)
            else:
                for i in res:
                    write_synset(i, out)
                print("", file=out)

        if len(t) == 4:  # .l <literal> <sensenum> <pos>
            syns = wn.look_up_sense(t[1], int(t[2]), t[3])
            if not syns:
                print("Word sense not found\n", file=out)
            else:
                write_synset(syns, out)
                print("", file=out)
        return

    if t[0] == ".rl":   # .rl
        if len(t) != 3 and len(t) != 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        if len(t) == 3:  # .rl <literal> <pos>
            ss = wn.look_up_literal(t[1], t[2])
            if not ss:
                print("Literal not found", file=out)
            else:
                for j in ss:
                    write_synset(j, out)
                    rs = set()
                    for _, rel in j.ilrs:
                        if rel not in rs:
                            print("  {0}".format(rel))
                            rs.add(rel)
                    print("", file=out)

        if len(t) == 4:  # .rl <literal> <pos> <relation>
            ss = wn.look_up_literal(t[1], t[2])
            if not ss:
                print("Literal not found", file=out)
            else:
                for j in ss:
                    write_synset_id(wn, j.wnid, t[2], out)
                    ids = wn.look_up_relation(j.wnid, t[2], t[3])
                    if ids:
                        for i in ids:
                            print("  ", end="", file=out)
                            write_synset_id(wn, i, t[2], out)
                    print("", file=out)
        return

    if t[0] == ".ri":   # .ri
        if len(t) != 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        ids = wn.look_up_relation(t[1], t[2], t[3])
        if not ids:
            print("Synset not found or has no relations of the specified type", file=out)
        else:
            for i in ids:
                write_synset_id(wn, i, t[2], out)
        return

    if t[0] == ".ti":   # .ti
        if len(t) != 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        oss = wn.trace_relation_os(t[1], t[2], t[3])
        if not oss:
            print("Synset not found\n", file=out)
        else:
            print("\n".join(oss), end="\n\n", file=out)
        return

    if t[0] == ".tl":   # .tl
        if len(t) != 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        senses = wn.look_up_literal(t[1], t[2])
        if not senses:
            print("Literal not found\n", file=out)
        else:
            for i in senses:
                oss = wn.trace_relation_os(i.wnid, t[2], t[3])
                if not oss:
                    print("Synset not found\n", file=out)
                else:
                    print("\n".join(oss), end="\n\n", file=out)
        return

    if t[0] == ".ci":   # .ci
        if len(t) < 5:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        foundtarg = wn.is_id_connected_with(t[1], t[2], t[3], set(t[4:]))
        if foundtarg:
            print("Connection found to {0}".format(foundtarg), file=out)
        else:
            print("No connection found", file=out)
        return

    if t[0] == ".cl":   # .cl
        if len(t) < 5:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        foundid, foundtarg = wn.is_literal_connected_with(t[1], t[2], t[3], set(t[4:]))
        if foundid and foundtarg:
            print("Connection found:\nSense of literal: {0}\nTarget id: {1}".format(foundid, foundtarg), file=out)
        else:
            print("No connection found", file=out)
        return

    if t[0] == ".s":    # .s
        if not sf:
            print("Sorry, semantic features not loaded.", file=out)
            return

        if len(t) != 2:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        ids = sorted(sf.look_up_feature(t[1]))
        if ids:
            print("{0} synset(s) found:\n{1}".format(len(ids), "\n".join(ids)), file=out)
        else:
            print("Semantic feature not found", file=out)
        return

    if t[0] == ".sc":   # .sc
        if not sf:
            print("Sorry, semantic features not loaded.", file=out)
            return

        if len(t) != 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        foundid, foundtargid = sf.is_literal_compatible_with_feature(t[1], t[2], t[3])
        if foundid and foundtargid:
            print("Compatibility found:\nSense of literal: ", end="", file=out)
            write_synset_id(wn, foundid, t[2], out)
            print("Synset ID pertaining to feature: ", end="", file=out)
            write_synset_id(wn, foundtargid, t[2], out)
        else:
            print("Compatibility not found", file=out)
        return

    if t[0] == ".cli":  # .cli <literal> <pos> <id> [hyponyms]
        hyps = len(t) == 5 and t[4] == "hyponyms"

        if not (len(t) == 4 or hyps):
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        if wn.is_literal_compatible_with_synset(t[1], t[2], t[3], hyps):
            print("Compatible", file=out)
        else:
            print("Not compatible", file=out)
        return

    if t[0] == ".slc":  # .slc <literal1> <literal2> <pos> <relation>
        addtop = len(t) == 6 and t[5] == "top"

        if not (len(t) == 5 or addtop):
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        print("Results:", file=out)
        for key, (wnid1, wnid2) in sorted(wn.similarity_leacock_chodorow(t[1], t[2], t[3], t[4], addtop).items(),
                                          reverse=True):  # tSims
            print("  {0}\t{1}  {2}".format(key, wnid1, wnid2), file=out)
        return

    if t[0] == ".md":   # .md
        if len(t) != 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        print(wn.get_max_depth(t[1], t[2], t[3]), file=out)
        return

    if t[0] == ".sg":   # .sg
        if len(t) != 4:
            print("Incorrect format for command {0}\n".format(t[0]), file=out)
            return

        print(wn.get_sub_graph_size(t[1], t[2], t[3]), file=out)
        return

    print("Unknown command\n", file=out)


def write_synset(syns, out):
    """This is exact same function as Synset.write_str(out)"""
    buff = []
    for i in syns.synonyms:
        buff.append("{0}:{1}".format(i.literal, i.sense))
    print("{0}  {{{1}}}  ({2})".format(syns.wnid, ", ".join(buff), syns.definition), file=out)


def write_synset_id(wn, wnid, pos, out):
    syns = wn.look_up_id(wnid, pos)
    if syns:
        write_synset(syns, out)


def main():
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("Usage:\n  {0} <WN_XML_file> [<semantic_features_XML_file>]".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    # init WN
    print("Reading XML...", file=sys.stderr)
    # Logging to devnull for all OS
    # Source: http://stackoverflow.com/a/2929946
    wn = WNQuery.WNQuery(sys.argv[1], open(os.devnull, "w"))
    wn.write_stats(sys.stderr)

    # init SemFeatures (if appl.)
    if len(sys.argv) == 3:
        print("Reading SemFeatures...", file=sys.stderr)
        sf = SemFeatures.SemFeaturesParserContentHandler(wn)
        stats = sf.read_xml(sys.argv[2])
        print("{0} pairs read".format(stats), file=sys.stderr)
    else:
        sf = None

    # query loop
    print("Type your query, or .h for help, .q to quit", file=sys.stderr)
    while True:
        # print(">", end="", file=sys.stderr)
        # line = sys.stdin.readline().strip()
        sys.stderr.flush()
        line = input('>').strip()
        if line == ".q":
            sys.exit(0)
        elif line != "":
            try:
                process_query(wn, sf, line, sys.stdout)
            except InvalidPOSException as e:
                print(e, file=sys.stderr)


class InvalidPOSException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


if __name__ == '__main__':
    main()
