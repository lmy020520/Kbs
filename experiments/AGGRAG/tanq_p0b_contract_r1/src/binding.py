"""Literal source binding, never entailment or automatic rebinding."""
from urllib.parse import urlsplit,unquote
import unicodedata

def locations(unit,quote):
    if not isinstance(quote,str) or not quote:return []
    out=[]
    def walk(x,path):
        if isinstance(x,str):
            start=0
            while True:
                i=x.find(quote,start)
                if i<0:break
                out.append({'json_pointer':path,'start_char':i,'end_char':i+len(quote)});start=i+1
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,path+'/'+str(i))
        elif isinstance(x,dict):
            for k,v in x.items():
                if k not in ('found_in_url','proof_type'):walk(v,path+'/'+k.replace('~','~0').replace('/','~1'))
    walk(unit.get('source',{}),'/source');return out

def page(unit):
    u=unit.get('source',{}).get('found_in_url')
    if not isinstance(u,str) or not u:return None
    try:p=urlsplit(u)
    except ValueError:return None
    path=unicodedata.normalize('NFKC',unquote(p.path))
    if p.hostname and p.hostname.endswith('wikipedia.org'):path=path.replace('_',' ')
    return (p.hostname,path,p.query) # HTTP/HTTPS are the same page, queries/revisions are preserved.

def bind_quote(evidence_id,quote,units):
    byid={u['evidence_id']:u for u in units}
    if not isinstance(quote,str) or not quote.strip():return {'status':'MISSING_QUOTE','strict_accepted':False,'matches':[]}
    if not isinstance(evidence_id,str) or evidence_id not in byid:return {'status':'INVALID_EVIDENCE_ID','strict_accepted':False,'matches':[]}
    matches=[{'evidence_id':k,'locations':loc} for k,u in byid.items() if (loc:=locations(u,quote))]
    declared=next((m for m in matches if m['evidence_id']==evidence_id),None)
    if declared:return {'status':'EXACT_SOURCE_MATCH','strict_accepted':True,'matches':matches,'declared_locations':declared['locations'],'multiple_spans':len(declared['locations'])>1,'semantic_support':'UNVERIFIED'}
    if not matches:status='QUOTE_NOT_FOUND'
    elif len(matches)>1:status='AMBIGUOUS_SOURCE'
    elif page(byid[evidence_id]) is None or page(byid[matches[0]['evidence_id']]) is None:status='AMBIGUOUS_SOURCE'
    elif page(byid[evidence_id])==page(byid[matches[0]['evidence_id']]):status='SAME_PAGE_OTHER_CHUNK'
    else:status='DIFFERENT_PAGE_MATCH'
    return {'status':status,'strict_accepted':False,'matches':matches,'automatically_rebound':False,'semantic_support':'UNVERIFIED'}
