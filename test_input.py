#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'han'

import os
import torch
import logging
import spacy
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from models import *
from dataset import Dataset, DocTextEn, DocTextCh
from utils.load_config import init_logging, read_config
from utils.functions import to_long_tensor, count_parameters, draw_heatmap_sea

init_logging()
logger = logging.getLogger(__name__)


def main():
    logger.info('------------MODEL TEST INPUT--------------')
    logger.info('loading config file...')

    # manual set
    global_config = read_config('config/global_config.yaml')

    # set random seed
    seed = global_config['global']['random_seed']
    torch.manual_seed(seed)

    torch.set_grad_enabled(False)  # make sure all tensors below have require_grad=False

    logger.info('reading dataset...')
    dataset = Dataset(global_config)

    logger.info('constructing model...')
    dataset_h5_path = global_config['data']['dataset_h5']
    model = MatchLSTMPlus(dataset_h5_path)

    model.eval()  # let training = False, make sure right dropout
    logging.info('model parameters count: %d' % count_parameters(model))

    # load model weight
    logger.info('loading model weight...')
    model_weight_path = global_config['data']['model_path']
    is_exist_model_weight = os.path.exists(model_weight_path)
    assert is_exist_model_weight, "not found model weight file on '%s'" % model_weight_path

    weight = torch.load(model_weight_path, map_location=lambda storage, loc: storage)
    model.load_state_dict(weight, strict=False)

    context = "《战国无双3》（）是由光荣和ω-force开发的战国无双系列的正统第三续作。本作以三大故事为主轴，分别是以武田信玄等人为主的《关东三国志》，织田信长等人为主的《战国三杰》，石田三成等人为主的《关原的年轻武者》，丰富游戏内的剧情。此部份专门介绍角色，欲知武器情报、奥义字或擅长攻击类型等，请至战国无双系列1.由于乡里大辅先生因故去世，不得不寻找其他声优接手。从猛将传 and Z开始。2.战国无双 编年史的原创男女主角亦有专属声优。此模式是任天堂游戏谜之村雨城改编的新增模式。本作中共有20张战场地图（不含村雨城），后来发行的猛将传再新增3张战场地图。但游戏内战役数量繁多，部分地图会有兼用的状况，战役虚实则是以光荣发行的2本「战国无双3 人物真书」内容为主，以下是相关介绍。（注：前方加☆者为猛将传新增关卡及地图。）合并本篇和猛将传的内容，村雨城模式剔除，战国史模式可直接游玩。主打两大模式「战史演武」&「争霸演武」。系列作品外传作品"
    question1 = "《战国无双3》是由哪两个公司合作开发的？"
    answer1 = ['光荣和ω-force']

    question2 = '男女主角亦有专属声优这一模式是由谁改编的？'
    answer2 = ['村雨城', '任天堂游戏谜之村雨城']

    question3 = '战国史模式主打哪两个模式？'
    answer3 = ['「战史演武」&「争霸演武」']

    # change here to select questions
    question = question2
    answer = answer2[0]

    # preprocess
    preprocess_config = global_config['preprocess']
    context_doc = DocTextCh(context, preprocess_config)
    question_doc = DocTextCh(question, preprocess_config)

    link_char = ''
    # mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei']
    mpl.rcParams['font.sans-serif'] = ['SimHei']
    
    context_doc.update_em(question_doc)
    question_doc.update_em(context_doc)

    context_token = context_doc.token
    question_token = question_doc.token

    context_id_char = None
    question_id_char = None
    if preprocess_config['use_char']:
        context_id_char = to_long_tensor(dataset.sentence_char2id(context_token))
        question_id_char = to_long_tensor(dataset.sentence_char2id(question_token))

    context_id, context_f = context_doc.to_id(dataset.meta_data)
    question_id, question_f = question_doc.to_id(dataset.meta_data)
    
    bat_input = [context_id, question_id, context_id_char, question_id_char, context_f, question_f]
    bat_input = [x.unsqueeze(0) if x is not None else x for x in bat_input]

    # predict
    out_ans_prop, out_ans_range, vis_param = model.forward(*bat_input)
    out_ans_range = out_ans_range.numpy()
    # ans_range = beam_search(ans_range_prop, k=5)

    start = out_ans_range[0][0]
    end = out_ans_range[0][1] + 1

    out_answer_id = context_id[start:end]
    out_answer = dataset.sentence_id2word(out_answer_id)

    logging.info('Predict Answer: ' + link_char.join(out_answer))

    # to show on visdom
    s = 0
    e = 48

    x_left = vis_param['match']['left']['alpha'][0, :, s:e].numpy()
    x_right = vis_param['match']['right']['alpha'][0, :, s:e].numpy()

    x_left_gated = vis_param['match']['left']['gated'][0, :, s:e].numpy()
    x_right_gated = vis_param['match']['right']['gated'][0, :, s:e].numpy()

    draw_heatmap_sea(x_left,
                     xlabels=context_token[s:e],
                     ylabels=question_token,
                     answer=answer,
                     save_path='data/test-left.png',
                     bottom=0.2)
    draw_heatmap_sea(x_right,
                     xlabels=context_token[s:e],
                     ylabels=question_token,
                     answer=answer,
                     save_path='data/test-right.png',
                     bottom=0.2)
    # plt.show()


if __name__ == '__main__':
    main()