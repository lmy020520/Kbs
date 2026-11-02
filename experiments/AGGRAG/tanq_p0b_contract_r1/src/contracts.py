"""R1 strict, total validators. No repair, coercion, model or reference access."""
import json,math,unicodedata,re

def norm(value):
    return ' '.join(unicodedata.normalize('NFKC',value).replace('_',' ').casefold().split())

def parse_json(text):
    if not isinstance(text,str):return {'status':'JSON_INVALID','reason':'RESPONSE_NOT_STRING','raw':text}
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('DUPLICATE_JSON_KEY')
            out[k]=v
        return out
    def constant(_):raise ValueError('NONFINITE_JSON_NUMBER')
    try:return {'status':'JSON_VALID','value':json.loads(text,object_pairs_hook=pairs,parse_constant=constant)}
    except (ValueError,RecursionError) as e:return {'status':'JSON_INVALID','reason':str(e),'raw':text}

def text(x):return isinstance(x,str) and bool(x.strip()) and len(x)<=200 and not any(c in x for c in '\n\r|')
def number(x):
    if not isinstance(x,(int,float)) or isinstance(x,bool):return False
    if isinstance(x,int) and abs(x)>2**53:return False
    return math.isfinite(x)
RESERVED={'facts','relation facts','sql','subject','subject key','predicate','predicate key','object','object key','evidence id','numeric value','filter','attribute','value','entity type','entity type key','raw index'}

def validate_plan(obj):
    errors=[]
    def err(path,code):errors.append({'path':path,'reason':code})
    if not isinstance(obj,dict):return {'status':'PLAN_INVALID','errors':[{'path':'','reason':'PLAN_ROOT_MUST_BE_OBJECT'}],'raw':obj}
    if set(obj)!={'version','entity_type','predicates','outputs','filter'}:err('','PLAN_KEYS_INVALID_RAW_SQL_NOT_ALLOWED')
    if obj.get('version')!='r1':err('version','VERSION_MUST_BE_r1')
    if not text(obj.get('entity_type')) or norm(obj.get('entity_type','')) in RESERVED:err('entity_type','ENTITY_TYPE_REQUIRED_NOT_STORAGE_COLUMN')
    catalog={};preds=obj.get('predicates')
    if not isinstance(preds,list) or not 1<=len(preds)<=16:err('predicates','REQUIRE_1_TO_16_PREDICATES')
    else:
        for i,p in enumerate(preds):
            path=f'predicates/{i}'
            if not isinstance(p,dict) or set(p)!={'name','kind','cardinality'}:err(path,'PREDICATE_SHAPE_INVALID');continue
            if not text(p['name']) or norm(p['name']) in RESERVED:err(path,'PREDICATE_IS_INVALID_OR_STORAGE_COLUMN');continue
            if p['kind'] not in ('text','number') or p['cardinality'] not in ('one','many'):err(path,'PREDICATE_TYPE_OR_CARDINALITY_INVALID');continue
            key=norm(p['name'])
            if key in catalog:err(path,'DUPLICATE_PREDICATE')
            catalog[key]=p
    outputs=obj.get('outputs');seen=set()
    if not isinstance(outputs,list) or not 1<=len(outputs)<=12:err('outputs','REQUIRE_1_TO_12_OUTPUT_ATTRIBUTES')
    else:
        for i,p in enumerate(outputs):
            path=f'outputs/{i}'
            if not isinstance(p,dict) or set(p)!={'predicate','column'} or not text(p.get('predicate')) or not text(p.get('column')):err(path,'OUTPUT_SHAPE_INVALID');continue
            key=norm(p['predicate'])
            if key not in catalog:err(path,'UNDECLARED_OUTPUT_PREDICATE')
            if norm(p['column'])!=key or norm(p['column'])=='entity':err(path,'COLUMN_MUST_NAME_PUBLIC_PLAN_PREDICATE_NOT_GENERIC_PLACEHOLDER')
            if key in seen:err(path,'DUPLICATE_OUTPUT_ATTRIBUTE')
            seen.add(key)
    nodes=[0]
    def condition(c,path,depth):
        nodes[0]+=1
        if nodes[0]>64 or depth>4:err(path,'FILTER_COMPLEXITY_LIMIT');return
        if not isinstance(c,dict):err(path,'CONDITION_MUST_BE_OBJECT');return
        if 'conditions' in c:
            if set(c)!={'op','conditions'} or c.get('op') not in ('and','or') or not isinstance(c.get('conditions'),list):err(path,'LOGICAL_GROUP_INVALID');return
            if len(c['conditions'])>16 or (c['op']=='or' and not c['conditions']):err(path,'INVALID_CONDITION_COUNT');return
            for i,child in enumerate(c['conditions']):condition(child,path+'/'+str(i),depth+1)
        else:
            if set(c)!={'predicate','operator','value'} or not text(c.get('predicate')):err(path,'LEAF_SHAPE_INVALID');return
            p=catalog.get(norm(c['predicate']))
            if p is None:err(path,'UNDECLARED_FILTER_PREDICATE');return
            op=c['operator'];v=c['value']
            if p['kind']=='text':
                if op!='eq' or not text(v):err(path,'TEXT_FILTER_REQUIRES_EQ_STRING')
            elif op not in ('eq','lt','le','gt','ge') or not number(v) or p['cardinality']!='one':err(path,'NUMERIC_FILTER_REQUIRES_FINITE_NUMBER_SINGLE_VALUE')
    condition(obj.get('filter'),'filter',0)
    return {'status':'PLAN_INVALID' if errors else 'PLAN_VALID_STRUCTURAL','errors':errors,'raw':obj,'semantic_equivalence_to_question':'UNVERIFIED'}

def columns_for(plan):return ['entity']+[o['column'] for o in plan['outputs']]

def validate_table(obj,plan):
    if validate_plan(plan)['status']!='PLAN_VALID_STRUCTURAL':return {'status':'PLAN_INVALID','errors':[{'reason':'TABLE_REQUIRES_VALID_PLAN'}],'raw':obj}
    errors=[]
    if not isinstance(obj,dict):return {'status':'TABLE_INVALID','errors':[{'reason':'TABLE_ROOT_MUST_BE_OBJECT'}],'raw':obj}
    if set(obj)!={'columns','rows'}:errors.append({'reason':'TABLE_KEYS_INVALID'})
    cols=obj.get('columns');rows=obj.get('rows');expected=columns_for(plan)
    if not isinstance(cols,list) or cols!=expected:
        errors.append({'reason':'LONG_FORM_INSTEAD_OF_WIDE' if cols==['entity','attribute','value'] else 'COLUMNS_DIFFER_FROM_QUESTION_ONLY_PLAN','expected':expected})
    if not isinstance(rows,list):errors.append({'reason':'ROWS_MUST_BE_LIST'})
    else:
        seen={}
        for i,row in enumerate(rows):
            if not isinstance(row,list) or len(row)!=len(expected):errors.append({'row':i,'reason':'RAGGED_ROW'});continue
            if not text(row[0]):errors.append({'row':i,'reason':'ENTITY_LABEL_INVALID'});continue
            key=norm(row[0])
            if key in seen:errors.append({'row':i,'previous_row':seen[key],'reason':'DUPLICATE_NORMALIZED_ENTITY'})
            seen[key]=i
            for j,cell in enumerate(row[1:],1):
                if cell is None:continue
                if isinstance(cell,str) and len(cell)<=2000 and not any(c in cell for c in '\r\n|'):continue
                if number(cell):continue
                errors.append({'row':i,'column':j,'reason':'CELL_MUST_BE_SINGLE_LINE_STRING_FINITE_NUMBER_OR_NULL'})
    return {'status':'TABLE_INVALID' if errors else 'TABLE_VALID','errors':errors,'raw':obj,'missing_cells':sum(v is None or v=='' for r in rows if isinstance(r,list) for v in r[1:]) if isinstance(rows,list) else None}

def render_table(obj,plan):
    valid=validate_table(obj,plan)
    if valid['status']!='TABLE_VALID':return valid
    def scalar(x):return '' if x is None else str(x)
    return {'status':'RENDERED','text':'\n'.join(' | '.join(map(scalar,row)) for row in [obj['columns']]+obj['rows']),'validation':valid}
