# -*- coding: utf-8 -*-
# Author: XuMing <xuming624@qq.com>
# Brief: read train and test data
import os

import numpy as np

from utils.data_utils import build_dict
from utils.data_utils import map_item2id
from utils.data_utils import read_lines
from utils.io_utils import dump_pkl
from utils.io_utils import load_pkl


def _load_data(path, col_sep='\t', word_sep=' ', pos_sep='/'):
    lines = read_lines(path)
    word_lst = []
    pos_lst = []
    label_lst = []
    for line in lines:
        if col_sep not in line:
            continue
        index = line.index(col_sep)
        label = line[:index]
        if pos_sep in label:
            label = label.split(pos_sep)[0]
        label_lst.extend(label)
        sentence = line[index + 1:]
        # word and pos
        word_pos_list = sentence.split(word_sep)
        word, pos = [], []
        for item in word_pos_list:
            if pos_sep in item:
                r_index = item.rindex(pos_sep)
                w, p = item[:r_index], item[r_index + 1:]
                if w == '' or p == '':
                    continue
                word.append(w)
                pos.append(p)
        word_lst.extend(word)
        pos_lst.extend(pos)
    return word_lst, pos_lst, label_lst


def build_vocab(train_path, word_vocab_path, pos_vocab_path, label_vocab_path,
                col_sep='\t', min_count=5, word_vocab_start=2, pos_vocab_start=1):
    word_lst, pos_lst, label_lst = _load_data(train_path, col_sep=col_sep)
    # word vocab
    word_vocab = build_dict(word_lst, start=word_vocab_start,
                            min_count=min_count, sort=True, lower=True)
    # save
    dump_pkl(word_vocab, word_vocab_path, overwrite=True)
    # pos vocab
    pos_vocab = build_dict(pos_lst, start=pos_vocab_start, sort=True, lower=False)
    # save
    dump_pkl(pos_vocab, pos_vocab_path, overwrite=True)
    # label vocab
    label_types = [str(i) for i in label_lst]
    label_vocab = build_dict(label_types)
    # save
    dump_pkl(label_vocab, label_vocab_path, overwrite=True)


def load_vocab(word_vocab_path, pos_vocab_path, label_vocab_path):
    """
    load vocab dict
    :param word_vocab_path:
    :param pos_vocab_path:
    :param label_vocab_path:
    :return:
    """
    return load_pkl(word_vocab_path), load_pkl(pos_vocab_path), load_pkl(label_vocab_path)


def build_word_embedding(path, overwrite=False, sentence_w2v_path=None,
                         word_vocab_path=None, word_vocab_start=2, w2v_dim=256):
    if os.path.exists(path) and not overwrite:
        print("already has $s and use it." % path)
        return
    w2v_dict_full = load_pkl(sentence_w2v_path)
    word_vocab = load_pkl(word_vocab_path)
    word_vocab_count = len(w2v_dict_full) + word_vocab_start
    word_emb = np.zeros((word_vocab_count, w2v_dim), dtype='float32')
    for word in word_vocab:
        index = word_vocab[word]
        if word in w2v_dict_full:
            word_emb[index, :] = w2v_dict_full[word]
        else:
            random_vec = np.random.uniform(-0.25, 0.25, size=(w2v_dim,)).astype('float32')
            word_emb[index, :] = random_vec
    # save
    dump_pkl(word_emb, path)


def build_pos_embedding(path, overwrite=False,
                        pos_vocab_path=None, pos_vocab_start=1, pos_dim=64):
    if os.path.exists(path) and not overwrite:
        return
    pos_vocab = load_pkl(pos_vocab_path)
    pos_vocab_count = len(pos_vocab) + pos_vocab_start
    pos_emb = np.random.normal(size=(pos_vocab_count, pos_dim,)).astype('float32')
    for i in range(pos_vocab_start):
        pos_emb[i, :] = 0.
    # save
    dump_pkl(pos_emb, path)


def load_emb(w2v_path, p2v_path):
    """
    加载词向量、词性向量
    :param w2v_path:
    :param p2v_path:
    :return:
    """
    return load_pkl(w2v_path), load_pkl(p2v_path)


def _get_word_arr(word_pos_vocab, word_vocab, pos_vocab,
                  pos_sep='/',max_len=300):
    """
    获取词序列
    :param word_pos_vocab: list，句子和词性
    :param word_vocab: 词表
    :param pos_vocab: 词性表
    :param pos_sep: 词性表
    :return: word_arr, np.array, 字符id序列
             pos_arr, np.array, 词性标记序列
    """
    word_literal, pos_literal = [], []
    for item in word_pos_vocab:
        if pos_sep in item:
            r_index = item.rindex(pos_sep)
            w, p = item[:r_index], item[r_index + 1:]
            if w == '' or p == '':
                continue
            word_literal.append(w)
            pos_literal.append(p)
    # word list
    word_arr = map_item2id(word_literal, word_vocab, max_len, lower=True)
    # pos list
    pos_arr = map_item2id(pos_literal, pos_vocab, max_len, lower=False)
    return word_arr, pos_arr, len(word_literal)


def _init_data(lines, word_vocab, pos_vocab, label_vocab,
               col_sep='\t', word_sep=' ', pos_sep='/', max_len=300):
    """
    load data
    :param lines:
    :param word_vocab:
    :param pos_vocab:
    :param lable_vocab:
    :param word_sep:
    :param pos_sep:
    :return:
    """
    data_count = len(lines)
    # init
    words = np.zeros((data_count, max_len), dtype='int32')
    pos = np.zeros((data_count, max_len), dtype='int32')
    sentence_actual_lengths = np.zeros((data_count), dtype='int32')
    labels = np.zeros((data_count), dtype='int32')
    instance_index = 0
    # set data
    for i in range(data_count):
        index = lines[i].index(col_sep)
        label = lines[i][:index]
        if pos_sep in label:
            label = label.split(pos_sep)[0]
        sentence = lines[i][index + 1:]
        word_pos_vocab = sentence.split(word_sep)
        word_arr, pos_arr, actual_len = _get_word_arr(word_pos_vocab, word_vocab, pos_vocab)

        words[instance_index, :] = word_arr
        pos[instance_index, :] = pos_arr
        sentence_actual_lengths[instance_index] = actual_len
        labels[instance_index] = label_vocab[label] if label in label_vocab else 0
        instance_index += 1
    return words, pos, labels


def train_reader(path, word_vocab, pos_vocab, label_vocab, col_sep='\t'):
    """
    load train data
    :param word_vocab:
    :param pos_vocab:
    :param label_vocab:
    :return:
    """
    return _init_data(read_lines(path),
                      word_vocab, pos_vocab, label_vocab, col_sep=col_sep)


def test_reader(path, word_vocab, pos_vocab, label_vocab, col_sep='\t'):
    """
    load test data
    :param word_vocab:
    :param pos_vocab:
    :param label_vocab:
    :return:
    """
    sentences, pos, _ = _init_data(read_lines(path),
                                   word_vocab, pos_vocab, label_vocab, col_sep=col_sep)
    return sentences, pos


def data_reader(path, col_sep=','):
    contents, labels = [], []
    word_col = 1
    lbl_col = 0
    with open(path, mode='r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            line_split = line.split(col_sep, 1)
            if line_split and len(line_split) > 1:
                # train data
                data = line_split[word_col].strip()
                content = _get_content_words(data)
                label = line_split[lbl_col].strip()
                contents.append(content)
                labels.append(label)
    return contents, labels


def _get_content_words(text, word_sep=' ', pos_sep='/'):
    content = ''
    for word in text.split(word_sep):
        if pos_sep in word:
            content += word.split(pos_sep)[0]
    return content
