"""R2 schemas constrain representation only; no reference values enter schemas."""
from contracts import columns_for

def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def string():return {'type':'string'}
def arr(item,minimum=0,maximum=512):return {'type':'array','items':item,'minItems':minimum,'maxItems':maximum}
def enum(*values):return {'type':'string','enum':list(values)}
def plan_schema():
    leaf=obj({'predicate':string(),'operator':enum('eq','lt','le','gt','ge'),'value':{'anyOf':[string(),{'type':'number'}]}})
    condition=leaf
    for _ in range(4):condition={'anyOf':[leaf,obj({'op':enum('and','or'),'conditions':arr(condition,0,16)})]}
    core=obj({'version':enum('r2'),'entity_type':string(),'predicates':arr(obj({'name':string(),'kind':enum('text','number'),'cardinality':enum('one','many')}),1,16),'outputs':arr(obj({'predicate':string(),'column':string()}),1,12),'filter':condition})
    # Span offsets are Unicode codepoints. Every non-whitespace question character is accounted for.
    unit=obj({'start':{'type':'integer'},'end':{'type':'integer'},'text':string(),'kind':enum('entity_scope','output','condition','logic','syntax'),'target':string()})
    relation=obj({'predicate':string(),'subject_role':enum('answer_entity'),'object_role':enum('value')})
    return obj({'query':core,'question_units':arr(unit,1,128),'relations':arr(relation,1,16),'unresolved':arr(string(),0,32)})
def table_schema(plan):
    columns=columns_for(plan);width=len(columns)
    cell={'anyOf':[{'type':'string'},{'type':'number'},{'type':'null'}]}
    # Tuple schemas pin column names and order. Rows have an exact width, validated again post-generation.
    return obj({'columns':{'type':'array','prefixItems':[enum(c) for c in columns],'items':False,'minItems':width,'maxItems':width},'rows':arr({'type':'array','items':cell,'minItems':width,'maxItems':width})})
def facts_schema(plan,units):
    variants=[]
    for p in plan['predicates']:
        variants.append(obj({'subject':string(),'entity_type':enum(plan['entity_type']),'predicate':enum(p['name']),'value':{'type':'number'} if p['kind']=='number' else string(),'evidence_id':enum(*(u['evidence_id'] for u in units)),'quote':string()}))
    return obj({'facts':arr({'anyOf':variants})})
def validate_schema(value,schema):
    from jsonschema import Draft202012Validator
    return [{'path':'/'+('/'.join(map(str,e.absolute_path))),'reason':e.message} for e in Draft202012Validator(schema).iter_errors(value)]
def compile_regex(schema):
    # Same outlines-core revision pinned by the existing server environment; CPU only.
    from outlines_core.fsm.json_schema import build_regex_from_schema
    import json
    return build_regex_from_schema(json.dumps(schema))
