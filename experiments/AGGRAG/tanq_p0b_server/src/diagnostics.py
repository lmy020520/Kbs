"""Project-defined exact normalized string diagnostics, not natural semantic correctness."""
from collections import Counter,defaultdict
from baselines import norm,table

def parse_reference(text):
 lines=[x.strip() for x in text.strip().splitlines() if x.strip()]
 if lines and lines[0].lower().startswith('title |'):lines=lines[1:]
 rows=[[c.strip() for c in x.split('|')] for x in lines]
 if not rows:return {'columns':[],'rows':[]}
 return {'columns':rows[0],'rows':rows[1:]}
def compare(pred,ref):
 table(pred);table(ref)
 pc,rc=Counter(norm(r[0]) for r in pred['rows']),Counter(norm(r[0]) for r in ref['rows'])
 ps,rs=set(pc),set(rc);tp=len(ps&rs);precision=tp/len(ps) if ps else (1.0 if not rs else 0.0);recall=tp/len(rs) if rs else 1.0
 errors=[]
 for k in sorted(rs-ps):errors.append({'type':'MISSING_ENTITY','entity_key':k,'scope':'AUTHOR_REFERENCE_STRING_UNMATCHED'})
 for k in sorted(ps-rs):errors.append({'type':'WRONG_ENTITY','entity_key':k,'scope':'UNMATCHED_REFERENCE_LABEL; natural correctness UNKNOWN'})
 for k,n in pc.items():
  if n>1:errors.append({'type':'DUPLICATED_ENTITY','entity_key':k,'count':n})
 def cells(t):
  out=defaultdict(list)
  for row in t['rows']:
   for h,v in zip(t['columns'][1:],row[1:]):out[(norm(row[0]),norm(h))].append(v)
  return out
 p,r=cells(pred),cells(ref);eligible={k:v[0] for k,v in r.items() if len(v)==1 and rc[k[0]]==1};correct=0;evaluable=0
 for k,v in eligible.items():
  vals=p.get(k,[])
  if len(vals)>1:errors.append({'type':'UNRESOLVED','key':k,'reason':'ambiguous duplicate predicted cell','reference':v,'predictions':vals});continue
  evaluable+=1
  if not vals or not vals[0].strip():errors.append({'type':'MISSING_ATTRIBUTE','key':k,'reference':v,'prediction':vals});continue
  if norm(vals[0])==norm(v):correct+=1;continue
  other=[owner for (owner,h),value in eligible.items() if h==k[1] and owner!=k[0] and norm(value)==norm(vals[0])]
  errors.append({'type':'WRONG_ATTRIBUTE','key':k,'reference':v,'prediction':vals[0],'scope':'STRING_MISMATCH_ONLY'})
  if other:errors.append({'type':'WRONG_ENTITY_ATTRIBUTE_LINK','key':k,'reference':v,'prediction':vals[0],'other_reference_owners':other,'scope':'OTHER_ROW_VALUE_SIGNAL; semantic attribution UNRESOLVED'})
 def canon(t):return sorted((norm(row[0]),tuple(sorted(zip(map(norm,t['columns'][1:]),map(norm,row[1:]))))) for row in t['rows'])
 return {'scope':'PROJECT_CUSTOM_AUTHOR_REFERENCE_FIDELITY_NOT_OFFICIAL_OR_SEMANTIC_GOLD','entity_label_precision':precision,'entity_label_recall':recall,'entity_label_f1':2*precision*recall/(precision+recall) if precision+recall else 0,'exact_table_match':canon(pred)==canon(ref),'duplicate_entity_occurrences':sum(n-1 for n in pc.values()),'eligible_reference_attribute_cells':len(eligible),'evaluable_cells':evaluable,'exact_cell_matches':correct,'cell_accuracy':correct/evaluable if evaluable else None,'unsupported_cell_rate':None,'human_semantic_gold':0,'errors':errors}
