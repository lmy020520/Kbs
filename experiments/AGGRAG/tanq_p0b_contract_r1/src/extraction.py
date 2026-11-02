"""Every rejected candidate is retained; invalid envelopes are never unwrapped."""
from contracts import norm,text,number,validate_plan
from binding import bind_quote
REQUIRED={'subject','entity_type','predicate','value','evidence_id','quote'}
def validate_extraction(obj,plan,units):
    if validate_plan(plan)['status']!='PLAN_VALID_STRUCTURAL':return {'status':'PLAN_INVALID','raw':obj,'accepted':[],'checks':[]}
    if not isinstance(obj,dict):return {'status':'EXTRACTION_INVALID','reason':'FACTS_ROOT_MUST_BE_OBJECT','raw':obj,'accepted':[],'checks':[]}
    if set(obj)!={'facts'} or not isinstance(obj['facts'],list):return {'status':'EXTRACTION_INVALID','reason':'FACTS_ENVELOPE_INVALID','raw':obj,'accepted':[],'checks':[]}
    catalog={norm(p['name']):p for p in plan['predicates']};accepted=[];checks=[]
    for i,f in enumerate(obj['facts']):
        errors=[];binding=bind_quote(f.get('evidence_id'),f.get('quote'),units) if isinstance(f,dict) else None
        if not isinstance(f,dict) or set(f)!=REQUIRED:
            errors.append('FACT_FIELDS_INVALID')
            if isinstance(f,dict) and not f.get('quote'):errors.append('MISSING_QUOTE')
        else:
            if not all(text(f[k]) for k in ('subject','entity_type','predicate','evidence_id')):errors.append('FACT_STRING_FIELDS_INVALID')
            if not isinstance(f['quote'],str) or not f['quote'].strip():errors.append('MISSING_QUOTE')
            p=catalog.get(norm(f['predicate'])) if isinstance(f['predicate'],str) else None
            if p is None:errors.append('UNDECLARED_PREDICATE')
            if isinstance(f['entity_type'],str) and norm(f['entity_type'])!=norm(plan['entity_type']):errors.append('WRONG_SUBJECT_ROLE')
            if p is not None and ((p['kind']=='number' and not number(f['value'])) or (p['kind']=='text' and not text(f['value']))):errors.append('VALUE_TYPE_INVALID_NO_COERCION')
            binding=bind_quote(f['evidence_id'],f['quote'],units)
            if not binding['strict_accepted']:errors.append('SOURCE_BINDING_NOT_EXACT')
        check={'index':i,'raw':f,'status':'FACT_VALID_MECHANICAL' if not errors else 'FACT_REJECTED','errors':errors,'binding':binding,'semantic_support':'UNVERIFIED'}
        checks.append(check)
        if not errors:accepted.append({**f,'raw_index':i})
    rejected=sum(c['status']=='FACT_REJECTED' for c in checks)
    return {'status':'EXTRACTION_PARTIAL' if rejected else 'EXTRACTION_VALID','raw':obj,'accepted':accepted,'checks':checks,'candidate_count':len(checks),'rejected_count':rejected,'semantic_support':'UNVERIFIED'}
