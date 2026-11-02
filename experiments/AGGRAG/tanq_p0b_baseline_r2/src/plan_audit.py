"""Generic lexical traceability guard, NOT an independent semantic parser or Gold oracle."""
import re
from contracts import validate_plan,norm
from schemas import plan_schema,validate_schema
SYNTAX={'who','what','which','was','were','is','are','a','an','the','and','or','with','of','for','to','their','its','that','have','has','had','please','list','show','table','answer','filter','by','in','on','does','do','did','me','give','all','these','those'}
def pointer(root,path):
    if not path.startswith('/'):raise ValueError('ABSOLUTE_POINTER_REQUIRED')
    for key in path[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~')
        root=root[int(key)] if isinstance(root,list) else root[key]
    return root

def leaves(node,path='/filter'):
    if 'conditions' in node:
        return [x for i,c in enumerate(node['conditions']) for x in leaves(c,path+'/conditions/'+str(i))]
    return [(path,node)]

def audit_plan(question,envelope):
    errors=validate_schema(envelope,plan_schema())
    if errors:return {'status':'PLAN_INVALID','errors':errors,'execution_allowed':False}
    query=envelope['query'];base=validate_plan(query)
    if base['status']!='PLAN_VALID_STRUCTURAL':return {**base,'execution_allowed':False}
    issues=[];covered=set();targets=set();condition_text=[]
    for i,u in enumerate(envelope['question_units']):
        start,end=u['start'],u['end'];path=u['target'];kind=u['kind']
        if isinstance(start,bool) or isinstance(end,bool) or not 0<=start<end<=len(question) or question[start:end]!=u['text']:
            issues.append({'unit':i,'reason':'QUESTION_SPAN_INVALID'});continue
        if any(j in covered for j in range(start,end)):issues.append({'unit':i,'reason':'QUESTION_SPAN_OVERLAP'})
        covered.update(range(start,end))
        if kind=='syntax':
            words=re.findall(r'\w+',u['text'].casefold())
            if path or any(w not in SYNTAX for w in words):issues.append({'unit':i,'reason':'CONTENT_HIDDEN_AS_SYNTAX'})
            continue
        try:target=pointer(query,path)
        except (KeyError,IndexError,ValueError,TypeError):issues.append({'unit':i,'reason':'INVALID_PLAN_POINTER'});continue
        targets.add((kind,path))
        if kind=='entity_scope':
            words=[w for w in re.findall(r'\w+',u['text'].casefold()) if w not in SYNTAX]
            label=re.sub(r'[^a-z0-9]','',query['entity_type'].casefold())
            if any(w.rstrip('s') not in label for w in words):issues.append({'unit':i,'reason':'CONTENT_HIDDEN_IN_SUBJECT_TYPE'})
        if kind=='logic' and any(w not in {'and','or'} for w in re.findall(r'\w+',u['text'].casefold())):issues.append({'unit':i,'reason':'CONTENT_HIDDEN_AS_LOGIC'})
        if kind=='entity_scope' and path!='/entity_type':issues.append({'unit':i,'reason':'SUBJECT_ROLE_TARGET_INVALID'})
        if kind=='output' and not re.fullmatch(r'/outputs/\d+',path):issues.append({'unit':i,'reason':'OUTPUT_TARGET_INVALID'})
        if kind=='condition':
            condition_text.append(u['text'])
            if not isinstance(target,dict) or set(target)!={'predicate','operator','value'}:issues.append({'unit':i,'reason':'CONDITION_MUST_POINT_TO_LEAF'})
        if kind=='logic':
            if not isinstance(target,dict) or target.get('op') not in ('and','or'):issues.append({'unit':i,'reason':'LOGIC_TARGET_INVALID'})
            else:
                words=set(re.findall(r'\w+',u['text'].casefold()))
                if words&{'and','or'} and target['op'] not in words:issues.append({'unit':i,'reason':'EXPLICIT_LOGIC_MISMATCH'})
    uncovered=[i for i,c in enumerate(question) if not c.isspace() and i not in covered]
    if uncovered:issues.append({'reason':'QUESTION_CONTENT_NOT_ACCOUNTED','positions':uncovered})
    if ('entity_scope','/entity_type') not in targets:issues.append({'reason':'SUBJECT_SCOPE_UNANCHORED'})
    for i,_ in enumerate(query['outputs']):
        if ('output','/outputs/'+str(i)) not in targets:issues.append({'reason':'OUTPUT_UNANCHORED','index':i})
    for path,_ in leaves(query['filter']):
        if ('condition',path) not in targets:issues.append({'reason':'FILTER_LEAF_UNANCHORED','path':path})
    # An explicit literal filter value must be traceable to its linked question text.
    for path,leaf in leaves(query['filter']):
        spans=[u['text'] for u in envelope['question_units'] if u['kind']=='condition' and u['target']==path]
        value=str(leaf['value'])
        if not any(norm(value) in norm(s) for s in spans):issues.append({'reason':'FILTER_VALUE_NOT_IN_LINKED_QUESTION_SPAN','path':path})
    expected={norm(p['name']) for p in query['predicates']}
    relations=[norm(r['predicate']) for r in envelope['relations']]
    if set(relations)!=expected or len(relations)!=len(expected):issues.append({'reason':'RELATION_ROLE_CATALOG_INCOMPLETE'})
    if envelope['unresolved']:issues.append({'reason':'MODEL_DECLARED_UNRESOLVED','items':envelope['unresolved']})
    # A model-written trace cannot prove arbitrary natural-language equivalence. Never promote to VERIFIED.
    return {'status':'PLAN_UNVERIFIED','structural_status':'PLAN_VALID_STRUCTURAL','lexical_trace_status':'FAILED' if issues else 'PASS','execution_allowed':not issues,'errors':issues,'semantic_completeness':'UNVERIFIED','scope':'Trace-pass permits exploratory execution only; not semantic plan accuracy','query':query}
