"""Mechanical Unicode-character locations, not entailment or semantic judgment."""
def locate(unit,quote):
 if not isinstance(quote,str) or not quote:return []
 out=[]
 def walk(x,pointer):
  if isinstance(x,str):
   start=0
   while True:
    i=x.find(quote,start)
    if i<0:break
    out.append({'json_pointer':pointer,'start_char':i,'end_char':i+len(quote),'coordinate':'Python Unicode code points, end exclusive'});start=i+1
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,pointer+'/'+str(i))
  elif isinstance(x,dict):
   for k,v in x.items():
    if k not in ('found_in_url','proof_type'):walk(v,pointer+'/'+k.replace('~','~0').replace('/','~1'))
 walk(unit['source'],'/source');return out
