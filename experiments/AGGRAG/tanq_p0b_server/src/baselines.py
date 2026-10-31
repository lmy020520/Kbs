"""Traditional local-only baselines. No imports or reads of evaluation data."""
import json,re,sqlite3,unicodedata,hashlib,time,os
from pathlib import Path

def norm(x):return ' '.join(unicodedata.normalize('NFKC',str(x)).casefold().split())
def dump(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
def table(obj):
 if not isinstance(obj,dict) or set(obj)-{'columns','rows'}:raise ValueError('Expected columns/rows only')
 cols=obj['columns'];rows=obj['rows']
 if not isinstance(cols,list) or len(cols)<2 or not all(isinstance(c,str) and c.strip() for c in cols):raise ValueError('Need entity-first and attribute columns')
 if len({norm(c) for c in cols})!=len(cols):raise ValueError('Duplicate columns')
 if not isinstance(rows,list) or any(not isinstance(r,list) or len(r)!=len(cols) for r in rows):raise ValueError('Ragged rows')
 for r in [cols]+rows:
  if any(not isinstance(v,str) or any(c in v for c in '|\r\n') for v in r):raise ValueError('Cells must be strings without pipes/newlines')
 return '\n'.join(' | '.join(r) for r in [cols]+rows)

def validate_pack(p):
 if set(p)!={'sample_id','question','evidence_units'}:raise ValueError('Unexpected predictor fields')
 ids=[e['evidence_id'] for e in p['evidence_units']]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate source ID')
 forbidden={'answer_table','answer_list','filter_pass','extension_entity','init_answer_wikidata_id','extension_wikidata_id','eval_result'}
 def walk(x):
  if isinstance(x,dict):
   if set(x)&forbidden:raise ValueError('Reference metadata leaked')
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(p)

def source_strings(x):
 if isinstance(x,str):yield x
 elif isinstance(x,list):
  for v in x:yield from source_strings(v)
 elif isinstance(x,dict):
  for k,v in x.items():
   if k not in ('found_in_url','proof_type'):yield from source_strings(v)

def verified_facts(facts,unit):
 valid=[];rejected=[];strings=list(source_strings(unit['source']))
 for f in facts:
  if not isinstance(f,dict) or set(f)!={'subject','predicate','object','quote'} or not all(isinstance(v,str) and v.strip() for v in f.values()):rejected.append({'fact':f,'reason':'FORMAT_ERROR'});continue
  if not any(f['quote'] in s for s in strings):rejected.append({'fact':f,'reason':'QUOTE_NOT_LITERAL_IN_SOURCE'});continue
  valid.append({**f,'evidence_id':unit['evidence_id']})
 return valid,rejected

def database(facts):
 c=sqlite3.connect(':memory:');c.execute('CREATE TABLE facts(subject TEXT, predicate TEXT, object TEXT, subject_key TEXT, predicate_key TEXT, object_key TEXT, evidence_id TEXT, numeric_value REAL)')
 for f in facts:
  try:n=float(f['object'])
  except ValueError:n=None
  c.execute('INSERT INTO facts VALUES(?,?,?,?,?,?,?,?)',(f['subject'],f['predicate'],f['object'],norm(f['subject']),norm(f['predicate']),norm(f['object']),f['evidence_id'],n))
 c.commit();return c

def readonly_join(facts,sql):
 if not re.match(r'^\s*(SELECT|WITH)\b',sql,re.I):raise ValueError('Read-only SELECT required')
 c=database(facts)
 # No functions, table reads or statements beyond the in-memory fact relation.
 allow_funcs={'min','max','count','group_concat','lower','upper','coalesce','cast','substr','length','abs','round','sum','avg','like','replace'}
 def authorize(action,a,b,db,origin):
  if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
  if action==sqlite3.SQLITE_READ:return sqlite3.SQLITE_OK if a=='facts' else sqlite3.SQLITE_DENY
  if action==sqlite3.SQLITE_FUNCTION:return sqlite3.SQLITE_OK if (b or a or '').lower() in allow_funcs else sqlite3.SQLITE_DENY
  return sqlite3.SQLITE_DENY
 c.set_authorizer(authorize);ticks=[0]
 def progress():ticks[0]+=1;return ticks[0]>1000
 c.set_progress_handler(progress,1000)
 try:
  cursor=c.execute(sql);rows=cursor.fetchmany(10001)
  if len(rows)>10000:raise ValueError('Output bound exceeded')
  result={'columns':[d[0] for d in cursor.description],'rows':[['' if v is None else str(v) for v in r] for r in rows]};table(result);return result
 finally:c.close()

SCHEMA='Return one JSON object {"columns":["entity", "attribute", ...], "rows":[["entity name","value",...],...]}. All cells strings, no pipes or line breaks. Entity must be first column. Include only answers supported by supplied evidence, preserving conditions; do not invent missing facts. No Markdown fences.'
DIRECT='Using the question and ALL supplied source evidence (including distractors), generate the requested answer table. '+SCHEMA
PLAN='Translate only the question into {"predicates":["canonical predicate",...],"sql":"SELECT ..."}. This is a generic query plan, not an answer. Relation facts(subject,predicate,object,subject_key,predicate_key,object_key,evidence_id,numeric_value). Keys are NFKC-casefold-whitespace-normalized. Use subject_key for entity joins; object_key for filters. Preserve all query conditions. Request necessary predicates in predicates. Use a read-only SQLite SELECT with entity first and requested attributes as remaining columns. Use DISTINCT/grouping where appropriate; no extra relations. Never embed an answer entity list.'
EXTRACT='Extract ALL relevant subject-predicate-object candidates from this single evidence unit using the supplied query predicates, including possible non-answer entities. Return {"facts":[{"subject":"name","predicate":"canonical predicate","object":"value","quote":"verbatim contiguous source substring"}]}. Preserve uncertainty and conditional qualifications in values; never invent cross-source links. Empty list allowed. Quote is a literal locator, not proof of semantic correctness.'

class LocalGenerator:
 def __init__(self,path,max_context,max_new):
  if not path:raise RuntimeError('BLOCKED_MODEL_BUDGET: no authorized local generator configured')
  p=Path(path).resolve()
  if not p.is_dir():raise RuntimeError('Local model directory does not exist; no downloads allowed')
  os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['CUDA_VISIBLE_DEVICES']=''
  import torch
  from transformers import AutoModelForCausalLM,AutoTokenizer
  self.tok=AutoTokenizer.from_pretrained(p,local_files_only=True,trust_remote_code=False)
  self.model=AutoModelForCausalLM.from_pretrained(p,local_files_only=True,trust_remote_code=False).eval()
  self.max_context=max_context;self.max_new=max_new;self.torch=torch
 def __call__(self,prompt):
  text=self.tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True)
  tokens=self.tok(text,return_tensors='pt');n=tokens['input_ids'].shape[1]
  if n+self.max_new>self.max_context:raise RuntimeError('CONTEXT_TOO_LONG: no silent evidence truncation')
  t=time.perf_counter()
  with self.torch.inference_mode():out=self.model.generate(**tokens,max_new_tokens=self.max_new,do_sample=False,pad_token_id=self.tok.eos_token_id)
  return self.tok.decode(out[0,n:],skip_special_tokens=True),{'input_tokens':n,'output_tokens':int(out.shape[1]-n),'seconds':time.perf_counter()-t,'decode':'greedy','temperature':'not applicable: do_sample=False'}

def predict(pack,arm,call):
 validate_pack(pack)
 if arm=='B0':return json.loads(call('direct',DIRECT+'\n'+dump({'question':pack['question'],'evidence_units':pack['evidence_units']})))
 if arm!='B1':raise ValueError('Only B0/B1 authorized')
 plan=json.loads(call('plan',PLAN+'\nQuestion: '+pack['question']))
 if set(plan)!={'predicates','sql'} or not isinstance(plan['predicates'],list) or not all(isinstance(x,str) for x in plan['predicates']):raise ValueError('Invalid query plan')
 facts=[];rejects=[]
 for unit in pack['evidence_units']:
  obj=json.loads(call('extract:'+unit['evidence_id'],EXTRACT+'\n'+dump({'question':pack['question'],'predicates':plan['predicates'],'evidence':unit})))
  if set(obj)!={'facts'} or not isinstance(obj['facts'],list):raise ValueError('Invalid extraction')
  v,r=verified_facts(obj['facts'],unit);facts.extend(v);rejects.extend(r)
 result=readonly_join(facts,plan['sql'])
 return result,{'plan':plan,'facts':facts,'quote_or_format_rejections':rejects,'semantic_support':'UNVERIFIED'}
