# -*- coding: utf-8 -*-
"""Context retrieval (ViMedQA).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1tQCF1SNXyrks5ybk7gCFXOCMouvf6q9s
"""

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
from deep_translator import GoogleTranslator
translator = GoogleTranslator(source='vi', target='en')
import re
import pandas as pd
import string
from tqdm import tqdm

def text_preprocessing(text):
  text = re.sub(r'[\d].', ' ', text)
  text = re.sub(' +', ' ', text)
  return text

def test_set_preprocessing(file_path):
  test_data = pd.read_csv(file_path)
  ques_token = []
  #ques_opt_token = []
  for idx, row in test_data.iterrows():
    ques = ''.join([e for e in row['question'] if e not in string.punctuation]).lower()
    #opts = ' '.join([re.sub(r"[A-E]\.", "", val).strip().lower() for val in test_data.iloc[idx, 2:].values if type(val) == str])
    ques_token.append(ques.split())
    #ques_opt_token.append((ques+' '+opts).split())
  test_data['ques_token'] = ques_token
  #test_data['ques_opt_token'] = ques_opt_token
  return test_data

def corpus_preprocessing(file_path):
  corpus_df = pd.read_csv(file_path)
  #corpus_df['topic'] = corpus_df['topic'].apply(text_preprocessing)
  #corpus_df['context'] = corpus_df['context'].apply(text_preprocessing)

  remove_idx = []
  for idx, row in enumerate(corpus_df['context']):
    if len(row.split()) < 5:
      remove_idx.append(idx)
  corpus_df = corpus_df.drop(index=remove_idx)

  #topic_token = []
  context_token = []
  for idx, row in corpus_df.iterrows():
    #topic = ''.join([e for e in row['topic'] if e not in string.punctuation]).lower()
    #topic_token.append(topic.split())
    context = ''.join([e for e in row['context'] if e not in string.punctuation]).lower()
    context_token.append(context.split())
  #corpus_df['topic_token'] = topic_token
  corpus_df['context_token'] = context_token
  return corpus_df

def bm25_searcher(test, corpus, top_k=1):
  words = corpus['context_token'].tolist()
  bm25 = BM25Okapi(words)
  indexs = list(range(len(words)))
  contexts = []
  for question_index in range(len(test)):
    top_docs = []
    tokenized_query = test.iloc[question_index]['ques_token']
    ##### BM25 search (lexical search) #####
    top_indexs = bm25.get_top_n(tokenized_query, indexs, n=top_k)
    hits = [{'corpus_id' : index} for index in top_indexs]
    query = test.iloc[question_index]['question']
    ##### Re-Ranking #####
    cross_inp = [[query, corpus['topic'].iloc[hit['corpus_id']] + '. ' + corpus['context'].iloc[hit['corpus_id']]] for hit in hits]
    cross_scores = cross_encoder.predict(cross_inp)
    for idx in range(len(cross_scores)):
      hits[idx]['cross-score'] = cross_scores[idx]
    hits = sorted(hits, key=lambda x: x['cross-score'], reverse=True)
    for hit in hits[0:3]: #only top 3
      top_docs.append(corpus['context'].iloc[hit['corpus_id']].replace("\n", " "))
    contexts.append('. '.join(top_docs))
  test['context'] = contexts
  return test

def translate_text(text):
    if isinstance(text, str):
      try:
        translated_text = translator.translate(text)
        return translated_text
      except:
        chunks = [text[x:x+250] for x in range(0, len(text), 250) if len(text[x:x+250]) > 1]
        translated_text = ' '.join(translator.translate_batch(chunks))
        return translated_text
    else:
        return ''

def translate_df(df):
  en_test_data = []
  for idx, row in tqdm(df.iterrows()):
      id = row['id']
      question = translate_text(row['question'])
      option_1 = translate_text(row['option_1'])
      option_2 = translate_text(row['option_2'])
      option_3 = translate_text(row['option_3'])
      option_4 = translate_text(row['option_4'])
      option_5 = translate_text(row['option_5'])
      option_6 = translate_text(row['option_6'])
      context = translate_text(row['context'])
      data = {'id': id,
              'question': question,
              'option_1': option_1,
              'option_2': option_2,
              'option_3': option_3,
              'option_4': option_4,
              'option_5': option_5,
              'option_6': option_6,
              'context': context,
              }
      en_test_data.append(data)
  return pd.DataFrame(en_test_data)