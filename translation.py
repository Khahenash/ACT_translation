#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
:Authors:
	Carl Goubeau

:Date:
	2014/9/8 (creation)

:Description:
    Translation tool for unknown words in a dictionary
"""

import sys
import os
import codecs
import re
import math
from operator import itemgetter
import xml.etree.ElementTree as ET
from script_lib import *



####################################################################
###########            LEXICONEXTRACTOR                 ############
####################################################################


class LexiconExtractor:
    def __init__(self, source, target, dict_path):
        print "\n=== Lexicon Extractor ==="
        self.sourceList = source
        self.targetList = target
        self.frEnDict = {}
        self._targetFreq = {}

        print "Loading dictionary ..."
        fr_en_dict = codecs.open(dict_path, "r", "utf-8")
        for line in fr_en_dict.readlines():
            l = line.split(";")
            if l[0] in self.frEnDict:
                if l[3] not in self.frEnDict[l[0]]:
                    self.frEnDict[l[0]].append(l[3])
            else:
                self.frEnDict[l[0]] = [l[3]]
        fr_en_dict.close()

        # print "Loading cognates ..."
        #TODO

        print "Building source word frequency dictionary ..."
        self._sourceFreq = {}
        for w in self.sourceList:
            if w in self._sourceFreq:
                self._sourceFreq[w] += 1
            else:
                self._sourceFreq[w] = 1
        print color.GREEN + "[DONE]" + color.END

        print "Building target word frequency dictionary ..."
        for w in self.targetList:
            if w in self._targetFreq:
                self._targetFreq[w] += 1
            else:
                self._targetFreq[w] = 1
        print color.GREEN + "[DONE]" + color.END


    def translate(self, vector, stopwords):
        translated_vector = {"<unk>": 0}
        for word in vector.keys():
            if word in self.frEnDict and word not in stopwords:
                translation_lst = self.frEnDict[word]

                freq_sum = 0
                for elem in translation_lst:
                    if elem in self._targetFreq:
                        freq_sum += self._targetFreq[elem]

                for tr_word in translation_lst:
                    if tr_word in self._targetFreq:
                        translated_vector[tr_word] = float(vector[word]) * float(self._targetFreq[tr_word]) / float(freq_sum)

            # <unk> ??? FIXME
            else:
                translated_vector["<unk>"] += vector[word]
        return translated_vector



####################################################################
###########              CORPORACLEANER                 ############
####################################################################


class CorporaCleaner:
    """
    custom cleaner to process POS tagged .lem file
    """
    def __init__(self, source_path, target_path):
        """
        :param source_path:
        :param target_path:
        """
        self.r = re.compile("[^A-Za-z\-_']")
        self.source = source_path
        self.target = target_path


    def removeaccent(self, word_list):
        """
        remove accent for each element in a list

        :param word_list: list to process
        :return: list without accents
        """
        result = []
        for elem in word_list:
            result.append(self._removeacc(elem))
        return result


    def tolist(self, file_path, lemmaindex):
        """
        build the word list for a given file:
        remove accent, element with punctuation

        :param file_path: file to read
        :param lemmaindex: location of the lemma in a POS tagged token
        :return: list of word
        """
        resource_path = "resources/" + file_path.split("/")[-1].split(".")[0] + ".lst"

        if not os.path.isfile(resource_path):
            print "Building word list  [" + file_path.split("/")[-1] + "] ..."
            fi = codecs.open(file_path, "r", "utf-8")
            word_lst = fi.read().split(" ")
            fi.close()

            resource_file = codecs.open(resource_path, "w", "utf-8")

            result = []
            for w in word_lst:
                w = w.split("/")[lemmaindex].split(":")[0].lower()
                if self._isvalidword(self._removeacc(w)):
                    result.append(w)
                    resource_file.write(w + "\n")

            resource_file.close()
            print "size: ", len(result),  #
            print color.GREEN + "[DONE]" + color.END
        else:
            result = loaddata(resource_path)

        return result


    @staticmethod
    def _removeacc(s):
        """
        remove accent in s

        :param s: string to process
        :return: string without accents
        """
        s = s.replace(u"é", u"e")
        s = s.replace(u"è", u"e")
        s = s.replace(u"ê", u"e")
        s = s.replace(u"ë", u"e")

        s = s.replace(u"ï", u"i")
        s = s.replace(u"î", u"i")

        s = s.replace(u"à", u"a")
        s = s.replace(u"â", u"a")

        s = s.replace(u"ô", u"o")

        s = s.replace(u"ç", u"c")

        s = s.replace(u"û", u"u")

        s = s.replace(u"œ", u"oe")

        return s


    def _isvalidword(self, s):
        """
        check if s is a valid word: doesn't contain num or punct

        str s: string to check
        """
        return len(self.r.findall(s)) == 0 and len(s) != 0 and not "__" in s



####################################################################
###########               FUNCTIONS                     ############
####################################################################

def loaddata(file_path):
    """
    :param file_path: file to load
    :return: list containing each line as element
    """
    data = []
    print "Loading data file [" + file_path + "] ...",  #
    for e in codecs.open(file_path, "r", "utf-8").readlines():
        data.append(e.replace("\n", ""))
    print color.GREEN + "[DONE]" + color.END

    return data


def buildcontextvectors(word_list, window, stopwords):
    vectors = {}

    window_lst = ["<unk>" for i in range(0, window)]
    center = int(math.floor(window / 2))
    for w in word_list + ["<unk>" for i in range(0, center)]:
        window_lst = window_lst[1:] + [w]
        if window_lst[center] == "<unk>" and window_lst[center] in stopwords:
            continue
        if window_lst[center] not in vectors:
            vectors[window_lst[center]] = {}
        for elem in (window_lst[:center] + window_lst[center + 1:]):
            if not elem == "<unk>" and elem not in stopwords:
                if elem in vectors[window_lst[center]]:
                    vectors[window_lst[center]][elem] += 1
                else:
                    vectors[window_lst[center]][elem] = 1

    return vectors


def removehapax(word_lst, language):
    word_dict = {}
    word_list = []

    print "Removing hapax [" + language + "] ... ",  #

    for e in word_lst:
        if not e in word_dict:
            word_dict[e] = 1
        else:
            word_dict[e] += 1

    print len(word_dict),  #

    for key in word_dict.keys():
        if word_dict[key] > 1:
            word_list.append(key)

    print color.GREEN + "[DONE]" + color.END

    return word_list


def getcognatelist(fr, en):
    print "\nProcessing Cognates"
    cognates_list = []
    exception_lst = []

    if not os.path.isfile("resources/exceptions.lst"):
        print color.YELLOW + "[WARNING]" + color.END + " resources/exceptions.lst: file not found !"
        print "ignoring exceptions ..."
    else:
        exception_lst = loaddata("resources/exceptions.lst")

    for elem_fr in fr:
        for elem_en in en:
            if elem_fr[:5] == elem_en[:5]:
                if elem_fr[:5] in exception_lst:
                    if elem_fr[:7] == elem_en[:7]:
                        cognates_list.append((elem_fr, elem_en))
                else:
                    cognates_list.append((elem_fr, elem_en))
    print "size: ", len(cognates_list),  #
    print color.GREEN + "[DONE]" + color.END

    return cognates_list


def cosine(v1, v2):
    if len(v2.keys()) == 0 or len(v1.keys() == 0):
        return 0.0

    v1v2 = 0
    v1v1 = 0
    v2v2 = 0
    for attr in set(v1.keys() + v2.keys()):
        if attr in v1:
            attr1 = v1[attr]
        else:
            attr1 = 0

        if attr in v2:
            attr2 = v2[attr]
        else:
            attr2 = 0

        v1v2 += (attr1 * attr2)
        v1v1 += (attr1 * attr1)
        v2v2 += (attr2 * attr2)
    return v1v2 / (math.sqrt(v1v1) * math.sqrt(v2v2))





####################################################################
###########                  MAIN                       ############
####################################################################


if __name__ == "__main__":
    if len(sys.argv) > 2:
        for arg in [1, 2]:
            if not os.path.isfile(sys.argv[arg]):
                raise SystemExit, "[ERROR] " + sys.argv[arg] + ": file not found !"
    else:
        raise SystemExit, "[ERROR] " + sys.argv[0] + " expected at least 2 arguments !"

    # CLeaning en & fr data
    cc = CorporaCleaner(sys.argv[1], sys.argv[2])

    fr_list_with_accent = cc.tolist(cc.source, -1)
    fr_list_without_accent = cc.removeaccent(fr_list_with_accent)

    en_list = cc.tolist(cc.target, -2)


    #TODO integrer les cognats
    # Searching cognates
    #fr_list_without_hapax = removehapax(fr_list_without_accent, "french")
    #en_list_without_hapax = removehapax(en_list, "english")

    #getcognatelist(fr_list_without_hapax, en_list_without_hapax)



    en_stopwords = loaddata("resources/english_stopwords.lst")
    fr_stopwords = loaddata("resources/french_stopwords.lst")

    # Building context vectors
    le = LexiconExtractor(fr_list_with_accent, en_list, "resources/dicfrenelda-utf8.txt")
    fr_vectors = buildcontextvectors(fr_list_with_accent, 7, fr_stopwords)
    en_vectors = buildcontextvectors(en_list, 7, en_stopwords)



    tree = ET.parse("ts.xml")
    root = tree.getroot()

    res_trad = []
    nb_ok = 0


    #FIXME plusieurs trad possibles en resultat dans ts.xml !!!!
    for trad in root:
        src_word = trad[0][2].text
        print src_word
        if src_word in fr_vectors:
            cv = le.translate(fr_vectors[src_word], en_stopwords)
            result = {}
            for v2 in en_vectors:
                c = cosine(cv, en_vectors[v2])
                result[v2] = c
            l = result.items()
            l.sort(key=itemgetter(1), reverse=True)

            if trad[1][2].text in [e[0] for e in l[:10]]:
                res_trad.append((src_word, True))
                nb_ok += 1
            else:
                res_trad.append((src_word, False))
            print l[:10]

    print nb_ok

